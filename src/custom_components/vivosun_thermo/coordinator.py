from asyncio import Future, wait_for
from logging import getLogger
from struct import unpack_from
from typing import Any, Final, TypedDict, cast

from bleak.backends.device import BLEDevice
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, ConfigEntryData

_LOGGER = getLogger(__name__)

_BLE_SENSOR_COMMAND = bytearray([0x0D])

_BLE_COMMAND_UUID: Final = "0000fff5-0000-1000-8000-00805f9b34fb"
_BLE_STATUS_UUID: Final = "0000fff3-0000-1000-8000-00805f9b34fb"

_BLE_READ_TIMEOUT: Final = 1
_BLE_CONNECT_TIMEOUT: Final = 30
_BLE_CONNECT_MAX_ATTEMPTS: Final = 3

_MAIN_TEMP_OFFSET: Final = 1
_MAIN_HUMIDITY_OFFSET: Final = 3
_EXTERNAL_TEMP_OFFSET: Final = 7
_EXTERNAL_HUMIDITY_OFFSET: Final = 9

_VALUE_NONE: Final = -1


class ProbeData(TypedDict):
    temperature_c: float
    humidity: float
    vpd: float


class SensorData(TypedDict):
    main: ProbeData
    external: ProbeData | None


class VivosunThermoSensorCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, data: ConfigEntryData):
        super().__init__(
            hass,
            _LOGGER,
            name=data["name"],
            update_interval=DEFAULT_SCAN_INTERVAL,
            update_method=self._read_sensor_data,
        )
        self.hass = hass
        self.discovery_name = data["discovery_name"]
        self.discovery_address = data["discovery_address"]

    async def _read_sensor_data(self) -> dict[str, Any]:
        # Resolve a fresh, routable BLEDevice each poll instead of holding a
        # single long-lived BleakClient built from a bare address string.
        # This lets HA pick whichever adapter/proxy can currently reach the
        # device, instead of always trying the same (possibly stale) route.
        ble_device = bluetooth.async_ble_device_from_address(
            self.hass, self.discovery_address, connectable=True
        )
        if ble_device is None:
            raise UpdateFailed(
                f"Could not find VIVOSUN device with address {self.discovery_address}"
            )
        data = await self._read_raw_data(ble_device)
        return cast(dict, self._decode_raw_data(data))

    @staticmethod
    async def _read_raw_data(ble_device: BLEDevice) -> bytearray:
        client = await establish_connection(
            BleakClientWithServiceCache,
            ble_device,
            ble_device.name or ble_device.address,
            max_attempts=_BLE_CONNECT_MAX_ATTEMPTS,
            timeout=_BLE_CONNECT_TIMEOUT,
        )
        try:
            future = Future()
            await client.start_notify(_BLE_STATUS_UUID, lambda _, d: future.set_result(d))
            await client.write_gatt_char(_BLE_COMMAND_UUID, _BLE_SENSOR_COMMAND)
            data = await wait_for(future, _BLE_READ_TIMEOUT)
            await client.stop_notify(_BLE_STATUS_UUID)
            return data
        finally:
            await client.disconnect()

    @staticmethod
    def _decode_int16(data: bytearray, offset: int) -> int:
        return unpack_from("<h", data, offset)[0]

    @staticmethod
    def _decode_float(data: bytearray, offset: int) -> float:
        return unpack_from("<h", data, offset)[0] / 16

    @staticmethod
    def _calculate_vpd(temp_c: float, humidity: float):
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
        main_probe = cls._decode_probe_data(data, _MAIN_TEMP_OFFSET, _MAIN_HUMIDITY_OFFSET)
        external_probe_available = (
            cls._decode_int16(data, _EXTERNAL_TEMP_OFFSET) != _VALUE_NONE
            and cls._decode_int16(data, _EXTERNAL_HUMIDITY_OFFSET) != _VALUE_NONE
        )
        external_probe = (
            cls._decode_probe_data(data, _EXTERNAL_TEMP_OFFSET, _EXTERNAL_HUMIDITY_OFFSET)
            if external_probe_available
            else None
        )
        return SensorData(main=main_probe, external=external_probe)
