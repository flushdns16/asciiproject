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
        "INSERT OR REPLACE INTO videos (path, fps, frames) VALUES (?, ?, ?)",
        (clean_path, video.fps, json.dumps(video.frames))
    )
    conn.commit()
    conn.close()
    
    return {"message": "Başarılı", "saved_path": clean_path}

# Matrix Yağmuru ve Merkezde Net Yazı Üretici
@app.post("/upload-text")
async def upload_text(data: AsciiTextRequest):
    clean_path = data.path.strip().lower()
    if not clean_path.isalnum():
        raise HTTPException(status_code=400, detail="Sadece harf ve rakam kullanabilirsiniz.")

    text = data.text.strip().upper()
    if not text:
        raise HTTPException(status_code=400, detail="Metin boş olamaz.")

    cols = 120
    rows = 50
    total_frames = 40
    fps = 10
    frames = []

    # ASCII Harf Fontları (Merkezde net okunması için)
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

    # Her sütun için Matrix yağmur damlası başlangıç pozisyonu
    drops = [random.randint(0, rows) for _ in range(cols)]
    matrix_chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ@#$*&"

    for f in range(total_frames):
        # 1. Adım: Arka planı Matrix yağmuru ile doldur
        screen = [[" " for _ in range(cols)] for _ in range(rows)]
        for x in range(cols):
            drop_y = drops[x]
            for y in range(rows):
                # Akış efekti
                dist = (y - drop_y) % rows
                if dist < 15:  # Kuyruk uzunluğu
                    screen[y][x] = random.choice(matrix_chars)
            drops[x] = (drops[x] + 1) % rows

        # 2. Adım: Tam merkeze kullanıcının metnini net bir şekilde bas
        text_grid_lines = 5
        char_width = 5
        total_text_width = len(text) * (char_width + 1)
        start_x = max(2, (cols - total_text_width) // 2)
        start_y = (rows - text_grid_lines) // 2

        curr_x = start_x
        for char in text:
            char_lines = FONT.get(char, FONT[' '])
            for r_idx, line_str in enumerate(char_lines):
                target_y = start_y + r_idx
                if 0 <= target_y < rows:
                    for c_idx, pixel in enumerate(line_str):
                        target_x = curr_x + c_idx
                        if 0 <= target_x < cols and pixel != ' ':
                            # Merkezdeki yazı Matrix akışından üstün tutulur ve net basılır
                            screen[target_y][target_x] = pixel
            curr_x += char_width + 1

        # Matrisi kare stringine dönüştür
        frame_str = ""
        for r in screen:
            frame_str += "".join(r) + "\n"
        frames.append(frame_str)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO videos (path, fps, frames) VALUES (?, ?, ?)",
        (clean_path, fps, json.dumps(frames))
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
