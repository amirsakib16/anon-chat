# Whisper — Anonymous Chat Rooms

Ephemeral, anonymous chat rooms with a polished mobile-first UI.  
No accounts. No database. Messages live only in memory while the room is open.

## Features

- **Create or join** rooms with a short shareable code
- **Real-time messaging** via Socket.IO
- **Photo sharing** (base64 in-memory only — nothing is persisted)
- **Leave button** — room disappears when the last person leaves
- **Typing indicators**, online count, smooth animations
- **Fully responsive** (iOS / Android / desktop)
- **Vercel-ready** structure

## Quick start (local)

```bash
cd anon-chat
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000

## Deploy to Vercel

1. Push this folder to a GitHub repository.
2. Go to [vercel.com/new](https://vercel.com/new) → Import the repo.
3. Framework Preset: **Other** (or leave detected).
4. Root Directory: the folder containing `app.py` (if nested).
5. Deploy.

> **Note on WebSockets & state**  
> Vercel now supports WebSockets (public beta). Connections are pinned to one function instance.  
> Because rooms are stored **in memory**, users who land on different instances won’t see each other’s messages.  
> For a hobby / demo project this is usually fine (low traffic keeps one warm instance).  
> For production multi-instance reliability, add a shared store (e.g. Vercel KV / Upstash Redis).

### Optional: longer function duration

In the Vercel project settings (or `vercel.json`) you can raise `maxDuration` (Hobby max 300s). Clients auto-reconnect and rejoin the room.

## Project structure

```
anon-chat/
├── app.py              # Flask + Socket.IO server
├── requirements.txt
├── vercel.json
├── templates/
│   └── index.html      # Full UI (CSS + JS inlined)
└── README.md
```

## Privacy model

- No signup / no cookies for identity
- Nicknames are temporary and only known inside the room
- Messages & images exist only in the process memory
- When the last user leaves, the room is deleted
- Photos are sent as data URLs and never written to disk

Enjoy whispering.