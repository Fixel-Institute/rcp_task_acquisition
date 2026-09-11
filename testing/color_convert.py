import cv2


def desmurf(video_path, old_file, new_file):
    # open original fil
    og_file_path = old_file  # os.path.join(video_path, old_file)
    cap = cv2.VideoCapture(og_file_path)
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    print(frame_width, frame_height)
    # Open new video file
    new_file_path = new_file  # os.path.join(video_path, new_file)
    new_vid = cv2.VideoWriter(
        new_file_path, cv2.VideoWriter_fourcc("m", "p", "4", "v"), fps, (frame_width, frame_height)
    )

    # Check if the video file was opened successfully
    if not cap.isOpened():
        print(f"Error: Could not open video file {old_file}")
        return

    while cap.isOpened():
        # print("new frame")
        # cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)

        # Read the frame
        ret, frame = cap.read()
        if not ret:
            break
        new_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        # frame_list.append(frame)
        new_vid.write(new_frame)

    cap.release()


def desmurf_loop(video_path, file_list):

    for file in file_list:
        name_list = file.split(".")
        name_list[0] += "_color"
        new_file = ".".join(name_list)
        print(new_file)
        desmurf(video_path, file, new_file)


video_path = "D:/RawDataLocal/20260401/unitME/session013"
# old_file = "20260401_unitME_session012_rightCamA_trial1.mp4"
# new_file = "20260401_unitME_session012_rightCamA_trial1_color.mp4"
# desmurf(video_path, old_file, new_file)

file_list = [
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_rightCamB_trial12.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_rightCamB_trial13.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_rightCamB_trial14.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_leftCamA_trial1.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_leftCamA_trial2.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_leftCamA_trial3.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_leftCamA_trial4.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_leftCamA_trial5.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_leftCamA_trial6.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_leftCamA_trial7.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_leftCamA_trial8.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_leftCamA_trial9.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_leftCamA_trial10.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_leftCamA_trial11.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_leftCamA_trial12.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_leftCamA_trial13.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_leftCamA_trial14.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_leftCamB_trial1.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_leftCamB_trial2.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_leftCamB_trial3.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_leftCamB_trial4.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_leftCamB_trial5.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_leftCamB_trial6.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_leftCamB_trial7.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_leftCamB_trial8.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_leftCamB_trial9.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_leftCamB_trial10.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_leftCamB_trial11.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_leftCamB_trial12.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_leftCamB_trial13.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_leftCamB_trial14.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_rightCamA_trial1.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_rightCamA_trial2.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_rightCamA_trial3.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_rightCamA_trial4.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_rightCamA_trial5.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_rightCamA_trial6.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_rightCamA_trial7.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_rightCamA_trial8.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_rightCamA_trial9.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_rightCamA_trial10.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_rightCamA_trial11.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_rightCamA_trial12.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_rightCamA_trial13.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_rightCamA_trial14.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_rightCamB_trial1.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_rightCamB_trial2.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_rightCamB_trial3.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_rightCamB_trial4.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_rightCamB_trial5.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_rightCamB_trial6.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_rightCamB_trial7.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_rightCamB_trial8.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_rightCamB_trial9.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_rightCamB_trial10.mp4",
    "D:/RawDataLocal/20260401/unitME/session013/20260401_unitME_session013_rightCamB_trial11.mp4",
]

desmurf_loop(video_path, file_list)
