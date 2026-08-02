"""
开发板数据接入 — MQTT 订阅 + REST 查询 + WebSocket 实时推送

数据流: 开发板 --MQTT--> 本模块 --REST/WS--> 手机 App
  GET  /api/board/status          — 最近一次传感器数据
  GET  /api/board/events          — 事件历史 (识别/触发)
  WS   /ws/board                  — 实时推送 (手机订阅)
"""
import json
import asyncio
import logging
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.database import get_connection

logger = logging.getLogger("board")
router = APIRouter(prefix="/api", tags=["board"])

MQTT_ENABLED = False
MQTT_CLIENT = None
_ws_clients: list[WebSocket] = []

# ============ MQTT 客户端（线程） ============

def mqtt_on_message(client, userdata, msg):
    """开发板数据到达 → 存库 + 推送给手机"""
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        payload["received_at"] = datetime.now().isoformat()
        payload["topic"] = msg.topic

        # 存库
        conn = get_connection()
        conn.execute("""
            INSERT INTO board_events (topic, payload, created_at)
            VALUES (?, ?, datetime('now'))
        """, (msg.topic, json.dumps(payload, ensure_ascii=False)))
        conn.commit()
        conn.close()

        # 推送给所有连接的手机
        async def _push():
            for ws in list(_ws_clients):
                try:
                    await ws.send_text(json.dumps(payload, ensure_ascii=False))
                except Exception:
                    _ws_clients.remove(ws)
        asyncio.run_coroutine_threadsafe(_push(), asyncio.get_event_loop())
        logger.info("board event: %s", msg.topic)
    except Exception as e:
        logger.warning("mqtt parse error: %s", e)


def mqtt_connect(host: str, port: int = 1883):
    """启动 MQTT 订阅（paho-mqtt，在后台线程运行）"""
    global MQTT_ENABLED, MQTT_CLIENT
    try:
        import paho.mqtt.client as paho
    except ImportError:
        logger.warning("paho-mqtt 未安装: pip install paho-mqtt")
        return

    client = paho.Client("smartkitchen-backend")
    client.on_message = mqtt_on_message
    try:
        client.connect(host, port, 30)
        client.subscribe("kitchen/+/sensor")
        client.subscribe("kitchen/+/cmd")
        client.loop_start()
        MQTT_ENABLED = True
        MQTT_CLIENT = client
        logger.info("MQTT connected: %s:%d", host, port)
    except Exception as e:
        logger.warning("MQTT connect failed: %s", e)


# ============ REST API ============

@router.get("/board/status")
async def board_status():
    """最近一次开发板传感器数据"""
    conn = get_connection()
    row = conn.execute(
        "SELECT payload, created_at FROM board_events "
        "WHERE topic LIKE '%/sensor' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if not row:
        return {"success": True, "online": False, "data": None,
                "message": "开发板未上报数据（检查 MQTT 配置）"}
    data = json.loads(row["payload"])
    data["_time"] = row["created_at"]
    return {"success": True, "online": True, "data": data}


@router.get("/board/events")
async def board_events(limit: int = 20):
    """开发板事件历史（识别/触发/传感器）"""
    conn = get_connection()
    rows = conn.execute(
        "SELECT topic, payload, created_at FROM board_events "
        "ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return {"success": True, "events": [
        {"topic": r["topic"], "data": json.loads(r["payload"]),
         "time": r["created_at"]} for r in rows
    ]}


# ============ WebSocket 实时推送 ============

@router.websocket("/ws/board")
async def board_ws(websocket: WebSocket):
    """手机 App 订阅开发板实时数据"""
    await websocket.accept()
    _ws_clients.append(websocket)
    try:
        while True:
            # 收到手机消息: {"cmd": "ping"}
            msg = await websocket.receive_text()
            if msg == '{"cmd": "ping"}':
                await websocket.send_text('{"pong": true}')
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in _ws_clients:
            _ws_clients.remove(websocket)
