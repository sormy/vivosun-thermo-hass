from asyncio import Future, timeout, wait_for
from contextlib import suppress
from logging import getLogger
from struct import unpack_from
from typing import Final, TypedDict, cast

from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, ConfigEntryData

_LOGGER = getLogger(__name__)

_BLE_SENSOR_COMMAND = bytearray([0x0D])

_BLE_COMMAND_UUID: Final = "0000fff5-0000-1000-8000-00805f9b34fb"
_BLE_STATUS_UUID: Final = "0000fff3-0000-1000-8000-00805f9b34fb"

_BLE_READ_TIMEOUT: Final = 1
_BLE_CONNECT_TIMEOUT: Final = 30
_BLE_CONNECT_ATTEMPTS: Final = 3

_MAIN_TEMP_OFFSET: Final = 1
_MAIN_HUMIDITY_OFFSET: Final = 3
_EXTERNAL_TEMP_OFFSET: Final = 7
_EXTERNAL_HUMIDITY_OFFSET: Final = 9

_VALUE_NONE: Final = -1

# The external humidity reading sits last, so its int16 closes the shortest usable frame.
_BLE_PAYLOAD_MIN_SIZE: Final = _EXTERNAL_HUMIDITY_OFFSET + 2

# The device also broadcasts both probes in its manufacturer data, so a poll can be answered
# without connecting. Payload (after the 2-byte company id): MAC reversed (6), an unknown uint16,
# main temperature, main humidity, external temperature, external humidity (int16 / 16 each),
# then a uint32 that counts seconds since power-up. 0x0019 is the regular advertisement; 0x8019
# shows up after a button press, and Home Assistant keeps the last one of each, so the newer
# counter wins.
_ADV_MANUFACTURER_IDS: Final = (0x0019, 0x8019)
_ADV_MAIN_TEMP_OFFSET: Final = 8
_ADV_MAIN_HUMIDITY_OFFSET: Final = 10
_ADV_EXTERNAL_TEMP_OFFSET: Final = 12
_ADV_EXTERNAL_HUMIDITY_OFFSET: Final = 14
_ADV_COUNTER_OFFSET: Final = 16
_ADV_PAYLOAD_MIN_SIZE: Final = _ADV_COUNTER_OFFSET + 4


class ProbeData(TypedDict):
    temperature_c: float
    humidity: float
    vpd: float


class SensorData(TypedDict):
    main: ProbeData
    external: ProbeData | None


