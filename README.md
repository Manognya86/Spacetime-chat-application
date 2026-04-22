# 🌌 SPACETIME CHAT — Python Edition

A real-time multi-user chat where each user experiences time at a different rate.

---

## 🚀 Getting Started

### 1. Install dependencies

```
pip install aiohttp websockets
```

### 2. Run the server

```
python server.py
```

### 3. Open in browser

```
http://localhost:3000
```

Open multiple tabs (or share your LAN IP) to test time dilation between users.

---

## 🎮 Demo Scenario

1. Open 3 browser tabs at http://localhost:3000
2. Tab 1 → select **Event Horizon** (0.05× time)
3. Tab 2 → select **Deep Space** (1.0× — normal)
4. Tab 3 → select **Light Speed** (5.0× time)
5. Type "Hello" from Tab 2
6. Watch:
   - Tab 3 sees it almost instantly
   - Tab 1 receives it much later
   - Tab 3 can reply before Tab 1 even sees the original

---

## ⚙️ Architecture

```
server.py           ← Async Python server (aiohttp + WebSockets)
requirements.txt    ← pip dependencies
client/
  index.html        ← Full UI (zero npm, zero build step)
```

### How It Works

```
Server timestamps all events with global time (ms since start)
↓
All events broadcast to every client immediately
↓
Each client buffers events, advances local time at their scale:
  local_time += frame_delta × timeScale
↓
Message renders only when: event.globalTime <= local_time
```

### Gravity Zones

| Zone          | Scale | Description                    |
|---------------|-------|--------------------------------|
| Event Horizon | 0.05× | Near-black-hole time crawl     |
| Heavy Gravity | 0.2×  | Very slow time perception      |
| Orbital       | 0.6×  | Slightly slow                  |
| Deep Space    | 1.0×  | Normal reference frame         |
| Void          | 2.5×  | Accelerated perception         |
| Light Speed   | 5.0×  | Time flies                     |

---

## 🌐 Multiplayer on LAN

Find your IP:
- Windows: `ipconfig`
- Mac/Linux: `ifconfig`

Others connect to: `http://YOUR_IP:3000`

---

## 🔧 Change Port

```bash
PORT=8080 python server.py
```

Or on Windows PowerShell:
```powershell
$env:PORT=8080; python server.py
```
