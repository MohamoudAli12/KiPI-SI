"""plugin.json passes the checks KiCad makes when it loads the plugin, beyond its schema."""

import json
import re
from pathlib import Path

from kipi_si.launcher import appid

ROOT = Path(__file__).resolve().parents[2]

# KiCad's API_PLUGIN::IsValidIdentifier (KiCad 10): reverse-DNS, and no underscores. An
# identifier the schema accepts but this rejects makes KiCad skip the plugin silently
# ("identifier ... does not meet requirements" only under WXTRACE=KICAD_API).
KICAD_IDENTIFIER = re.compile(
    r"^[a-zA-Z]{2,}(\.([a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]|[a-zA-Z0-9])){2,}$")


def _manifest():
    return json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))


def test_kicad_accepts_the_plugin_identifier():
    assert KICAD_IDENTIFIER.match(_manifest()["identifier"])


def test_the_taskbar_id_is_the_plugin_identifier():
    assert appid.APP_ID == _manifest()["identifier"]


def test_every_icon_the_manifest_names_ships():
    for action in _manifest()["actions"]:
        for key in ("icons-light", "icons-dark"):
            for icon in action.get(key, []):
                assert (ROOT / icon).is_file(), icon
