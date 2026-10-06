from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel
import asyncio
import json
import sqlite3
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

# Metni ASCII Sanatına ve Zıplayan Animasyona Çevirme Endpoint'i
@app.post("/upload-text")
async def upload_text(data: AsciiTextRequest):
    clean_path = data.path.strip().lower()
    if not clean_path.isalnum():
        raise HTTPException(status_code=400, detail="Sadece harf ve rakam kullanabilirsiniz.")

    text = data.text.strip().upper()
    if not text:
        raise HTTPException(status_code=400, detail="Metin boş olamaz.")

    cols = 130
    rows = 65
    total_frames = 30  # 3 saniyelik zıplama döngüsü için 30 kare
    fps = 10
    frames = []

    # Basit ama şık bir ASCII font sözlüğü (Büyük harfler için)
    FONT = {
        'A': ["  A  ", " A A ", "AAAAA", "A   A"],
        'B': ["BBBB ", "B   B", "BBBB ", "B   B", "BBBB "],
        'C': [" CCC ", "C    ", "C    ", " CCC "],
        'D': ["DDDD ", "D   D", "D   D", "DDDD "],
        'E': ["EEEEE", "E    ", "EEEE ", "E    ", "EEEEE"],
        'F': ["FFFFF", "F    ", "FFF  ", "F    ", "F    "],
        'G': [" GGG ", "G    ", "G  GG", " GGG "],
        'H': ["H   H", "H   H", "HHHHH", "H   H", "H   H"],
        'I': [" III ", "  I  ", "  I  ", " III "],
        'J': ["  JJJ", "    J", "    J", "J   J", " JJJ "],
        'K': ["K   K", "K  K ", "KKK  ", "K  K ", "K   K"],
        'L': ["L    ", "L    ", "L    ", "LLLLL"],
        'M': ["M   M", "MM MM", "M M M", "M   M"],
        'N': ["N   N", "NN  N", "N N N", "N  NN"],
        'O': [" OOO ", "O   O", "O   O", " OOO "],
        'P': ["PPPP ", "P   P", "PPPP ", "P    "],
        'Q': [" QQQ ", "Q   Q", "Q Q Q", " QQQQ"],
        'R': ["RRRR ", "R   R", "RRRR ", "R  R "],
        'S': [" SSS ", "S    ", " SSS ", "    S", " SSS "],
        'T': ["TTTTT", "  T  ", "  T  ", "  T  "],
        'U': ["U   U", "U   U", "U   U", " UUU "],
        'V': ["V   V", "V   V", " V V ", "  V  "],
        'W': ["W   W", "W W W", "WW WW", "W   W"],
        'X': ["X   X", " X X ", " X X ", "X   X"],
        'Y': ["Y   Y", " Y Y ", "  Y  ", "  Y  "],
        'Z': ["ZZZZZ", "   Z ", "  Z  ", "EEEEE"],
        ' ': ["     ", "     ", "     "],
        '!': ["  !  ", "  !  ", "     ", "  !  "]
    }

    # Metni satırlara dök
    lines = []
    for char in text:
        if char in FONT:
            lines.append(FONT[char])
        else:
            lines.append([" ? "])

    # Zıplama efekti için her karede dikey ofset (offset) hesapla
    import math
    for f in range(total_frames):
        screen = [[" " for _ in range(cols)] for _ in range(rows)]
        
        # Zıplama yüksekliği (sinüs dalgası ile akıcı hareket)
        bounce = int(math.sin(f / 5.0) * 3)
        center_y = (rows // 2) + bounce
        
        # Metni yatayda ortala
        char_width = 5
        total_text_width = len(text) * (char_width + 1)
        start_x = max(2, (cols - total_text_width) // 2)

        curr_x = start_x
        for char_idx, char in enumerate(text):
            char_grid = FONT.get(char, FONT[' '])
            for r_idx, row_str in enumerate(char_grid):
                target_y = center_y + r_idx
                if 0 <= target_y < rows:
                    for c_idx, pixel in enumerate(row_str):
                        target_x = curr_x + c_idx
                        if 0 <= target_x < cols and pixel != ' ':
                            # Çevresine matrix havası katmak için karakter seçelim
                            screen[target_y][target_x] = '#' if (f + r_idx) % 2 == 0 else '@'
            curr_x += char_width + 1

        # Matrisi stringe çevir
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
