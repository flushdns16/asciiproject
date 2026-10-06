from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel
import asyncio
import json
import sqlite3
import os
import yt_dlp
import cv2

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

class URLVideoRequest(BaseModel):
    url: str
    path: str

# ASCII Karakter Dönüştürücü (Sunucu tarafı işleme için)
ASCII_CHARS = "@#W$9876543210?!abc;:+-. "

def frame_to_ascii(frame, cols=130, rows=65):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, (cols, rows))
    ascii_image = ""
    for y in range(rows):
        for x in range(cols):
            pixel_val = resized[y, x]
            char_idx = int((pixel_val / 255.0) * (len(ASCII_CHARS) - 1))
            ascii_image += ASCII_CHARS[char_idx]
        ascii_image += "\n"
    return ascii_image

@app.post("/upload")
async def upload_video(video: AsciiVideo):
    clean_path = video.path.strip().lower()
    if not clean_path.isalnum():
        raise HTTPException(status_code=400, detail="Sadece harf ve rakam kullanabilirsiniz.")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO videos (path, fps, frames) VALUES (?, ?, ?)",
        (clean_path, video.fps, json.dumps(video.frames))
    )
    conn.commit()
    conn.close()
    
    return {"message": "Başarılı", "saved_path": clean_path}

# YOUTUBE / SHORTS URL İLE İŞLEME ENDPOINT'İ
@app.post("/upload-url")
async def upload_url(data: URLVideoRequest):
    clean_path = data.path.strip().lower()
    if not clean_path.isalnum():
        raise HTTPException(status_code=400, detail="Sadece harf ve rakam kullanabilirsiniz.")

    temp_filename = f"temp_{clean_path}.mp4"
    
    try:
        ydl_opts = {
            'format': 'worst[ext=mp4]/worst', # Render için hızlı ve hafif indirme
            'outtmpl': temp_filename,
            'quiet': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([data.url])

        if not os.path.exists(temp_filename):
            raise HTTPException(status_code=400, detail="Video indirilemedi veya URL geçersiz.")

        # OpenCV ile karelere ayır
        cap = cv2.VideoCapture(temp_filename)
        fps = 10
        total_frames = 0
        frames = []
        
        video_fps = cap.get(cv2.CAP_PROP_FPS) or 30
        frame_skip = max(1, int(video_fps / fps))

        count = 0
        while cap.isOpened() and len(frames) < 350:
            ret, frame = cap.read()
            if not ret:
                break
            if count % frame_skip == 0:
                ascii_frame = frame_to_ascii(frame)
                frames.append(ascii_frame)
            count += 1
        
        cap.release()
        
        # Geçici dosyayı temizle
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

        if not frames:
            raise HTTPException(status_code=400, detail="Videodan kare alınamadı.")

        # Veritabanına kaydet
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO videos (path, fps, frames) VALUES (?, ?, ?)",
            (clean_path, fps, json.dumps(frames))
        )
        conn.commit()
        conn.close()

        return {"message": "Başarılı", "saved_path": clean_path}

    except Exception as e:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/{path}")
async def stream_video(path: str):
    path_clean = path.strip().lower()
    
    if path_clean == "debug":
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT path FROM videos")
        rows = cursor.fetchall()
        conn.close()
        return PlainTextResponse(str([r[0] for r in rows]))

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

    return StreamingResponse(frame_generator(), media_type="text/plain")

@app.get("/")
def read_index():
    with open("index.html", "r", encoding="utf-8") as f:
        return PlainTextResponse(f.read(), media_type="text/html")
