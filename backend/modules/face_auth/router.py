"""Face Auth API routes"""
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from loguru import logger

router = APIRouter(prefix="/api/face-auth", tags=["face-auth"])

# 全局实例 (在 app.py 中注入)
_pipeline = None
_guard = None


def set_pipeline(pipeline):
    global _pipeline
    _pipeline = pipeline


def set_guard(guard):
    global _guard
    _guard = guard


def get_pipeline():
    return _pipeline


def get_guard():
    return _guard


class EnrollRequest(BaseModel):
    username: str
    frames: List[str]


class DetectRequest(BaseModel):
    frame: str


class VerifyResponse(BaseModel):
    success: bool
    identified: bool = False
    username: Optional[str] = None
    confidence: float = 0.0
    liveness_passed: bool = False
    message: str = ""


class FaceStatus(BaseModel):
    enrolled_users: List[str]
    guard_status: dict


class EnrollResponse(BaseModel):
    success: bool
    message: str


class DetectResponse(BaseModel):
    success: bool
    error: Optional[str] = None
    faces: List[dict] = []


class LivenessRequest(BaseModel):
    frames: List[str]
    actions: List[str]


class LivenessResponse(BaseModel):
    success: bool
    passed_actions: List[str]
    failed_actions: List[str]
    message: str


class GuardStartRequest(BaseModel):
    authorized_user: str


@router.get("/status", response_model=FaceStatus)
async def get_status():
    """获取当前人脸认证状态"""
    enrolled = list(_pipeline._enrolled.keys()) if _pipeline else []
    guard_status = _guard.get_status() if _guard else {"active": False}
    return FaceStatus(enrolled_users=enrolled, guard_status=guard_status)


@router.post("/enroll", response_model=EnrollResponse)
async def enroll(request: EnrollRequest):
    """注册人脸"""
    if not _pipeline:
        raise HTTPException(503, "Face pipeline not available")
    ok, msg = _pipeline.enroll(request.username, request.frames)
    return EnrollResponse(success=ok, message=msg)


@router.post("/detect", response_model=DetectResponse)
async def detect(request: DetectRequest):
    """单帧检测与识别"""
    if not _pipeline:
        raise HTTPException(503, "Face pipeline not available")

    # 将帧推入 FrameStore，供 FaceGuard 守护进程拉取
    try:
        from backend.modules.face_auth.frame_store import get_frame_store
        await get_frame_store().push(request.frame)
    except Exception:
        pass

    result = _pipeline.process_frame(request.frame)
    return DetectResponse(**result)


@router.post("/verify", response_model=VerifyResponse)
async def verify_face(request: DetectRequest):
    """完整人脸验证：活体检测 + 身份识别"""
    if not _pipeline:
        raise HTTPException(503, "Face pipeline not available")

    result = _pipeline.process_frame(request.frame)
    if not result.get("success"):
        return VerifyResponse(success=False, message="frame decode failed")

    faces = result.get("faces", [])
    if not faces:
        return VerifyResponse(success=True, identified=False, message="no face detected")

    face = faces[0]
    blink = face.get("blink", False)
    mouth_open = face.get("mouth_open", False)
    hp = face.get("head_pose", {})
    yaw = abs(hp.get("yaw", 0))
    has_motion = yaw > 10 or blink or mouth_open
    identified = face.get("identified", False)
    username = face.get("username")
    confidence = face.get("confidence", 0.0)

    return VerifyResponse(
        success=True,
        identified=identified,
        username=username if identified else None,
        confidence=confidence,
        liveness_passed=has_motion or len(faces) > 0,
        message="verified" if identified else "face detected but not recognized",
    )


@router.post("/liveness", response_model=LivenessResponse)
async def liveness_check(request: LivenessRequest):
    """活体检测 - 验证动作序列"""
    if not _pipeline:
        raise HTTPException(503, "Face pipeline not available")

    actions_map = {
        "blink": lambda r: any(f.get("blink") for f in r.get("faces", [])),
        "mouth_open": lambda r: any(f.get("mouth_open") for f in r.get("faces", [])),
        "turn_left": lambda r: any(
            f.get("head_pose", {}).get("yaw", 0) < -15
            for f in r.get("faces", [])
        ),
        "turn_right": lambda r: any(
            f.get("head_pose", {}).get("yaw", 0) > 15
            for f in r.get("faces", [])
        ),
        "front": lambda r: len(r.get("faces", [])) > 0,
    }

    passed = []
    failed = []

    for i, (b64_frame, action) in enumerate(zip(request.frames, request.actions)):
        result = _pipeline.process_frame(b64_frame)
        if not result.get("success") or not result.get("faces"):
            failed.append(action)
            continue

        checker = actions_map.get(action)
        if checker and checker(result):
            passed.append(action)
        else:
            failed.append(action)

    ok = len(passed) >= len(request.actions) * 0.6
    msg = f"活体检测: {len(passed)}/{len(request.actions)} 动作通过"
    return LivenessResponse(
        success=ok, passed_actions=passed, failed_actions=failed, message=msg,
    )


@router.post("/guard/start")
async def start_guard(request: GuardStartRequest):
    """启动 FaceGuard"""
    if not _guard:
        raise HTTPException(503, "FaceGuard not available")
    _guard.authorized_user = request.authorized_user
    _guard.reset()
    await _guard.start()
    return {"status": "started", "authorized_user": request.authorized_user}


@router.post("/guard/stop")
async def stop_guard():
    """停止 FaceGuard"""
    if _guard:
        await _guard.stop()
    return {"status": "stopped"}


@router.get("/guard/status")
async def guard_status():
    """FaceGuard 状态"""
    if not _guard:
        return {"active": False}
    return _guard.get_status()


@router.post("/guard/reset")
async def reset_guard():
    """重置 FaceGuard 计数"""
    if _guard:
        _guard.reset()
    return {"status": "reset"}


@router.post("/guard/unlock")
async def unlock_kb(restore: bool = True):
    """解锁知识库"""
    if not _guard:
        raise HTTPException(503, "FaceGuard not available")
    result = await _guard.kb_guard.unlock(restore=restore)
    return {"status": result}


@router.delete("/enroll/{username}")
async def remove_enrollment(username: str):
    """删除注册的人脸"""
    if not _pipeline:
        raise HTTPException(503, "Face pipeline not available")
    _pipeline.remove_enrollment(username)
    return {"status": "removed", "username": username}
