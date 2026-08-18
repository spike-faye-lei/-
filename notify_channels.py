"""外部通知渠道：钉钉 / 飞书 / 企业微信 群机器人 Webhook 推送

用法：
    在 .env 配置（可选，不配置则降级为本地日志，不影响主流程）：
      DINGTALK_WEBHOOK=https://oapi.dingtalk.com/robot/send?access_token=xxx
      FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
      WEWORK_WEBHOOK=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx

生产环境 HR 无需打开网页：面试完成/初筛完成/待审核超时等事件自动推送到群。
"""
import json
import os

import requests

# .env 读取（复用 config 的轻量实现）
try:
    from config import load_dotenv
    load_dotenv()
except ImportError:
    pass

CHANNEL_HOOKS = {
    "钉钉": os.environ.get("DINGTALK_WEBHOOK", ""),
    "飞书": os.environ.get("FEISHU_WEBHOOK", ""),
    "企业微信": os.environ.get("WEWORK_WEBHOOK", ""),
}


def _load_dotenv_fresh():
    """每次发送前重新读 .env（用户改配置不用重启）"""
    try:
        from config import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    CHANNEL_HOOKS["钉钉"] = os.environ.get("DINGTALK_WEBHOOK", "")
    CHANNEL_HOOKS["飞书"] = os.environ.get("FEISHU_WEBHOOK", "")
    CHANNEL_HOOKS["企业微信"] = os.environ.get("WEWORK_WEBHOOK", "")


def send_dingtalk(webhook_url: str, content: str) -> bool:
    """钉钉群机器人：text 消息。返回是否发送成功"""
    try:
        resp = requests.post(
            webhook_url,
            json={"msgtype": "text", "text": {"content": content}},
            timeout=8,
        )
        return resp.status_code == 200 and resp.json().get("errcode") == 0
    except requests.exceptions.RequestException:
        return False


def send_feishu(webhook_url: str, content: str) -> bool:
    """飞书群机器人：text 消息"""
    try:
        resp = requests.post(
            webhook_url,
            json={"msg_type": "text", "content": {"text": content}},
            timeout=8,
        )
        return resp.status_code == 200 and resp.json().get("code") == 0
    except requests.exceptions.RequestException:
        return False


def send_wework(webhook_url: str, content: str) -> bool:
    """企业微信群机器人：text 消息"""
    try:
        resp = requests.post(
            webhook_url,
            json={"msgtype": "text", "text": {"content": content}},
            timeout=8,
        )
        return resp.status_code == 200 and resp.json().get("errcode") == 0
    except requests.exceptions.RequestException:
        return False


_SENDERS = {"钉钉": send_dingtalk, "飞书": send_feishu, "企业微信": send_wework}


def notify(channel: str, content: str) -> str:
    """统一发送入口：按渠道推送到群机器人；未配置 webhook 时降级为本地日志

    返回结果描述（成功/降级/失败），调用方写入通知记录。
    """
    _load_dotenv_fresh()
    hook = CHANNEL_HOOKS.get(channel, "")
    if not hook:
        return f"（模拟发送 · 未配置 {channel} webhook，仅本地记录）"
    ok = _SENDERS.get(channel, send_dingtalk)(hook, content)
    return f"（已推送 {channel} 群机器人）" if ok else f"（{channel} 推送失败，请检查 webhook 配置）"


def interview_done_message(candidate, score, decision, job):
    """面试完成事件的消息文案（推送到 HR 群，附审核提示）"""
    return (
        f"【AI 招聘】候选人 {candidate} 已完成 AI 面试\n"
        f"岗位：{job} ｜ 综合评分：{score} 分 ｜ AI 建议：{decision}\n"
        f"请在「待审核队列」中做最终录用决定（唯一需人工确认的节点）"
    )


def screening_done_message(job_title, total, passed, eliminated):
    """批量初筛完成事件的消息文案"""
    return (
        f"【AI 招聘】{job_title} 初筛完成\n"
        f"共 {total} 人：通过 {passed} 人 / 淘汰 {eliminated} 人（淘汰原因已存库，可申诉复审）\n"
        f"请登录系统勾选进入面试队列的候选人"
    )
