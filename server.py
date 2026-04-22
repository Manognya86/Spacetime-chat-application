#!/usr/bin/env python3
"""
SPACETIME CHAT v2 — Python WebSocket Server
pip install aiohttp websockets
"""

import asyncio
import json
import time
import uuid
import os
import pathlib
from typing import Dict, Any

try:
    from aiohttp import web
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

# ─── Config ───────────────────────────────────────────────────────────────────
PORT        = int(os.environ.get("PORT", 3000))
CLIENT_DIR  = pathlib.Path(__file__).parent / "client"
SERVER_START_MS = time.time() * 1000

GRAVITY_ZONES = {
    "singularity": {"label": "Event Horizon", "scale": 0.05, "color": "#ff2244"},
    "heavy":       {"label": "Heavy Gravity",  "scale": 0.2,  "color": "#ff6b35"},
    "orbit":       {"label": "Orbital",        "scale": 0.6,  "color": "#ffd700"},
    "normal":      {"label": "Deep Space",     "scale": 1.0,  "color": "#00d4ff"},
    "light":       {"label": "Void",           "scale": 2.5,  "color": "#a855f7"},
    "extreme":     {"label": "Light Speed",    "scale": 5.0,  "color": "#00ff88"},
}

USER_COLORS = [
    "#00d4ff","#ff6b35","#a855f7","#00ff88",
    "#ffd700","#ff2244","#ff9ef7","#7dd3fc",
    "#fb923c","#34d399","#f472b6","#60a5fa",
]

EMOJI_LIST = ["👍","❤️","😂","😮","😢","🔥","⚡","🌌"]

# ─── State ────────────────────────────────────────────────────────────────────
users:    Dict[str, Dict[str, Any]] = {}
messages: list = []
reactions: Dict[str, Dict[str, list]] = {}
typing_users: Dict[str, float] = {}
color_counter = 0


def now_ms() -> float:
    return time.time() * 1000 - SERVER_START_MS


def user_public(uid: str) -> dict:
    u = users[uid]
    return {
        "id": uid,
        "name": u["name"],
        "timeScale": u["timeScale"],
        "color": u["color"],
        "zone": u["zone"],
    }


def get_user_list() -> list:
    return [user_public(uid) for uid in users]


async def _send(ws, payload: str):
    try:
        await ws.send_str(payload)
    except Exception:
        pass


async def broadcast(data: dict, exclude_id: str = None):
    payload = json.dumps(data)
    for uid, u in list(users.items()):
        if uid != exclude_id:
            await _send(u["ws"], payload)


async def broadcast_all(data: dict):
    await broadcast(data)


# ─── WebSocket handler ────────────────────────────────────────────────────────
async def ws_handler(request):
    global color_counter

    ws = web.WebSocketResponse(heartbeat=30)
    await ws.prepare(request)

    user_id = str(uuid.uuid4())
    color   = USER_COLORS[color_counter % len(USER_COLORS)]
    color_counter += 1

    user = {
        "ws":        ws,
        "name":      f"Traveler_{user_id[:4].upper()}",
        "timeScale": 1.0,
        "zone":      "normal",
        "color":     color,
        "joinedAt":  now_ms(),
    }
    users[user_id] = user
    print(f"[+] {user['name']} connected  ({user_id[:8]})")

    await ws.send_str(json.dumps({
        "type":           "init",
        "userId":         user_id,
        "user":           user_public(user_id),
        "users":          get_user_list(),
        "recentMessages": messages[-60:],
        "reactions":      reactions,
        "globalTime":     now_ms(),
        "gravityZones":   GRAVITY_ZONES,
        "emojiList":      EMOJI_LIST,
        "serverStartMs":  SERVER_START_MS,
    }))

    await broadcast({
        "type":       "user_joined",
        "userId":     user_id,
        "user":       user_public(user_id),
        "globalTime": now_ms(),
    }, exclude_id=user_id)

    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                except Exception:
                    continue
                await handle_client_msg(user_id, user, data)
            elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSE):
                break
    finally:
        users.pop(user_id, None)
        typing_users.pop(user_id, None)
        print(f"[-] {user['name']} disconnected")
        await broadcast_all({
            "type":       "user_left",
            "userId":     user_id,
            "name":       user["name"],
            "globalTime": now_ms(),
        })

    return ws


