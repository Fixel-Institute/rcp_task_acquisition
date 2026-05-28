# -*- coding: utf-8 -*-
import cv2

from rcp_task_acquisition.utils.logger import get_logger
from threading import Thread, Event
from queue import Queue, Full, Empty
logger = get_logger("./models/AsyncVideoWriter") 


class AsyncVideoWriter:
    def __init__(self, video_file, timestamp_file, fps, width, height,
                 max_queue=256, fourcc='mp4v'):
        self.video_file = video_file
        self.timestamp_file = timestamp_file
        self.fps = fps
        self.width = width
        self.height = height
        self.max_queue = max_queue

        self.q = Queue(maxsize=max_queue)
        self.stop_event = Event()
        self.dropped_by_writer = 0

        self.writer = cv2.VideoWriter(
            video_file,
            cv2.VideoWriter_fourcc(*fourcc),
            fps,
            (width, height)
        )

        if not self.writer.isOpened():
            raise RuntimeError(f"Could not open video writer: {video_file}")

        self.f = open(timestamp_file, "w")
        self.f.write("frame_id,timestamp\n")

        self.thread = Thread(target=self._worker, daemon=False)
        self.thread.start()


    def write(self, frame_bgr, frame_id, timestamp_delta):
        """
        Non-blocking enqueue. If the queue fills, record that the writer
        could not keep up rather than blocking acquisition.
        """
        try:
            self.q.put_nowait((frame_bgr, frame_id, timestamp_delta))
            return True
        except Full:
            self.dropped_by_writer += 1
            return False

    def _worker(self):
        while not self.stop_event.is_set() or not self.q.empty():
            try:
                frame_bgr, frame_id, timestamp_delta = self.q.get(timeout=0.1)
            except Empty:
                continue

            try:
                self.writer.write(frame_bgr)
                self.f.write(f"{frame_id},{round(timestamp_delta)}\n")
            finally:
                self.q.task_done()


    def close(self):
        self.stop_event.set()
        self.thread.join()
        self.f.close()
        self.writer.release()# -*- coding: utf-8 -*-

