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
make setup
```

`make setup` creates `.venv`, installs both requirement files, and writes the
`.env` that VS Code reads.

| Target            | What it does                                          |
| ----------------- | ----------------------------------------------------- |
| `make format`     | Rewrites `src` and `tests` with black and isort        |
| `make lint`       | black, flake8, pyright and isort in check-only mode    |
| `make test`       | pytest on the current interpreter                     |
| `make test-cov`   | pytest with an HTML coverage report in `coverage/`     |
| `make tox`        | The full suite on every interpreter in `tox.ini`       |
| `make prepublish` | `lint` and `tox` together — the gate CI enforces       |

CI runs `make setup`, `make lint`, then tox, so `make prepublish` is the same
gate on your machine.

## Releasing

The version appears in both `manifest.json` and `pyproject.toml`, and a test
fails if they disagree.

1. Bump `version` in `src/custom_components/vivosun_thermo/manifest.json` and
   in `pyproject.toml` to the same value.
2. Run `make prepublish`. This must pass on every supported interpreter before
   anything is tagged.
3. Commit the bump, then tag it and push both:

    ```sh
    git tag 1.0.2
    git push origin main --tags
    ```

4. Publish a GitHub release for that tag. Home Assistant reads the version from
   `manifest.json`, so the tag and that field must match.

## License

This project is licensed under the **MIT License**. See the `LICENSE` file for details.
