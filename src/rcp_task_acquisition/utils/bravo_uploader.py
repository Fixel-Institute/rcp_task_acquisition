
import os, sys
import traceback
import numpy as np
import scipy.io as sio
from scipy import stats, signal, optimize
import pandas as pd
import yaml
import json
import datetime

from library.BRAVO.BRAVORequestAPI import BRAVOPlatformRequest

def getTimestamp(text):
    return datetime.datetime.fromisoformat(text[0:4] + "-" + text[4:6] + "-" + text[6:8] + "T" + text[8:10] + ":" + text[10:12] + ":" + text[12:14] + "+00:00").timestamp()

def bits_to_bytes(bits, msb_first=True, pad=True):
    bits = np.asarray(bits).astype(np.uint8).ravel()
    if pad and bits.size % 8:
        bits = np.concatenate([bits, np.zeros(8 - bits.size % 8, dtype=np.uint8)])
    elif bits.size % 8:
        bits = bits[:-(bits.size % 8)]
    weights = 2 ** (np.arange(7, -1, -1) if msb_first else np.arange(8))
    byte_vals = bits.reshape(-1, 8).dot(weights).astype(np.uint8)
    return bytes(byte_vals.tolist())

def getCharArray(rawBytes, startIndex=1):
    currentIndex = startIndex
    characters = []
    while currentIndex < len(rawBytes):
        char = bits_to_bytes(rawBytes[currentIndex:currentIndex+8])
        characters.append(char)
        currentIndex += 8
    return b''.join(characters)

def loadDelsysData(rawBytes):
    DataChannels = []
    DataSensorInfos = {}
    DataSamplingRate = []
    DelsysData = {}
    currentIndex = 0
    while currentIndex < len(rawBytes):
        headerByte = rawBytes[currentIndex:currentIndex+5]
        if not b'RCPUF' == headerByte:
            print("Invalid header byte at index", currentIndex)
            break
        timestamp = int.from_bytes(rawBytes[currentIndex+5:currentIndex+13], byteorder='little')
        packetNameLength = int.from_bytes(rawBytes[currentIndex+13:currentIndex+17], byteorder='little')
        dataLength = int.from_bytes(rawBytes[currentIndex+17:currentIndex+21], byteorder='little')
        packetName = rawBytes[currentIndex+21:currentIndex+21+packetNameLength].split(b'\x00', 1)[0].decode('utf-8')
        if packetName == "Delsys_ChannelIDs":
            data = rawBytes[currentIndex+21+packetNameLength:currentIndex+21+packetNameLength+dataLength]
            DataChannels.append(data.decode('utf-8'))
            DataSensorInfos[data.decode('utf-8')] = {}
        elif packetName.endswith("|SensorId"):
            data = rawBytes[currentIndex+21+packetNameLength:currentIndex+21+packetNameLength+dataLength]
            if packetName.split("|")[0] not in DataSensorInfos:
                DataSensorInfos[packetName.split("|")[0]] = {}
            DataSensorInfos[packetName.split("|")[0]]["SensorId"] = int.from_bytes(data, byteorder='little')
        elif packetName.endswith("|Name"):
            data = rawBytes[currentIndex+21+packetNameLength:currentIndex+21+packetNameLength+dataLength]
            if packetName.split("|")[0] not in DataSensorInfos:
                DataSensorInfos[packetName.split("|")[0]] = {}
            DataSensorInfos[packetName.split("|")[0]]["Name"] = data.decode('utf-8')
        elif packetName.endswith("|SamplingRate"):
            data = rawBytes[currentIndex+21+packetNameLength:currentIndex+21+packetNameLength+dataLength]
            if packetName.split("|")[0] not in DataSensorInfos:
                DataSensorInfos[packetName.split("|")[0]] = {}
            DataSensorInfos[packetName.split("|")[0]]["SamplingRate"] = np.frombuffer(data, dtype=np.float64)
        elif packetName.startswith("Delsys_DataPacket"):
            ChannelName = packetName.split("|")[-1]
            data = np.frombuffer(rawBytes[currentIndex+21+packetNameLength:currentIndex+21+packetNameLength+dataLength], dtype=np.float64)
            if ChannelName not in DelsysData:
                DelsysData[ChannelName] = []
            DelsysData[ChannelName].append(data)
        else:
            raise ValueError("Unknown packet name:", packetName)
        currentIndex += 21 + packetNameLength + dataLength
    for key in DelsysData.keys():
        DelsysData[key] = np.concatenate(DelsysData[key], axis=0)
    return {
        "ChannelNames": DataChannels,
        "ChannelInfos": DataSensorInfos,
        "Data": DelsysData,
    }

