# -*- coding: utf-8 -*-
"""登录认证模块 — SQLite + bcrypt + 暴力破解防护"""
import sqlite3
import hashlib
import os
import secrets
import time
import bcrypt
from functools import wraps
from datetime import timedelta
from flask import request, jsonify, redirect, url_for, session

DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")
_MAX_ATTEMPTS  = 5
_LOCKOUT_SECS  = 15 * 60

# ── secret_key 固定存文件，重启后 session 不失效 ──────────────
KEY_FILE = os.path.join(os.path.dirname(__file__), ".flask_secret")
def get_secret_key():
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE) as f:
            return f.read().strip()
    key = secrets.token_hex(32)
    with open(KEY_FILE, "w") as f:
        f.write(key)
    try:
        os.chmod(KEY_FILE, 0o600)
    except Exception:
        pass
    return key

# ── 数据库初始化 ──────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now'))
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS login_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        ip TEXT NOT NULL,
        attempted_at REAL NOT NULL
    )""")
    # 默认管理员（首次）
    default_user = os.environ.get("ADMIN_USER", "admin")
    default_pass = os.environ.get("ADMIN_PASS", "admin123")
    c.execute("SELECT id FROM users WHERE username=?", (default_user,))
    if not c.fetchone():
        pw_hash = bcrypt.hashpw(default_pass.encode(), bcrypt.gensalt()).decode()
        c.execute("INSERT INTO users (username, password_hash) VALUES (?,?)",
                  (default_user, pw_hash))
    conn.commit()
    conn.close()

def _hash_pw(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def _check_login(username, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT password_hash FROM users WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()
    if not row:
        return False
    stored = row[0]
    # 兼容旧 SHA256（迁移期）
    if len(stored) == 64 and not stored.startswith("$2"):
        return hashlib.sha256(password.encode()).hexdigest() == stored
    return bcrypt.checkpw(password.encode(), stored.encode())

def _client_ip():
    return request.headers.get("X-Forwarded-For", request.remote_addr).split(",")[0].strip()

def _is_locked(username, ip):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    since = time.time() - _LOCKOUT_SECS
    c.execute("SELECT COUNT(*) FROM login_attempts WHERE (username=? OR ip=?) AND attempted_at>?",
              (username, ip, since))
    count = c.fetchone()[0]
    conn.close()
    return count >= _MAX_ATTEMPTS

def _record_attempt(username, ip):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO login_attempts (username,ip,attempted_at) VALUES (?,?,?)",
              (username, ip, time.time()))
    c.execute("DELETE FROM login_attempts WHERE attempted_at<?", (time.time() - 3600,))
    conn.commit()
    conn.close()

def _clear_attempts(username, ip):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM login_attempts WHERE username=? OR ip=?", (username, ip))
    conn.commit()
    conn.close()

def _remaining_attempts(username, ip):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    since = time.time() - _LOCKOUT_SECS
    c.execute("SELECT COUNT(*) FROM login_attempts WHERE (username=? OR ip=?) AND attempted_at>?",
              (username, ip, since))
    count = c.fetchone()[0]
    conn.close()
    return max(0, _MAX_ATTEMPTS - count)

# ── 装饰器（页面路由用）──────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged_in"):
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"ok": False, "error": "未登录"}), 401
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated

# ── before_request 全局拦截 ───────────────────────────────────
def require_login_for_all():
    PUBLIC = {"/login", "/logout"}
    if request.path in PUBLIC or request.path.startswith("/static/"):
        return
    if not session.get("logged_in"):
        if request.path.startswith("/api/"):
            return jsonify({"ok": False, "error": "未登录，请先登录"}), 401
        return redirect(url_for("login_page"))
    session.modified = True
