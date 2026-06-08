# -*- coding: utf-8 -*-
import os
from pathlib import Path
from pyshortcuts import make_shortcut


# is used in the pyproject.toml for the 'create-shortcut' script
# makes a desktop shortcut to run the script
def create_shortcut():
    run_dir = Path(__file__).parent.parent
    main_dir = Path(__file__).parent.parent.parent.parent
    
    main = os.path.join(run_dir, "__main__.py")
    icon_img = os.path.join(main_dir, "library", "rcp_logo_ucsf_uf.ico")
    
    make_shortcut(main, name='UCSF-UF RCP Task Acquisition', icon=icon_img, terminal=False)