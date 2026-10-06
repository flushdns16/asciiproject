from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
import asyncio
import json

app = FastAPI()

# Bellekte (RAM) video verilerini tutacağımız sözlük
MEMORY_DB = {}

class AsciiVideo(BaseModel):
    path: str
    fps: int
    frames: list

@app.post("/upload")
async def upload_video(video: AsciiVideo):
    if not video.path.isalnum():
        raise HTTPException(status_code=400, detail="Sadece harf ve rakam kullanabilirsiniz.")
    
    if len(video.frames) > 900:
        raise HTTPException(status_code=400, detail="Video çok uzun (Max 30 saniye)")

    # Veriyi doğrudan RAM'e kaydediyoruz
    MEMORY_DB[video.path.lower()] = {
        "fps": video.fps,
        "frames": video.frames
    }
    
    return {"message": "Başarılı"}

@app.get("/{path}", response_class=PlainTextResponse)
async def stream_video(path: str):
    path_clean = path.lower()
    if path_clean not in MEMORY_DB:
        raise HTTPException(status_code=404, detail="Veri paketi bulunamadı.")
    
    video_data = MEMORY_DB[path_clean]
    fps = video_data["fps"]
    frames = video_data["frames"]
    delay = 1.0 / fps

    async def frame_generator():
        try:
            for frame in frames:
                # Terminali temizle ve çerçeveyi bas
                yield "\033[H\033[J" + frame
                await asyncio.sleep(delay)
        except asyncio.CancelledError:
            pass

    return frame_generator()

@app.get("/")
def read_index():
    with open("index.html", "r", encoding="utf-8") as f:
        return PlainTextResponse(f.read(), media_type="text/html")
