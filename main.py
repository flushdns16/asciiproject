from fastapi import FastAPI, HTTPException, Request
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
            is_text INTEGER DEFAULT 0,
            raw_text TEXT
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
        "INSERT OR REPLACE INTO videos (path, fps, frames, is_text, raw_text) VALUES (?, ?, ?, ?, ?)",
        (clean_path, video.fps, json.dumps(video.frames), 0, "")
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

    # Standart geniş format (Terminal tam ekranı ve mobil için optimize)
    cols = 120
    rows = 40
    total_frames = 20
    fps = 12
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
        "INSERT OR REPLACE INTO videos (path, fps, frames, is_text, raw_text) VALUES (?, ?, ?, ?, ?)",
        (clean_path, fps, json.dumps(frames), 1, text)
    )
    conn.commit()
    conn.close()

    return {"message": "Başarılı", "saved_path": clean_path}

@app.get("/{path}")
async def stream_video(path: str, request: Request):
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

    # Eğer istek tarayıcıdan (User-Agent içinde curl geçmiyorsa) geliyorsa, şahane bir HTML konsol wrapper içinde sunalım
    user_agent = request.headers.get("user-agent", "").lower()
    if "curl" not in user_agent and "wget" not in user_agent and is_text:
        # Mobil ve masaüstü tarayıcılar için tam ekran esnek responsive HTML görünüm
        html_content = f"""
        <!DOCTYPE html>
        <html lang="tr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Matrix Terminal // {path_clean}</title>
            <style>
                body {{
                    background-color: #000;
                    color: #00ff66;
                    font-family: 'Courier New', Courier, monospace;
                    margin: 0;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    overflow: hidden;
                }}
                #terminal {{
                    font-size: min(1.8vw, 1.8vh);
                    line-height: min(1.9vw, 1.9vh);
                    white-space: pre;
                    background: #000;
                    padding: 10px;
                    border: 1px solid #00ff66;
                    box-shadow: 0 0 30px rgba(0, 255, 102, 0.3);
                }}
                .matrix-rain {{ color: #00ff66; }}
                .matrix-text {{ color: #ffffff; font-weight: bold; text-shadow: 0 0 8px #ffffff; }}
            </style>
        </head>
        <body>
            <div id="terminal">Yükleniyor...</div>
            <script>
                const frames = {json.dumps(frames)};
                let idx = 0;
                const term = document.getElementById('terminal');
                
                // HTML karelerini temizleyip tarayıcı içi esnek gösterim
                setInterval(() => {{
                    term.innerHTML = frames[idx];
                    idx = (idx + 1) % frames.length;
                }}, {int(delay * 1000)});
            </script>
        </body>
        </html>
        """
        return PlainTextResponse(html_content, media_type="text/html")

    # Terminal için ham ANSI akışı
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
