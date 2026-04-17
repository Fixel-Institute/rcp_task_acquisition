# -*- coding: utf-8 -*-
import sys
import subprocess
from pathlib import Path
import importlib.metadata as importlib_metadata

from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./utils/task_acquisition_version") 



top_dir = Path(__file__).parent.parent.resolve()


def _get_from_setuptools_scm():

    out = subprocess.check_output([sys.executable, '-m', 'setuptools_scm'], cwd=top_dir)

    out = out.decode().strip()
    return out if len(out) > 0 else None


__version__ = _get_from_setuptools_scm()
logger.debug(__version__)

if __version__ == None:
    try:
        __version__ = importlib_metadata.version("rcp_task_acquisition")
    except importlib_metadata.PackageNotFoundError:
        logger.warning("No version available")
        __version__ = "0.0.0"