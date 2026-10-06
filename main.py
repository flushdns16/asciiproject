from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel
import asyncio
import json
import sqlite3

app = FastAPI()
DB_NAME = "ascii.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            path TEXT PRIMARY KEY,
            fps INTEGER,
            frames TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

class AsciiVideo(BaseModel):
    path: str
    fps: int
    frames: list

@app.post("/upload")
async def upload_video(video: AsciiVideo):
    clean_path = video.path.strip().lower()
    if not clean_path.isalnum():
        raise HTTPException(status_code=400, detail="Sadece harf ve rakam kullanabilirsiniz.")
    
    if len(video.frames) > 900:
        raise HTTPException(status_code=400, detail="Video çok uzun (Max 30 saniye)")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO videos (path, fps, frames) VALUES (?, ?, ?)",
        (clean_path, video.fps, json.dumps(video.frames))
    )
    conn.commit()
    conn.close()
    
    return {"message": "Başarılı", "saved_path": clean_path}

# VERİTABANINDA NE VAR GÖRMEK İÇİN GİZLİ KAPI
@app.get("/debug/list")
def list_videos():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT path, fps FROM videos")
    rows = cursor.fetchall()
    conn.close()
    return {"registered_paths": [row[0] for row in rows]}

@app.get("/{path}", response_class=PlainTextResponse)
async def stream_video(path: str):
    path_clean = path.strip().lower()
    
    # Eğer debug sayfasına gitmek isterse engelleme
    if path_clean == "debug":
        return "Debug active"

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT fps, frames FROM videos WHERE path = ?", (path_clean,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Veri paketi bulunamadı.")
    
    fps = row[0]
    frames = json.loads(row[1])
    delay = 1.0 / fps

    async def frame_generator():
        try:
            for frame in frames:
                yield "\033[H\033[J" + frame
                await asyncio.sleep(delay)
        except asyncio.CancelledError:
            pass

    return frame_generator()

@app.get("/")
def read_index():
    with open("index.html", "r", encoding="utf-8") as f:
        return PlainTextResponse(f.read(), media_type="text/html")
