import requests
import json
import os
import pickle as pkl
import datetime

DefaultConfigurations = {
    "TimeSeriesRecording": {
        "StandardFilter": {
            "name": "Standard Bandpass Filter",
            "description": "",
            "options": ["No Filter", "Butterworth 1-100Hz"],
            "value": "No Filter"
        },
        "NotchFilter": {
            "name": "Powerline Noise Notch Filter",
            "description": "",
            "options": ["No Filter", "Notch 55-65Hz", "Notch 45-55Hz"],
            "value": "No Filter"
        },
        "WienerFilter": {
            "name": "Wiener Filter for Artifact Removals",
            "description": "",
            "options": ["No Filter", "Use Wiener Filter"],
            "value": "No Filter"
        },
        "CardiacFilter": {
            "name": "Cardiac Filter for EKG Removals",
            "description": "",
            "options": ["No Filter", "Use Adaptive Template Matching"],
            "value": "No Filter"
        },
        "SpectrogramMethod": {
            "name": "Time-Frequency Analysis Algorithm",
            "description": "",
            "options": ["Welch's Periodogram", "Short-time Fourier Transform", "Wavelet",
                        "Autoregressive Model (Yule-Walker)"],
            "value": "Welch's Periodogram"
        },
        "BaselineCorrection": {
            "name": "Baseline Correlation for Time-Frequency Analysis",
            "description": "",
            "options": ["No Correction"],
            "value": "No Correction"
        },
        "Normalization": {
            "name": "Normalization for Time-Frequency Analysis",
            "description": "",
            "options": ["No Normalization", "1/f PSD Trend Removal"],
            "value": "No Normalization"
        },
    },
    "PowerSpectralDensity": {
        "PSDMethod": {
            "name": "Power Spectrum Estimation Algorithm",
            "description": "",
            "options": ["Estimated Medtronic PSD", "Welch's Periodogram", "Autoregressive Model (Yule-Walker)",
                        "Short-time Fourier Transform"],
            "value": "Welch's Periodogram"
        },
        "MonopolarEstimation": {
            "name": "Monopolar Estimation Algorithm",
            "description": "",
            "options": ["No Estimation", "DETEC Algorithm (Strelow et. al., 2022)"],
            "value": "No Estimation"
        },
    }
}


