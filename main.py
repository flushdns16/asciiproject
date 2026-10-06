from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel
import asyncio
import json
import sqlite3
import random
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
            frames TEXT,
            is_text INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

init_db()

class AsciiVideo(BaseModel):
    path: str
    fps: int
    frames: list

class AsciiTextRequest(BaseModel):
    text: str
    path: str

@app.post("/upload")
async def upload_video(video: AsciiVideo):
    clean_path = video.path.strip().lower()
    if not clean_path.isalnum():
        raise HTTPException(status_code=400, detail="Sadece harf ve rakam kullanabilirsiniz.")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO videos (path, fps, frames, is_text) VALUES (?, ?, ?, ?)",
        (clean_path, video.fps, json.dumps(video.frames), 0)
    )
    conn.commit()
    conn.close()
    
    return {"message": "Başarılı", "saved_path": clean_path}

@app.post("/upload-text")
async def upload_text(data: AsciiTextRequest):
    clean_path = data.path.strip().lower()
    if not clean_path.isalnum():
        raise HTTPException(status_code=400, detail="Sadece harf ve rakam kullanabilirsiniz.")

    text = data.text.strip().upper()
    if not text:
        raise HTTPException(status_code=400, detail="Metin boş olamaz.")

    cols = 90
    rows = 35
    total_frames = 25
    fps = 10
    frames = []

    FONT = {
        'A': ["  A  ", " A A ", "AAAAA", "A   A", "A   A"],
        'B': ["BBBB ", "B   B", "BBBB ", "B   B", "BBBB "],
        'C': [" CCC ", "C    ", "C    ", "C    ", " CCC "],
        'D': ["DDDD ", "D   D", "D   D", "D   D", "DDDD "],
        'E': ["EEEEE", "E    ", "EEEE ", "E    ", "EEEEE"],
        'F': ["FFFFF", "F    ", "FFF  ", "F    ", "F    "],
        'G': [" GGG ", "G    ", "G  GG", "G   G", " GGG "],
        'H': ["H   H", "H   H", "HHHHH", "H   H", "H   H"],
        'I': [" III ", "  I  ", "  I  ", "  I  ", " III "],
        'J': ["  JJJ", "    J", "    J", "J   J", " JJJ "],
        'K': ["K   K", "K  K ", "KKK  ", "K  K ", "K   K"],
        'L': ["L    ", "L    ", "L    ", "L    ", "LLLLL"],
        'M': ["M   M", "MM MM", "M M M", "M   M", "M   M"],
        'N': ["N   N", "NN  N", "N N N", "N  NN", "N   N"],
        'O': [" OOO ", "O   O", "O   O", "O   O", " OOO "],
        'P': ["PPPP ", "P   P", "PPPP ", "P    ", "P    "],
        'Q': [" QQQ ", "Q   Q", "Q Q Q", " QQQQ", "    Q"],
        'R': ["RRRR ", "R   R", "RRRR ", "R  R ", "R   R"],
        'S': [" SSS ", "S    ", " SSS ", "    S", " SSS "],
        'T': ["TTTTT", "  T  ", "  T  ", "  T  ", "  T  "],
        'U': ["U   U", "U   U", "U   U", "U   U", " UUU "],
        'V': ["V   V", "V   V", " V V ", " V V ", "  V  "],
        'W': ["W   W", "W W W", "WW WW", "W   W", "W   W"],
        'X': ["X   X", " X X ", "  X  ", " X X ", "X   X"],
        'Y': ["Y   Y", " Y Y ", "  Y  ", "  Y  ", "  Y  "],
        'Z': ["ZZZZZ", "   Z ", "  Z  ", " Z   ", "EEEEE"],
        ' ': ["     ", "     ", "     ", "     ", "     "],
        '!': ["  !  ", "  !  ", "  !  ", "     ", "  !  "]
    }

    drops = [random.randint(0, rows) for _ in range(cols)]
    matrix_chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ@#$*&"

    for f in range(total_frames):
        screen_chars = [[" " for _ in range(cols)] for _ in range(rows)]
        screen_types = [[0 for _ in range(cols)] for _ in range(rows)]

        for x in range(cols):
            drop_y = drops[x]
            for y in range(rows):
                dist = (y - drop_y + rows) % rows
                if dist < 12:
                    screen_chars[y][x] = random.choice(matrix_chars)
                    screen_types[y][x] = 0
            drops[x] = (drops[x] + 1) % rows

        text_lines = 5
        char_w = 5
        total_w = len(text) * (char_w + 1)
        start_x = max(2, (cols - total_w) // 2)
        start_y = (rows - text_lines) // 2

        curr_x = start_x
        for char in text:
            grid = FONT.get(char, FONT[' '])
            for r_idx, line_str in enumerate(grid):
                ty = start_y + r_idx
                if 0 <= ty < rows:
                    for c_idx, pixel in enumerate(line_str):
                        tx = curr_x + c_idx
                        if 0 <= tx < cols and pixel != ' ':
                            screen_chars[ty][tx] = pixel
                            screen_types[ty][tx] = 1
            curr_x += char_w + 1

        frame_str = ""
        current_color = ""
        for r in range(rows):
            for c in range(cols):
                t = screen_types[r][c]
                color_code = "\033[97m" if t == 1 else "\033[32m"
                if color_code != current_color:
                    frame_str += color_code
                    current_color = color_code
                frame_str += screen_chars[r][c]
            frame_str += "\n"
        frames.append(frame_str)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO videos (path, fps, frames, is_text) VALUES (?, ?, ?, ?)",
        (clean_path, fps, json.dumps(frames), 1)
    )
    conn.commit()
    conn.close()

    return {"message": "Başarılı", "saved_path": clean_path}

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
    cursor.execute("SELECT fps, frames, is_text FROM videos WHERE path = ?", (path_clean,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Veri paketi bulunamadı.")
    
    fps = row[0]
    frames = json.loads(row[1])
    is_text = row[2]
    delay = 1.0 / fps

    async def frame_generator():
        try:
            while True:
                for frame in frames:
                    yield ("\033[H\033[J" + frame).encode('utf-8')
                    await asyncio.sleep(delay)
                if not is_text:
                    break
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        frame_generator(), 
        media_type="text/plain; charset=utf-8",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Connection": "keep-alive"
        }
    )

@app.get("/")
def read_index():
    with open("index.html", "r", encoding="utf-8") as f:
        return PlainTextResponse(f.read(), media_type="text/html")
