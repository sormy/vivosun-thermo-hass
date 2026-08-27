# VIVOSUN Thermo component for Home Assistant

VIVOSUN Thermo component for Home Assistant has these features:

-   Scan for nearby devices and add them into Home Assistant automatically with prompt.
-   Read the current temperature, humidity from your deviceand and compute VPD.
-   Supports both probes - main and external.

## Supported Devices

-   **VS-THB1S**: VIVOSUN AeroLab Hygrometer Thermometer

## Installation

### HACS

Add `https://github.com/sormy/vivosun-thermo-hass` as a custom repository of type
`Integration`, then download **VIVOSUN Thermo** and restart Home Assistant.

### Manual

`/config` is the Home Assistant configuration directory. The clone goes to a
temporary directory and is deleted afterwards, so the only thing left under
`custom_components` is the integration itself.

```sh
git clone --depth 1 https://github.com/sormy/vivosun-thermo-hass /tmp/vivosun-thermo-hass
mkdir -p /config/custom_components
rm -rf /config/custom_components/vivosun_thermo
cp -r /tmp/vivosun-thermo-hass/custom_components/vivosun_thermo /config/custom_components/
rm -rf /tmp/vivosun-thermo-hass
ha core restart
```

Append `--branch <version>` to the clone to install a specific release rather
than the default branch.

### Adding the device

1. Navigate to Devices and Services.
2. Enable pairing mode on the device.
3. Home Assistant prompts to add it; proceed with the prompt.

## Updating

HACS offers the update itself. A manual install updates by running the command
above again — it replaces the integration in place.

## Development

```sh
brew install python
make setup
```

`make setup` creates `.venv`, installs both requirement files, and writes the
`.env` that VS Code reads.

| Target            | What it does                                          |
| ----------------- | ----------------------------------------------------- |
| `make format`     | Rewrites `custom_components` and `tests` with black and isort |
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

1. Bump `version` in `custom_components/vivosun_thermo/manifest.json` and
   in `pyproject.toml` to the same value.
2. Run `make prepublish`. This must pass on every supported interpreter before
   anything is tagged.
3. Commit the bump, then tag it and push both:

    ```sh
    git tag 1.0.2
    git push origin main --tags
    ```

4. Publish a GitHub release for that tag. HACS reads the tag name of the latest
   **release** — a pushed tag on its own is invisible to it — and Home Assistant
   reads `manifest.json`, so the tag and that field must match.

## License

This project is licensed under the **MIT License**. See the `LICENSE` file for details.
