import json
import sqlite3
from config import DB_PATH

db = sqlite3.connect(DB_PATH, check_same_thread=False)
db.row_factory = sqlite3.Row
db.executescript("""
create table if not exists chats(chat_id integer primary key, title text, type text, session_user integer);
create table if not exists cfg(chat integer, k text, v text, primary key(chat,k));
create table if not exists users(user_id integer primary key, username text, first_name text);
create table if not exists bot_users(user_id integer primary key);
create table if not exists sessions(user_id integer primary key, data blob);
create table if not exists warns(chat integer, user integer, n integer, primary key(chat,user));
create table if not exists notes(chat integer, name text, data text, primary key(chat,name));
create table if not exists filt(chat integer, kw text, data text, primary key(chat,kw));
create table if not exists bl(chat integer, word text, primary key(chat,word));
""")
db.commit()


def q(sql, *a):
    cur = db.execute(sql, a)
    db.commit()
    return cur


def one(sql, *a):
    return db.execute(sql, a).fetchone()


def rows(sql, *a):
    return db.execute(sql, a).fetchall()


def cget(chat, k, d=None):
    r = one("select v from cfg where chat=? and k=?", chat, k)
    return json.loads(r["v"]) if r else d


def cset(chat, k, v):
    q("insert into cfg values(?,?,?) on conflict(chat,k) do update set v=excluded.v", chat, k, json.dumps(v))
