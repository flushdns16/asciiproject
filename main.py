import json
import asyncio
import redis.asyncio as redis
from typing import List
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse
from pydantic import BaseModel

app = FastAPI()

# --- ÖNEMLİ: KENDİ UPSTASH REDIS LİNKİNİZİ BURAYA YAPIŞTIRIN ---
# Örnek: "rediss://default:sifreniz@karmasik-isim.upstash.io:30000"
REDIS_URL="rediss://default:********@neat-aphid-205293.upstash.io:6379"

redis_client = redis.from_url(REDIS_URL, decode_responses=True)

class AsciiVideo(BaseModel):
    path: str
    fps: int
    frames: List[str]

# Siteye ilk girildiğinde index.html sayfasını göster
@app.get("/")
async def get_homepage():
    return FileResponse("index.html")

# Kullanıcı web sitesinden videoyu dönüştürüp gönderdiğinde burası çalışır
@app.post("/upload")
async def upload_video(video: AsciiVideo):
    if not video.path.isalnum():
        raise HTTPException(status_code=400, detail="Sadece harf ve rakam")
    if len(video.frames) > 900:
        raise HTTPException(status_code=400, detail="Video çok uzun")

    # Redis'e kaydet (1 haftalık ömür - 604800 saniye)
    redis_key = f"ascii:{video.path.lower()}"
    payload = json.dumps({"fps": video.fps, "frames": video.frames})
    await redis_client.setex(redis_key, 604800, payload)
    
    return {"message": "Başarılı"}

# Akış Jeneratörü
async def frame_streamer(frames: List[str], fps: int):
    clear = "\033[2J\033[H"
    delay = 1.0 / fps
    try:
        while True: 
            for frame in frames:
                yield f"{clear}{frame}".encode('utf-8')
                await asyncio.sleep(delay)
    except asyncio.CancelledError:
        pass

# curl komutu atıldığında animasyonu başlatan kısım
@app.get("/{path}")
async def stream_video(path: str, request: Request):
    data = await redis_client.get(f"ascii:{path.lower()}")
    if not data:
        return HTMLResponse("<h2>Animasyon bulunamadı.</h2>", status_code=404)

    user_agent = request.headers.get("user-agent", "").lower()
    if "curl" not in user_agent:
        return HTMLResponse(f"<p>Terminalden şunu yazın: <br><code>curl {request.url}</code></p>")

    video_data = json.loads(data)
    return StreamingResponse(
        frame_streamer(video_data["frames"], video_data["fps"]),
        media_type="text/plain"
    )
