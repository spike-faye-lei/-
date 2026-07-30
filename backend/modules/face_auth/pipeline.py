"""FacePipeline - MediaPipe + Facenet 人脸检测与识别管线"""
import asyncio
import base64
import math
import time
from pathlib import Path
from typing import Optional, Tuple, List, Dict

import cv2
import numpy as np
from loguru import logger

try:
    import mediapipe as mp
    HAS_MEDIAPIPE = hasattr(mp, 'solutions') or hasattr(mp, 'tasks')
    HAS_MEDIAPIPE_SOLUTIONS = hasattr(mp, 'solutions')
except ImportError:
    HAS_MEDIAPIPE = False
    HAS_MEDIAPIPE_SOLUTIONS = False
    logger.warning("mediapipe not installed, face detection disabled")

try:
    from deepface import DeepFace
    HAS_DEEPFACE = True
except ImportError:
    HAS_DEEPFACE = False
    logger.warning("deepface not installed, face recognition disabled")

from .models import SimilarityMatcher
from .utils import (
    decode_base64_frame, bgr_to_rgb,
    eye_aspect_ratio, mouth_aspect_ratio,
    estimate_head_pose_geometric, extract_face_roi,
    l2_normalize,
)


class FacePipeline:
    """人脸检测与识别管线

    流程: 摄像头帧 → MediaPipe 468点面网 → EAR/MAR/HeadPose →
          ROI裁剪 → Facenet 128维嵌入 → 余弦匹配
    """

    # MediaPipe 关键点索引
    LEFT_EYE_IDX = 33    # 左眼外角
    RIGHT_EYE_IDX = 263  # 右眼外角
    NOSE_TIP_IDX = 1     # 鼻尖
    CHIN_IDX = 152       # 下巴
    FOREHEAD_IDX = 10    # 眉心
    MOUTH_TOP = 13       # 上唇
    MOUTH_BOTTOM = 14    # 下唇
    MOUTH_LEFT = 61      # 左嘴角
    MOUTH_RIGHT = 291    # 右嘴角

    # 左右眼 6 点索引: [外眼角, 上1, 上2, 内眼角, 下1, 下2]
    LEFT_EYE_INDICES = [33, 160, 158, 133, 153, 144]
    RIGHT_EYE_INDICES = [362, 385, 387, 263, 373, 380]

    # 3D 模型点 (用于 solvePnP)
    MODEL_POINTS = np.array([
        [0.0, 0.0, 0.0],        # 鼻尖
        [0.0, -63.6, -12.5],    # 下巴
        [-43.3, 32.7, -26.0],   # 左眼外角
        [43.3, 32.7, -26.0],    # 右眼外角
        [-28.9, -28.9, -10.0],  # 左嘴角
        [28.9, -28.9, -10.0],   # 右嘴角
    ], dtype=np.float64)

    def __init__(
        self,
        model_name: str = "Facenet",
        recognition_threshold: float = 0.60,
        enrollment_frames: int = 10,
        data_dir: Optional[Path] = None,
    ):
        self.model_name = model_name
        self.recognition_threshold = recognition_threshold
        self.enrollment_frames = enrollment_frames
        self.data_dir = data_dir or Path("face_data")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self._face_mesh = None
        self._camera_matrix = None
        self._dist_coeffs = None

        if HAS_MEDIAPIPE:
            self._init_mediapipe()

        self._matcher = SimilarityMatcher(threshold=recognition_threshold, margin=0.10)
        self._enrolled: Dict[str, np.ndarray] = {}
        self._load_enrolled()

        # 连续眨眼检测状态
        self._blink_counter: Dict[int, int] = {}
        self._blink_required_frames = 3
        self._blink_ear_threshold = 0.20

    def _init_mediapipe(self):
        if HAS_MEDIAPIPE_SOLUTIONS:
            mp_face_mesh = mp.solutions.face_mesh
            self._face_mesh = mp_face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=5,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
            self._use_tasks_api = False
        elif hasattr(mp, 'tasks'):
            # mediapipe >= 0.10.0 tasks API
            from mediapipe.tasks import python as mp_python
            from mediapipe.tasks.python import vision
            try:
                model_path = str(Path(__file__).parent / "face_landmarker.task")
                if not Path(model_path).exists():
                    logger.warning(f"MediaPipe model not found at {model_path}, face detection may not work")
                    self._face_mesh = None
                    self._use_tasks_api = False
                    return
                base_options = mp_python.BaseOptions(model_asset_path=model_path)
                options = vision.FaceLandmarkerOptions(
                    base_options=base_options,
                    running_mode=vision.RunningMode.IMAGE,
                    num_faces=5,
                )
                self._face_landmarker = vision.FaceLandmarker.create_from_options(options)
                self._use_tasks_api = True
                logger.info("Using mediapipe tasks API for face detection")
            except Exception as e:
                logger.warning(f"Failed to init mediapipe tasks API: {e}")
                self._face_mesh = None
                self._use_tasks_api = False
        else:
            self._face_mesh = None
            self._use_tasks_api = False

        focal_length = 640
        center = (320, 240)
        self._camera_matrix = np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1],
        ], dtype=np.float64)
        self._dist_coeffs = np.zeros((4, 1), dtype=np.float64)

    def _load_enrolled(self):
        """加载已注册用户的嵌入向量"""
        for npy_file in self.data_dir.glob("*.npy"):
            username = npy_file.stem
            embedding = np.load(str(npy_file))
            self._enrolled[username] = embedding
            logger.info(f"Loaded enrolled face: {username}")

    def save_enrollment(self, username: str, embedding: np.ndarray):
        np.save(str(self.data_dir / f"{username}.npy"), embedding)
        self._enrolled[username] = embedding
        logger.info(f"Enrolled new face: {username}")

    def remove_enrollment(self, username: str):
        filepath = self.data_dir / f"{username}.npy"
        if filepath.exists():
            filepath.unlink()
        self._enrolled.pop(username, None)
        logger.info(f"Removed enrolled face: {username}")

    def decode_frame(self, b64_data: str) -> Optional[np.ndarray]:
        """base64 → BGR image"""
        return decode_base64_frame(b64_data)

    # ---- 活体检测 ----

    def _ear(self, landmarks, eye_indices: List[int]) -> float:
        """Eye Aspect Ratio - 眨眼检测"""
        pts = [landmarks[i] for i in eye_indices]
        vertical_1 = self._distance(pts[1], pts[5])
        vertical_2 = self._distance(pts[2], pts[4])
        horizontal = self._distance(pts[0], pts[3])
        if horizontal < 1e-6:
            return 1.0
        return (vertical_1 + vertical_2) / (2.0 * horizontal)

    def detect_blink(self, landmarks, face_index: int = 0) -> bool:
        """眨眼检测 — 连续 3 帧 EAR < 0.20 判定为一次眨眼

        照片无法动态改变 EAR，重放视频也难以精确配合随机时刻。
        """
        left_ear = eye_aspect_ratio(landmarks, self.LEFT_EYE_INDICES)
        right_ear = eye_aspect_ratio(landmarks, self.RIGHT_EYE_INDICES)
        avg_ear = (left_ear + right_ear) / 2.0

        current_blink = avg_ear < self._blink_ear_threshold

        if current_blink:
            self._blink_counter[face_index] = self._blink_counter.get(face_index, 0) + 1
        else:
            self._blink_counter[face_index] = 0

        return self._blink_counter.get(face_index, 0) >= self._blink_required_frames

    def detect_mouth_open(self, landmarks) -> bool:
        """Mouth Aspect Ratio — 张嘴检测"""
        mar = mouth_aspect_ratio(
            landmarks,
            self.MOUTH_TOP, self.MOUTH_BOTTOM,
            self.MOUTH_LEFT, self.MOUTH_RIGHT,
        )
        return mar > 0.70

    # ---- 头部姿态 ----

    def estimate_head_pose_geometric(self, landmarks) -> Tuple[float, float, float]:
        """几何近似法估计头部姿态 (yaw, pitch, roll)"""
        return estimate_head_pose_geometric(
            landmarks,
            self.NOSE_TIP_IDX, self.FOREHEAD_IDX, self.CHIN_IDX,
            self.LEFT_EYE_IDX, self.RIGHT_EYE_IDX,
        )

    def estimate_head_pose_solvepnp(self, landmarks) -> Optional[Tuple[float, float, float]]:
        """solvePnP 精确姿态估计"""
        image_points = np.array([
            landmarks[self.NOSE_TIP_IDX],
            landmarks[self.CHIN_IDX],
            landmarks[self.LEFT_EYE_IDX],
            landmarks[self.RIGHT_EYE_IDX],
            landmarks[self.MOUTH_LEFT],
            landmarks[self.MOUTH_RIGHT],
        ], dtype=np.float64)

        success, rvec, tvec = cv2.solvePnP(
            self.MODEL_POINTS, image_points,
            self._camera_matrix, self._dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE,
        )
        if not success:
            return None

        rot_mat, _ = cv2.Rodrigues(rvec)
        sy = math.sqrt(rot_mat[0, 0] ** 2 + rot_mat[1, 0] ** 2)
        singular = sy < 1e-6
        if not singular:
            pitch = math.atan2(-rot_mat[2, 0], sy)
            yaw = math.atan2(rot_mat[1, 0], rot_mat[0, 0])
            roll = math.atan2(rot_mat[2, 1], rot_mat[2, 2])
        else:
            pitch = math.atan2(-rot_mat[2, 0], sy)
            yaw = math.atan2(-rot_mat[1, 2], rot_mat[1, 1])
            roll = 0
        return math.degrees(yaw), math.degrees(pitch), math.degrees(roll)

    def estimate_head_pose(self, landmarks) -> Tuple[float, float, float]:
        """头部姿态估计 - solvePnP 优先，失败时降级到几何近似"""
        if landmarks and HAS_MEDIAPIPE_SOLUTIONS:
            result = self.estimate_head_pose_solvepnp(landmarks)
            if result is not None:
                return result
        if landmarks:
            return self.estimate_head_pose_geometric(landmarks)
        return (0.0, 0.0, 0.0)

    # ---- 人脸检测与嵌入 ----

    def detect_faces(self, frame: np.ndarray) -> List[dict]:
        """检测帧中的所有人脸

        优先级:
        1. MediaPipe solutions API (旧版 mp.solutions)
        2. MediaPipe tasks API (新版 mp.tasks, >=0.10.0)
        3. OpenCV Haar Cascade 后备
        4. DeepFace detect 最后后备
        """
        # 方法 1: MediaPipe solutions API
        if self._face_mesh is not None and HAS_MEDIAPIPE_SOLUTIONS:
            rgb = bgr_to_rgb(frame)
            results = self._face_mesh.process(rgb)
            if results.multi_face_landmarks:
                faces = []
                h, w = frame.shape[:2]
                for face_lms in results.multi_face_landmarks:
                    landmarks = [(int(lm.x * w), int(lm.y * h)) for lm in face_lms.landmark]
                    xs = [p[0] for p in landmarks]; ys = [p[1] for p in landmarks]
                    bbox = (min(xs) - 20, min(ys) - 30, max(xs) - min(xs) + 40, max(ys) - min(ys) + 50)
                    faces.append({"bbox": bbox, "landmarks": landmarks})
                return faces
            return []

        # 方法 2: MediaPipe tasks API
        if getattr(self, '_use_tasks_api', False) and hasattr(self, '_face_landmarker'):
            rgb = bgr_to_rgb(frame)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = self._face_landmarker.detect(mp_image)
            if result.face_landmarks:
                faces = []
                h, w = frame.shape[:2]
                for face_lms in result.face_landmarks:
                    landmarks = [(int(lm.x * w), int(lm.y * h)) for lm in face_lms]
                    xs = [p[0] for p in landmarks]; ys = [p[1] for p in landmarks]
                    bbox = (min(xs) - 20, min(ys) - 30, max(xs) - min(xs) + 40, max(ys) - min(ys) + 50)
                    faces.append({"bbox": bbox, "landmarks": landmarks})
                return faces
            return []

        # 方法 3: OpenCV Haar Cascade
        cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        rects = cascade.detectMultiScale(gray, 1.1, 5, minSize=(80, 80))
        if len(rects) > 0:
            return [{"bbox": (int(x), int(y), int(w), int(h)), "landmarks": None} for (x, y, w, h) in rects]

        # 方法 4: DeepFace 后备
        if HAS_DEEPFACE:
            try:
                df_result = DeepFace.extract_faces(
                    img_path=frame,
                    detector_backend='opencv',
                    enforce_detection=False,
                )
                if df_result:
                    faces = []
                    for item in df_result:
                        area = item.get('facial_area', {})
                        x, y, w, h = area.get('x', 0), area.get('y', 0), area.get('w', 0), area.get('h', 0)
                        if w > 0 and h > 0:
                            faces.append({"bbox": (x, y, w, h), "landmarks": None})
                    return faces
            except Exception:
                pass

        return []

    def extract_face_roi(self, frame: np.ndarray, face: dict,
                         size: int = 128) -> Optional[np.ndarray]:
        """裁剪人脸 ROI → 128×128"""
        return extract_face_roi(frame, face["bbox"], size)

    def extract_embedding(self, face_img: np.ndarray) -> Optional[np.ndarray]:
        """Facenet 128维嵌入"""
        if not HAS_DEEPFACE:
            return None
        try:
            result = DeepFace.represent(
                img_path=face_img,
                model_name=self.model_name,
                enforce_detection=False,
            )
            emb = np.array(result[0]["embedding"], dtype=np.float32)
            return emb / np.linalg.norm(emb)  # L2 归一化
        except Exception as e:
            logger.warning(f"Embedding extraction failed: {e}")
            return None

    def identify(self, embedding: np.ndarray) -> Optional[Tuple[str, float]]:
        """余弦相似度匹配 — 阈值 ≥ 0.60 + 最高/次高分差值 > 0.10"""
        match, score, _ = self._matcher.match(embedding, self._enrolled)
        if match:
            return match, score
        return None

    def enroll(self, username: str, frames: List[str]) -> Tuple[bool, str]:
        """注册人脸 - 多帧取均值嵌入"""
        embeddings = []
        for b64 in frames:
            frame = self.decode_frame(b64)
            if frame is None:
                continue
            faces = self.detect_faces(frame)
            if not faces:
                continue
            for face in faces[:1]:
                roi = self.extract_face_roi(frame, face)
                if roi is None:
                    continue
                emb = self.extract_embedding(roi)
                if emb is not None:
                    embeddings.append(emb)

        if len(embeddings) < self.enrollment_frames:
            return False, f"需要至少 {self.enrollment_frames} 帧有效人脸, 当前 {len(embeddings)}"

        mean_embedding = np.mean(embeddings, axis=0)
        mean_embedding = mean_embedding / np.linalg.norm(mean_embedding)
        self.save_enrollment(username, mean_embedding)
        return True, f"注册成功, 使用 {len(embeddings)} 帧"

    def process_frame(self, b64_data: str) -> dict:
        """处理单帧 - 返回完整分析结果"""
        result = {
            "faces": [],
            "success": False,
        }

        frame = self.decode_frame(b64_data)
        if frame is None:
            result["error"] = "frame_decode_failed"
            return result

        faces = self.detect_faces(frame)
        result["success"] = True

        for i, face in enumerate(faces[:3]):  # 最多3张脸
            face_data = {"index": i}

            if face["landmarks"] and len(face["landmarks"]) >= 468:
                lm = face["landmarks"]
                left_ear = eye_aspect_ratio(lm, self.LEFT_EYE_INDICES)
                right_ear = eye_aspect_ratio(lm, self.RIGHT_EYE_INDICES)
                face_data["ear"] = round((left_ear + right_ear) / 2.0, 3)
                face_data["blink"] = self.detect_blink(lm, i)
                face_data["mar"] = round(mouth_aspect_ratio(lm, self.MOUTH_TOP, self.MOUTH_BOTTOM, self.MOUTH_LEFT, self.MOUTH_RIGHT), 3)
                face_data["mouth_open"] = self.detect_mouth_open(lm)
                yaw, pitch, roll = self.estimate_head_pose(lm)
                face_data["head_pose"] = {
                    "yaw": round(yaw, 1),
                    "pitch": round(pitch, 1),
                    "roll": round(roll, 1),
                }

            roi = self.extract_face_roi(frame, face)
            if roi is not None:
                emb = self.extract_embedding(roi)
                if emb is not None:
                    ident = self.identify(emb)
                    if ident:
                        face_data["identified"] = True
                        face_data["username"] = ident[0]
                        face_data["confidence"] = round(float(ident[1]), 3)
                    else:
                        face_data["identified"] = False
                        face_data["username"] = "unknown"

            result["faces"].append(face_data)

        return result
