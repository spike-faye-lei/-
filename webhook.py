"""Webhook 入口：让外部系统（钉钉/飞书审批流、企业微信、招聘平台回调）触发 AI 招聘流程

HR 不用打开网页：在钉钉里点一下（应用回调）→ 简历自动入库 → 自动解析 → 进入待初筛队列。
系统自动处理完，结果经 notify_channels 推回钉钉群。

接口：
    POST /webhook/resume-uploaded
    JSON: {"candidate_name": "张三", "resume_text": "简历全文...", "source": "钉钉审批流", "job_title": "AI 应用开发工程师"}
    响应: {"status": "accepted", "candidate_id": 123}

挂载方式（app.py）：
    from webhook import mount_webhook
    mount_webhook(demo)   # demo 为 gr.Blocks 实例（内部 FastAPI app 挂路由）
"""
import json
import os
import re

try:
    from config import load_dotenv
    load_dotenv()
except ImportError:
    pass

from algorithms import extract_fields
from db import (
    add_candidate,
    delete_candidate_data,
    get_interview,
    mark_notification_sent,
    update_candidate,
    update_interview_hr,
)
from job_profile import add_hr_feedback
from notify_channels import notify

# Webhook 鉴权：.env 配置 WEBHOOK_API_KEY 后，请求必须带 X-API-Key 头（防外部灌脏数据）
WEBHOOK_API_KEY = os.environ.get("WEBHOOK_API_KEY", "")


def check_api_key(headers: dict) -> bool:
    """校验 X-API-Key（未配置 WEBHOOK_API_KEY 时仅本机 127.0.0.1 可访问，配置后必须匹配）"""
    if not WEBHOOK_API_KEY:
        return True  # 服务只绑定 127.0.0.1，未配置 Key 时本机可访问（演示模式）
    return headers.get("X-API-Key", "") == WEBHOOK_API_KEY


def on_hr_decision(payload: dict) -> dict:
    """处理外部推送的 HR 审核决策（钉钉审批流点「通过/驳回」→ 自动回写系统）

    payload: {"interview_id": 123, "decision": "通过"|"驳回", "comment": "意见"}
    动作：回写面试结论 + 岗位反馈校准 + 通知/Offer 自动生成 + 群机器人推送结果。
    HR 全程不用打开网页——「无感集成」闭环的最后一步。
    """
    iid = (payload or {}).get("interview_id")
    decision = (payload or {}).get("decision", "")
    comment = (payload or {}).get("comment", "") or ""
    if not iid or decision not in ("通过", "驳回"):
        return {"status": "error", "message": "需要 interview_id 和 decision（通过/驳回）"}
    rec = get_interview(iid)
    if not rec:
        return {"status": "error", "message": f"面试记录 #{iid} 不存在"}
    # 延迟导入避免模块加载环（handlers 依赖 notify_channels/db，不依赖 webhook）
    from handlers import _link_candidate_flow
    update_interview_hr(iid, decision, comment)
    add_hr_feedback(decision, comment, rec.get("job") or "")
    nid = _link_candidate_flow(rec.get("candidate", ""), rec.get("job") or "", decision, "")
    if nid:
        mark_notification_sent(nid, "钉钉")
    notify("钉钉", f"【AI 招聘】{rec.get('candidate')} 审核结果：{decision}（来源：钉钉审批流）")
    return {"status": "accepted", "interview_id": iid, "message": f"#{iid} 已回写 {decision}"}


def on_data_deletion(payload: dict) -> dict:
    """候选人数据删除（PIPL 删除权）：候选人要求删除 → 全链路数据 + 简历文件清除"""
    cid = (payload or {}).get("candidate_id")
    name = (payload or {}).get("candidate_name")
    if not cid and not name:
        return {"status": "error", "message": "需要 candidate_id 或 candidate_name"}
    deleted = delete_candidate_data(candidate_id=cid, candidate_name=name)
    return {"status": "accepted", "deleted_records": deleted,
            "message": f"已删除 {deleted} 条关联记录（简历文件同步清除），符合 PIPL 删除权要求"}


