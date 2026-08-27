"""Tests for vivosun_thermo setup and teardown."""

from unittest.mock import AsyncMock

import pytest
from homeassistant.const import Platform

from custom_components.vivosun_thermo import async_setup_entry, async_unload_entry


class TestVivosunThermoSetup:
    """Test the config entry lifecycle."""

    async def test_setup_entry_publishes_coordinator(
        self, hass, mock_config_entry, mock_bleak_client, valid_sensor_data_both_probes
    ):
        """Setup polls once and leaves the coordinator on the entry for the platforms."""

        async def mock_notify(uuid, callback):
            callback(None, valid_sensor_data_both_probes)

        mock_bleak_client.start_notify = AsyncMock(side_effect=mock_notify)

        assert await async_setup_entry(hass, mock_config_entry) is True

        assert mock_config_entry.runtime_data.data["main"]["temperature_c"] == 22.5
        hass.config_entries.async_forward_entry_setups.assert_awaited_once_with(
            mock_config_entry, [Platform.SENSOR]
        )

    @pytest.mark.parametrize("unloaded", [True, False], ids=["unloaded", "still_loaded"])
    async def test_unload_entry_reports_platform_result(self, hass, mock_config_entry, unloaded):
        """Unload defers to the platform teardown and reports what it says."""
        hass.config_entries.async_unload_platforms = AsyncMock(return_value=unloaded)

        assert await async_unload_entry(hass, mock_config_entry) is unloaded

        hass.config_entries.async_unload_platforms.assert_awaited_once_with(
            mock_config_entry, [Platform.SENSOR]
        )
