from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
import asyncio
import json
import sqlite3

app = FastAPI()
DB_NAME = "ascii.db"

# SQLite veritabanını ve tablosunu hazırla
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
    if not video.path.isalnum():
        raise HTTPException(status_code=400, detail="Sadece harf ve rakam kullanabilirsiniz.")
    
    if len(video.frames) > 900:
        raise HTTPException(status_code=400, detail="Video çok uzun (Max 30 saniye)")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO videos (path, fps, frames) VALUES (?, ?, ?)",
        (video.path.lower(), video.fps, json.dumps(video.frames))
    )
    conn.commit()
    conn.close()
    
    return {"message": "Başarılı"}

@app.get("/{path}", response_class=PlainTextResponse)
async def stream_video(path: str):
    path_clean = path.lower()
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
