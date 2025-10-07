# server.py — FastAPI backend for WheelBot (global 30s rounds)
import random, time, asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db import get_conn, get_current_round_state, history, finalize_round

ROUND_SECONDS = 30
MULTS = ['x2','x3','x5','x50']
WEIGHTS = [0.50, 0.30, 0.15, 0.05]

app = FastAPI(title='WheelBot API')

ALLOWED_ORIGINS = [
    'https://main0crine-oss.github.io',  # твой GitHub Pages домен
    'http://localhost:8000',
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

@app.get('/api/round')
def api_round():
    conn = get_conn()
    st = get_current_round_state(conn)
    now = int(time.time())
    seconds_left = ROUND_SECONDS - ((now - st['started_at']) % ROUND_SECONDS)
    return {**st, 'seconds_left': seconds_left, 'round_seconds': ROUND_SECONDS}

@app.get('/api/history')
def api_history(limit: int = 50):
    conn = get_conn()
    return history(conn, limit=limit)

async def scheduler():
    conn = get_conn()
    while True:
        await asyncio.sleep(ROUND_SECONDS)
        result = random.choices(MULTS, weights=WEIGHTS)[0]
        finalize_round(conn, result)

@app.on_event('startup')
async def on_start():
    asyncio.create_task(scheduler())
