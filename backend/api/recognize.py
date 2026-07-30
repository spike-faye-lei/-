"""
食材识别接口
POST /recognize  - 接收图片, 返回识别结果
"""
import io
from fastapi import APIRouter, UploadFile, File, HTTPException
from PIL import Image
from backend.models.food_classifier import classifier

router = APIRouter(prefix="/api", tags=["recognize"])

@router.post("/recognize")
async def recognize(file: UploadFile = File(...)):
    """上传食材图片, 返回识别结果 + 营养信息"""
    if classifier.model is None:
        raise HTTPException(status_code=503, detail="模型未加载, 请先训练模型")

    contents = await file.read()
    try:
        image = Image.open(io.BytesIO(contents)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="无法解析图片, 请上传 JPG/PNG 格式")

    result = classifier.predict(image)
    topk = classifier.predict_topk(image, k=3)

    return {
        "success": True,
        "prediction": result,
        "top3": topk,
        "filename": file.filename,
    }

@router.post("/recognize/base64")
async def recognize_base64(data: dict):
    """接收 base64 编码的图片 (给手机端用)"""
    import base64
    if classifier.model is None:
        raise HTTPException(status_code=503, detail="模型未加载")

    try:
        img_data = base64.b64decode(data["image"])
        image = Image.open(io.BytesIO(img_data)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="图片解码失败")

    result = classifier.predict(image)
    return {"success": True, "prediction": result}
