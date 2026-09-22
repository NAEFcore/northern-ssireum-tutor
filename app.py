import math
import os
import tempfile
from collections import deque
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
import streamlit as st
import yt_dlp

st.set_page_config(
    page_title="Northern Ssireum Motion Trajectory",
    page_icon="🤼",
    layout="wide",
)

st.title("🤼 Northern Ssireum Motion Trajectory Analysis")
st.caption("YouTube video → actual frame analysis → Hip Center trajectory")

st.markdown(
    """
**Blue = Player A · Red = Player B**

The trajectory is drawn directly onto the analyzed video frames.
"""
)

mp_pose = mp.solutions.pose
mp_draw = mp.solutions.drawing_utils


class DualWrestlerTracker:
    def __init__(self, max_points=180):
        self.left_pose = mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            smooth_landmarks=True,
            min_detection_confidence=0.40,
            min_tracking_confidence=0.40,
        )
        self.right_pose = mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            smooth_landmarks=True,
            min_detection_confidence=0.40,
            min_tracking_confidence=0.40,
        )
        self.a = deque(maxlen=max_points)
        self.b = deque(maxlen=max_points)
        self.last_a = None
        self.last_b = None

    def close(self):
        self.left_pose.close()
        self.right_pose.close()

    @staticmethod
    def hip_center(result, width, height, offset_x=0):
        if not result or not result.pose_landmarks:
            return None

        lm = result.pose_landmarks.landmark
        lh = lm[mp_pose.PoseLandmark.LEFT_HIP]
        rh = lm[mp_pose.PoseLandmark.RIGHT_HIP]

        if max(lh.visibility, rh.visibility) < 0.25:
            return None

        x = int(((lh.x + rh.x) / 2) * width) + offset_x
        y = int(((lh.y + rh.y) / 2) * height)

        if x < 0 or y < 0:
            return None

        return x, y

    def assign(self, left_center, right_center, width, height):
        default_a = (int(width * 0.35), int(height * 0.55))
        default_b = (int(width * 0.65), int(height * 0.55))

        if self.last_a is None or self.last_b is None:
            a = left_center or default_a
            b = right_center or default_b
        elif left_center and right_center:
            normal = (
                math.dist(left_center, self.last_a)
                + math.dist(right_center, self.last_b)
            )
            flipped = (
                math.dist(right_center, self.last_a)
                + math.dist(left_center, self.last_b)
            )
            a, b = (
                (left_center, right_center)
                if normal <= flipped
                else (right_center, left_center)
            )
        elif left_center:
            if math.dist(left_center, self.last_a) <= math.dist(left_center, self.last_b):
                a, b = left_center, self.last_b
            else:
                a, b = self.last_a, left_center
        elif right_center:
            if math.dist(right_center, self.last_a) <= math.dist(right_center, self.last_b):
                a, b = right_center, self.last_b
            else:
                a, b = self.last_a, right_center
        else:
            a, b = self.last_a, self.last_b

        self.last_a, self.last_b = a, b
        return a, b

    def process(self, frame):
        h, w = frame.shape[:2]
        mid = w // 2

        left = frame[:, :mid]
        right = frame[:, mid:]

        r1 = self.left_pose.process(cv2.cvtColor(left, cv2.COLOR_BGR2RGB))
        r2 = self.right_pose.process(cv2.cvtColor(right, cv2.COLOR_BGR2RGB))

        c1 = self.hip_center(r1, mid, h, 0)
        c2 = self.hip_center(r2, w - mid, h, mid)

        a, b = self.assign(c1, c2, w, h)

        self.a.append(a)
        self.b.append(b)

        out = frame.copy()

        # Actual skeletons from the analyzed frames.
        if r1.pose_landmarks:
            mp_draw.draw_landmarks(
                out[:, :mid],
                r1.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
            )
        if r2.pose_landmarks:
            mp_draw.draw_landmarks(
                out[:, mid:],
                r2.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
            )

        # Actual accumulated trajectories.
        for points, color in (
            (self.a, (255, 0, 0)),      # Blue
            (self.b, (0, 0, 255)),      # Red
        ):
            pts = list(points)
            for i in range(1, len(pts)):
                cv2.line(out, pts[i - 1], pts[i], color, 3, cv2.LINE_AA)

        for point, color, label in (
            (a, (255, 0, 0), "A"),
            (b, (0, 0, 255), "B"),
        ):
            cv2.circle(out, point, 10, (255, 255, 255), -1)
            cv2.circle(out, point, 7, color, -1)
            cv2.putText(
                out,
                f"{label} Hip Center",
                (point[0] + 10, point[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

        cv2.line(out, a, b, (180, 180, 180), 2, cv2.LINE_AA)

        return out


def download_youtube(url):
    temp_dir = tempfile.mkdtemp(prefix="ssireum_")
    output = str(Path(temp_dir) / "source.%(ext)s")

    options = {
        "format": "bestvideo[ext=mp4][height<=720]/best[ext=mp4]/best",
        "outtmpl": output,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)

    if not os.path.exists(filename):
        mp4_files = list(Path(temp_dir).glob("*"))
        if not mp4_files:
            raise RuntimeError("YouTube video could not be downloaded.")
        filename = str(mp4_files[0])

    return filename


def analyze_video(source_path, max_seconds=30):
    cap = cv2.VideoCapture(source_path)
    if not cap.isOpened():
        raise RuntimeError("The downloaded video could not be opened.")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    frame_limit = min(total, int(fps * max_seconds)) if total else int(fps * max_seconds)

    out_dir = tempfile.mkdtemp(prefix="ssireum_result_")
    result_path = str(Path(out_dir) / "trajectory_analysis.mp4")

    writer = cv2.VideoWriter(
        result_path,
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )

    tracker = DualWrestlerTracker()
    progress = st.progress(0)
    status = st.empty()

    try:
        for index in range(frame_limit):
            ok, frame = cap.read()
            if not ok:
                break

            analyzed = tracker.process(frame)
            writer.write(analyzed)

            if index % 5 == 0:
                progress.progress(min((index + 1) / frame_limit, 1.0))
                status.write(f"Analyzing frame {index + 1} / {frame_limit}")

    finally:
        cap.release()
        writer.release()
        tracker.close()

    progress.progress(1.0)
    status.success("Analysis complete.")
    return result_path


with st.sidebar:
    st.header("Analysis Settings")
    max_seconds = st.slider(
        "Analysis length",
        min_value=5,
        max_value=60,
        value=20,
        step=5,
    )
    st.caption("Start with a short clip for testing.")

url = st.text_input(
    "YouTube URL",
    placeholder="https://www.youtube.com/watch?v=...",
)

if url:
    st.subheader("① Original YouTube Video")
    st.video(url)

    if st.button("▶ Analyze Motion Trajectory", type="primary"):
        try:
            with st.spinner("Downloading the actual YouTube video..."):
                source = download_youtube(url)

            st.info("The downloaded video is now being analyzed frame-by-frame.")

            result = analyze_video(source, max_seconds=max_seconds)

            st.subheader("② Actual Video + Skeleton + Hip Center Trajectory")
            with open(result, "rb") as f:
                video_bytes = f.read()

            st.video(video_bytes)

            st.download_button(
                "Download trajectory analysis video",
                data=video_bytes,
                file_name="trajectory_analysis.mp4",
                mime="video/mp4",
            )

        except Exception as exc:
            st.error(f"Analysis failed: {exc}")
            st.info(
                "If the error is related to YouTube downloading, try another public "
                "YouTube video URL first."
            )
else:
    st.info("Enter a public YouTube URL to begin.")