def _dispatch(path: str, payload: dict) -> dict:
    """Webhook 路由分发"""
    if path == "/webhook/resume-uploaded":
        return on_resume_uploaded(payload)
    if path == "/webhook/hr-decision":
        return on_hr_decision(payload)
    if path == "/webhook/data-deletion":
        return on_data_deletion(payload)
    return {"status": "error", "message": "路由不存在"}


def on_resume_uploaded(payload: dict) -> dict:
    """处理外部推送的简历：入库 → 代码侧解析 → 状态「已解析」→ 通知 HR

    返回 {"status": "accepted"|"error", "candidate_id", "message"}
    异步面试启动（start_interview_async）在企业版以任务队列实现，
    MVP 阶段候选人自动进入待初筛队列，由「智能初筛」批量处理。
    """
    resume_text = (payload or {}).get("resume_text", "")
    if not resume_text or not resume_text.strip():
        return {"status": "error", "message": "resume_text 不能为空"}
    name = payload.get("candidate_name") or extract_fields(resume_text).get("name") or "外部推送候选人"
    source = payload.get("source") or "外部系统推送"
    job_title = payload.get("job_title") or ""
    # 授权来源：外部系统推送默认视为「平台接口·授权」（调用方在推送前完成候选人授权）
    cid = add_candidate(name, resume_text, source=source, parsed=extract_fields(resume_text),
                        job_title=job_title, auth_source="平台接口·授权")
    update_candidate(cid, status="已解析", status_note="Webhook 推送入库，等待智能初筛")
    notify("钉钉", f"【AI 招聘】收到新简历：{name}（{source}），已入库待初筛（#{cid}）")
    return {"status": "accepted", "candidate_id": cid, "message": f"{name} 已入库待初筛"}


def start_webhook_server(port: int = 7861) -> None:
    """独立 Webhook HTTP 服务（与 Gradio 并行，端口 7861）

    用标准库 http.server 实现，零依赖、生命周期可控；Gradio 的 FastAPI app 在
    launch 时会重建，直接挂路由会丢，故独立端口更可靠。
    企业版迁移：本服务替换为 FastAPI 微服务即可，on_resume_uploaded 业务函数不变。

    接口：POST http://127.0.0.1:7861/webhook/resume-uploaded
    """
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            """批量任务进度查询：GET /batch/{id}/progress → {id, status, progress, result}"""
            m = re.match(r"^/batch/(\d+)/progress$", self.path)
            if not m:
                self._reply(404, {"status": "error", "message": "路由不存在"})
                return
            from db import get_batch_task
            t = get_batch_task(int(m.group(1)))
            if not t:
                self._reply(404, {"status": "error", "message": "任务不存在"})
                return
            self._reply(200, {"status": "accepted", "task": {
                "id": t["id"], "status": t["status"], "progress": t["progress"], "result": t["result"],
            }})

        def do_POST(self):
            if not self.path.startswith("/webhook/"):
                self._reply(404, {"status": "error", "message": "路由不存在"})
                return
            # 鉴权：配置了 WEBHOOK_API_KEY 时必须带 X-API-Key 头（IP 白名单由部署层/防火墙控制）
            if not check_api_key({k.lower(): v for k, v in self.headers.items()}):
                self._reply(401, {"status": "error", "message": "鉴权失败：X-API-Key 无效或缺失"})
                return
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length) or b"{}"
                try:
                    text = body.decode("utf-8")
                except UnicodeDecodeError:
                    text = body.decode("gbk", errors="replace")  # 非 UTF-8 客户端兜底
                payload = json.loads(text)
                result = _dispatch(self.path, payload if isinstance(payload, dict) else {})
                code = 200 if result.get("status") == "accepted" else 400
            except Exception as e:
                result, code = {"status": "error", "message": str(e)}, 500
            self._reply(code, result)

        def _reply(self, code, result):
            data = json.dumps(result, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass  # 静默访问日志

    try:
        server = HTTPServer(("127.0.0.1", port), Handler)
    except OSError as e:
        print(f"[webhook] port {port} unavailable: {e}")
        return
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"[webhook] server started: POST http://127.0.0.1:{port}/webhook/resume-uploaded")
