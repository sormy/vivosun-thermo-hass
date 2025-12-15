"""Test fixtures for vivosun_thermo integration."""

import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Mock pycares for python 3.13 (works fine as is on 3.14)
pycares = types.ModuleType("pycares")
pycares.ares_query_a_result = object  # type: ignore
pycares.ares_query_aaaa_result = object  # type: ignore
pycares.ares_query_cname_result = object  # type: ignore
pycares.ares_query_mx_result = object  # type: ignore
pycares.ares_query_ns_result = object  # type: ignore
pycares.ares_query_ptr_result = object  # type: ignore
pycares.ares_query_srv_result = object  # type: ignore
pycares.ares_query_txt_result = object  # type: ignore
sys.modules["pycares"] = pycares


# Mock DataUpdateCoordinator to avoid event loop issues
class MockDataUpdateCoordinator:
    """Mock DataUpdateCoordinator that doesn't require event loop."""

    def __init__(self, hass, logger, *, name, update_interval, update_method):
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_interval = update_interval
        self._update_method = update_method
        self.data = {}

    async def async_config_entry_first_refresh(self):
        """Mock first refresh."""
        self.data = await self._update_method()

    async def async_refresh(self):
        """Mock refresh."""
        self.data = await self._update_method()


# Mock hardware-specific modules before HA imports them
serial_mock = Mock()
serial_tools_mock = Mock()
serial_tools_mock.__path__ = []  # Make it a package
sys.modules["serial"] = serial_mock
sys.modules["serial.tools"] = serial_tools_mock
sys.modules["serial.tools.list_ports"] = Mock()
sys.modules["serial.tools.list_ports_common"] = Mock()
sys.modules["aiousbwatcher"] = Mock()
sys.modules["usb_devices"] = Mock()

# Mock HA helpers modules
update_coordinator_mock = Mock()
update_coordinator_mock.DataUpdateCoordinator = MockDataUpdateCoordinator
update_coordinator_mock.CoordinatorEntity = type(
    "CoordinatorEntity",
    (),
    {"__init__": lambda self, coordinator: setattr(self, "coordinator", coordinator)},
)
sys.modules["homeassistant.helpers.update_coordinator"] = update_coordinator_mock
sys.modules["homeassistant.helpers.frame"] = Mock()


# Mock BluetoothServiceInfoBleak to avoid importing HA internals
class BluetoothServiceInfoBleak:
    """Mock BluetoothServiceInfoBleak."""

    def __init__(
        self, name, address, rssi, manufacturer_data, service_data, service_uuids, source, **kwargs
    ):
        self.name = name
        self.address = address
        self.rssi = rssi
        self.manufacturer_data = manufacturer_data
        self.service_data = service_data
        self.service_uuids = service_uuids
        self.source = source
        # Store any additional kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)


# Add src directory to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from custom_components.vivosun_thermo.const import ConfigEntryData  # noqa: E402


@pytest.fixture
def mock_bleak_client():
    """Mock BleakClient."""
    with patch("custom_components.vivosun_thermo.coordinator.BleakClient") as mock:
        client = MagicMock()
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        client.start_notify = AsyncMock()
        client.stop_notify = AsyncMock()
        client.write_gatt_char = AsyncMock()
        mock.return_value = client
        yield client


@pytest.fixture
def mock_discovery_info():
    """Mock Bluetooth discovery info."""
    return BluetoothServiceInfoBleak(
        name="ThermoBeacon2",
        address="AA:BB:CC:DD:EE:FF",
        rssi=-60,
        manufacturer_data={},
        service_data={},
        service_uuids=[],
        source="local",
    )


@pytest.fixture
def config_entry_data():
    """Mock config entry data."""
    return ConfigEntryData(
        name="VIVOSUN AeroLab THB1S",
        discovery_name="ThermoBeacon2",
        discovery_address="AA:BB:CC:DD:EE:FF",
    )


@pytest.fixture
def mock_config_entry(config_entry_data):
    """Mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.data = config_entry_data
    entry.title = "VIVOSUN AeroLab THB1S"
    return entry


@pytest.fixture
def valid_sensor_data_both_probes():
    """Valid sensor data with both main and external probes."""
    # Format: Little-endian int16, divide by 16 for actual value
    # Main temp: 22.5°C (360/16), humidity: 65.0% (1040/16)
    # External temp: 18.0°C (288/16), humidity: 70.0% (1120/16)
    return bytearray(
        [
            0x00,  # 0: Unknown
            0x68,
            0x01,  # 1-2: Main temp = 360 (22.5°C)
            0x10,
            0x04,  # 3-4: Main humidity = 1040 (65.0%)
            0x00,
            0x00,  # 5-6: Unknown
            0x20,
            0x01,  # 7-8: External temp = 288 (18.0°C)
            0x60,
            0x04,  # 9-10: External humidity = 1120 (70.0%)
        ]
    )


@pytest.fixture
def valid_sensor_data_main_only():
    """Valid sensor data with main probe only."""
    return bytearray(
        [
            0x00,  # 0: Unknown
            0x68,
            0x01,  # 1-2: Main temp = 360 (22.5°C)
            0x10,
            0x04,  # 3-4: Main humidity = 1040 (65.0%)
            0x00,
            0x00,  # 5-6: Unknown
            0xFF,
            0xFF,  # 7-8: External temp = -1 (not connected)
            0xFF,
            0xFF,  # 9-10: External humidity = -1 (not connected)
        ]
    )


@pytest.fixture
def hass():
    """Create mock Home Assistant instance."""
    hass = MagicMock()
    hass.data = {}
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    return hass
