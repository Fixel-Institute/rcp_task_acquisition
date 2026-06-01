# -*- coding: utf-8 -*-
import cv2
import os

from rcp_task_acquisition.utils.logger import get_logger
from threading import Thread, Event
from queue import Queue, Full, Empty
import subprocess
import threading
logger = get_logger("./models/AsyncVideoWriter") 


class AsyncVideoWriter:
    STOP = object()
    
    def __init__(self, video_file, timestamp_file, fps, width, height,
                 max_queue=512, fourcc='mp4v'):
        self.video_file = video_file
        self.timestamp_file = timestamp_file
        self.fps = fps
        self.width = width
        self.height = height
        self.max_queue = max_queue
        self.fourcc = fourcc
        self.q = Queue(maxsize=max_queue)
        self.ready = Event()
        self.error = None
        self.stop_event = Event()
        self.dropped_by_writer = 0

        
        

        self.thread = Thread(target=self._worker, daemon=False)
        self.thread.start()
        self.ready.wait()
        
        if self.error is not None:
            raise self.error


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
        writer = None
        f = None
        
        try:
            writer = cv2.VideoWriter(
                self.video_file,
                cv2.VideoWriter_fourcc(*self.fourcc),
                self.fps,
                (self.width, self.height)
            )

            if not writer.isOpened():
                raise RuntimeError(f"Could not open video writer: {self.video_file}")

            f = open(self.timestamp_file, "w")
            f.write("frame_id,timestamp\n")
            self.ready.set()
        
            while not self.stop_event.is_set() or not self.q.empty():
                
                try:
                    
                    frame_bgr, frame_id, timestamp_delta = self.q.get(timeout=0.1)
                except Empty:
                    continue
    
                try:
                    writer.write(frame_bgr)
                    f.write(f"{frame_id},{round(timestamp_delta)}\n")
                finally:
                    self.q.task_done()
        except Exception as e:
            self.error = self.ready.set()
            logger.exception(f"Async video writer failed: {e}")
            
        finally:
            if f is not None:
                f.flush()
                os.fsync(f.fileno())
                f.close()
            if writer is not None:
                writer.release()
                


    def close(self):
        
        self.stop_event.set()
        # self.q.put(self.STOP)
        self.q.join()
        self.thread.join()
        
        if self.error is not None:
            raise self.error 
        # self.thread.join()
        # self.f.close()
        # self.writer.release()# -*- coding: utf-8 -*-

class AsyncFFmpegGPUWriter:
    STOP = object()

    def __init__(self, video_file, timestamp_file, fps, width, height,
                 max_queue=512, qp=23):
        self.video_file = video_file
        self.timestamp_file = timestamp_file
        self.fps = fps
        self.width = width
        self.height = height
        self.max_queue = max_queue
        self.qp = qp

        self.q = Queue(maxsize=max_queue)
        self.dropped_by_writer = 0
        self.error = None
        self.ready = threading.Event()
        logger.debug(f"FPS: {self.fps}")
        self.thread = threading.Thread(target=self._worker, daemon=False)
        self.thread.start()
        self.ready.wait()

        if self.error is not None:
            raise self.error

    def write(self, frame_bgr, frame_id, timestamp_delta):
        try:
            # Must enqueue an owned frame copy unless the producer already copied.
            self.q.put_nowait((frame_bgr, frame_id, timestamp_delta))
            return True
        except Full:
            self.dropped_by_writer += 1
            return False

    def _worker(self):
        proc = None
        f = None

        cmd = [
            "ffmpeg", "-y",
            "-f", "rawvideo",
            "-pix_fmt", "bgr24",
            "-s", f"{self.width}x{self.height}",
            "-r", str(self.fps),
            "-i", "-",
            "-an",
        
            "-c:v", "hevc_nvenc",
            "-preset", "p4",
            "-profile:v", "main",
            "-pix_fmt", "yuv420p",
        
            "-rc", "vbr",
            "-cq", str(self.qp),
            "-b:v", "0",
        
            "-movflags", "+faststart",
            self.video_file,
        ]

        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                bufsize=0
            )

            f = open(self.timestamp_file, "w")
            f.write("frame_id,timestamp\n")

            self.ready.set()

            while True:
                item = self.q.get()
                try:
                    if item is self.STOP:
                        return

                    frame_bgr, frame_id, timestamp_delta = item

                    # ffmpeg expects exactly width*height*3 bytes per frame.
                    # proc.stdin.write(frame_bgr.tobytes())
                    # proc.stdin.write(memoryview(frame_bgr))
                    proc.stdin.write(frame_bgr)
                    f.write(f"{frame_id},{round(timestamp_delta)}\n")

                finally:
                    self.q.task_done()

        except Exception as e:
            self.error = e
            self.ready.set()

        finally:
            if proc is not None and proc.stdin is not None:
                try:
                    proc.stdin.close()
                except Exception:
                    pass

            if proc is not None:
                stderr = proc.stderr.read().decode(errors="replace") if proc.stderr else ""
                ret = proc.wait()

                if ret != 0 and self.error is None:
                    self.error = RuntimeError(
                        f"ffmpeg exited with code {ret}\n{stderr[-4000:]}"
                    )

            if f is not None:
                f.flush()
                os.fsync(f.fileno())
                f.close()

    def close(self):
        self.q.put(self.STOP)
        self.q.join()
        self.thread.join()

        if self.error is not None:
            raise self.error