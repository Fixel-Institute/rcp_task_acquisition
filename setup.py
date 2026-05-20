from pathlib import Path
from setuptools import setup


# Getting path to local whl files to be downloaded
local_path: str = (Path(__file__).parent / "library" / "spinnaker_python-4.3.0.189-cp310-cp310-win_amd64.whl").as_uri()
main_file: str = (Path(__file__).parent / "rcp_task_acquistion" / "__main__.py")


if __name__ == "__main__":
    setup(
        install_requires=[
            "spyder==6.1.3",
            "wxpython>=4.2",
            "psychopy>=2026.1",
            "numpy==1.26.4",
            "ruamel.yaml",
            "labjack-ljm==1.23",
            "setuptools_scm",
            "pyshortcuts",
            "pyaudio",
            f"spinnaker_python @ {local_path}",
            # other dependencies...
            "pythonnet==3.0.5",
        ]
    )