async def handle_client_msg(uid: str, user: dict, data: dict):
    t   = data.get("type", "")
    now = now_ms()

    if t == "set_name":
        name = str(data.get("name","")).strip()[:24].replace("<","").replace(">","")
        if name:
            user["name"] = name
        await broadcast_all({"type":"user_updated","userId":uid,"user":user_public(uid),"globalTime":now})

    elif t == "set_zone":
        zk = data.get("zone","normal")
        if zk in GRAVITY_ZONES:
            user["zone"]      = zk
            user["timeScale"] = GRAVITY_ZONES[zk]["scale"]
        await broadcast_all({"type":"user_updated","userId":uid,"user":user_public(uid),"globalTime":now})

    elif t == "message":
        text = str(data.get("text","")).strip()[:500]
        if not text:
            return
        m = {
            "id":          str(uuid.uuid4()),
            "type":        "message",
            "userId":      uid,
            "authorName":  user["name"],
            "authorColor": user["color"],
            "text":        text,
            "globalTime":  now,
            "replyTo":     data.get("replyTo"),
            "timeBomb":    data.get("timeBomb"),   # seconds until deletion
        }
        messages.append(m)
        if len(messages) > 500:
            messages.pop(0)
        await broadcast_all(m)

    elif t == "reaction":
        msg_id = data.get("msgId","")
        emoji  = data.get("emoji","")
        if not msg_id or emoji not in EMOJI_LIST:
            return
        if msg_id not in reactions:
            reactions[msg_id] = {}
        if emoji not in reactions[msg_id]:
            reactions[msg_id][emoji] = []
        lst = reactions[msg_id][emoji]
        if uid in lst:
            lst.remove(uid)
        else:
            lst.append(uid)
        await broadcast_all({"type":"reaction_update","msgId":msg_id,"emoji":emoji,"users":lst,"globalTime":now})

    elif t == "typing":
        typing_users[uid] = time.time() + 4.0
        await broadcast({"type":"typing","userId":uid,"name":user["name"],"color":user["color"],"globalTime":now}, exclude_id=uid)

    elif t == "stop_typing":
        typing_users.pop(uid, None)
        await broadcast({"type":"stop_typing","userId":uid,"globalTime":now}, exclude_id=uid)

    elif t == "sync_request":
        await broadcast_all({
            "type":            "sync_event",
            "requestedBy":     uid,
            "requesterName":   user["name"],
            "requesterColor":  user["color"],
            "globalTime":      now,
            "duration":        6000,
        })

    elif t == "ping":
        await _send(user["ws"], json.dumps({"type":"pong","globalTime":now}))


# ─── Background tasks ─────────────────────────────────────────────────────────
async def tick_loop():
    while True:
        await asyncio.sleep(0.1)
        if not users:
            continue
        payload = json.dumps({"type":"tick","globalTime":now_ms()})
        for u in list(users.values()):
            await _send(u["ws"], payload)


async def typing_gc_loop():
    while True:
        await asyncio.sleep(1)
        now_s   = time.time()
        expired = [uid for uid, exp in list(typing_users.items()) if now_s > exp]
        for uid in expired:
            typing_users.pop(uid, None)
            await broadcast_all({"type":"stop_typing","userId":uid,"globalTime":now_ms()})


async def timebomb_loop():
    while True:
        await asyncio.sleep(0.5)
        n = now_ms()
        to_delete = [m["id"] for m in messages if m.get("timeBomb") and n >= m["globalTime"] + m["timeBomb"] * 1000]
        for mid in to_delete:
            messages[:] = [m for m in messages if m["id"] != mid]
            await broadcast_all({"type":"message_deleted","msgId":mid,"globalTime":n})


# ─── HTTP ─────────────────────────────────────────────────────────────────────
async def index_handler(request):
    f = CLIENT_DIR / "index.html"
    return web.FileResponse(f) if f.exists() else web.Response(text="Not found", status=404)


async def status_handler(request):
    return web.json_response({"users": get_user_list(), "messageCount": len(messages), "globalTime": now_ms()})


async def main():
    if not HAS_AIOHTTP:
        print("ERROR: run  pip install aiohttp websockets")
        return

    app = web.Application()
    app.router.add_get("/ws",         ws_handler)
    app.router.add_get("/api/status", status_handler)
    app.router.add_get("/",           index_handler)
    app.router.add_static("/",        CLIENT_DIR, show_index=True)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    print(f"🌌  Spacetime Chat v2  →  http://localhost:{PORT}")
    print(f"    Press Ctrl+C to stop\n")

    asyncio.create_task(tick_loop())
    asyncio.create_task(typing_gc_loop())
    asyncio.create_task(timebomb_loop())
    await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✦ Server stopped.")
