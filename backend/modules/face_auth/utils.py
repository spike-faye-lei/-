"""Face Auth 工具函数 — 几何计算、图像裁剪、BGR↔RGB 转换"""

import base64
import math
from typing import List, Optional, Tuple

import cv2
import numpy as np


def decode_base64_frame(b64_data: str) -> Optional[np.ndarray]:
    """base64 → BGR image (numpy array)"""
    try:
        if "," in b64_data:
            b64_data = b64_data.split(",", 1)[1]
        raw = base64.b64decode(b64_data)
        arr = np.frombuffer(raw, dtype=np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)
    except Exception:
        return None


def bgr_to_rgb(frame: np.ndarray) -> np.ndarray:
    """BGR → RGB (MediaPipe 需要 RGB)"""
    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)


def rgb_to_bgr(frame: np.ndarray) -> np.ndarray:
    """RGB → BGR"""
    return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)


def point_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """两点欧式距离"""
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def eye_aspect_ratio(landmarks: List[Tuple[int, int]],
                     eye_indices: List[int]) -> float:
    """Eye Aspect Ratio — 眨眼检测

    公式: (|p2-p6| + |p3-p5|) / (2 * |p1-p4|)

    Args:
        landmarks: 468点列表 [(x,y), ...]
        eye_indices: 眼睛6点索引 [p1,p2,p3,p4,p5,p6]
                     p1=外眼角, p4=内眼角
    """
    if len(eye_indices) != 6:
        return 1.0
    pts = [landmarks[i] for i in eye_indices]
    v1 = point_distance(pts[1], pts[5])
    v2 = point_distance(pts[2], pts[4])
    h = point_distance(pts[0], pts[3])
    if h < 1e-6:
        return 1.0
    return (v1 + v2) / (2.0 * h)


def mouth_aspect_ratio(landmarks: List[Tuple[int, int]],
                       top: int, bottom: int,
                       left: int, right: int) -> float:
    """Mouth Aspect Ratio — 张嘴检测"""
    return point_distance(landmarks[top], landmarks[bottom]) / \
           max(point_distance(landmarks[left], landmarks[right]), 1e-6)


def estimate_head_pose_geometric(
    landmarks: List[Tuple[int, int]],
    nose_idx: int, forehead_idx: int, chin_idx: int,
    left_eye_idx: int, right_eye_idx: int,
) -> Tuple[float, float, float]:
    """几何近似法估计头部姿态 (yaw, pitch, roll)

    系数解释:
    - 120: 将像素偏差映射到角度的经验放大因子 (640px 摄像头)
    - 200: 俯仰映射因子
    - 0.18: 正面时眉心与下巴垂直距离的基线归一化值
    """
    nose = landmarks[nose_idx]
    forehead = landmarks[forehead_idx]
    chin = landmarks[chin_idx]
    left_eye = landmarks[left_eye_idx]
    right_eye = landmarks[right_eye_idx]

    face_center_x = (left_eye[0] + right_eye[0]) / 2
    yaw = (nose[0] - face_center_x) * 120.0

    # 归一化：眉心到下巴的垂直距离
    face_height = max(forehead[1] - chin[1], 1e-6)
    pitch = (forehead[1] - chin[1] - 0.18) * 200.0 * (480.0 / face_height)

    roll = math.atan2(
        right_eye[1] - left_eye[1],
        right_eye[0] - left_eye[0] + 1e-6,
    )
    return yaw, pitch, roll


def extract_face_roi(
    frame: np.ndarray,
    bbox: Tuple[int, int, int, int],
    output_size: int = 128,
) -> Optional[np.ndarray]:
    """裁剪并缩放人脸区域

    Args:
        frame: BGR 图像
        bbox: (x, y, w, h)
        output_size: 输出尺寸 (正方形)

    Returns:
        128×128 BGR 图像 或 None
    """
    x, y, w, h = bbox
    x = max(0, x)
    y = max(0, y)
    w = min(w, frame.shape[1] - x)
    h = min(h, frame.shape[0] - y)
    if w <= 0 or h <= 0:
        return None
    roi = frame[y:y + h, x:x + w]
    return cv2.resize(roi, (output_size, output_size))


def l2_normalize(vec: np.ndarray) -> np.ndarray:
    """L2 归一化"""
    norm = np.linalg.norm(vec)
    if norm < 1e-6:
        return vec
    return vec / norm


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """余弦相似度 (均需预先 L2 归一化)"""
    return float(np.dot(a, b))