class VivosunThermoSensorCoordinator(DataUpdateCoordinator[SensorData]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        data = cast(ConfigEntryData, entry.data)
        super().__init__(
            hass,
            _LOGGER,
            name=data["name"],
            config_entry=entry,
            update_interval=DEFAULT_SCAN_INTERVAL,
            update_method=self._read_sensor_data,
        )
        self.discovery_name = data["discovery_name"]
        self.discovery_address = data["discovery_address"]
        self._last_adv_counter: int | None = None

    async def _read_sensor_data(self) -> SensorData:
        # Prefer the broadcast: it needs no connection, which some proxies cannot make to this
        # device (ESP32-C6 boards get "connection failed to be established", 0x3e).
        advertised = self._read_advertisement()
        if advertised is not None:
            return advertised
        client = await self._connect()
        try:
            data = await self._read_raw_data(client)
        except BleakError as err:
            raise UpdateFailed(f"Failed to read {self.discovery_address}: {err}") from err
        finally:
            # Teardown must never discard a good reading or mask the failure that caused it.
            with suppress(Exception):
                await client.disconnect()
        if len(data) < _BLE_PAYLOAD_MIN_SIZE:
            raise UpdateFailed(
                f"{self.discovery_address} sent {len(data)} bytes," f" need {_BLE_PAYLOAD_MIN_SIZE}"
            )
        return self._decode_raw_data(data)

    def _read_advertisement(self) -> SensorData | None:
        if not bluetooth.async_address_present(
            self.hass, self.discovery_address, connectable=False
        ):
            return None
        info = bluetooth.async_last_service_info(
            self.hass, self.discovery_address, connectable=False
        )
        if info is None:
            return None
        newest: tuple[int, bytes] | None = None
        for manufacturer_id in _ADV_MANUFACTURER_IDS:
            payload = info.manufacturer_data.get(manufacturer_id)
            if payload is None or len(payload) < _ADV_PAYLOAD_MIN_SIZE:
                continue
            counter = unpack_from("<I", payload, _ADV_COUNTER_OFFSET)[0]
            if newest is None or counter > newest[0]:
                newest = (counter, payload)
        if newest is None:
            return None
        counter, payload = newest
        # An unchanged counter means nothing new was heard since the last poll; let the
        # connection path try rather than repeat an old reading.
        if counter == self._last_adv_counter:
            return None
        self._last_adv_counter = counter
        return self._decode_frame(
            bytearray(payload),
            _ADV_MAIN_TEMP_OFFSET,
            _ADV_MAIN_HUMIDITY_OFFSET,
            _ADV_EXTERNAL_TEMP_OFFSET,
            _ADV_EXTERNAL_HUMIDITY_OFFSET,
        )

    def _resolve_device(self) -> BLEDevice:
        device = bluetooth.async_ble_device_from_address(
            self.hass, self.discovery_address, connectable=True
        )
        if device is None:
            raise UpdateFailed(f"Device {self.discovery_address} is not in range")
        return device

    async def _connect(self) -> BleakClientWithServiceCache:
        # Resolve the device every poll so Home Assistant routes through whichever adapter or
        # ESPHome proxy currently sees it. establish_connection ignores a timeout kwarg (it forces
        # its own on connect), so the caller-visible bound has to be applied out here.
        device = self._resolve_device()
        try:
            async with timeout(_BLE_CONNECT_TIMEOUT):
                return await establish_connection(
                    BleakClientWithServiceCache,
                    device,
                    self.discovery_name,
                    max_attempts=_BLE_CONNECT_ATTEMPTS,
                )
        except (BleakError, TimeoutError) as err:
            raise UpdateFailed(f"Failed to connect to {self.discovery_address}: {err}") from err

    @staticmethod
    async def _read_raw_data(client: BleakClientWithServiceCache) -> bytearray:
        future: Future[bytearray] = Future()

        def on_status(_: object, data: bytearray) -> None:
            # The device may send more than one frame; the first is the answer.
            if not future.done():
                future.set_result(data)

        await client.start_notify(_BLE_STATUS_UUID, on_status)
        await client.write_gatt_char(_BLE_COMMAND_UUID, _BLE_SENSOR_COMMAND)
        data = await wait_for(future, _BLE_READ_TIMEOUT)
        await client.stop_notify(_BLE_STATUS_UUID)
        return data

    @staticmethod
    def _decode_int16(data: bytearray, offset: int) -> int:
        return unpack_from("<h", data, offset)[0]

    @classmethod
    def _decode_float(cls, data: bytearray, offset: int) -> float:
        return cls._decode_int16(data, offset) / 16

    @staticmethod
    def _calculate_vpd(temp_c: float, humidity: float) -> float:
        # Calculate saturation vapor pressure (in kPa)
        svp = 0.61078 * 10 ** ((7.5 * temp_c) / (237.3 + temp_c))
        # Calculate actual vapor pressure (in kPa)
        avp = svp * (humidity / 100.0)
        # VPD is the difference
        return svp - avp

    @classmethod
    def _decode_probe_data(
        cls, data: bytearray, temp_offset: int, humidity_offset: int
    ) -> ProbeData:
        temp_c = cls._decode_float(data, temp_offset)
        humidity = cls._decode_float(data, humidity_offset)
        vpd = cls._calculate_vpd(temp_c, humidity)
        return ProbeData(temperature_c=temp_c, humidity=humidity, vpd=vpd)

    @classmethod
    def _decode_raw_data(cls, data: bytearray) -> SensorData:
        return cls._decode_frame(
            data,
            _MAIN_TEMP_OFFSET,
            _MAIN_HUMIDITY_OFFSET,
            _EXTERNAL_TEMP_OFFSET,
            _EXTERNAL_HUMIDITY_OFFSET,
        )

    @classmethod
    def _decode_frame(
        cls,
        data: bytearray,
        main_temp_offset: int,
        main_humidity_offset: int,
        external_temp_offset: int,
        external_humidity_offset: int,
    ) -> SensorData:
        main_probe = cls._decode_probe_data(data, main_temp_offset, main_humidity_offset)
        external_probe_available = (
            cls._decode_int16(data, external_temp_offset) != _VALUE_NONE
            and cls._decode_int16(data, external_humidity_offset) != _VALUE_NONE
        )
        external_probe = (
            cls._decode_probe_data(data, external_temp_offset, external_humidity_offset)
            if external_probe_available
            else None
        )
        return SensorData(main=main_probe, external=external_probe)
