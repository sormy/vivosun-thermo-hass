from asyncio import Future, wait_for
from logging import getLogger
from struct import unpack_from
from typing import Any, TypedDict, cast

from bleak import BleakClient

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    BLE_COMMAND_UUID,
    BLE_READ_TIMEOUT,
    BLE_SENSOR_COMMAND,
    BLE_STATUS_UUID,
    DEFAULT_SCAN_INTERVAL,
    EXTERNAL_HUMIDITY_OFFSET,
    EXTERNAL_TEMP_OFFSET,
    MAIN_HUMIDITY_OFFSET,
    MAIN_TEMP_OFFSET,
    VALUE_NONE,
)

_LOGGER = getLogger(__name__)


class ProbeData(TypedDict):
    temperature_c: float
    humidity: float
    vpd: float


class SensorData(TypedDict):
    main: ProbeData
    external: ProbeData | None


class VivosunThermoSensorCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, name: str, address: str):
        super().__init__(
            hass,
            _LOGGER,
            name=name,
            update_interval=DEFAULT_SCAN_INTERVAL,
            update_method=self._read_sensor_data,
        )
        self._client = BleakClient(address)

    async def _read_sensor_data(self) -> dict[str, Any]:
        data = await self._read_raw_data(self._client)
        return cast(dict, self._decode_raw_data(data))

    @staticmethod
    async def _read_raw_data(client: BleakClient) -> bytearray:
        async with client:
            future = Future()
            await client.start_notify(BLE_STATUS_UUID, lambda _, d: future.set_result(d))
            await client.write_gatt_char(BLE_COMMAND_UUID, BLE_SENSOR_COMMAND)
            data = await wait_for(future, BLE_READ_TIMEOUT)
            await client.stop_notify(BLE_STATUS_UUID)
            return data

    @staticmethod
    def _decode_int16(data: bytearray, offset: int) -> int:
        return unpack_from("<h", data, offset)[0]

    @staticmethod
    def _decode_float(data: bytearray, offset: int) -> float:
        return unpack_from("<h", data, offset)[0] / 16

    @staticmethod
    def _calculate_vpd(temp_c: float, humidity: float):
        return (610.78 * (10 ** ((7.5 * temp_c) / (237.3 + temp_c))) * humidity / 100) / 1000

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
        main_probe = cls._decode_probe_data(data, MAIN_TEMP_OFFSET, MAIN_HUMIDITY_OFFSET)
        external_probe_available = (
            cls._decode_int16(data, EXTERNAL_TEMP_OFFSET) != VALUE_NONE
            and cls._decode_int16(data, EXTERNAL_HUMIDITY_OFFSET) != VALUE_NONE
        )
        external_probe = (
            cls._decode_probe_data(data, EXTERNAL_TEMP_OFFSET, EXTERNAL_HUMIDITY_OFFSET)
            if external_probe_available
            else None
        )
        return SensorData(main=main_probe, external=external_probe)