def getShift(lj, delsys, lj_time, delsys_time):
    delsys_matched = np.interp(lj_time, delsys_time, delsys)
    corr = signal.correlate(delsys_matched - np.mean(delsys_matched), lj - np.mean(lj), mode='full')
    lags = signal.correlation_lags(len(delsys_matched), len(lj), mode='full')
    best_lag_idx = np.argmax(corr)
    best_lag_samples = lags[best_lag_idx]
    time_shift = best_lag_samples * (lj_time[1] - lj_time[0])
    return time_shift, 1

def scaleDelsysFs(x, a, b):
    return a * x + b

def getShift_PeakBased(lj, delsys, lj_time, delsys_time):
    peaks_delsys, _ = signal.find_peaks(delsys, height=3)
    if len(peaks_delsys) == 0:
        return 0, 1

    lj_start = np.where(lj[:-1] > lj[1:])[0]
    lj_end = np.where(lj[1:] > lj[:-1])[0]
    if len(lj_end) < len(lj_start):
        lj_start = lj_start[:len(lj_end)]
    if len(lj_start) == 0 or len(lj_end) == 0:
        return 0, 1

    peak_times_lj = np.array([(lj_time[start] + lj_time[end]) / 2 for start, end in zip(lj_start, lj_end)])
    peak_times_delsys = delsys_time[peaks_delsys]
    if len(peak_times_lj) == 0 or len(peak_times_delsys) == 0:
        return 0, 1

    if np.abs(len(peak_times_lj) - len(peak_times_delsys)) > 5:
        return getShift(lj, delsys, lj_time, delsys_time)

    if len(peak_times_lj) < len(peak_times_delsys):
        peak_times_delsys = peak_times_delsys[:len(peak_times_lj)]
    elif len(peak_times_delsys) < len(peak_times_lj):
        peak_times_lj = peak_times_lj[:len(peak_times_delsys)]

    popt, pcov = optimize.curve_fit(scaleDelsysFs, peak_times_delsys, peak_times_lj)
    return popt[1], popt[0]

