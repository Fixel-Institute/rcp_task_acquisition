"""
Relates to https://github.com/psychopy/psychopy/issues/7768
"""

import sys
import urllib.request
import site

from pathlib import Path


def main():
    if sys.version_info[:2] < (3, 12):
        print("Detected Python version < 3.12, skipping patch vlc.")
        return 0

    site_package_dir = site.getsitepackages()[-1]  # is supposed be last
    destination = Path(f"{site_package_dir}/vlc.py")
    if not destination.exists():
        print(
            "python-vlc is supposed be already installed. have you `pip install -e .` the project ?"
        )
        return 1

    # url = "https://github.com/oaubert/python-vlc/raw/refs/heads/master/generated/3.0/vlc.py"
    url = "https://github.com/oaubert/python-vlc/raw/4cc6e13a5e443d816bac34ad2bd44fef1d6b0f7a/generated/3.0/vlc.py"
    # prefer URL with commit-id. "master" might change anytime.

    # Download and save the file
    urllib.request.urlretrieve(url, destination)
    print(f"vlc.py patched with {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
