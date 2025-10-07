# db.py — SQLite helpers for WheelBot (global rounds + bets + users)
import sqlite3, time
from pathlib import Path

DB_PATH = Path(__file__).with_name("wheel.db")

SCHEMA = '''
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS users(
  tg_id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  balance INTEGER NOT NULL DEFAULT 1000
);
CREATE TABLE IF NOT EXISTS rounds(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  result TEXT,
  bank   INTEGER NOT NULL DEFAULT 0,
  started_at INTEGER NOT NULL,
  ended_at   INTEGER
);
CREATE TABLE IF NOT EXISTS bets(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  round_id INTEGER NOT NULL,
  tg_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  amount INTEGER NOT NULL,
  mult TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  FOREIGN KEY(round_id) REFERENCES rounds(id),
  FOREIGN KEY(tg_id) REFERENCES users(tg_id)
);
'''

def get_conn():
    first = not DB_PATH.exists()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    if first:
        conn.executescript(SCHEMA)
        conn.commit()
    return conn

def get_or_create_open_round(conn):
    row = conn.execute('SELECT * FROM rounds WHERE result IS NULL ORDER BY id DESC LIMIT 1').fetchone()
    if row: return row
    ts = int(time.time())
    conn.execute('INSERT INTO rounds(result, bank, started_at) VALUES (NULL, 0, ?)', (ts,))
    conn.commit()
    return conn.execute('SELECT * FROM rounds WHERE result IS NULL ORDER BY id DESC LIMIT 1').fetchone()

def add_user_if_needed(conn, tg_id:int, name:str, start_balance=1000):
    if conn.execute('SELECT 1 FROM users WHERE tg_id=?', (tg_id,)).fetchone(): return
    conn.execute('INSERT INTO users(tg_id,name,balance) VALUES (?,?,?)',(tg_id,name,start_balance)); conn.commit()

def get_balance(conn, tg_id:int, default=1000):
    r = conn.execute('SELECT balance FROM users WHERE tg_id=?', (tg_id,)).fetchone()
    return r['balance'] if r else default

def change_balance(conn, tg_id:int, delta:int):
    conn.execute('UPDATE users SET balance = balance + ? WHERE tg_id=?', (delta, tg_id)); conn.commit()

def place_bet(conn, tg_id:int, name:str, amount:int, mult:str):
    rnd = get_or_create_open_round(conn)
    conn.execute('INSERT INTO bets(round_id,tg_id,name,amount,mult,created_at) VALUES (?,?,?,?,?,?)',
                 (rnd['id'], tg_id, name, amount, mult, int(time.time())))
    conn.execute('UPDATE rounds SET bank = bank + ? WHERE id=?', (amount, rnd['id'])); conn.commit()
    return rnd['id']

def get_current_round_state(conn):
    rnd = get_or_create_open_round(conn)
    players = [dict(r) for r in conn.execute('SELECT name,amount,mult FROM bets WHERE round_id=? ORDER BY id DESC',(rnd['id'],))]
    return {'round_id': rnd['id'], 'bank': rnd['bank'], 'players': players, 'started_at': rnd['started_at']}

def finalize_round(conn, result:str):
    rnd = conn.execute('SELECT * FROM rounds WHERE result IS NULL ORDER BY id DESC LIMIT 1').fetchone()
    if not rnd: return None
    conn.execute('UPDATE rounds SET result=?, ended_at=? WHERE id=?', (result, int(time.time()), rnd['id'])); conn.commit()
    return rnd['id']

def history(conn, limit=50):
    return [dict(r) for r in conn.execute('SELECT id,result,bank,started_at,ended_at FROM rounds WHERE result IS NOT NULL ORDER BY id DESC LIMIT ?', (limit,))]
