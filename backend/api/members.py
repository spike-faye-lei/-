"""
家庭成员管理接口
"""
from fastapi import APIRouter, Query, HTTPException
from backend.database import get_members, add_member, delete_member, update_member_goal

router = APIRouter(prefix="/api", tags=["members"])

@router.get("/members")
async def list_members():
    return {"members": get_members()}

@router.post("/members")
async def create_member(name: str = Query(...), health_goal: str = Query("maintain")):
    result = add_member(name, health_goal)
    if not result:
        raise HTTPException(status_code=400, detail=f"添加失败，'{name}' 可能已存在")
    return {"success": True, "member": result}

@router.delete("/members/{member_id}")
async def remove_member(member_id: int):
    delete_member(member_id)
    return {"success": True}

@router.put("/members/{name}/goal")
async def set_goal(name: str, health_goal: str = Query(...)):
    update_member_goal(name, health_goal)
    return {"success": True}
