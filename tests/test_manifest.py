"""The integration manifest must agree with the packaging metadata beside it."""

import json
import tomllib
from pathlib import Path

import pytest

from custom_components.vivosun_thermo.const import DOMAIN

_ROOT = Path(__file__).parent.parent
_MANIFEST = _ROOT / "src" / "custom_components" / "vivosun_thermo" / "manifest.json"
_PYPROJECT = _ROOT / "pyproject.toml"


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(_MANIFEST.read_text())


@pytest.fixture(scope="module")
def pyproject() -> dict:
    return tomllib.loads(_PYPROJECT.read_text())


class TestManifest:
    """Release metadata is spread over two files and read by different tools."""

    def test_version_matches_pyproject(self, manifest, pyproject):
        """A release bumped in one file and not the other ships the wrong version."""
        assert manifest["version"] == pyproject["project"]["version"]

    def test_domain_matches_constant(self, manifest):
        """HA resolves the integration by directory and manifest domain, not by DOMAIN."""
        assert manifest["domain"] == DOMAIN
        assert _MANIFEST.parent.name == DOMAIN

    def test_declares_what_it_imports(self, manifest):
        """bleak-retry-connector is imported directly, so HA has to install it."""
        assert any(r.startswith("bleak-retry-connector") for r in manifest["requirements"])

    def test_keys_home_assistant_requires(self, manifest):
        """A missing key here fails at integration load, not at test time."""
        for key in ("domain", "name", "version", "documentation", "codeowners", "iot_class"):
            assert manifest.get(key), f"manifest.json is missing {key}"
