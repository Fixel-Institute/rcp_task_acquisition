import importlib
import os.path
import types
from pathlib import Path

import pytest


repo_top_dir = Path(__file__).parent.parent.resolve()


def _find_modules():
    rcp_pkg_dir = repo_top_dir.joinpath("src", "rcp_task_acquisition")
    return [
        ".".join(p.relative_to(rcp_pkg_dir).parts)[:-3]
        for p in rcp_pkg_dir.rglob("*.py")
        if not p.name.startswith("_")
    ]


@pytest.mark.parametrize("mod_name", _find_modules())
def test_import(mod_name):
    """Ensure that all modules can be imported"""
    mod = importlib.import_module(f"rcp_task_acquisition.{mod_name}")
    assert isinstance(mod, types.ModuleType)
