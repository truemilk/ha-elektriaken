"""Load pure integration modules without requiring Home Assistant locally."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).parents[1]
PACKAGE = "custom_components.elektriaken"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


package = types.ModuleType(PACKAGE)
package.__path__ = [str(ROOT / "custom_components" / "elektriaken")]
sys.modules.setdefault("custom_components", types.ModuleType("custom_components"))
sys.modules[PACKAGE] = package
_load(f"{PACKAGE}.models", ROOT / "custom_components" / "elektriaken" / "models.py")
