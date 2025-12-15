# VIVOSUN Thermo component for Home Assistant

VIVOSUN Thermo component for Home Assistant has these features:

-   Scan for nearby devices and add them into Home Assistant automatically with prompt.
-   Read the current temperature, humidity from your deviceand and compute VPD.
-   Supports both probes - main and external.

## Supported Devices

-   **VS-THB1S**: VIVOSUN AeroLab Hygrometer Thermometer

## Installation

1. Install component

Below `/config` is Home Assistant `config` directory:

```sh
cd /config
mkdir -pv /config/custom_components
cd /config/custom_components
git clone https://github.com/sormy/vivosun-thermo-hass
cp -rv vivosun-thermo-hass/src/custom_components/vivosun_thermo ./
```

2. Then restart Home Assistant. For example, `ha core restart` for HASS OS.
3. Navigate to Devices and Service
4. Home Assistant supposed to prompt for installation.
5. Enable pairing mode on device.
6. Proceed with installation in Home Assistant prompt.

## Updating

For example, HASS OS recipe for copy/paste:

```sh
cd /config/custom_components
cd vivosun-thermo-hass
git pull
cd -
rm -rf vivosun_thermo
cp -rv vivosun-thermo-hass/src/custom_components/vivosun_thermo ./
ha core restart
```

## Development

```sh
brew install python
make all
```

## License

This project is licensed under the **MIT License**. See the `LICENSE` file for details.
