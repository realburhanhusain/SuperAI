import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.expanduser('~/.superai/usage.db')

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS token_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            model TEXT NOT NULL,
            prompt_tokens INTEGER DEFAULT 0,
            completion_tokens INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            provider TEXT NOT NULL,
            account_id TEXT,
            latency_ms INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def log_usage(model: str, prompt_tokens: int, completion_tokens: int, provider: str, account_id: str = "default", latency_ms: int = 0):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        total_tokens = prompt_tokens + completion_tokens
        cursor.execute('''
            INSERT INTO token_usage (model, prompt_tokens, completion_tokens, total_tokens, provider, account_id, latency_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (model, prompt_tokens, completion_tokens, total_tokens, provider, account_id, latency_ms))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging usage: {e}")

def get_daily_spend():
    # Placeholder cost mapping - in a real app, load from config
    costs = {
        'gpt-4': 0.03,
        'claude-3-opus': 0.015,
        'gemini-1.5-pro': 0.007,
        'default': 0.001
    }
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Get last 7 days of token usage
    cursor.execute('''
        SELECT date(timestamp) as day, model, SUM(total_tokens)
        FROM token_usage
        WHERE timestamp >= date('now', '-7 days')
        GROUP BY day, model
    ''')
    rows = cursor.fetchall()
    conn.close()
    
    # Process into daily spend
    daily_spend = {}
    for r in rows:
        day, model, tokens = r
        cost_per_1k = costs.get(model, costs['default'])
        spend = (tokens / 1000.0) * cost_per_1k
        daily_spend[day] = daily_spend.get(day, 0) + spend
        
    return daily_spend

def get_model_usage():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT model, COUNT(*) as calls
        FROM token_usage
        WHERE timestamp >= date('now', '-30 days')
        GROUP BY model
    ''')
    rows = cursor.fetchall()
    conn.close()
    return {r[0]: r[1] for r in rows}

init_db()