def uploadRCPSession(session_path, session_info, on_success=None, on_error=None):
    try:
        SessionFiles = os.listdir(session_path)
        SessionMetadata = {}
        for file in SessionFiles:
            if file.endswith(".yaml"):
                config = yaml.safe_load(open(os.path.join(session_path, file), 'r'))
                SessionMetadata.update(config)

        requester = BRAVOPlatformRequest(os.getenv("BRAVOAccessKey"), os.getenv("BRAVOServer"))
        _ = requester.GetUserInfo()

        Participants = requester.QueryParticipants()
        ParticipantInfo = None
        for participant in Participants:
            if participant['Name'] == SessionMetadata["participant_id"]:
                ParticipantInfo = participant
                break
        if not ParticipantInfo:
            raise ValueError("Participant not found:", SessionMetadata["participant_id"])

        # Align Delsys and LabJack data
        LJData = pd.DataFrame()
        DSData = {}
        for file in SessionFiles:
            if file.endswith("_delsys.mdat"):
                DSData = loadDelsysData(open(os.path.join(session_path, file), 'rb').read())
            elif file.endswith("_labjack.txt"):
                LJData = pd.read_csv(os.path.join(session_path, file), sep=",", header=0)

        if LJData.empty and len(DSData.keys()) == 0:
            raise ValueError("Missing Delsys and LabJack data files in session directory.")

        SessionDate = getTimestamp(SessionMetadata.get("StartTime_UTC"))
        TimezoneOffset = getTimestamp(SessionMetadata.get("StartTime_Local")) - SessionDate
        timezone = f"UTC{int(TimezoneOffset // 3600):+03d}:{int((TimezoneOffset % 3600) // 60):02d}"

        if not LJData.empty:
            digital_series = LJData["Digital"].astype(int).values
            for j in range(16):
                if j < 8:
                    dio_name = f"FIO{j:01d}"
                else:
                    dio_name = f"EIO{j:01d}"
                LJData[dio_name] = (digital_series >> j) & 1
                if np.unique(LJData[dio_name].values).size == 1:
                    LJData.drop(columns=[dio_name], inplace=True)
                else:
                    LJData[dio_name] = LJData[dio_name].astype(np.uint8)
            del LJData["Digital"]

            LabJack_SamplingRate = SessionMetadata.get("actual_scan_rate")
            ChannelNames = LJData.columns.tolist()
            for i in range(len(ChannelNames)):
                for key in SessionMetadata["hardware"].keys():
                    if SessionMetadata["hardware"][key].get("labjack_input") == ChannelNames[i]:
                        ChannelNames[i] = f"{key} ({ChannelNames[i]})"
                        break

        time_scale = 1
        time_offset = 0
        if not LJData.empty and len(DSData.keys()) > 0:
            Delsys_Barcode = np.zeros(0)
            LabJack_Barcode = np.zeros(0)
            for key in ChannelNames:
                if key.startswith("Slow Barcode"):
                    col_name = key.split("(")[-1].rstrip(")")
                    LabJack_Barcode = LJData[col_name].values
                    break

            for key in DSData["ChannelNames"]:
                if DSData["ChannelInfos"][key]["Name"] == "Analog 2":
                    Delsys_Barcode = DSData["Data"][key]
                    Delsys_BarcodeSamplingRate = DSData["ChannelInfos"][key]["SamplingRate"]
                    break

            if LabJack_Barcode.size > 0 and Delsys_Barcode.size > 1000:
                Delsys_Barcode = Delsys_Barcode[500:]
                Timestamp_Delsys = np.arange(len(Delsys_Barcode)) / Delsys_BarcodeSamplingRate
                Timestamp_LJ = np.arange(len(LabJack_Barcode)) / LabJack_SamplingRate

                time_offset, time_scale = getShift_PeakBased(LabJack_Barcode, Delsys_Barcode, Timestamp_LJ, Timestamp_Delsys)
                print(f"Estimated time offset between LabJack and Delsys data: {time_offset:.3f} seconds with Delsys Sampling Rate scaled by {time_scale:.6f}")

                """ Visual Checking
                Timestamp_Delsys = np.arange(len(Delsys_Barcode)) / (Delsys_BarcodeSamplingRate / time_scale) + time_offset
                fig = plt.figure(figsize=(15, 10))
                ax = fig.add_subplot(1, 1, 1)
                ax.plot(Timestamp_LJ, LabJack_Barcode, label="LabJack Barcode", color="b", alpha=0.5)
                ax.plot(Timestamp_Delsys, Delsys_Barcode, label="Delsys Barcode", color="r", alpha=0.5)
                ax.set_xlabel("Time (s)")
                ax.set_ylabel("Amplitude")
                ax.set_title("Analog Waveform Comparison")
                ax.set_xlim(27.4,27.6)
                fig.show()
                """

        if not LJData.empty:
            sio.savemat(os.path.join(session_path, f"{session_info.replace(os.path.sep,'_')}_LabJack.mat"), {
                "Channels": ChannelNames,
                "Fs": np.ones((len(ChannelNames), 1)) * LabJack_SamplingRate,
                "Data": LJData.values.T,
                "DataType": "CustomizedStreamingData",
                "Metadata": json.dumps({**SessionMetadata,
                                        **{"DataType": "LabJack", "StartTime": SessionDate, "Timezone": timezone,
                                        "RecordingName": SessionMetadata.get("task", "")}}),
            }, do_compression=True)
            with open(os.path.join(session_path, f"{session_info.replace(os.path.sep,'_')}_LabJack.mat"), "rb") as file:
                requester.UploadMATFile(ParticipantInfo['Id'], file, {**SessionMetadata,
                                                                    **{"DataType": "LabJack", "StartTime": SessionDate,
                                                                        "Timezone": timezone}})

        if len(DSData.keys()) > 0:
            # Delsys Save
            Delsys_ChannelNames = []
            Delsys_Fs = []
            for uid in DSData["ChannelNames"]:
                Delsys_ChannelNames.append(
                    f"Sensor {int(DSData['ChannelInfos'][uid]['SensorId']):02d} - {DSData['ChannelInfos'][uid].get('Name', 'Unknown')}")
                Delsys_Fs.append(DSData["ChannelInfos"][uid].get("SamplingRate", 0) / time_scale)

            unique_fs = np.unique(Delsys_Fs)
            for fs in unique_fs:
                indices = [i for i, f in enumerate(Delsys_Fs) if f == fs]
                if np.abs(fs - 74) < 2:
                    sio.savemat(os.path.join(session_path, f"{session_info.replace(os.path.sep,'_')}_DelsysImpedance.mat"), {
                        "Channels": [Delsys_ChannelNames[i] for i in indices],
                        "Fs": np.ones((len(indices), 1)) * fs,
                        "Data": np.array([DSData["Data"][DSData["ChannelNames"][i]] for i in indices]),
                        "DataType": "CustomizedStreamingData",
                        "Metadata": json.dumps({**SessionMetadata,
                                                **{"DataType": "Delsys_Impedance", "StartTime": SessionDate + time_offset,
                                                "Timezone": timezone, "SamplingRateScale": 1/time_scale,
                                                "RecordingName": SessionMetadata.get("task", "")}}),
                    }, do_compression=True)
                    with open(os.path.join(session_path, f"{session_info.replace(os.path.sep,'_')}_DelsysImpedance.mat"), "rb") as file:
                        requester.UploadMATFile(ParticipantInfo['Id'], file, {**SessionMetadata,
                                                                            **{"DataType": "Delsys", "StartTime": SessionDate + time_offset,
                                                                                "Timezone": timezone, "SamplingRateScale": 1/time_scale}})

                elif np.abs(fs - 148) < 2:
                    sio.savemat(os.path.join(session_path, f"{session_info.replace(os.path.sep,'_')}_DelsysIMU.mat"), {
                        "Channels": [Delsys_ChannelNames[i] for i in indices],
                        "Fs": np.ones((len(indices), 1)) * fs,
                        "Data": np.array([DSData["Data"][DSData["ChannelNames"][i]] for i in indices]),
                        "DataType": "CustomizedStreamingData",
                        "Metadata": json.dumps({**SessionMetadata,
                                                **{"DataType": "Delsys_IMU", "StartTime": SessionDate + time_offset,
                                                "Timezone": timezone, "SamplingRateScale": 1/time_scale,
                                                "RecordingName": SessionMetadata.get("task", "")}}),
                    }, do_compression=True)
                    with open(os.path.join(session_path, f"{session_info.replace(os.path.sep,'_')}_DelsysIMU.mat"), "rb") as file:
                        requester.UploadMATFile(ParticipantInfo['Id'], file, {**SessionMetadata,
                                                                            **{"DataType": "Delsys", "StartTime": SessionDate + time_offset,
                                                                                "Timezone": timezone, "SamplingRateScale": 1/time_scale}})

                elif np.abs(fs - 1259) < 2:
                    sio.savemat(os.path.join(session_path, f"{session_info.replace(os.path.sep,'_')}_DelsysEMG.mat"), {
                        "Channels": [Delsys_ChannelNames[i] for i in indices],
                        "Fs": np.ones((len(indices), 1)) * fs,
                        "Data": np.array([DSData["Data"][DSData["ChannelNames"][i]] for i in indices]),
                        "DataType": "CustomizedStreamingData",
                        "Metadata": json.dumps({**SessionMetadata,
                                                **{"DataType": "Delsys_EMG", "StartTime": SessionDate + time_offset,
                                                "Timezone": timezone, "SamplingRateScale": 1/time_scale,
                                                "RecordingName": SessionMetadata.get("task", "")}}),
                    }, do_compression=True)
                    with open(os.path.join(session_path, f"{session_info.replace(os.path.sep,'_')}_DelsysEMG.mat"), "rb") as file:
                        requester.UploadMATFile(ParticipantInfo['Id'], file, {**SessionMetadata,
                                                                            **{"DataType": "Delsys", "StartTime": SessionDate + time_offset,
                                                                                "Timezone": timezone, "SamplingRateScale": 1/time_scale}})

                elif np.abs(fs - 2222) < 2:
                    sio.savemat(os.path.join(session_path, f"{session_info.replace(os.path.sep,'_')}_DelsysAnalog.mat"), {
                        "Channels": [Delsys_ChannelNames[i] for i in indices],
                        "Fs": np.ones((len(indices), 1)) * fs,
                        "Data": np.array([DSData["Data"][DSData["ChannelNames"][i]] for i in indices]),
                        "DataType": "CustomizedStreamingData",
                        "Metadata": json.dumps({**SessionMetadata,
                                                **{"DataType": "Delsys_Analog", "StartTime": SessionDate + time_offset,
                                                "Timezone": timezone, "SamplingRateScale": 1/time_scale,
                                                "RecordingName": SessionMetadata.get("task", "")}}),
                    }, do_compression=True)
                    with open(os.path.join(session_path, f"{session_info.replace(os.path.sep,'_')}_DelsysAnalog.mat"), "rb") as file:
                        requester.UploadMATFile(ParticipantInfo['Id'], file, {**SessionMetadata,
                                                                            **{"DataType": "Delsys", "StartTime": SessionDate + time_offset,
                                                                                "Timezone": timezone, "SamplingRateScale": 1/time_scale}})

        if on_success:
            on_success(f"Session {session_info} processed and uploaded successfully.")

    except Exception as e:
        if on_error:
            on_error(traceback.format_exc())
        else:
            print(traceback.format_exc())