class BRAVOPlatformRequest:
    def __init__(self, api_key, server="http://localhost"):
        self.__Server = server
        self.__request = requests.Session()
        self.__API_Key = api_key

    def query(self, url, data=None, files=None, content_type="application/json"):
        if not content_type:
            Headers = {"X-Secure-API-Key": self.__API_Key}
        else:
            Headers = {"Content-Type": content_type, "X-Secure-API-Key": self.__API_Key}

        if data:
            return self.__request.post(self.__Server + url,
                                       json.dumps(data) if content_type else data,
                                       headers=Headers)
        elif files:
            return self.__request.post(self.__Server + url,
                                       files=files,
                                       headers=Headers)
        else:
            return self.__request.post(self.__Server + url,
                                       headers=Headers)

    def GetUserInfo(self):
        response = self.query("/api/queryProfile")
        if response.status_code == 200:
            payload = response.json()
            self.User = payload
            return payload
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            else:
                raise Exception(f"Network Error: {response.status_code}")

    def QueryParticipants(self):
        response = self.query("/api/queryParticipants")
        if response.status_code == 200:
            payload = response.json()
            return payload
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            else:
                raise Exception(f"Network Error: {response.status_code}")

    def QueryParticipantInformation(self, participant_uid):
        form = {"ParticipantId": participant_uid}
        response = self.query("/api/queryParticipantInformation", data=form)
        if response.status_code == 200:
            payload = response.json()
            return payload
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            else:
                raise Exception(f"Network Error: {response.status_code}")

    def UpdateParticipantInformation(self, participant_uid, info):
        form = {"ParticipantId": participant_uid}
        form = {**form, **info}

        response = self.query("/api/updateParticipantInformation", data=form)
        if response.status_code == 200:
            payload = response.json()
            return payload
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            else:
                raise Exception(f"Network Error: {response.status_code}")

    def ListAllStudies(self):
        form = {"RequestType": "GetStudies"}
        response = self.query("/api/manageStudyInformation", data=form)
        if response.status_code == 200:
            payload = response.json()
            return payload
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            else:
                raise Exception(f"Network Error: {response.status_code}")

    def CreateNewStudy(self, study_name):
        form = {"RequestType": "CreateStudy", "StudyName": study_name}
        response = self.query("/api/manageStudyInformation", data=form)
        if response.status_code == 200:
            payload = response.json()
            return payload
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            else:
                raise Exception(f"Network Error: {response.status_code}")

    def AddParticipantToStudy(self, study_id, participant_uid):
        form = {"RequestType": "AddParticipant", "StudyId": study_id, "ParticipantId": participant_uid}
        response = self.query("/api/manageStudyInformation", data=form)
        if response.status_code == 200:
            return True
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            else:
                raise Exception(f"Network Error: {response.status_code}")

    def RemoveParticipantFromStudy(self, study_id, participant_uid):
        form = {"RequestType": "RemoveParticipant", "StudyId": study_id, "ParticipantId": participant_uid}
        response = self.query("/api/manageStudyInformation", data=form)
        if response.status_code == 200:
            return True
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            else:
                raise Exception(f"Network Error: {response.status_code}")

    def QueryTherapyHistory(self, participant_uid):
        form = {"ParticipantId": participant_uid}
        response = self.query("/api/queryTherapyHistory", data=form)
        if response.status_code == 200:
            payload = response.json()
            return payload
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            else:
                raise Exception(f"Network Error: {response.status_code}")

    def QueryTherapeuticEffectAnalysis(self, participant_uid, analysis_uid=None, config=None):
        form = {"ParticipantId": participant_uid, "RequestType": "Overview"}
        if analysis_uid:
            form["RequestType"] = "RequestData"
            form["AnalysisId"] = analysis_uid
            form["ActiveChannels"] = "RequestAllChannel"

        if config:
            form["ProcessingConfiguration"] = config

        response = self.query("/api/queryTherapeuticEffectAnalysis", data=form)
        if response.status_code == 200:
            payload = response.json()
            return payload
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            else:
                raise Exception(f"Network Error: {response.status_code}")

    def SetRecordingTimeShift(self, participant_uid, analysis_uid, recording_uid, shift=0):
        form = {"RequestType": "RemoveParticipant", "ParticipantId": participant_uid, "AnalysisId": analysis_uid,
                "RecordingId": recording_uid, "Alignment": shift}
        response = self.query("/api/setRecordingTimeShift", data=form)
        if response.status_code == 200:
            return True
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            else:
                raise Exception(f"Network Error: {response.status_code}")

    def QueryNeuralActivitySnapshot(self, participant_uid, config=None):
        form = {"ParticipantId": participant_uid, "RequestType": "RequestAll"}
        if config:
            form["ProcessingConfiguration"] = config

        response = self.query("/api/queryNeuralActivitySnapshot", data=form)
        if response.status_code == 200:
            payload = response.json()
            return payload
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            else:
                raise Exception(f"Network Error: {response.status_code}")

    def QueryTimeSeriesAnalysis(self, participant_uid, recording_uid=None, therapy_uid=None, config=None,
                                refresh=False):
        form = {"ParticipantId": participant_uid, "RequestType": "Overview"}
        if recording_uid:
            form["RequestType"] = "RequestData"
            form["AnalysisId"] = recording_uid
            form["TherapyId"] = therapy_uid
            form["ActiveChannels"] = "RequestAllChannel"

        if refresh:
            form["RequestType"] = "DeleteCache"

        if config:
            form["ProcessingConfiguration"] = config

        response = self.query("/api/queryTimeseriesAnalysis", data=form)
        if response.status_code == 200:
            if refresh:
                return self.QueryTimeSeriesAnalysis(participant_uid, recording_uid, therapy_uid, config)

            payload = response.json()
            return payload
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            else:
                raise Exception(f"Network Error: {response.status_code}")

    def QueryChronicNeuralActivity(self, participant_uid, refresh=False):
        form = {"ParticipantId": participant_uid, "RequestType": "RequestAll"}
        if refresh:
            form["RequestType"] = "DeleteCache"

        response = self.query("/api/queryChronicNeuralActivity", data=form)
        if response.status_code == 200:
            if refresh:
                return self.QueryChronicNeuralActivity(participant_uid)

            payload = response.json()
            return payload
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            else:
                raise Exception(f"Network Error: {response.status_code}")

    def QueryChronicTimeline(self, participant_uid):
        form = {"ParticipantId": participant_uid, "RequestType": "RequestAll"}
        response = self.query("/api/queryChronicTimeline", data=form)
        if response.status_code == 200:
            payload = response.json()
            return payload
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            else:
                raise Exception(f"Network Error: {response.status_code}")

    def QueryRawTimeseries(self, participant_uid, recording_uid=None):
        form = {"ParticipantId": participant_uid, "RequestType": "Overview"}
        if recording_uid:
            form["RequestType"] = "RawTimeseries"
            form["RecordingId"] = recording_uid

        response = self.query("/api/queryRawTimeseries", data=form)
        if response.status_code == 200:
            payload = response.json()
            return payload
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            else:
                raise Exception(f"Network Error: {response.status_code}")

    def QuerySurveyForms(self, form_link=None, version=None):
        form = {"RequestType": "RequestAll"}
        if form_link:
            form["RequestType"] = "RequestForm"
            form["FormLink"] = form_link
            if version:
                form["VersionRel"] = version

        response = self.query("/api/querySurveyForms", data=form)
        if response.status_code == 200:
            payload = response.json()
            return payload
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            else:
                raise Exception(f"Network Error: {response.status_code}")

    def CreateSurveyForm(self, institute, form_name):
        form = {"RequestType": "Create", "Institute": institute, "FormName": form_name,
                "FormType": "API-Generated Form", "FormContent": []}
        response = self.query("/api/setSurveyForms", data=form)
        if response.status_code == 200:
            payload = response.json()
            return payload
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            else:
                raise Exception(f"Network Error: {response.status_code}")

    def DeleteSurveyForm(self, form_uid):
        form = {"FormId": form_uid}

        response = self.query("/api/deleteSurveyForms", data=form)
        if response.status_code == 200:
            return True
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            else:
                raise Exception(f"Network Error: {response.status_code}")

    def UpdateSurveyForm(self, form_link, content):
        form = {"RequestType": "Create", "FormLink": form_link, "FormContent": content}
        response = self.query("/api/setSurveyForms", data=form)
        if response.status_code == 200:
            payload = response.json()
            return payload
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            else:
                raise Exception(f"Network Error: {response.status_code}")

    def SubmitSurveyResponse(self, form_uid, version, responder_code, result={}, date=None):
        form = {"RequestType": "SubmitForm", "FormId": form_uid, "Version": version, "Passcode": responder_code,
                "FormResults": result}
        if not date:
            form["Date"] = datetime.datetime.now(datetime.timezone.utc).timestamp()
        else:
            form["Date"] = date

        response = self.query("/api/querySurveyForms", data=form)
        if response.status_code == 200:
            payload = response.json()
            return payload
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            else:
                raise Exception(f"Network Error: {response.status_code}")

    def QuerySurveyResponse(self, participant_uid, form_uid=None):
        form = {"ParticipantId": participant_uid, "RequestType": "RequestAll"}
        if form_uid:
            form["RequestType"] = "RequestRecords"
            form["FormId"] = form_uid
        response = self.query("/api/queryParticipantSurveyRecords", data=form)

        if response.status_code == 200:
            payload = response.json()
            return payload
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            else:
                raise Exception(f"Network Error: {response.status_code}")

    def QueryEvents(self, participant_uid, data=False):
        form = {"ParticipantId": participant_uid, "RequestType": "RequestAll"}
        if data:
            form["RequestType"] = "RequestData"
        response = self.query("/api/queryParticipantEvents", data=form)

        if response.status_code == 200:
            payload = response.json()
            return payload
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            else:
                raise Exception(f"Network Error: {response.status_code}")

    def DeleteData(self, recording_uid, participant=None):
        participantObj = participant if participant else self.__ActiveParticipant
        data = {"participant": participantObj["uid"], "study": participantObj["study"], "recording_uid": recording_uid}
        response = self.query("/api/deleteData", data)
        if response.status_code == 200:
            return True
        elif response.status_code == 301:
            return True
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            else:
                raise Exception(f"Network Error: {response.status_code}")

    def RequestAnalysisPipeline(self, request_type, participant_uid):
        data = {"RequestType": request_type, "AnalysisName": request_type, "ParticipantId": participant_uid}
        response = self.query("/api/queryAnalysisPipeline", data)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 301:
            return True
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            else:
                raise Exception(f"Network Error: {response.status_code}")

    def RequestAIPrediction(self, request_type, data):
        data = {"RequestType": request_type, "AnalysisName": request_type, "Data": data}
        response = self.query("/api/requestAIPrediction", data)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 301:
            return True
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            else:
                raise Exception(f"Network Error: {response.status_code}")

    def UploadMedtronicJSON(self, participant, file, metadata={"device_location": "", "infer_from_device": True}):
        form = {
            "File": file,
            "DataType": (None, "MedtronicJSON"),
            "ParticipantId": (None, participant),
            "Institute": (None, self.User["Institute"]),
            "Metadata": (None, json.dumps(metadata))
        }

        response = self.query("/api/uploadData", files=form, content_type=None)
        if response.status_code == 200:
            return True
        elif response.status_code == 301:
            return True
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            else:
                raise Exception(f"Network Error: {response.status_code}")

    def UploadMATFile(self, participant, file, metadata=dict()):
        if not "StartTime" in metadata:
            metadata["StartTime"] = datetime.datetime.now(datetime.timezone.utc).timestamp()

        form = {
            "File": file,
            "DataType": (None, "MATFile"),
            "ParticipantId": (None, participant),
            "Institute": (None, self.User["Institute"]),
            "Metadata": (None, json.dumps(metadata))
        }

        response = self.query("/api/uploadData", files=form, content_type=None)
        if response.status_code == 200:
            return True
        elif response.status_code == 301:
            return True
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            else:
                raise Exception(f"Network Error: {response.status_code}")
