import glob
import os
import shutil
from datetime import datetime
from pathlib import Path, PurePath

import pywintypes
import win32con
import win32file

from rcp_task_acquisition.utils.logger import get_logger

logger = get_logger("./utils/deidentify_dates")

import rcp_task_acquisition.utils.file_utils as fu
from rcp_task_acquisition.utils.constants import CONFIG_FILE_PATH


def set_all_times(path, dt):
    ts = dt.timestamp()
    os.utime(path, (ts, ts))  # accessed + modified

    wt = pywintypes.Time(dt)  # creation via Windows API
    handle = win32file.CreateFile(
        path,
        win32con.GENERIC_WRITE,
        win32con.FILE_SHARE_READ | win32con.FILE_SHARE_WRITE | win32con.FILE_SHARE_DELETE,
        None,
        win32con.OPEN_EXISTING,
        win32con.FILE_FLAG_BACKUP_SEMANTICS,  # needed to also handle directories
        None,
    )
    try:
        win32file.SetFileTime(handle, wt, wt, wt)  # creation, access, write
    finally:
        handle.close()


class SimpleLCG:
    def __init__(self, seed=12345):
        self.state = seed & 0xFFFFFFFF

    def next_random(self):
        self.state = (1664525 * self.state + 1013904223) & 0xFFFFFFFF
        return self.state

    def pulse_count(self):
        return self.next_random() % 10


class DateDeidentification:
    def __init__(self, user_cfg):
        self.config = user_cfg
        self.raw_data_dir = Path(self.config["RawDataDir"])
        self.deid_data_dir = os.path.join(
            os.path.split(self.raw_data_dir)[0], "DeidentifiedDataLocal"
        )

        rand_num_generator = SimpleLCG(seed=12345)
        date_offset_list = [rand_num_generator.pulse_count() for _ in range(6)]
        self.date_offset = int("".join(map(str, date_offset_list)))

        self.deid_metadata = datetime(2000, 1, 1)

    def deidentify_one_session(self, session_path):

        date_original = os.path.split(os.path.split(os.path.split(session_path)[0])[0])[1]
        date_ordinal = datetime.strptime(date_original, "%Y%m%d").date().toordinal()
        session = os.path.split(session_path)[1]

        date_shift = self.date_offset - date_ordinal
        rng = SimpleLCG(seed=date_shift)
        datepad_list = [rng.pulse_count() for _ in range(2)]
        rn = int("".join(map(str, datepad_list)))
        date_deided = str(f"{date_shift}{rn}")

        unit_dirW = os.path.join(self.deid_data_dir, date_deided, self.config["unitRef"], session)
        if not os.path.exists(unit_dirW):
            os.makedirs(unit_dirW)
        unit_dest = os.path.split(unit_dirW)[0]
        date_dest = os.path.split(unit_dest)[0]

        metafiles = glob.glob(os.path.join(session_path, "*"))
        for m in metafiles:
            mname = PurePath(m.replace(date_original, date_deided)).name
            mdest = os.path.join(unit_dirW, mname)
            if not os.path.isfile(mdest) or (os.path.getsize(m) != os.path.getsize(mdest)):
                shutil.copyfile(m, mdest)

            if "metadata.yaml" in mdest:
                metadata = fu.read_metadata(mdest)
                fields = list(metadata.keys())
                for f in fields:
                    if "Time" in f:
                        del metadata[f]
                fu.write_metadata(metadata, mdest)

            set_all_times(mdest, self.deid_metadata)
        set_all_times(unit_dest, self.deid_metadata)
        set_all_times(date_dest, self.deid_metadata)
        set_all_times(unit_dirW, self.deid_metadata)
        set_all_times(self.deid_data_dir, self.deid_metadata)
        logger.debug(f"deid_data: {self.deid_data_dir}")

    def deidentify_all_data(self):
        dirlist = []

        prev_date_list = [name for name in os.listdir(self.raw_data_dir)]
        for d in prev_date_list:
            unit_dirR = os.path.join(self.raw_data_dir, d, self.config["unitRef"])
            if os.path.exists(unit_dirR):
                prev_expt_list = [name for name in os.listdir(unit_dirR)]
                for s in prev_expt_list:
                    dirlist.append(os.path.join(unit_dirR, s))
                    session_path = os.path.join(unit_dirR, s)
                    self.deidentify_one_session(session_path)


def run_all_dates():
    config_path = os.path.join(CONFIG_FILE_PATH, "userdata.yaml")
    config = fu.read_config(config_path)

    deidentify = DateDeidentification(config)
    deidentify.deidentify_all_data()
    print("Data deidentification done!")
