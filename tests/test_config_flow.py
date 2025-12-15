"""Tests for vivosun_thermo config flow."""

from unittest.mock import MagicMock, patch

from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.const import ATTR_NAME

from custom_components.vivosun_thermo.config_flow import VivosunThermoConfigFlow

# pyright: reportTypedDictNotRequiredAccess=false


class TestVivosunThermoConfigFlow:
    """Test VivosunThermoConfigFlow."""

    async def test_flow_initialization(self):
        """Test config flow initializes correctly."""
        flow = VivosunThermoConfigFlow()
        assert flow.VERSION == 1

    async def test_bluetooth_discovery_sets_attributes(self):
        """Test bluetooth discovery sets flow attributes."""
        flow = VivosunThermoConfigFlow()
        flow.hass = MagicMock()
        flow.context = {}

        discovery_info = BluetoothServiceInfoBleak(
            name="ThermoBeacon2",
            address="AA:BB:CC:DD:EE:FF",
            rssi=-60,
            manufacturer_data={},
            service_data={},
            service_uuids=[],
            source="local",
            device=MagicMock(),
            advertisement=MagicMock(),
            connectable=True,
            time=0,
            tx_power=-127,
        )

        with patch.object(flow, "async_set_unique_id"):
            with patch.object(flow, "_abort_if_unique_id_configured"):
                with patch.object(flow, "async_show_form") as mock_show:
                    mock_show.return_value = {"type": "form"}
                    await flow.async_step_bluetooth(discovery_info)

                    assert flow.discovery_name == "ThermoBeacon2"
                    assert flow.discovery_address == "AA:BB:CC:DD:EE:FF"
                    assert flow.name == "VIVOSUN AeroLab THB1S"

    async def test_bluetooth_discovery_unknown_device(self):
        """Test bluetooth discovery with unknown device uses discovery name."""
        flow = VivosunThermoConfigFlow()
        flow.hass = MagicMock()
        flow.context = {}

        discovery_info = BluetoothServiceInfoBleak(
            name="UnknownDevice",
            address="AA:BB:CC:DD:EE:FF",
            rssi=-60,
            manufacturer_data={},
            service_data={},
            service_uuids=[],
            source="local",
            device=MagicMock(),
            advertisement=MagicMock(),
            connectable=True,
            time=0,
            tx_power=-127,
        )

        with patch.object(flow, "async_set_unique_id"):
            with patch.object(flow, "_abort_if_unique_id_configured"):
                with patch.object(flow, "async_show_form") as mock_show:
                    mock_show.return_value = {"type": "form"}
                    await flow.async_step_bluetooth(discovery_info)

                    assert flow.name == "UnknownDevice"

    async def test_bluetooth_discovery_sets_unique_id(self):
        """Test bluetooth discovery sets unique ID correctly."""
        flow = VivosunThermoConfigFlow()
        flow.hass = MagicMock()
        flow.context = {}

        discovery_info = BluetoothServiceInfoBleak(
            name="ThermoBeacon2",
            address="AA:BB:CC:DD:EE:11",
            rssi=-60,
            manufacturer_data={},
            service_data={},
            service_uuids=[],
            source="local",
            device=MagicMock(),
            advertisement=MagicMock(),
            connectable=True,
            time=0,
            tx_power=-127,
        )

        with patch.object(flow, "async_set_unique_id") as mock_set_id:
            with patch.object(flow, "_abort_if_unique_id_configured"):
                with patch.object(flow, "async_show_form") as mock_show:
                    mock_show.return_value = {"type": "form"}
                    await flow.async_step_bluetooth(discovery_info)

                    mock_set_id.assert_called_once_with("ThermoBeacon2-AA:BB:CC:DD:EE:11")

    async def test_confirm_creates_entry(self):
        """Test confirm step creates config entry."""
        flow = VivosunThermoConfigFlow()
        flow.hass = MagicMock()
        flow.name = "VIVOSUN AeroLab THB1S"
        flow.discovery_name = "ThermoBeacon2"
        flow.discovery_address = "AA:BB:CC:DD:EE:FF"

        result = await flow.async_step_confirm(user_input={ATTR_NAME: "VIVOSUN AeroLab THB1S"})

        assert result["type"] == "create_entry"
        assert result["title"] == "VIVOSUN AeroLab THB1S"
        assert result["data"]["name"] == "VIVOSUN AeroLab THB1S"
        assert result["data"]["discovery_name"] == "ThermoBeacon2"
        assert result["data"]["discovery_address"] == "AA:BB:CC:DD:EE:FF"

    async def test_confirm_custom_name(self):
        """Test confirm step with custom name."""
        flow = VivosunThermoConfigFlow()
        flow.hass = MagicMock()
        flow.name = "VIVOSUN AeroLab THB1S"
        flow.discovery_name = "ThermoBeacon2"
        flow.discovery_address = "AA:BB:CC:DD:EE:FF"

        result = await flow.async_step_confirm(user_input={ATTR_NAME: "My Custom Name"})

        assert result["type"] == "create_entry"
        assert result["title"] == "My Custom Name"
        assert result["data"]["name"] == "My Custom Name"

    async def test_confirm_shows_form_when_no_input(self):
        """Test confirm step shows form when user_input is None."""
        flow = VivosunThermoConfigFlow()
        flow.hass = MagicMock()
        flow.name = "VIVOSUN AeroLab THB1S"

        result = await flow.async_step_confirm(user_input=None)

        assert result["type"] == "form"
        assert result["step_id"] == "confirm"

    async def test_user_step_not_supported(self):
        """Test manual user setup is not supported."""
        flow = VivosunThermoConfigFlow()
        flow.hass = MagicMock()

        result = await flow.async_step_user(user_input=None)

        assert result["type"] == "abort"
        assert result["reason"] == "not_supported"

    async def test_title_placeholders_set(self):
        """Test title placeholders are set in context."""
        flow = VivosunThermoConfigFlow()
        flow.hass = MagicMock()
        flow.context = {}

        discovery_info = BluetoothServiceInfoBleak(
            name="ThermoBeacon2",
            address="AA:BB:CC:DD:EE:FF",
            rssi=-60,
            manufacturer_data={},
            service_data={},
            service_uuids=[],
            source="local",
            device=MagicMock(),
            advertisement=MagicMock(),
            connectable=True,
            time=0,
            tx_power=-127,
        )

        with patch.object(flow, "async_set_unique_id"):
            with patch.object(flow, "_abort_if_unique_id_configured"):
                with patch.object(flow, "async_show_form") as mock_show:
                    mock_show.return_value = {"type": "form"}
                    await flow.async_step_bluetooth(discovery_info)

                    assert ATTR_NAME in flow.context["title_placeholders"]
                    assert flow.context["title_placeholders"][ATTR_NAME] == "VIVOSUN AeroLab THB1S"

    async def test_multiple_devices_unique_ids(self):
        """Test multiple devices get different unique IDs."""
        flow1 = VivosunThermoConfigFlow()
        flow1.hass = MagicMock()
        flow1.context = {}

        discovery1 = BluetoothServiceInfoBleak(
            name="ThermoBeacon2",
            address="AA:BB:CC:DD:EE:01",
            rssi=-60,
            manufacturer_data={},
            service_data={},
            service_uuids=[],
            source="local",
            device=MagicMock(),
            advertisement=MagicMock(),
            connectable=True,
            time=0,
            tx_power=-127,
        )

        flow2 = VivosunThermoConfigFlow()
        flow2.hass = MagicMock()
        flow2.context = {}

        discovery2 = BluetoothServiceInfoBleak(
            name="ThermoBeacon2",
            address="AA:BB:CC:DD:EE:02",
            rssi=-60,
            manufacturer_data={},
            service_data={},
            service_uuids=[],
            source="local",
            device=MagicMock(),
            advertisement=MagicMock(),
            connectable=True,
            time=0,
            tx_power=-127,
        )

        with patch.object(flow1, "async_set_unique_id") as mock_set_id1:
            with patch.object(flow1, "_abort_if_unique_id_configured"):
                with patch.object(flow1, "async_show_form"):
                    await flow1.async_step_bluetooth(discovery1)

        with patch.object(flow2, "async_set_unique_id") as mock_set_id2:
            with patch.object(flow2, "_abort_if_unique_id_configured"):
                with patch.object(flow2, "async_show_form"):
                    await flow2.async_step_bluetooth(discovery2)

        # Verify different unique IDs
        mock_set_id1.assert_called_once_with("ThermoBeacon2-AA:BB:CC:DD:EE:01")
        mock_set_id2.assert_called_once_with("ThermoBeacon2-AA:BB:CC:DD:EE:02")
