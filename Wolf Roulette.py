import telebot
import sqlite3
import random
import uuid
import re
import time
import threading
import functools
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
import json

API_TOKEN = '7614599671:AAEdQxvefbJQAtmwm844Z0c3w-BM1lba9x0'
ADMIN_ID = 6812997550
DEVELOPER_CHANNEL = "@bshshshkk"
DEVELOPER_USERNAME = "j49_c"

bot = telebot.TeleBot(API_TOKEN, parse_mode=None)

def get_bot_name():
    try:
        return bot.get_me().first_name or "الذئب الأبيض"
    except Exception:
        return "الذئب الأبيض"

def btn(text, cbd=None, url=None, color=None):
    b = InlineKeyboardButton(text=text, callback_data=cbd, url=url)
    color_map = {
        'green': 'success',
        'red':   'danger',
        'blue':  'primary',
    }
    if color and color in color_map:
        b.style = color_map[color]
    return b

def kb(*rows):
    m = InlineKeyboardMarkup()
    for row in rows:
        if isinstance(row, list):
            m.row(*row)
        else:
            m.row(row)
    return m

user_last_msg = {}

def get_bot_photo():
    conn = get_db()
    try:
        r = conn.execute("SELECT value FROM bot_settings WHERE key='bot_photo'").fetchone()
        return r['value'] if r and r['value'] else None
    finally:
        conn.close()

def send_or_edit(chat_id, text, markup=None, parse_mode="HTML", user_id=None, force_new=False):
    uid = user_id or chat_id
    last = user_last_msg.get(uid)
    photo = get_bot_photo()

    if photo:
        if last and not force_new:
            try:
                bot.edit_message_media(
                    media=telebot.types.InputMediaPhoto(photo, caption=text, parse_mode=parse_mode),
                    chat_id=chat_id,
                    message_id=last,
                    reply_markup=markup
                )
                return
            except Exception:
                try:
                    bot.delete_message(chat_id, last)
                except Exception:
                    pass
        try:
            msg = bot.send_photo(chat_id, photo, caption=text, parse_mode=parse_mode, reply_markup=markup)
            user_last_msg[uid] = msg.message_id
            return msg
        except Exception:
            pass

    if last and not force_new:
        try:
            bot.edit_message_text(text, chat_id, last, reply_markup=markup, parse_mode=parse_mode, disable_web_page_preview=True)
            return
        except Exception:
            try:
                bot.delete_message(chat_id, last)
            except Exception:
                pass

    try:
        msg = bot.send_message(chat_id, text, reply_markup=markup, parse_mode=parse_mode, disable_web_page_preview=True)
        user_last_msg[uid] = msg.message_id
        return msg
    except Exception as e:
        print(f"send_or_edit error: {e}")

def send_new(chat_id, text, markup=None, parse_mode="HTML"):
    try:
        return bot.send_message(chat_id, text, reply_markup=markup, parse_mode=parse_mode, disable_web_page_preview=True)
    except Exception as e:
        print(f"send_new error: {e}")

def del_msg(chat_id, msg_id):
    try:
        bot.delete_message(chat_id, msg_id)
    except Exception:
        pass

def notify(call_or_uid, text):
    try:
        if isinstance(call_or_uid, CallbackQuery):
            bot.answer_callback_query(call_or_uid.id, text, show_alert=True)
        else:
            bot.answer_callback_query(call_or_uid, text, show_alert=True)
    except Exception:
        pass

def get_db():
    conn = sqlite3.connect('bot.db', check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn

def db_exec(query, params=(), fetchone=False, fetchall=False, commit=False):
    conn = get_db()
    try:
        cur = conn.execute(query, params)
        if commit:
            conn.commit()
        if fetchone:
            return cur.fetchone()
        if fetchall:
            return cur.fetchall()
        return cur
    finally:
        conn.close()

def init_db():
    conn = get_db()
    try:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT DEFAULT '',
                full_name TEXT DEFAULT '',
                joined_at TEXT,
                is_banned INTEGER DEFAULT 0,
                ban_reason TEXT DEFAULT '',
                total_roulettes_created INTEGER DEFAULT 0,
                total_participations INTEGER DEFAULT 0,
                state TEXT DEFAULT '',
                temp_data TEXT DEFAULT '{}',
                notify_participants INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER,
                channel_id INTEGER UNIQUE,
                channel_username TEXT DEFAULT '',
                channel_title TEXT DEFAULT '',
                added_at TEXT
            );
            CREATE TABLE IF NOT EXISTS roulettes (
                roulette_id TEXT PRIMARY KEY,
                creator_id INTEGER,
                channel_id INTEGER,
                channel_username TEXT DEFAULT '',
                channel_message_id INTEGER,
                text TEXT,
                photo_id TEXT DEFAULT '',
                winners_count INTEGER DEFAULT 1,
                max_participants INTEGER,
                end_time TEXT,
                conditional_channel_id INTEGER,
                conditional_channel_username TEXT DEFAULT '',
                conditional_channel_id_2 INTEGER,
                conditional_channel_username_2 TEXT DEFAULT '',
                join_type TEXT DEFAULT 'captcha',
                is_active INTEGER DEFAULT 1,
                is_finished INTEGER DEFAULT 0,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                roulette_id TEXT,
                user_id INTEGER,
                tickets INTEGER DEFAULT 1,
                joined_at TEXT,
                referred_by INTEGER
            );
            CREATE TABLE IF NOT EXISTS winners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                roulette_id TEXT,
                user_id INTEGER,
                won_at TEXT
            );
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                roulette_id TEXT,
                referrer_id INTEGER,
                referred_id INTEGER,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                roulette_id TEXT,
                user_id INTEGER
            );
            CREATE TABLE IF NOT EXISTS creator_bans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_id INTEGER,
                user_id INTEGER,
                banned_at TEXT
            );
            CREATE TABLE IF NOT EXISTS bot_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            CREATE TABLE IF NOT EXISTS contests (
                contest_id TEXT PRIMARY KEY,
                creator_id INTEGER,
                channel_id INTEGER,
                channel_username TEXT DEFAULT '',
                channel_message_id INTEGER DEFAULT 0,
                title TEXT,
                description TEXT,
                photo_id TEXT DEFAULT '',
                max_participants INTEGER,
                ranks_count INTEGER DEFAULT 3,
                auto_accept INTEGER DEFAULT 1,
                is_active INTEGER DEFAULT 1,
                is_finished INTEGER DEFAULT 0,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS contest_participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contest_id TEXT,
                user_id INTEGER,
                display_name TEXT,
                username TEXT DEFAULT '',
                channel_message_id INTEGER DEFAULT 0,
                votes INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                joined_at TEXT
            );
            CREATE TABLE IF NOT EXISTS contest_votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contest_id TEXT,
                voter_id INTEGER,
                voted_for INTEGER,
                voted_at TEXT
            );
            CREATE TABLE IF NOT EXISTS forced_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER UNIQUE,
                channel_username TEXT DEFAULT '',
                channel_title TEXT DEFAULT '',
                added_at TEXT
            );
        ''')
        for k, v in [('maintenance_mode', '0'), ('bot_photo', '')]:
            conn.execute("INSERT OR IGNORE INTO bot_settings VALUES (?,?)", (k, v))
        conn.commit()
    finally:
        conn.close()

def migrate_db():
    cols = [
        ("roulettes", "photo_id", "TEXT DEFAULT ''"),
        ("roulettes", "conditional_channel_id_2", "INTEGER"),
        ("roulettes", "conditional_channel_username_2", "TEXT DEFAULT ''"),
        ("roulettes", "join_type", "TEXT DEFAULT 'captcha'"),
        ("contests", "photo_id", "TEXT DEFAULT ''"),
        ("contests", "channel_message_id", "INTEGER DEFAULT 0"),
        ("users", "state", "TEXT DEFAULT ''"),
        ("users", "temp_data", "TEXT DEFAULT '{}'"),
        ("users", "notify_participants", "INTEGER DEFAULT 1"),
        ("contest_participants", "username", "TEXT DEFAULT ''"),
    ]
    conn = get_db()
    try:
        for t, c, ct in cols:
            try:
                conn.execute(f"ALTER TABLE {t} ADD COLUMN {c} {ct}")
                conn.commit()
            except Exception:
                pass
    finally:
        conn.close()

def add_user(user_id, username, full_name):
    conn = get_db()
    try:
        ex = conn.execute('SELECT user_id FROM users WHERE user_id=?', (user_id,)).fetchone()
        is_new = not bool(ex)
        conn.execute('''
            INSERT OR IGNORE INTO users
            (user_id,username,full_name,joined_at,state,temp_data,notify_participants)
            VALUES (?,?,?,?,?,?,1)
        ''', (user_id, username or '', full_name or '', datetime.now().isoformat(), '', '{}'))
        conn.execute('UPDATE users SET username=?,full_name=? WHERE user_id=?', (username or '', full_name or '', user_id))
        conn.commit()
        return is_new
    finally:
        conn.close()

def get_user(user_id):
    return db_exec('SELECT * FROM users WHERE user_id=?', (user_id,), fetchone=True)

def is_banned(user_id):
    r = db_exec('SELECT is_banned FROM users WHERE user_id=?', (user_id,), fetchone=True)
    return bool(r and r['is_banned'])

def set_user_state(user_id, state, temp=None):
    conn = get_db()
    try:
        conn.execute('UPDATE users SET state=?,temp_data=? WHERE user_id=?', (state, json.dumps(temp or {}), user_id))
        conn.commit()
    finally:
        conn.close()

def get_user_state(user_id):
    r = db_exec('SELECT state,temp_data FROM users WHERE user_id=?', (user_id,), fetchone=True)
    if r:
        try:
            return r['state'], json.loads(r['temp_data'] or '{}')
        except Exception:
            return r['state'], {}
    return '', {}

def clear_user_state(user_id):
    conn = get_db()
    try:
        conn.execute("UPDATE users SET state='',temp_data='{}' WHERE user_id=?", (user_id,))
        conn.commit()
    finally:
        conn.close()

def get_notify_setting(user_id):
    r = db_exec('SELECT notify_participants FROM users WHERE user_id=?', (user_id,), fetchone=True)
    return bool(r and r['notify_participants'])

def toggle_notify(user_id):
    cur = get_notify_setting(user_id)
    conn = get_db()
    try:
        conn.execute('UPDATE users SET notify_participants=? WHERE user_id=?', (0 if cur else 1, user_id))
        conn.commit()
    finally:
        conn.close()
    return not cur

def is_maintenance():
    r = db_exec("SELECT value FROM bot_settings WHERE key='maintenance_mode'", fetchone=True)
    return r and r['value'] == '1'

def set_maintenance(val):
    conn = get_db()
    try:
        conn.execute("UPDATE bot_settings SET value=? WHERE key='maintenance_mode'", ('1' if val else '0',))
        conn.commit()
    finally:
        conn.close()

def get_setting(key):
    r = db_exec("SELECT value FROM bot_settings WHERE key=?", (key,), fetchone=True)
    return r['value'] if r else None

def set_setting(key, value):
    conn = get_db()
    try:
        conn.execute("INSERT OR REPLACE INTO bot_settings VALUES (?,?)", (key, value))
        conn.commit()
    finally:
        conn.close()

def get_all_users():
    return db_exec('SELECT user_id FROM users', fetchall=True)

def get_stats():
    conn = get_db()
    try:
        tu = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        bu = conn.execute('SELECT COUNT(*) FROM users WHERE is_banned=1').fetchone()[0]
        tr = conn.execute('SELECT COUNT(*) FROM roulettes').fetchone()[0]
        ar = conn.execute('SELECT COUNT(*) FROM roulettes WHERE is_active=1 AND is_finished=0').fetchone()[0]
        tp = conn.execute('SELECT COUNT(*) FROM participants').fetchone()[0]
        tc = conn.execute('SELECT COUNT(*) FROM contests').fetchone()[0]
        top = conn.execute('SELECT user_id,username,total_roulettes_created FROM users ORDER BY total_roulettes_created DESC LIMIT 1').fetchone()
        today = datetime.now().date().isoformat()
        tu2 = conn.execute("SELECT COUNT(*) FROM users WHERE joined_at LIKE ?", (today + '%',)).fetchone()[0]
        fc = conn.execute('SELECT COUNT(*) FROM forced_channels').fetchone()[0]
        return dict(total_users=tu, banned=bu, total_roulettes=tr, active_roulettes=ar, total_parts=tp, total_contests=tc, top_creator=top, today_users=tu2, forced_channels=fc)
    finally:
        conn.close()

def get_user_stats(user_id):
    conn = get_db()
    try:
        my_roulettes = conn.execute('SELECT COUNT(*) FROM roulettes WHERE creator_id=?', (user_id,)).fetchone()[0]
        my_contests = conn.execute('SELECT COUNT(*) FROM contests WHERE creator_id=?', (user_id,)).fetchone()[0]
        total_my_parts = conn.execute('''SELECT COUNT(*) FROM participants p JOIN roulettes r ON p.roulette_id=r.roulette_id WHERE r.creator_id=?''', (user_id,)).fetchone()[0]
        total_my_winners = conn.execute('''SELECT COUNT(*) FROM winners w JOIN roulettes r ON w.roulette_id=r.roulette_id WHERE r.creator_id=?''', (user_id,)).fetchone()[0]
        joined_roulettes = conn.execute('SELECT COUNT(*) FROM participants WHERE user_id=?', (user_id,)).fetchone()[0]
        wins = conn.execute('SELECT COUNT(*) FROM winners WHERE user_id=?', (user_id,)).fetchone()[0]
        total_tickets = conn.execute('SELECT COALESCE(SUM(tickets),0) FROM participants WHERE user_id=?', (user_id,)).fetchone()[0]
        joined_contests = conn.execute('SELECT COUNT(*) FROM contest_participants WHERE user_id=?', (user_id,)).fetchone()[0]
        return dict(my_roulettes=my_roulettes, my_contests=my_contests, total_my_parts=total_my_parts, total_my_winners=total_my_winners, joined_roulettes=joined_roulettes, wins=wins, total_tickets=total_tickets, joined_contests=joined_contests)
    finally:
        conn.close()

def add_channel(owner_id, channel_id, username, title):
    conn = get_db()
    try:
        conn.execute('INSERT OR REPLACE INTO channels (owner_id,channel_id,channel_username,channel_title,added_at) VALUES (?,?,?,?,?)', (owner_id, channel_id, username or '', title or '', datetime.now().isoformat()))
        conn.commit()
    finally:
        conn.close()

def get_user_channels(user_id):
    return db_exec('SELECT * FROM channels WHERE owner_id=?', (user_id,), fetchall=True)

def get_channel(channel_id):
    return db_exec('SELECT * FROM channels WHERE channel_id=?', (channel_id,), fetchone=True)

def remove_channel(owner_id, channel_id):
    conn = get_db()
    try:
        conn.execute('DELETE FROM channels WHERE owner_id=? AND channel_id=?', (owner_id, channel_id))
        conn.commit()
    finally:
        conn.close()

def is_ch_admin(channel_id, user_id):
    try:
        m = bot.get_chat_member(channel_id, user_id)
        return m.status in ['administrator', 'creator']
    except Exception:
        return False

def is_ch_member(channel_id, user_id):
    try:
        m = bot.get_chat_member(channel_id, user_id)
        return m.status not in ['left', 'kicked']
    except Exception:
        return False

def can_use_channel(channel_id, user_id):
    if not get_channel(channel_id):
        return False
    return is_ch_admin(channel_id, user_id)

def get_forced_channels():
    return db_exec('SELECT * FROM forced_channels', fetchall=True)

def add_forced_channel(channel_id, username, title):
    conn = get_db()
    try:
        conn.execute('INSERT OR REPLACE INTO forced_channels (channel_id,channel_username,channel_title,added_at) VALUES (?,?,?,?)', (channel_id, username or '', title or '', datetime.now().isoformat()))
        conn.commit()
    finally:
        conn.close()

def remove_forced_channel(channel_id):
    conn = get_db()
    try:
        conn.execute('DELETE FROM forced_channels WHERE channel_id=?', (channel_id,))
        conn.commit()
    finally:
        conn.close()

def check_forced_subscription(user_id):
    fcs = get_forced_channels()
    return [fc for fc in fcs if not is_ch_member(fc['channel_id'], user_id)]

def create_roulette(rid, creator_id, channel_id, ch_username, ch_msg_id, text, photo_id, winners_count, max_p, end_time, cc1, cu1, cc2, cu2, join_type='captcha'):
    conn = get_db()
    try:
        conn.execute('''
            INSERT INTO roulettes (
                roulette_id, creator_id, channel_id,
                channel_username, channel_message_id,
                text, photo_id, winners_count,
                max_participants, end_time,
                conditional_channel_id,
                conditional_channel_username,
                conditional_channel_id_2,
                conditional_channel_username_2,
                join_type,
                is_active, is_finished, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,0,?)
        ''', (rid, creator_id, channel_id, ch_username or '', ch_msg_id, text, photo_id or '', winners_count, max_p, end_time, cc1, cu1 or '', cc2, cu2 or '', join_type or 'captcha', datetime.now().isoformat()))
        conn.execute('UPDATE users SET total_roulettes_created=total_roulettes_created+1 WHERE user_id=?', (creator_id,))
        conn.commit()
    finally:
        conn.close()

def get_roulette(rid):
    return db_exec('SELECT * FROM roulettes WHERE roulette_id=?', (rid,), fetchone=True)

def get_active_roulettes():
    return db_exec('SELECT * FROM roulettes WHERE is_active=1 AND is_finished=0', fetchall=True)

def get_creator_roulettes(creator_id):
    return db_exec('SELECT * FROM roulettes WHERE creator_id=? AND is_finished=0 ORDER BY created_at DESC', (creator_id,), fetchall=True)

def update_roulette_active(rid, val):
    conn = get_db()
    try:
        conn.execute('UPDATE roulettes SET is_active=? WHERE roulette_id=?', (1 if val else 0, rid))
        conn.commit()
    finally:
        conn.close()

def finish_roulette(rid):
    conn = get_db()
    try:
        conn.execute('UPDATE roulettes SET is_finished=1,is_active=0 WHERE roulette_id=?', (rid,))
        conn.commit()
    finally:
        conn.close()

def update_roulette_msg_id(rid, msg_id):
    conn = get_db()
    try:
        conn.execute('UPDATE roulettes SET channel_message_id=? WHERE roulette_id=?', (msg_id, rid))
        conn.commit()
    finally:
        conn.close()

def add_participant(rid, user_id, referred_by=None):
    conn = get_db()
    try:
        ex = conn.execute('SELECT id FROM participants WHERE roulette_id=? AND user_id=?', (rid, user_id)).fetchone()
        if ex:
            return False
        conn.execute('INSERT INTO participants (roulette_id,user_id,tickets,joined_at,referred_by) VALUES (?,?,1,?,?)', (rid, user_id, datetime.now().isoformat(), referred_by))
        conn.execute('UPDATE users SET total_participations=total_participations+1 WHERE user_id=?', (user_id,))
        conn.commit()
        return True
    finally:
        conn.close()

def get_participants(rid):
    return db_exec('SELECT * FROM participants WHERE roulette_id=?', (rid,), fetchall=True)

def get_participant(rid, user_id):
    return db_exec('SELECT * FROM participants WHERE roulette_id=? AND user_id=?', (rid, user_id), fetchone=True)

def get_part_count(rid):
    r = db_exec('SELECT COUNT(*) FROM participants WHERE roulette_id=?', (rid,), fetchone=True)
    return r[0] if r else 0

def add_ticket(rid, user_id):
    conn = get_db()
    try:
        conn.execute('UPDATE participants SET tickets=tickets+1 WHERE roulette_id=? AND user_id=?', (rid, user_id))
        conn.commit()
    finally:
        conn.close()

def get_tickets(rid, user_id):
    r = db_exec('SELECT tickets FROM participants WHERE roulette_id=? AND user_id=?', (rid, user_id), fetchone=True)
    return r['tickets'] if r else 0

def remove_participant(rid, user_id):
    conn = get_db()
    try:
        conn.execute('DELETE FROM participants WHERE roulette_id=? AND user_id=?', (rid, user_id))
        conn.commit()
    finally:
        conn.close()

def add_referral(rid, referrer, referred):
    conn = get_db()
    try:
        ex = conn.execute('SELECT id FROM referrals WHERE roulette_id=? AND referred_id=?', (rid, referred)).fetchone()
        if not ex:
            conn.execute('INSERT INTO referrals (roulette_id,referrer_id,referred_id,created_at) VALUES (?,?,?,?)', (rid, referrer, referred, datetime.now().isoformat()))
            conn.commit()
            return True
        return False
    finally:
        conn.close()

def add_winner(rid, user_id):
    conn = get_db()
    try:
        conn.execute('INSERT INTO winners (roulette_id,user_id,won_at) VALUES (?,?,?)', (rid, user_id, datetime.now().isoformat()))
        conn.commit()
    finally:
        conn.close()

def get_winners(rid):
    return db_exec('SELECT * FROM winners WHERE roulette_id=?', (rid,), fetchall=True)

def add_reminder(rid, user_id):
    conn = get_db()
    try:
        ex = conn.execute('SELECT id FROM reminders WHERE roulette_id=? AND user_id=?', (rid, user_id)).fetchone()
        if not ex:
            conn.execute('INSERT INTO reminders (roulette_id,user_id) VALUES (?,?)', (rid, user_id))
            conn.commit()
    finally:
        conn.close()

def get_reminders(rid):
    return db_exec('SELECT user_id FROM reminders WHERE roulette_id=?', (rid,), fetchall=True)

def ban_from_creator(creator_id, user_id):
    conn = get_db()
    try:
        ex = conn.execute('SELECT id FROM creator_bans WHERE creator_id=? AND user_id=?', (creator_id, user_id)).fetchone()
        if not ex:
            conn.execute('INSERT INTO creator_bans (creator_id,user_id,banned_at) VALUES (?,?,?)', (creator_id, user_id, datetime.now().isoformat()))
            conn.commit()
    finally:
        conn.close()

def is_banned_from_creator(creator_id, user_id):
    r = db_exec('SELECT id FROM creator_bans WHERE creator_id=? AND user_id=?', (creator_id, user_id), fetchone=True)
    return bool(r)

def perform_draw(rid):
    parts = get_participants(rid)
    r = get_roulette(rid)
    if not parts or not r:
        return []
    pool = []
    for p in parts:
        for _ in range(p['tickets']):
            pool.append(p['user_id'])
    wc = min(r['winners_count'], len(set(pool)))
    random.shuffle(pool)
    winners, seen = [], set()
    for uid in pool:
        if uid not in seen:
            winners.append(uid)
            seen.add(uid)
        if len(winners) >= wc:
            break
    for w in winners:
        add_winner(rid, w)
    finish_roulette(rid)
    return winners

def create_contest(cid, creator_id, channel_id, ch_username, title, description, photo_id, max_p, ranks, auto_accept):
    conn = get_db()
    try:
        conn.execute('''
            INSERT INTO contests
            (contest_id,creator_id,channel_id,channel_username,
             channel_message_id,title,description,photo_id,
             max_participants,ranks_count,auto_accept,
             is_active,is_finished,created_at)
            VALUES (?,?,?,?,0,?,?,?,?,?,?,1,0,?)
        ''', (cid, creator_id, channel_id, ch_username or '', title, description, photo_id or '', max_p, ranks, 1 if auto_accept else 0, datetime.now().isoformat()))
        conn.commit()
    finally:
        conn.close()

def get_contest(cid):
    return db_exec('SELECT * FROM contests WHERE contest_id=?', (cid,), fetchone=True)

def get_contest_parts(cid, status='accepted'):
    return db_exec('SELECT * FROM contest_participants WHERE contest_id=? AND status=? ORDER BY votes DESC', (cid, status), fetchall=True)

def add_contest_part(cid, user_id, display_name, username, ch_msg_id, status='accepted'):
    conn = get_db()
    try:
        ex = conn.execute('SELECT id FROM contest_participants WHERE contest_id=? AND user_id=?', (cid, user_id)).fetchone()
        if ex:
            return False
        conn.execute('INSERT INTO contest_participants (contest_id,user_id,display_name,username,channel_message_id,status,joined_at) VALUES (?,?,?,?,?,?,?)', (cid, user_id, display_name, username or '', ch_msg_id, status, datetime.now().isoformat()))
        conn.commit()
        return True
    finally:
        conn.close()

def add_vote_new(cid, voter_id, voted_for):
    conn = get_db()
    try:
        ex = conn.execute('SELECT id FROM contest_votes WHERE contest_id=? AND voter_id=? AND voted_for=?', (cid, voter_id, voted_for)).fetchone()
        if ex:
            return False, "already_voted"
        conn.execute('INSERT INTO contest_votes (contest_id,voter_id,voted_for,voted_at) VALUES (?,?,?,?)', (cid, voter_id, voted_for, datetime.now().isoformat()))
        conn.execute('UPDATE contest_participants SET votes=votes+1 WHERE contest_id=? AND user_id=?', (cid, voted_for))
        conn.commit()
        return True, "success"
    finally:
        conn.close()

def has_voted_for(cid, voter_id, voted_for):
    r = db_exec('SELECT id FROM contest_votes WHERE contest_id=? AND voter_id=? AND voted_for=?', (cid, voter_id, voted_for), fetchone=True)
    return bool(r)

def finish_contest(cid):
    conn = get_db()
    try:
        conn.execute('UPDATE contests SET is_finished=1,is_active=0 WHERE contest_id=?', (cid,))
        conn.commit()
    finally:
        conn.close()

POSITIVE_EMOJIS = ["🎉","🔥","⭐","🏆","💎","🎯","🚀","💫","🌟","🎊","👑","💪"]
CAPTCHA_EMOJIS = ["🐶","🐱","🐭","🐹","🐰","🦊","🐻","🐼","🐨","🐯","🦁","🐮","🐷","🐸","🐵","🐔","🐧","🐦","🦆","🦅","🦉","🦇","🐺","🐗","🦄","🐝","🐛","🦋","🐌","🐞","🦎","🐍","🦖","🦕","🐙","🦑"]
CAPTCHA_TIMEOUT = 300
captcha_store = {}

def gen_captcha(user_id, target_id):
    correct = random.choice(CAPTCHA_EMOJIS)
    wrong = random.sample([e for e in CAPTCHA_EMOJIS if e != correct], 3)
    options = [correct] + wrong
    random.shuffle(options)
    captcha_store[f"{user_id}_{target_id}"] = {'correct': correct, 'options': options, 'expires': time.time() + CAPTCHA_TIMEOUT}
    return correct, options

def get_captcha(user_id, target_id):
    data = captcha_store.get(f"{user_id}_{target_id}")
    if not data:
        return None
    if time.time() > data['expires']:
        captcha_store.pop(f"{user_id}_{target_id}", None)
        return None
    return data

def clear_captcha(user_id, target_id):
    captcha_store.pop(f"{user_id}_{target_id}", None)

def _captcha_cleanup_worker():
    while True:
        try:
            now = time.time()
            expired = [k for k, v in list(captcha_store.items()) if now > v.get('expires', 0)]
            for k in expired:
                captcha_store.pop(k, None)
        except Exception as e:
            print(f"captcha_cleanup error: {e}")
        time.sleep(300)

def _roulette_timer_worker():
    while True:
        try:
            conn = get_db()
            try:
                now = datetime.now().isoformat()
                expired = conn.execute('''SELECT roulette_id, creator_id FROM roulettes WHERE end_time IS NOT NULL AND end_time <= ? AND is_finished=0''', (now,)).fetchall()
            finally:
                conn.close()
            for r in expired:
                rid = r['roulette_id']
                try:
                    if get_part_count(rid) > 0:
                        _execute_draw(rid, auto=True)
                    else:
                        finish_roulette(rid)
                        try:
                            update_roulette_msg(rid)
                        except Exception:
                            pass
                        try:
                            send_new(r['creator_id'], "⏰ انتهى وقت الروليت، ولم يكن هناك مشاركون.")
                        except Exception:
                            pass
                except Exception as e:
                    print(f"timer error (rid={rid}): {e}")
        except Exception as e:
            print(f"timer outer error: {e}")
        time.sleep(60)

def contains_link(text):
    patterns = [r'https?://', r'www\.', r't\.me/', r'\+\d{7,15}', r'telegram\.me', r'telegram\.org',]
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            return True
    return False

def extract_text(msg):
    try:
        if msg.html_text:
            return msg.html_text
    except Exception:
        pass
    try:
        if msg.html_caption:
            return msg.html_caption
    except Exception:
        pass
    return msg.text or msg.caption or ""

def get_mention(user_id):
    try:
        c = bot.get_chat(user_id)
        n = c.first_name or f"مستخدم {user_id}"
        return f'<a href="tg://user?id={user_id}">{n}</a>'
    except Exception:
        return f"مستخدم {user_id}"

def get_dname(user_id):
    try:
        c = bot.get_chat(user_id)
        return (f"@{c.username}" if c.username else (c.first_name or f"مستخدم {user_id}"))
    except Exception:
        return f"مستخدم {user_id}"

def fmt_dt(s):
    try:
        return datetime.fromisoformat(s).strftime("%Y/%m/%d %H:%M")
    except Exception:
        return s

def ref_link(user_id, rid):
    u = bot.get_me().username
    return f"https://t.me/{u}?start=ref_{user_id}_{rid}"

def get_channel_link(rid):
    r = get_roulette(rid)
    if r and r['channel_username']:
        return f"https://t.me/{r['channel_username']}"
    return None

def notify_admin_new_user(user_id, username, full_name):
    try:
        uname = f"@{username}" if username else "لا يوجد"
        mention = f'<a href="tg://user?id={user_id}">{full_name or "مستخدم"}</a>'
        send_new(ADMIN_ID, f"👤 مستخدم جديد!\n\nالاسم: {mention}\nاليوزر: {uname}\nالآيدي: <code>{user_id}</code>\nالتاريخ: {fmt_dt(datetime.now().isoformat())}")
    except Exception:
        pass

ROULETTE_PROMPT = "✏️ أرسل نص الروليت\n\nيمكنك استخدام تنسيقات تيليجرام (عريض، مائل، تحته خط...)\n\n🚫 ممنوع: الروابط والأرقام"
MAINTENANCE_MSG = "🔧 البوت في وضع الصيانة\n\nسيعود قريباً 🙏"
NO_PERM = "🚫 ليس لديك صلاحية."

def _build_footer():
    try:
        bot_username = bot.get_me().username
        bot_name = get_bot_name()
    except Exception:
        bot_username = ""
        bot_name = "الذئب الأبيض"
    bot_url = f"https://t.me/{bot_username}"
    ch_url = f"https://t.me/{DEVELOPER_CHANNEL.replace('@', '')}"
    return f'\n\n<a href="{bot_url}">{bot_name}</a> › <a href="{ch_url}">قناة البوت</a>'

def _build_roulette_text(r, count):
    if hasattr(r, 'keys'):
        text = r['text']
        ccu1 = r['conditional_channel_username'] or ''
        ccu2 = r['conditional_channel_username_2'] or ''
        wc   = r['winners_count']
        mp   = r['max_participants']
        et   = r['end_time']
    else:
        text = r.get('text', '')
        ccu1 = r.get('conditional_channel_username', '')
        ccu2 = r.get('conditional_channel_username_2', '')
        wc   = r.get('winners_count', 1)
        mp   = r.get('max_participants')
        et   = r.get('end_time')

    cond = ""
    if ccu1:
        cond += f'\n\n📢 شرط المشاركة: الاشتراك بالقناة <a href="https://t.me/{ccu1}">هنا</a>'
    if ccu2:
        cond += f'\n📢 شرط إضافي: الاشتراك بالقناة <a href="https://t.me/{ccu2}">هنا</a>'

    info = f"\n\n🏆 عدد الفائزين: {wc}\n"
    info += f"👥 المشاركون: {count}"
    if mp:
        info += f" / {mp}"
    if et:
        info += f"\n⏰ ينتهي في: {fmt_dt(et)}"

    return f"<blockquote>{text}</blockquote>" + cond + info + _build_footer()

def _build_contest_text(data, count):
    ranks_e = {1: "🥇", 2: "🥈", 3: "🥉"}
    rc = data.get('contest_ranks', data.get('ranks_count', 3))
    mp = data.get('contest_max_p', data.get('max_participants', '?'))
    title = data.get('contest_title', data.get('title', ''))
    desc = data.get('contest_description', data.get('description', ''))
    ranks_lines = "\n".join([f"  {ranks_e.get(i, f'#{i}')} المركز {i}" for i in range(1, rc + 1)])
    return f"🏆 <b>{title}</b>\n\n{desc}\n\n🥇 <b>المراكز الفائزة:</b>\n{ranks_lines}\n\n👥 <b>المشاركون:</b> {count} / {mp}\n\n👇 <b>اضغط للمشاركة!</b>" + _build_footer()

def _build_roulette_preview(r_data, uid):
    count = 0
    text = _build_roulette_text(r_data, count)
    wc   = r_data.get('winners_count', 1)
    mp   = r_data.get('max_participants')
    et   = r_data.get('end_time')
    ccu1 = r_data.get('conditional_channel_username', '')
    ccu2 = r_data.get('conditional_channel_username_2', '')
    jt   = r_data.get('join_type', 'captcha')
    jt_label = "⚡ انضمام مباشر" if jt == 'direct' else "🔐 تحقق بكابتشا"
    preview = f"👁 <b>معاينة الروليت قبل النشر</b>\n\n{text}\n\n📋 <b>ملخص:</b>\n🏆 الفائزون: <b>{wc}</b>\n👥 الحد الأقصى: <b>{mp or 'غير محدد'}</b>\n⏰ وقت الانتهاء: <b>{fmt_dt(et) if et else 'غير محدد'}</b>\n🚪 نوع الانضمام: <b>{jt_label}</b>\n"
    if ccu1:
        preview += f"📢 شرط 1: <b>@{ccu1}</b>\n"
    if ccu2:
        preview += f"📢 شرط 2: <b>@{ccu2}</b>\n"
    if r_data.get('photo_id'):
        preview += "🖼️ الصورة: <b>✅ مضافة</b>\n"
    preview += "\nهل تريد النشر الآن؟"
    return preview

def _build_contest_preview(temp):
    rc    = temp.get('contest_ranks', 3)
    mp    = temp.get('contest_max_p', '?')
    title = temp.get('contest_title', '')
    desc  = temp.get('contest_description', '')
    auto  = temp.get('auto_accept', True)
    ranks_e = {1: "🥇", 2: "🥈", 3: "🥉"}
    ranks_lines = "\n".join([f"  {ranks_e.get(i, f'#{i}')} المركز {i}" for i in range(1, rc + 1)])
    preview = f"👁 <b>معاينة المسابقة قبل النشر</b>\n\n🏆 <b>{title}</b>\n\n{desc}\n\n🥇 <b>المراكز الفائزة:</b>\n{ranks_lines}\n\n👥 الحد الأقصى: <b>{mp}</b>\n👤 القبول: <b>{'تلقائي ✅' if auto else 'يدوي 👤'}</b>\n"
    if temp.get('contest_photo'):
        preview += "🖼️ الصورة: <b>✅ مضافة</b>\n"
    preview += "\nهل تريد النشر الآن؟"
    return preview

def _send_captcha(chat_id, uid, rid):
    correct, options = gen_captcha(uid, rid)
    btns = []
    for i, e in enumerate(options):
        btns.append(btn(e, cbd=f"cap_{i}_{rid}", color='blue'))
    send_new(chat_id, f"🔐 تحقق سريع!\n\nاختر الإيموجي الصحيح: <b>{correct}</b>", markup=kb(btns))

def _send_contest_captcha(chat_id, uid, cid):
    correct, options = gen_captcha(uid, f"contest_{cid}")
    btns = []
    for i, e in enumerate(options):
        btns.append(btn(e, cbd=f"ccap_{i}_{cid}", color='blue'))
    try:
        bot.send_message(chat_id, f"🔐 تحقق سريع!\n\nاختر الإيموجي الصحيح: <b>{correct}</b>", parse_mode="HTML", reply_markup=kb(btns))
    except Exception:
        send_new(chat_id, f"🔐 تحقق!\n\nاختر: <b>{correct}</b>", markup=kb(btns))

def _send_vote_captcha(uid, cid, pid):
    correct, options = gen_captcha(uid, f"vote_{cid}_{pid}")
    btns = []
    for i, e in enumerate(options):
        btns.append(btn(e, cbd=f"vcap_{i}_{cid}_{pid}", color='blue'))
    send_new(uid, f"🔐 تحقق قبل التصويت!\n\nاختر الإيموجي الصحيح: <b>{correct}</b>", markup=kb(btns))

def main_menu_kb(uid=None):
    bot_name = get_bot_name()
    rows = [
        [btn("🎯 إنشاء روليت", cbd="create_roulette", color='green'), btn("🏆 إنشاء مسابقة", cbd="create_contest", color='green')],
        [btn("📊 روليتاتي", cbd="my_roulettes", color='blue'), btn("🏅 مسابقاتي", cbd="my_contests", color='blue')],
        [btn("📋 قنواتي", cbd="my_channels", color='red')],
        [btn("🔔 تذكيراتي", cbd="my_reminders", color='blue'), btn("🎫 تذاكري", cbd="my_tickets", color='blue')],
        [btn("📈 إحصائياتي", cbd="my_stats", color='red')],
        [btn("💬 تواصل مع المطور", url=f"https://t.me/{DEVELOPER_USERNAME}", color='green'), btn("📢 قناة البوت", url=f"https://t.me/{DEVELOPER_CHANNEL.replace('@', '')}", color='green')]
    ]
    if uid and uid == ADMIN_ID:
        rows.append([btn("🛠️ لوحة التحكم", cbd="adm_panel", color='red')])
    return kb(*rows)

def admin_kb():
    return kb(
        [btn("📊 إحصائيات", cbd="adm_stats", color='blue'), btn("📢 إذاعة", cbd="adm_broadcast", color='blue')],
        [btn("🚫 حظر", cbd="adm_ban", color='red'), btn("✅ فك حظر", cbd="adm_unban", color='green')],
        [btn("🔧 صيانة", cbd="adm_maintenance", color='red'), btn("📋 روليتات نشطة", cbd="adm_roulettes", color='blue')],
        [btn("📢 اشتراك إجباري", cbd="adm_forced", color='green')],
        [btn("🖼️ صورة البوت", cbd="adm_photo", color='blue')],
        [btn("🔙 رجوع", cbd="back_main", color='red')]
    )

def admin_back_kb():
    return kb([btn("🔙 لوحة الأدمن", cbd="adm_panel", color='red')])

def cancel_kb():
    return kb([btn("❌ إلغاء", cbd="back_main", color='red')])

def back_kb(cb="back_main"):
    return kb([btn("🔙 رجوع", cbd=cb, color='red')])

def my_channels_kb(channels):
    rows = []
    for ch in channels:
        n = ch['channel_username'] or ch['channel_title']
        rows.append([btn(f"📢 @{n}", cbd=f"ch_info_{ch['channel_id']}", color='blue')])
    rows.append([btn("➕ ربط قناة جديدة", cbd="bind_channel", color='green')])
    rows.append([btn("🔙 رجوع", cbd="back_main", color='red')])
    return kb(*rows)

def channel_info_kb(channel_id):
    return kb(
        [btn("🗑️ حذف القناة", cbd=f"ch_del_confirm_{channel_id}", color='red')],
        [btn("🔙 رجوع", cbd="my_channels", color='red')]
    )

def confirm_del_kb(channel_id):
    return kb(
        [btn("✅ نعم احذف", cbd=f"ch_del_{channel_id}", color='red'), btn("❌ لا", cbd=f"ch_info_{channel_id}", color='green')]
    )

def bind_kb():
    try:
        u = bot.get_me().username
        add_url = f"https://t.me/{u}?startchannel=true&admin=post_messages+edit_messages+delete_messages"
    except Exception:
        add_url = "https://t.me/"
    return kb(
        [btn("📥 أضفني لقناتك", url=add_url, color='green')],
        [btn("✅ أضفت البوت", cbd="bot_added", color='green')],
        [btn("🔙 رجوع", cbd="my_channels", color='red')]
    )

def choose_channel_kb(channels, action):
    rows = []
    for ch in channels:
        n = ch['channel_username'] or ch['channel_title']
        rows.append([btn(f"📢 @{n}", cbd=f"sel_ch_{action}_{ch['channel_id']}", color='blue')])
    rows.append([btn("🔙 رجوع", cbd="back_main", color='red')])
    return kb(*rows)

def roulette_options_kb():
    return kb(
        [btn("📢 إضافة قناة شرط أولى", cbd="add_cond_1", color='blue')],
        [btn("⏭️ تخطي", cbd="skip_cond", color='green')],
        [btn("✏️ تعديل النص", cbd="edit_r_text", color='blue')],
        [btn("❌ إلغاء", cbd="back_main", color='red')]
    )

def after_cond1_kb():
    return kb(
        [btn("📢 إضافة قناة شرط ثانية", cbd="add_cond_2", color='blue')],
        [btn("⏭️ اكتفِ بقناة وحدة", cbd="skip_cond_2", color='green')],
        [btn("❌ إلغاء", cbd="back_main", color='red')]
    )

def max_part_kb():
    return kb(
        [btn("50", cbd="maxp_50", color='blue'), btn("100", cbd="maxp_100", color='blue')],
        [btn("500", cbd="maxp_500", color='blue'), btn("1000", cbd="maxp_1000", color='blue')],
        [btn("⏭️ بدون حد أقصى", cbd="maxp_none", color='green')],
        [btn("❌ إلغاء", cbd="back_main", color='red')]
    )

def end_time_kb():
    return kb(
        [btn("1 ساعة", cbd="et_1", color='blue'), btn("6 ساعات", cbd="et_6", color='blue')],
        [btn("12 ساعة", cbd="et_12", color='blue'), btn("24 ساعة", cbd="et_24", color='blue')],
        [btn("3 أيام", cbd="et_72", color='blue'), btn("7 أيام", cbd="et_168", color='blue')],
        [btn("✏️ مخصص", cbd="et_custom", color='blue')],
        [btn("⏭️ بدون وقت انتهاء", cbd="et_none", color='green')],
        [btn("❌ إلغاء", cbd="back_main", color='red')]
    )

def confirm_publish_roulette_kb():
    return kb(
        [btn("✅ نشر الروليت الآن", cbd="confirm_pub_r", color='green')],
        [btn("❌ إلغاء", cbd="back_main", color='red')]
    )

def join_type_kb():
    return kb(
        [btn("🔐 تحقق بكابتشا", cbd="jtype_captcha", color='blue')],
        [btn("⚡ انضمام مباشر", cbd="jtype_direct", color='green')],
        [btn("❌ إلغاء", cbd="back_main", color='red')]
    )

def confirm_publish_contest_kb():
    return kb(
        [btn("✅ نشر المسابقة الآن", cbd="confirm_pub_c", color='green')],
        [btn("❌ إلغاء", cbd="back_main", color='red')]
    )

def roulette_ch_kb(rid, is_active, creator_id):
    try:
        bot_username = bot.get_me().username
    except Exception:
        bot_username = ""

    join_url = f"https://t.me/{bot_username}?start=join_{rid}"
    r = get_roulette(rid)
    raw_jt = r['join_type'] if r else None
    join_type = raw_jt if raw_jt in ('direct', 'captcha') else 'captcha'

    if (r and r['channel_username'] and r['channel_message_id']):
        post_url = f"https://t.me/{r['channel_username']}/{r['channel_message_id']}"
        share_url = f"https://t.me/share/url?url={post_url}&text=🔥+شارك+معي!"
    else:
        share_url = f"https://t.me/{bot_username}"

    ref_url = f"https://t.me/{bot_username}?start=getref_{rid}"
    remind_url = f"https://t.me/{bot_username}?start=remind_{rid}"

    count = get_part_count(rid)
    tog = "⏸️ إيقاف" if is_active else "▶️ تشغيل"
    tog_c = 'red' if is_active else 'green'

    if join_type == 'direct':
        return kb(
            [btn("⚡ المشاركة في السحب", cbd=f"quickjoin_{rid}", color='green')],
            [btn("🚀 مشاركة الروليت", url=share_url, color='blue'), btn("🔗 زيادة فرصتك", url=ref_url, color='blue')],
            [btn("🔔 تفعيل إشعار الفوز", url=remind_url, color='blue')],
            [btn(tog, cbd=f"toggle_{rid}", color=tog_c), btn("🏁 ابدأ السحب", cbd=f"draw_{rid}", color='green')],
            [btn(f"📊 المشاركون ({count})", cbd=f"view_part_{rid}", color='blue'), btn("🔄 إعادة نشر", cbd=f"repost_{rid}", color='blue')]
        )
    else:
        return kb(
            [btn("🎁 المشاركة في السحب", url=join_url, color='green')],
            [btn("🚀 مشاركة الروليت", url=share_url, color='blue'), btn("🔗 زيادة فرصتك", url=ref_url, color='blue')],
            [btn("🔔 ذكرني إذا فزت", url=remind_url, color='blue')],
            [btn(tog, cbd=f"toggle_{rid}", color=tog_c), btn("🏁 ابدأ السحب", cbd=f"draw_{rid}", color='green')],
            [btn(f"📊 المشاركون ({count})", cbd=f"view_part_{rid}", color='blue'), btn("🔄 إعادة نشر", cbd=f"repost_{rid}", color='blue')]
        )

def roulette_done_kb(rid):
    return kb([btn("🔄 إعادة السحب", cbd=f"redraw_{rid}", color='blue')])

def notify_roulette_kb(rid, notify_on):
    r = get_roulette(rid)
    ch_url = None
    if r and r['channel_username'] and r['channel_message_id']:
        ch_url = f"https://t.me/{r['channel_username']}/{r['channel_message_id']}"
    notify_text = "🔔 إيقاف إشعارات المشاركين" if notify_on else "🔕 تفعيل إشعارات المشاركين"
    rows = []
    if ch_url:
        rows.append([btn("📢 اذهب للروليت", url=ch_url, color='blue')])
    rows.append([btn(notify_text, cbd=f"toggle_notify_{rid}", color='red' if notify_on else 'green')])
    return kb(*rows)

def part_kb(rid, user_id):
    return kb(
        [btn("❌ طرد", cbd=f"kick_{rid}_{user_id}", color='red'), btn("🚫 حظر دائم", cbd=f"pban_{rid}_{user_id}", color='red')]
    )

def my_roulettes_kb(roulettes):
    rows = []
    for r in roulettes:
        ch = (f"@{r['channel_username']}" if r['channel_username'] else "قناة")
        txt = r['text'][:25]
        rows.append([btn(f"🎯 {txt}... | {ch}", cbd=f"my_r_{r['roulette_id']}", color='blue')])
    rows.append([btn("🔙 رجوع", cbd="back_main", color='red')])
    return kb(*rows)

def my_roulette_detail_kb(rid, is_active, channel_username, channel_msg_id):
    tog = "⏸️ إيقاف" if is_active else "▶️ تشغيل"
    tog_c = 'red' if is_active else 'green'
    rows = [
        [btn(tog, cbd=f"toggle_{rid}", color=tog_c), btn("🏁 ابدأ السحب", cbd=f"draw_{rid}", color='green')],
        [btn("🔄 إعادة نشر", cbd=f"repost_{rid}", color='blue')],
    ]
    if channel_username and channel_msg_id:
        rows.append([btn("📢 اذهب للقناة", url=f"https://t.me/{channel_username}/{channel_msg_id}", color='blue')])
    rows.append([btn("🔙 روليتاتي", cbd="my_roulettes", color='red')])
    return kb(*rows)

def contest_ch_kb(cid):
    try:
        bot_username = bot.get_me().username
    except Exception:
        bot_username = ""
    join_url = f"https://t.me/{bot_username}?start=join_contest_{cid}"
    return kb(
        [btn("🏆 المشاركة", url=join_url, color='green')],
        [btn("🏁 إنهاء وإعلان النتائج", cbd=f"end_contest_confirm_{cid}", color='red')]
    )

def vote_kb_build(cid, pid, votes=0):
    try:
        bot_username = bot.get_me().username
    except Exception:
        bot_username = ""
    vote_url = f"https://t.me/{bot_username}?start=vote_{cid}_{pid}"
    e = random.choice(POSITIVE_EMOJIS)
    return kb([btn(f"{e} تصويت | {votes} 🗳️", url=vote_url, color='green')])

def contest_accept_kb(cid, uid):
    return kb(
        [btn("✅ قبول", cbd=f"cp_accept_{cid}_{uid}", color='green'), btn("❌ رفض", cbd=f"cp_reject_{cid}_{uid}", color='red')]
    )

def contest_creation_kb():
    return kb(
        [btn("✅ قبول تلقائي", cbd="c_auto_yes", color='green')],
        [btn("👤 قبول يدوي", cbd="c_auto_no", color='blue')],
        [btn("❌ إلغاء", cbd="back_main", color='red')]
    )

def forced_channels_kb(channels):
    rows = []
    for fc in channels:
        n = fc['channel_username'] or fc['channel_title']
        rows.append([btn(f"📢 @{n} ← اضغط للحذف", cbd=f"del_forced_{fc['channel_id']}", color='red')])
    rows.append([btn("➕ إضافة قناة إجبارية", cbd="add_forced_ch", color='green')])
    rows.append([btn("🔙 رجوع", cbd="adm_panel", color='red')])
    return kb(*rows)

def check_sub_kb(channels):
    rows = []
    for fc in channels:
        n = fc['channel_username'] or fc['channel_title']
        url = f"https://t.me/{n}" if n else "https://t.me/"
        rows.append([btn(f"📢 اشترك في @{n}", url=url, color='green')])
    rows.append([btn("✅ اشتركت، تابع", cbd="check_sub_done", color='green')])
    return kb(*rows)

def my_contests_kb(contests):
    rows = []
    for c in contests:
        ch = (f"@{c['channel_username']}" if c['channel_username'] else "قناة")
        rows.append([btn(f"🏆 {c['title'][:25]} | {ch}", cbd=f"my_c_{c['contest_id']}", color='blue')])
    rows.append([btn("🔙 رجوع", cbd="back_main", color='red')])
    return kb(*rows)

def my_contest_detail_kb(cid, is_active, channel_username, channel_msg_id):
    tog = "⏸️ إيقاف" if is_active else "▶️ تشغيل"
    tog_c = 'red' if is_active else 'green'
    rows = [
        [btn(tog, cbd=f"toggle_contest_{cid}", color=tog_c)],
        [btn("🏁 إنهاء وإعلان النتائج", cbd=f"end_contest_confirm_{cid}", color='red')],
        [btn("👥 استبعاد مشارك", cbd=f"exclude_cp_{cid}", color='red')],
    ]
    if channel_username and channel_msg_id:
        rows.append([btn("📢 اذهب للقناة", url=f"https://t.me/{channel_username}/{channel_msg_id}", color='blue')])
    rows.append([btn("🔙 مسابقاتي", cbd="my_contests", color='red')])
    return kb(*rows)

def contest_join_confirm_kb(cid):
    return kb(
        [btn("✅ نعم، أريد المشاركة", cbd=f"confirm_join_c_{cid}", color='green')],
        [btn("❌ لا، إلغاء", cbd="back_main", color='red')]
    )

def withdraw_contest_kb(cid):
    return kb(
        [btn("🚪 سحب مشاركتي", cbd=f"withdraw_contest_{cid}", color='red')],
        [btn("🔙 رجوع", cbd="back_main", color='red')]
    )

def end_contest_confirm_kb(cid):
    return kb(
        [btn("✅ نعم، أنهِ المسابقة", cbd=f"end_contest_{cid}", color='red')],
        [btn("❌ إلغاء", cbd=f"my_c_{cid}", color='green')]
    )

def check_user(func):
    @functools.wraps(func)
    def wrapper(update, *args, **kwargs):
        if hasattr(update, 'from_user') and update.from_user:
            u = update.from_user
        else:
            return func(update, *args, **kwargs)
        uid = u.id
        fn = (f"{u.first_name or ''} {u.last_name or ''}").strip()
        is_new = add_user(uid, u.username or '', fn)
        if is_new and uid != ADMIN_ID:
            threading.Thread(target=notify_admin_new_user, args=(uid, u.username or '', fn), daemon=True).start()
        if uid != ADMIN_ID and is_maintenance():
            if isinstance(update, CallbackQuery):
                bot.answer_callback_query(update.id, MAINTENANCE_MSG, show_alert=True)
            else:
                send_or_edit(update.chat.id, MAINTENANCE_MSG, user_id=uid)
            return
        if uid != ADMIN_ID and is_banned(uid):
            if isinstance(update, CallbackQuery):
                bot.answer_callback_query(update.id, "🚫 أنت محظور.", show_alert=True)
            else:
                send_or_edit(update.chat.id, "🚫 أنت محظور من استخدام البوت.", user_id=uid)
            return
        return func(update, *args, **kwargs)
    return wrapper

def check_forced(func):
    @functools.wraps(func)
    def wrapper(update, *args, **kwargs):
        if hasattr(update, 'from_user') and update.from_user:
            uid = update.from_user.id
            chat_id = (update.message.chat.id if isinstance(update, CallbackQuery) else update.chat.id)
        else:
            return func(update, *args, **kwargs)
        if uid == ADMIN_ID:
            return func(update, *args, **kwargs)
        not_joined = check_forced_subscription(uid)
        if not_joined:
            if isinstance(update, CallbackQuery):
                bot.answer_callback_query(update.id, "يجب الاشتراك في القنوات أولاً!", show_alert=True)
            send_or_edit(chat_id, "📢 يجب الاشتراك في هذه القنوات أولاً:", markup=check_sub_kb(not_joined), user_id=uid)
            return
        return func(update, *args, **kwargs)
    return wrapper

@bot.message_handler(commands=['start'])
@check_user
def start_cmd(msg):
    uid = msg.from_user.id
    args = msg.text.split()

    not_joined = check_forced_subscription(uid)
    if uid != ADMIN_ID and not_joined:
        send_or_edit(msg.chat.id, "📢 يجب الاشتراك في هذه القنوات أولاً:", markup=check_sub_kb(not_joined), user_id=uid)
        return

    if uid != ADMIN_ID and not is_ch_member(DEVELOPER_CHANNEL, uid):
        markup = kb(
            [btn("📢 اشترك في قناة البوت", url=f"https://t.me/{DEVELOPER_CHANNEL.replace('@','')}", color='green')],
            [btn("✅ اشتركت، تابع", cbd="check_dev_sub", color='green')]
        )
        send_or_edit(msg.chat.id, f"⚠️ يجب الاشتراك في {DEVELOPER_CHANNEL} أولاً!", markup=markup, user_id=uid)
        return

    if len(args) > 1:
        param = args[1]

        if param.startswith("getref_"):
            rid = param[7:]
            r = get_roulette(rid)
            if not r or r['is_finished']:
                send_or_edit(msg.chat.id, "⚠️ الروليت غير موجود أو انتهى.", markup=main_menu_kb(uid), user_id=uid)
                return
            if not get_participant(rid, uid):
                send_or_edit(msg.chat.id, "⚠️ يجب المشاركة في الروليت أولاً!", markup=main_menu_kb(uid), user_id=uid)
                return
            rl = ref_link(uid, rid)
            t = get_tickets(rid, uid)
            send_new(uid, f"🔗 رابط الإحالة الخاص بك:\n\n<code>{rl}</code>\n\n🎫 تذاكرك الحالية: <b>{t}</b>\n\n💡 كل شخص يشارك عبر رابطك يحصل على تذكرة إضافية!\nكلما زادت تذاكرك، زادت فرصتك 🏆")
            bot_name = get_bot_name()
            send_or_edit(msg.chat.id, f"👋 أهلاً بك في {bot_name}!\n\nاختر من القائمة:", markup=main_menu_kb(uid), user_id=uid)
            return

        if param.startswith("ref_"):
            parts = param.split("_", 2)
            if len(parts) == 3:
                try:
                    referrer_id = int(parts[1])
                    rid = parts[2]
                    set_user_state(uid, 'pending_join', {'referrer_id': referrer_id, 'roulette_id': rid})
                    _show_join_prompt(msg.chat.id, uid, rid)
                    return
                except Exception:
                    pass

        if param.startswith("vote_"):
            parts = param.split("_", 2)
            if len(parts) == 3:
                try:
                    cid = parts[1]
                    pid = int(parts[2])
                    _handle_vote_deeplink(msg, uid, cid, pid)
                    return
                except Exception:
                    pass

        if param.startswith("join_contest_"):
            cid = param.replace("join_contest_", "")
            _handle_join_contest_start(msg, uid, cid)
            return

        if param.startswith("join_"):
            rid = param[5:]
            _show_join_prompt(msg.chat.id, uid, rid)
            return

        if param.startswith("remind_"):
            rid = param[7:]
            r = get_roulette(rid)
            if not r or r['is_finished']:
                send_or_edit(msg.chat.id, "⚠️ الروليت غير موجود أو انتهى.", markup=main_menu_kb(uid), user_id=uid)
                return
            add_reminder(rid, uid)
            bot_name = get_bot_name()
            send_or_edit(msg.chat.id, "🔔 تم تفعيل إشعار الفوز!\n\nسيتم إشعارك فور انتهاء السحب 🎯", markup=main_menu_kb(uid), user_id=uid)
            return

    clear_user_state(uid)
    bot_name = get_bot_name()
    send_or_edit(msg.chat.id, f"👋 أهلاً بك في {bot_name}!\n\nاختر من القائمة:", markup=main_menu_kb(uid), user_id=uid)

@bot.callback_query_handler(func=lambda c: c.data == "check_dev_sub")
@check_user
def handle_check_dev_sub(call):
    uid = call.from_user.id
    if is_ch_member(DEVELOPER_CHANNEL, uid):
        bot.answer_callback_query(call.id, "✅ تم التحقق!")
        clear_user_state(uid)
        bot_name = get_bot_name()
        send_or_edit(call.message.chat.id, f"👋 أهلاً بك في {bot_name}!\n\nاختر من القائمة:", markup=main_menu_kb(uid), user_id=uid)
    else:
        bot.answer_callback_query(call.id, "❌ لم تشترك بعد!", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data == "check_sub_done")
@check_user
def handle_check_sub_done(call):
    uid = call.from_user.id
    not_joined = check_forced_subscription(uid)
    if not_joined:
        bot.answer_callback_query(call.id, "❌ لم تشترك في كل القنوات!", show_alert=True)
        send_or_edit(call.message.chat.id, "📢 يجب الاشتراك في هذه القنوات أولاً:", markup=check_sub_kb(not_joined), user_id=uid)
    else:
        bot.answer_callback_query(call.id, "✅ شكراً!")
        clear_user_state(uid)
        bot_name = get_bot_name()
        send_or_edit(call.message.chat.id, f"👋 أهلاً بك في {bot_name}!\n\nاختر من القائمة:", markup=main_menu_kb(uid), user_id=uid)

@bot.callback_query_handler(func=lambda c: c.data == "back_main")
@check_user
def handle_back_main(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id)
    clear_user_state(uid)
    bot_name = get_bot_name()
    send_or_edit(call.message.chat.id, f"👋 أهلاً بك في {bot_name}!\n\nاختر من القائمة:", markup=main_menu_kb(uid), user_id=uid)

@bot.callback_query_handler(func=lambda c: c.data.startswith("rcheck_sub_"))
@check_user
def handle_rcheck_sub(call):
    uid = call.from_user.id
    rid = call.data.replace("rcheck_sub_", "")
    bot.answer_callback_query(call.id)

    r = get_roulette(rid)
    if not r or r['is_finished']:
        bot.answer_callback_query(call.id, "⚠️ الروليت غير موجود أو انتهى.", show_alert=True)
        return

    required_channels = []

    if r['channel_id'] and not is_ch_member(r['channel_id'], uid):
        cu = r['channel_username'] or ''
        required_channels.append({'channel_id': r['channel_id'], 'channel_username': cu, 'channel_title': f"@{cu}" if cu else "قناة السحب"})

    cc1 = r['conditional_channel_id']
    cu1 = r['conditional_channel_username'] or ''
    if cc1 and not is_ch_member(cc1, uid):
        required_channels.append({'channel_id': cc1, 'channel_username': cu1, 'channel_title': f"@{cu1}" if cu1 else "قناة شرط 1"})

    cc2 = r['conditional_channel_id_2']
    cu2 = r['conditional_channel_username_2'] or ''
    if cc2 and not is_ch_member(cc2, uid):
        required_channels.append({'channel_id': cc2, 'channel_username': cu2, 'channel_title': f"@{cu2}" if cu2 else "قناة شرط 2"})

    if required_channels:
        bot.answer_callback_query(call.id, "❌ لم تشترك في كل القنوات المطلوبة!", show_alert=True)
        rows = []
        for ch in required_channels:
            n = ch['channel_username'] or ch['channel_title']
            url = f"https://t.me/{n}" if n else "https://t.me/"
            rows.append([btn(f"📢 اشترك في @{n}", url=url, color='green')])
        rows.append([btn("✅ اشتركت، تابع للمشاركة", cbd=f"rcheck_sub_{rid}", color='green')])
        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=kb(*rows))
        except Exception:
            send_new(call.message.chat.id, "📢 يجب الاشتراك في هذه القنوات أولاً للمشاركة:", markup=kb(*rows))
        return

    del_msg(call.message.chat.id, call.message.message_id)
    join_type = r['join_type'] if r['join_type'] else 'captcha'
    if join_type == 'direct':
        _direct_join(call.message.chat.id, uid, rid)
    else:
        _send_captcha(call.message.chat.id, uid, rid)

@bot.message_handler(commands=['admin'])
@check_user
def admin_cmd(msg):
    uid = msg.from_user.id
    if uid != ADMIN_ID:
        return
    s = get_stats()
    send_or_edit(msg.chat.id, f"🛠️ لوحة تحكم المطور\n\n👥 المستخدمون: <b>{s['total_users']}</b>\n🎯 الروليتات النشطة: <b>{s['active_roulettes']}</b>\n🏆 المسابقات: <b>{s['total_contests']}</b>", markup=admin_kb(), user_id=ADMIN_ID)

@bot.callback_query_handler(func=lambda c: c.data == "adm_panel")
def handle_adm_panel(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, NO_PERM, show_alert=True)
        return
    bot.answer_callback_query(call.id)
    send_or_edit(call.message.chat.id, "🛠️ لوحة تحكم المطور", markup=admin_kb(), user_id=ADMIN_ID)

@bot.callback_query_handler(func=lambda c: c.data == "adm_stats")
def handle_adm_stats(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, NO_PERM, show_alert=True)
        return
    bot.answer_callback_query(call.id)
    s = get_stats()
    tc_text = "لا يوجد"
    if s['top_creator']:
        tc = s['top_creator']
        tc_text = f"@{tc['username']}" if tc['username'] else f"ID:{tc['user_id']}"
        tc_text += f" ({tc['total_roulettes_created']})"
    send_or_edit(call.message.chat.id, f"📊 إحصائيات البوت\n\n👥 المستخدمون: <b>{s['total_users']}</b>\n🆕 اليوم: <b>{s['today_users']}</b>\n🚫 محظورون: <b>{s['banned']}</b>\n\n🎯 الروليتات: <b>{s['total_roulettes']}</b>\n✅ نشطة: <b>{s['active_roulettes']}</b>\n👤 المشاركات: <b>{s['total_parts']}</b>\n\n🏆 المسابقات: <b>{s['total_contests']}</b>\n📢 قنوات إجبارية: <b>{s['forced_channels']}</b>\n\n⭐ أكثر منشئ: <b>{tc_text}</b>", markup=admin_back_kb(), user_id=ADMIN_ID)

@bot.callback_query_handler(func=lambda c: c.data == "adm_maintenance")
def handle_adm_maintenance(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, NO_PERM, show_alert=True)
        return
    cur = is_maintenance()
    set_maintenance(not cur)
    status = "🔧 تم تفعيل الصيانة" if not cur else "✅ تم إلغاء الصيانة"
    bot.answer_callback_query(call.id, status, show_alert=True)
    send_or_edit(call.message.chat.id, f"🛠️ لوحة تحكم المطور\n\n{status}", markup=admin_kb(), user_id=ADMIN_ID)

@bot.callback_query_handler(func=lambda c: c.data == "adm_ban")
def handle_adm_ban(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, NO_PERM, show_alert=True)
        return
    bot.answer_callback_query(call.id)
    set_user_state(ADMIN_ID, 'adm_ban')
    send_or_edit(call.message.chat.id, "🚫 أرسل آيدي المستخدم للحظر:", markup=admin_back_kb(), user_id=ADMIN_ID)

@bot.callback_query_handler(func=lambda c: c.data == "adm_unban")
def handle_adm_unban(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, NO_PERM, show_alert=True)
        return
    bot.answer_callback_query(call.id)
    set_user_state(ADMIN_ID, 'adm_unban')
    send_or_edit(call.message.chat.id, "✅ أرسل آيدي المستخدم لفك الحظر:", markup=admin_back_kb(), user_id=ADMIN_ID)

@bot.callback_query_handler(func=lambda c: c.data == "adm_broadcast")
def handle_adm_broadcast(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, NO_PERM, show_alert=True)
        return
    bot.answer_callback_query(call.id)
    set_user_state(ADMIN_ID, 'adm_broadcast')
    send_or_edit(call.message.chat.id, "📢 أرسل نص الإذاعة:", markup=admin_back_kb(), user_id=ADMIN_ID)

@bot.callback_query_handler(func=lambda c: c.data == "adm_roulettes")
def handle_adm_roulettes(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, NO_PERM, show_alert=True)
        return
    bot.answer_callback_query(call.id)
    roulettes = get_active_roulettes()
    if not roulettes:
        text = "📋 لا توجد روليتات نشطة."
    else:
        lines = ["📋 الروليتات النشطة:\n"]
        for r in roulettes:
            count = get_part_count(r['roulette_id'])
            ch = f"@{r['channel_username']}" if r['channel_username'] else "قناة"
            creator = get_dname(r['creator_id'])
            lines.append(f"🎯 {ch} | {count} مشارك | {creator}\n   <code>{r['roulette_id'][:8]}...</code>")
        text = "\n".join(lines)
    send_or_edit(call.message.chat.id, text, markup=admin_back_kb(), user_id=ADMIN_ID)

@bot.callback_query_handler(func=lambda c: c.data == "adm_photo")
def handle_adm_photo(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, NO_PERM, show_alert=True)
        return
    bot.answer_callback_query(call.id)
    set_user_state(ADMIN_ID, 'adm_photo')
    cur = get_setting('bot_photo')
    txt = "🖼️ تعيين صورة البوت\n\nأرسل صورة لتعيينها\nأو أرسل <code>حذف</code> لإزالة الصورة."
    if cur:
        txt += "\n\n✅ يوجد صورة حالية."
    send_or_edit(call.message.chat.id, txt, markup=admin_back_kb(), user_id=ADMIN_ID)

@bot.callback_query_handler(func=lambda c: c.data == "adm_forced")
def handle_adm_forced(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, NO_PERM, show_alert=True)
        return
    bot.answer_callback_query(call.id)
    fcs = get_forced_channels()
    send_or_edit(call.message.chat.id, f"📢 قنوات الاشتراك الإجباري\n\nعدد القنوات: {len(fcs)}\n\nاضغط على قناة لحذفها:", markup=forced_channels_kb(fcs), user_id=ADMIN_ID)

@bot.callback_query_handler(func=lambda c: c.data == "add_forced_ch")
def handle_add_forced_ch(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, NO_PERM, show_alert=True)
        return
    bot.answer_callback_query(call.id)
    set_user_state(ADMIN_ID, 'adm_add_forced')
    send_or_edit(call.message.chat.id, "📢 أرسل رابط القناة أو @username:", markup=admin_back_kb(), user_id=ADMIN_ID)

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_forced_"))
def handle_del_forced(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, NO_PERM, show_alert=True)
        return
    ch_id = int(call.data.replace("del_forced_", ""))
    remove_forced_channel(ch_id)
    bot.answer_callback_query(call.id, "✅ تم حذف القناة.", show_alert=True)
    fcs = get_forced_channels()
    send_or_edit(call.message.chat.id, f"📢 قنوات الاشتراك الإجباري\n\nعدد القنوات: {len(fcs)}", markup=forced_channels_kb(fcs), user_id=ADMIN_ID)

@bot.callback_query_handler(func=lambda c: c.data == "my_channels")
@check_user
@check_forced
def handle_my_channels(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id)
    chs = get_user_channels(uid)
    text = f"📋 قنواتي\n\nعدد القنوات: {len(chs)}" if chs else "📋 قنواتي\n\nلا توجد قنوات مربوطة."
    send_or_edit(call.message.chat.id, text, markup=my_channels_kb(chs), user_id=uid)

@bot.callback_query_handler(func=lambda c: c.data.startswith("ch_info_"))
@check_user
def handle_ch_info(call):
    uid = call.from_user.id
    ch_id = int(call.data.replace("ch_info_", ""))
    bot.answer_callback_query(call.id)
    ch = get_channel(ch_id)
    if not ch or ch['owner_id'] != uid:
        bot.answer_callback_query(call.id, NO_PERM, show_alert=True)
        return
    n = ch['channel_username'] or ch['channel_title']
    send_or_edit(call.message.chat.id, f"📢 معلومات القناة\n\nالاسم: @{n}\nالآيدي: <code>{ch['channel_id']}</code>\nتاريخ الإضافة: {fmt_dt(ch['added_at'])}", markup=channel_info_kb(ch_id), user_id=uid)

@bot.callback_query_handler(func=lambda c: c.data.startswith("ch_del_confirm_"))
@check_user
def handle_ch_del_confirm(call):
    uid = call.from_user.id
    ch_id = int(call.data.replace("ch_del_confirm_", ""))
    bot.answer_callback_query(call.id)
    ch = get_channel(ch_id)
    if not ch:
        return
    n = ch['channel_username'] or ch['channel_title']
    send_or_edit(call.message.chat.id, f"⚠️ تأكيد حذف القناة @{n}\n\nسيتم إيقاف الروليتات النشطة فيها.", markup=confirm_del_kb(ch_id), user_id=uid)

@bot.callback_query_handler(func=lambda c: c.data.startswith("ch_del_") and not c.data.startswith("ch_del_confirm_"))
@check_user
def handle_ch_del(call):
    uid = call.from_user.id
    ch_id = int(call.data.replace("ch_del_", ""))
    bot.answer_callback_query(call.id)
    ch = get_channel(ch_id)
    if not ch or ch['owner_id'] != uid:
        return
    for r in get_active_roulettes():
        if r['channel_id'] == ch_id:
            update_roulette_active(r['roulette_id'], False)
            try:
                send_new(r['creator_id'], "⚠️ تم إيقاف روليت بسبب حذف القناة.")
            except Exception:
                pass
    remove_channel(uid, ch_id)
    chs = get_user_channels(uid)
    send_or_edit(call.message.chat.id, "✅ تم حذف القناة.\n\n📋 قنواتي:", markup=my_channels_kb(chs), user_id=uid)

@bot.callback_query_handler(func=lambda c: c.data == "bind_channel")
@check_user
def handle_bind_channel(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id)
    set_user_state(uid, 'await_ch_link')
    send_or_edit(call.message.chat.id, "📌 ربط قناة جديدة\n\n1️⃣ اضغط أضفني لقناتك\n2️⃣ اختر قناتك وأعطِ البوت صلاحية النشر\n3️⃣ اضغط أضفت البوت\n4️⃣ أرسل @username أو رابط القناة", markup=bind_kb(), user_id=uid)

@bot.callback_query_handler(func=lambda c: c.data == "bot_added")
@check_user
def handle_bot_added(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id)
    set_user_state(uid, 'await_ch_link')
    send_or_edit(call.message.chat.id, "✅ أرسل رابط قناتك أو @username:", markup=cancel_kb(), user_id=uid)

def _process_ch_link(msg, uid):
    text = msg.text.strip() if msg.text else ""
    del_msg(msg.chat.id, msg.message_id)
    m = re.match(r'^(?:https?://t\.me/)?@?([a-zA-Z0-9_]+)$', text)
    if not m:
        send_or_edit(msg.chat.id, "⚠️ رابط غير صالح. أرسل مثل: @YourChannel", markup=cancel_kb(), user_id=uid)
        return
    identifier = "@" + m.group(1)
    try:
        chat = bot.get_chat(identifier)
        if chat.type != 'channel':
            send_or_edit(msg.chat.id, "⚠️ هذا ليس رابط قناة.", markup=cancel_kb(), user_id=uid)
            return
        bot_member = bot.get_chat_member(chat.id, bot.get_me().id)
        if bot_member.status not in ['administrator', 'creator']:
            send_or_edit(msg.chat.id, "⚠️ البوت ليس مشرفاً في القناة.\nأضف البوت كمشرف أولاً.", markup=bind_kb(), user_id=uid)
            return
        if not is_ch_admin(chat.id, uid):
            send_or_edit(msg.chat.id, "⚠️ أنت لست مشرفاً في هذه القناة.", markup=cancel_kb(), user_id=uid)
            return
        add_channel(uid, chat.id, chat.username or '', chat.title or '')
        clear_user_state(uid)
        chs = get_user_channels(uid)
        send_or_edit(msg.chat.id, f"✅ تم ربط القناة @{chat.username or chat.title}", markup=my_channels_kb(chs), user_id=uid)
    except Exception as e:
        send_or_edit(msg.chat.id, f"⚠️ خطأ: {str(e)}", markup=cancel_kb(), user_id=uid)

def _show_join_prompt(chat_id, uid, rid):
    r = get_roulette(rid)
    if not r:
        send_new(chat_id, "⚠️ الروليت غير موجود.")
        return
    if r['is_finished']:
        send_new(chat_id, "⚠️ هذا الروليت قد انتهى.")
        return
    if r['creator_id'] == uid:
        send_new(chat_id, "⚠️ لا يمكنك المشاركة في روليتك الخاص.")
        return
    if get_participant(rid, uid):
        send_new(chat_id, "✅ أنت مشارك بالفعل!")
        return
    if is_banned_from_creator(r['creator_id'], uid):
        send_new(chat_id, "🚫 أنت محظور من سحوبات هذا المنشئ.")
        return

    required_channels = []

    if r['channel_id'] and not is_ch_member(r['channel_id'], uid):
        cu = r['channel_username'] or ''
        required_channels.append({'channel_id': r['channel_id'], 'channel_username': cu, 'channel_title': f"@{cu}" if cu else "قناة السحب"})

    cc1 = r['conditional_channel_id']
    cu1 = r['conditional_channel_username'] or ''
    if cc1 and not is_ch_member(cc1, uid):
        required_channels.append({'channel_id': cc1, 'channel_username': cu1, 'channel_title': f"@{cu1}" if cu1 else "قناة شرط 1"})

    cc2 = r['conditional_channel_id_2']
    cu2 = r['conditional_channel_username_2'] or ''
    if cc2 and not is_ch_member(cc2, uid):
        required_channels.append({'channel_id': cc2, 'channel_username': cu2, 'channel_title': f"@{cu2}" if cu2 else "قناة شرط 2"})

    if required_channels:
        _, temp = get_user_state(uid)
        temp['pending_roulette_id'] = rid
        set_user_state(uid, 'pending_roulette_sub', temp)

        rows = []
        for ch in required_channels:
            n = ch['channel_username'] or ch['channel_title']
            url = f"https://t.me/{n}" if n else "https://t.me/"
            rows.append([btn(f"📢 اشترك في @{n}", url=url, color='green')])
        rows.append([btn("✅ اشتركت، تابع للمشاركة", cbd=f"rcheck_sub_{rid}", color='green')])
        send_new(chat_id, "📢 يجب الاشتراك في هذه القنوات أولاً للمشاركة في السحب:", markup=kb(*rows))
        return

    join_type = r['join_type'] if r['join_type'] else 'captcha'
    if join_type == 'direct':
        _direct_join(chat_id, uid, rid)
    else:
        _send_captcha(chat_id, uid, rid)

def _direct_join(chat_id, uid, rid, referrer_id=None):
    added = add_participant(rid, uid, referrer_id)
    if not added:
        send_new(chat_id, "✅ أنت مشارك بالفعل!")
        return

    if referrer_id and referrer_id != uid:
        was_new = add_referral(rid, referrer_id, uid)
        if was_new:
            add_ticket(rid, referrer_id)
            t = get_tickets(rid, referrer_id)
            try:
                send_new(referrer_id, f"🎫 حصلت على تذكرة إضافية!\nإجمالي تذاكرك: <b>{t}</b> 🎫")
            except Exception:
                pass

    update_roulette_msg(rid)
    r = get_roulette(rid)
    count = get_part_count(rid)

    if get_notify_setting(r['creator_id']):
        try:
            u_info = bot.get_chat(uid)
            uname = f"@{u_info.username}" if u_info.username else "لا يوجد"
            uname_display = u_info.first_name or f"مستخدم {uid}"
            if u_info.last_name:
                uname_display += f" {u_info.last_name}"
        except Exception:
            uname = "لا يوجد"
            uname_display = f"مستخدم {uid}"
        try:
            send_new(r['creator_id'], f"👤 مشارك جديد في روليتك!\n\nالاسم: {uname_display}\nاليوزر: {uname}\nالآيدي: <code>{uid}</code>\nإجمالي المشاركين: <b>{count}</b>", markup=part_kb(rid, uid))
        except Exception:
            pass

    send_new(chat_id, "🎉 تم تسجيل مشاركتك بنجاح!\n\nحظاً موفقاً في السحب! 🍀\n\nيمكنك زيادة فرصتك عبر دعوة أصدقائك! 🔗")
    clear_user_state(uid)

    if r and r['max_participants']:
        if count >= r['max_participants']:
            _execute_draw(rid, auto=True)

def update_roulette_msg(rid, winners=None):
    r = get_roulette(rid)
    if not r:
        return
    count = get_part_count(rid)
    text = _build_roulette_text(r, count)

    if not r['is_active'] and not winners:
        text += "\n\n⛔ المشاركة متوقفة مؤقتاً."

    if winners:
        wl = [f"🏆 {get_mention(w)}" for w in winners]
        text += "\n\n🎊 الفائزون:\n" + "\n".join(wl)
        markup = roulette_done_kb(rid)
    else:
        markup = roulette_ch_kb(rid, bool(r['is_active']), r['creator_id'])

    photo = r['photo_id']
    try:
        if photo:
            bot.edit_message_media(media=telebot.types.InputMediaPhoto(photo, caption=text, parse_mode="HTML"), chat_id=r['channel_id'], message_id=r['channel_message_id'], reply_markup=markup)
        else:
            bot.edit_message_text(text, r['channel_id'], r['channel_message_id'], parse_mode="HTML", reply_markup=markup, disable_web_page_preview=True)
    except telebot.apihelper.ApiTelegramException as e:
        if "message is not modified" not in str(e).lower():
            print(f"update_roulette_msg error: {e}")
    except Exception as e:
        print(f"update_roulette_msg error: {e}")

def _execute_draw(rid, auto=False):
    r = get_roulette(rid)
    if not r or r['is_finished']:
        return
    winners = perform_draw(rid)
    if not winners:
        return
    update_roulette_msg(rid, winners)
    ch_link = get_channel_link(rid)
    rems = get_reminders(rid)
    reminded_users = {rem['user_id'] for rem in rems}

    for w in winners:
        try:
            send_new(w, f"🎊 مبروك! لقد فزت!\n\n📝 {r['text'][:100]}\n📢 {ch_link or 'القناة'}\n\nتواصل مع المنشئ! 🎁")
        except Exception:
            pass

    for rem_uid in reminded_users:
        if rem_uid not in winners:
            try:
                send_new(rem_uid, f"🔔 انتهى الروليت!\n\nللأسف لم تفز هذه المرة.\nحظاً أوفر في المرة القادمة! 🍀")
            except Exception:
                pass

    try:
        send_new(r['creator_id'], f"{'⚡ اكتمل العدد وتم السحب التلقائي!' if auto else '✅ تم السحب!'}\n\n🏆 عدد الفائزين: {len(winners)}\n\n" + "\n".join([f"🎯 {get_mention(w)}" for w in winners]))
    except Exception:
        pass

def _publish_roulette(msg, uid, temp):
    required = ['channel_id', 'roulette_text', 'winners_count']
    for k in required:
        if k not in temp:
            send_new(msg.chat.id, "⚠️ بيانات ناقصة. ابدأ من جديد.")
            clear_user_state(uid)
            return

    rid = str(uuid.uuid4())
    r_data = {
        'text': temp['roulette_text'],
        'conditional_channel_username': temp.get('cond_ch_username_1', ''),
        'conditional_channel_username_2': temp.get('cond_ch_username_2', ''),
        'winners_count': temp['winners_count'],
        'max_participants': temp.get('max_participants'),
        'end_time': temp.get('end_time'),
        'photo_id': temp.get('photo_id', '')
    }
    text = _build_roulette_text(r_data, 0)
    markup = roulette_ch_kb(rid, True, uid)

    try:
        if temp.get('photo_id'):
            sent = bot.send_photo(temp['channel_id'], temp['photo_id'], caption=text, parse_mode="HTML", reply_markup=markup)
        else:
            sent = bot.send_message(temp['channel_id'], text, parse_mode="HTML", reply_markup=markup, disable_web_page_preview=True)

        create_roulette(rid, uid, temp['channel_id'], temp.get('channel_username', ''), sent.message_id, temp['roulette_text'], temp.get('photo_id', ''), temp['winners_count'], temp.get('max_participants'), temp.get('end_time'), temp.get('cond_ch_id_1'), temp.get('cond_ch_username_1', ''), temp.get('cond_ch_id_2'), temp.get('cond_ch_username_2', ''), temp.get('join_type', 'captcha'))
        clear_user_state(uid)

        notify_on = get_notify_setting(uid)
        ch_link = None
        if temp.get('channel_username') and sent.message_id:
            ch_link = f"https://t.me/{temp['channel_username']}/{sent.message_id}"

        notify_text = "🔔 إيقاف إشعارات المشاركين" if notify_on else "🔕 تفعيل إشعارات المشاركين"
        rows = []
        if ch_link:
            rows.append([btn("📢 اذهب للروليت", url=ch_link, color='blue')])
        rows.append([btn(notify_text, cbd=f"toggle_notify_{rid}", color='red' if notify_on else 'green')])

        send_new(uid, f"🎉 تم نشر الروليت بنجاح!\n\n📢 القناة: @{temp.get('channel_username','')}\n👥 المشاركون: <b>0</b>\n🏆 الفائزون: <b>{temp['winners_count']}</b>\n⏰ ينتهي: <b>{fmt_dt(temp['end_time']) if temp.get('end_time') else 'غير محدد'}</b>", markup=kb(*rows))

        bot_name = get_bot_name()
        send_or_edit(msg.chat.id, f"👋 أهلاً بك في {bot_name}!\n\nاختر من القائمة:", markup=main_menu_kb(uid), user_id=uid)

    except Exception as e:
        send_new(msg.chat.id, f"⚠️ فشل النشر: {str(e)}")
        clear_user_state(uid)

def _process_cond_ch(msg, uid, slot):
    text = msg.text.strip() if msg.text else ""
    del_msg(msg.chat.id, msg.message_id)
    m = re.match(r'^(?:https?://t\.me/)?@?([a-zA-Z0-9_]+)$', text)
    if not m:
        send_or_edit(msg.chat.id, "⚠️ رابط غير صالح.", markup=cancel_kb(), user_id=uid)
        return
    identifier = "@" + m.group(1)
    try:
        chat = bot.get_chat(identifier)
        if chat.type != 'channel':
            send_or_edit(msg.chat.id, "⚠️ هذا ليس رابط قناة.", markup=cancel_kb(), user_id=uid)
            return
        _, temp = get_user_state(uid)
        temp[f'cond_ch_id_{slot}'] = chat.id
        temp[f'cond_ch_username_{slot}'] = chat.username or chat.title or ''
        if slot == 1:
            set_user_state(uid, 'await_cond_choice', temp)
            send_or_edit(msg.chat.id, f"✅ تم حفظ القناة الشرطية: @{chat.username or chat.title}\n\nهل تريد إضافة قناة ثانية؟", markup=after_cond1_kb(), user_id=uid)
        else:
            set_user_state(uid, 'await_winner_count', temp)
            send_or_edit(msg.chat.id, "✅ تم حفظ القناة الثانية.\n\n🏆 كم عدد الفائزين؟", markup=cancel_kb(), user_id=uid)
    except Exception as e:
        send_or_edit(msg.chat.id, f"⚠️ خطأ: {str(e)}", markup=cancel_kb(), user_id=uid)

@bot.callback_query_handler(func=lambda c: c.data == "create_roulette")
@check_user
@check_forced
def handle_create_roulette(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id)
    chs = get_user_channels(uid)
    if not chs:
        send_or_edit(call.message.chat.id, "⚠️ يجب ربط قناة أولاً!", markup=my_channels_kb([]), user_id=uid)
        return
    if len(chs) == 1:
        set_user_state(uid, 'await_r_text', {'channel_id': chs[0]['channel_id'], 'channel_username': chs[0]['channel_username'] or '', 'channel_title': chs[0]['channel_title'] or ''})
        send_or_edit(call.message.chat.id, ROULETTE_PROMPT, markup=cancel_kb(), user_id=uid)
        return
    send_or_edit(call.message.chat.id, "📢 اختر القناة:", markup=choose_channel_kb(chs, "roulette"), user_id=uid)

@bot.callback_query_handler(func=lambda c: c.data.startswith("sel_ch_roulette_"))
@check_user
def handle_sel_ch_roulette(call):
    uid = call.from_user.id
    ch_id = int(call.data.replace("sel_ch_roulette_", ""))
    bot.answer_callback_query(call.id)
    if not can_use_channel(ch_id, uid):
        bot.answer_callback_query(call.id, NO_PERM, show_alert=True)
        return
    ch = get_channel(ch_id)
    set_user_state(uid, 'await_r_text', {'channel_id': ch_id, 'channel_username': ch['channel_username'] or '', 'channel_title': ch['channel_title'] or ''})
    send_or_edit(call.message.chat.id, ROULETTE_PROMPT, markup=cancel_kb(), user_id=uid)

@bot.callback_query_handler(func=lambda c: c.data in ["add_cond_1", "add_cond_2"])
@check_user
def handle_add_cond(call):
    uid = call.from_user.id
    slot = 1 if call.data == "add_cond_1" else 2
    bot.answer_callback_query(call.id)
    _, temp = get_user_state(uid)
    set_user_state(uid, f'await_cond_{slot}', temp)
    send_or_edit(call.message.chat.id, f"📢 أرسل رابط القناة الشرطية {'الأولى' if slot == 1 else 'الثانية'}:", markup=cancel_kb(), user_id=uid)

@bot.callback_query_handler(func=lambda c: c.data in ["skip_cond", "skip_cond_2"])
@check_user
def handle_skip_cond(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id)
    _, temp = get_user_state(uid)
    if call.data == "skip_cond":
        temp['cond_ch_id_1'] = None
        temp['cond_ch_username_1'] = ''
        temp['cond_ch_id_2'] = None
        temp['cond_ch_username_2'] = ''
    else:
        temp['cond_ch_id_2'] = None
        temp['cond_ch_username_2'] = ''
    set_user_state(uid, 'await_winner_count', temp)
    send_or_edit(call.message.chat.id, "🏆 كم عدد الفائزين؟", markup=cancel_kb(), user_id=uid)

@bot.callback_query_handler(func=lambda c: c.data == "edit_r_text")
@check_user
def handle_edit_r_text(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id)
    _, temp = get_user_state(uid)
    set_user_state(uid, 'await_r_text', temp)
    send_or_edit(call.message.chat.id, ROULETTE_PROMPT, markup=cancel_kb(), user_id=uid)

@bot.callback_query_handler(func=lambda c: c.data.startswith("maxp_"))
@check_user
def handle_maxp(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id)
    _, temp = get_user_state(uid)
    val = call.data.replace("maxp_", "")
    temp['max_participants'] = None if val == "none" else int(val)
    set_user_state(uid, 'await_end_time', temp)
    send_or_edit(call.message.chat.id, "⏰ متى ينتهي الروليت؟", markup=end_time_kb(), user_id=uid)

@bot.callback_query_handler(func=lambda c: c.data.startswith("et_"))
@check_user
def handle_et(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id)
    _, temp = get_user_state(uid)
    val = call.data.replace("et_", "")
    if val == "none":
        temp['end_time'] = None
        set_user_state(uid, 'await_join_type', temp)
        send_or_edit(call.message.chat.id, "🚪 اختر نظام الانضمام للروليت:\n\n🔐 كابتشا: يحل المستخدم تحققاً بسيطاً قبل التسجيل\n⚡ مباشر: يتسجل المستخدم فوراً بعد التحقق من الاشتراك", markup=join_type_kb(), user_id=uid)
    elif val == "custom":
        set_user_state(uid, 'await_et_custom', temp)
        send_or_edit(call.message.chat.id, "⏰ أرسل عدد الساعات (مثال: 48):", markup=cancel_kb(), user_id=uid)
    else:
        temp['end_time'] = (datetime.now() + timedelta(hours=int(val))).isoformat()
        set_user_state(uid, 'await_join_type', temp)
        send_or_edit(call.message.chat.id, "🚪 اختر نظام الانضمام للروليت:\n\n🔐 كابتشا: يحل المستخدم تحققاً بسيطاً قبل التسجيل\n⚡ مباشر: يتسجل المستخدم فوراً بعد التحقق من الاشتراك", markup=join_type_kb(), user_id=uid)

@bot.callback_query_handler(func=lambda c: c.data in ["jtype_captcha", "jtype_direct"])
@check_user
def handle_join_type(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id)
    _, temp = get_user_state(uid)
    temp['join_type'] = 'direct' if call.data == "jtype_direct" else 'captcha'
    set_user_state(uid, 'await_photo', temp)
    photo_kb = kb([btn("⏭️ تخطي بدون صورة", cbd="skip_photo", color='green')], [btn("❌ إلغاء", cbd="back_main", color='red')])
    label = "⚡ انضمام مباشر" if temp['join_type'] == 'direct' else "🔐 تحقق بكابتشا"
    send_or_edit(call.message.chat.id, f"✅ تم اختيار: <b>{label}</b>\n\n🖼️ هل تريد إضافة صورة للروليت؟\nأرسل الصورة أو اضغط تخطي:", markup=photo_kb, user_id=uid)

@bot.callback_query_handler(func=lambda c: c.data == "skip_photo")
@check_user
def handle_skip_photo(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id)
    _, temp = get_user_state(uid)
    temp['photo_id'] = ''
    set_user_state(uid, 'await_confirm_pub_r', temp)
    r_data = {
        'text': temp.get('roulette_text', ''),
        'conditional_channel_username': temp.get('cond_ch_username_1', ''),
        'conditional_channel_username_2': temp.get('cond_ch_username_2', ''),
        'winners_count': temp.get('winners_count', 1),
        'max_participants': temp.get('max_participants'),
        'end_time': temp.get('end_time'),
        'photo_id': '',
        'join_type': temp.get('join_type', 'captcha')
    }
    preview = _build_roulette_preview(r_data, uid)
    send_or_edit(call.message.chat.id, preview, markup=confirm_publish_roulette_kb(), user_id=uid)

@bot.callback_query_handler(func=lambda c: c.data == "confirm_pub_r")
@check_user
def handle_confirm_pub_r(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id)
    _, temp = get_user_state(uid)
    _publish_roulette(call.message, uid, temp)

@bot.callback_query_handler(func=lambda c: c.data.startswith("toggle_notify_"))
@check_user
def handle_toggle_notify(call):
    uid = call.from_user.id
    rid = call.data.replace("toggle_notify_", "")
    r = get_roulette(rid)
    if not r or r['creator_id'] != uid:
        bot.answer_callback_query(call.id, NO_PERM, show_alert=True)
        return
    new_val = toggle_notify(uid)
    bot.answer_callback_query(call.id, "🔔 تم تفعيل الإشعارات." if new_val else "🔕 تم إيقاف الإشعارات.", show_alert=True)
    notify_text = "🔔 إيقاف إشعارات المشاركين" if new_val else "🔕 تفعيل إشعارات المشاركين"
    ch_link = None
    if r['channel_username'] and r['channel_message_id']:
        ch_link = f"https://t.me/{r['channel_username']}/{r['channel_message_id']}"
    rows = []
    if ch_link:
        rows.append([btn("📢 اذهب للروليت", url=ch_link, color='blue')])
    rows.append([btn(notify_text, cbd=f"toggle_notify_{rid}", color='red' if new_val else 'green')])
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=kb(*rows))
    except Exception:
        pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("cap_"))
@check_user
def handle_captcha_cb(call):
    uid = call.from_user.id
    parts = call.data.split("_", 2)
    if len(parts) < 3:
        return
    try:
        idx = int(parts[1])
    except ValueError:
        return
    rid = parts[2]

    cap = get_captcha(uid, rid)
    if not cap:
        bot.answer_callback_query(call.id, "⏰ انتهت صلاحية الكابتشا.\nاضغط مشاركة مجدداً.", show_alert=True)
        del_msg(call.message.chat.id, call.message.message_id)
        return

    chosen = cap['options'][idx]
    if chosen != cap['correct']:
        clear_captcha(uid, rid)
        bot.answer_callback_query(call.id, "❌ إجابة خاطئة!\nاضغط المشاركة مجدداً.", show_alert=True)
        del_msg(call.message.chat.id, call.message.message_id)
        return

    clear_captcha(uid, rid)
    bot.answer_callback_query(call.id, "✅ إجابة صحيحة!")
    del_msg(call.message.chat.id, call.message.message_id)

    state, temp = get_user_state(uid)
    referrer_id = temp.get('referrer_id')
    ref_rid = temp.get('roulette_id')
    if ref_rid != rid:
        referrer_id = None

    added = add_participant(rid, uid, referrer_id)
    if not added:
        send_new(uid, "✅ أنت مشارك بالفعل!")
        return

    if referrer_id and referrer_id != uid:
        was_new = add_referral(rid, referrer_id, uid)
        if was_new:
            add_ticket(rid, referrer_id)
            t = get_tickets(rid, referrer_id)
            try:
                send_new(referrer_id, f"🎫 حصلت على تذكرة إضافية!\nإجمالي تذاكرك: <b>{t}</b> 🎫")
            except Exception:
                pass

    update_roulette_msg(rid)
    r = get_roulette(rid)
    count = get_part_count(rid)

    if get_notify_setting(r['creator_id']):
        try:
            u_info = bot.get_chat(uid)
            uname = f"@{u_info.username}" if u_info.username else "لا يوجد"
            uname_display = u_info.first_name or f"مستخدم {uid}"
            if u_info.last_name:
                uname_display += f" {u_info.last_name}"
        except Exception:
            uname = "لا يوجد"
            uname_display = f"مستخدم {uid}"
        try:
            send_new(r['creator_id'], f"👤 مشارك جديد في روليتك!\n\nالاسم: {uname_display}\nاليوزر: {uname}\nالآيدي: <code>{uid}</code>\nإجمالي المشاركين: <b>{count}</b>", markup=part_kb(rid, uid))
        except Exception:
            pass

    send_new(uid, "🎉 تم تسجيل مشاركتك بنجاح!\n\nحظاً موفقاً في السحب! 🍀\n\nيمكنك زيادة فرصتك عبر دعوة أصدقائك! 🔗")
    clear_user_state(uid)

    if r and r['max_participants']:
        if count >= r['max_participants']:
            _execute_draw(rid, auto=True)

@bot.callback_query_handler(func=lambda c: c.data.startswith("toggle_") and not c.data.startswith("toggle_contest_") and not c.data.startswith("toggle_notify_"))
@check_user
def handle_toggle(call):
    uid = call.from_user.id
    rid = call.data[7:]
    r = get_roulette(rid)
    if not r:
        bot.answer_callback_query(call.id, "⚠️ الروليت غير موجود.", show_alert=True)
        return
    if uid != r['creator_id'] and uid != ADMIN_ID:
        bot.answer_callback_query(call.id, "🚫 فقط صاحب الروليت يمكنه التحكم!", show_alert=True)
        return
    new_val = not bool(r['is_active'])
    update_roulette_active(rid, new_val)
    bot.answer_callback_query(call.id, "✅ تم تشغيل المشاركة." if new_val else "⛔ تم إيقاف المشاركة.", show_alert=True)
    update_roulette_msg(rid)

@bot.callback_query_handler(func=lambda c: c.data.startswith("draw_"))
@check_user
def handle_draw(call):
    uid = call.from_user.id
    rid = call.data[5:]
    r = get_roulette(rid)
    if not r:
        bot.answer_callback_query(call.id, "⚠️ الروليت غير موجود.", show_alert=True)
        return
    if uid != r['creator_id'] and uid != ADMIN_ID:
        bot.answer_callback_query(call.id, "🚫 فقط صاحب الروليت يمكنه بدء السحب!", show_alert=True)
        return
    if r['is_finished']:
        bot.answer_callback_query(call.id, "⚠️ تم السحب مسبقاً.", show_alert=True)
        return
    if get_part_count(rid) == 0:
        bot.answer_callback_query(call.id, "⚠️ لا يوجد مشاركون بعد.", show_alert=True)
        return
    bot.answer_callback_query(call.id, "🎰 جاري السحب...", show_alert=True)
    _execute_draw(rid)

@bot.callback_query_handler(func=lambda c: c.data.startswith("redraw_"))
@check_user
def handle_redraw(call):
    uid = call.from_user.id
    rid = call.data[7:]
    r = get_roulette(rid)
    if not r:
        bot.answer_callback_query(call.id, "⚠️ غير موجود.", show_alert=True)
        return
    if uid != r['creator_id'] and uid != ADMIN_ID:
        bot.answer_callback_query(call.id, NO_PERM, show_alert=True)
        return
    bot.answer_callback_query(call.id, "🔄 جاري إعادة السحب...", show_alert=True)
    conn = get_db()
    try:
        conn.execute('DELETE FROM winners WHERE roulette_id=?', (rid,))
        conn.execute('UPDATE roulettes SET is_finished=0,is_active=1 WHERE roulette_id=?', (rid,))
        conn.commit()
    finally:
        conn.close()
    _execute_draw(rid)

@bot.callback_query_handler(func=lambda c: c.data.startswith("repost_"))
@check_user
def handle_repost(call):
    uid = call.from_user.id
    rid = call.data[7:]
    r = get_roulette(rid)
    if not r:
        bot.answer_callback_query(call.id, "⚠️ الروليت غير موجود.", show_alert=True)
        return
    if uid != r['creator_id'] and uid != ADMIN_ID:
        bot.answer_callback_query(call.id, NO_PERM, show_alert=True)
        return
    bot.answer_callback_query(call.id, "🔄 جاري إعادة النشر...", show_alert=True)
    try:
        bot.delete_message(r['channel_id'], r['channel_message_id'])
    except Exception:
        pass
    count = get_part_count(rid)
    text = _build_roulette_text(r, count)
    markup = roulette_ch_kb(rid, bool(r['is_active']), r['creator_id'])
    try:
        if r['photo_id']:
            msg = bot.send_photo(r['channel_id'], r['photo_id'], caption=text, parse_mode="HTML", reply_markup=markup)
        else:
            msg = bot.send_message(r['channel_id'], text, parse_mode="HTML", reply_markup=markup, disable_web_page_preview=True)
        update_roulette_msg_id(rid, msg.message_id)
    except Exception as e:
        try:
            send_new(uid, f"⚠️ فشل إعادة النشر: {str(e)}")
        except Exception:
            pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("kick_"))
@check_user
def handle_kick(call):
    uid = call.from_user.id
    parts = call.data.split("_", 2)
    if len(parts) < 3:
        return
    rid, target = parts[1], int(parts[2])
    r = get_roulette(rid)
    if not r or (uid != r['creator_id'] and uid != ADMIN_ID):
        bot.answer_callback_query(call.id, NO_PERM, show_alert=True)
        return
    remove_participant(rid, target)
    update_roulette_msg(rid)
    bot.answer_callback_query(call.id, "✅ تم طرد المشارك.", show_alert=True)
    try:
        bot.edit_message_text(call.message.text + "\n\n✅ تم طرد المشارك.", call.message.chat.id, call.message.message_id, parse_mode="HTML")
    except Exception:
        pass
    try:
        send_new(target, "⚠️ تم إزالتك من الروليت.")
    except Exception:
        pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("pban_"))
@check_user
def handle_pban(call):
    uid = call.from_user.id
    parts = call.data.split("_", 2)
    if len(parts) < 3:
        return
    rid, target = parts[1], int(parts[2])
    r = get_roulette(rid)
    if not r or (uid != r['creator_id'] and uid != ADMIN_ID):
        bot.answer_callback_query(call.id, NO_PERM, show_alert=True)
        return
    remove_participant(rid, target)
    ban_from_creator(r['creator_id'], target)
    update_roulette_msg(rid)
    bot.answer_callback_query(call.id, "✅ تم الحظر الدائم.", show_alert=True)
    try:
        bot.edit_message_text(call.message.text + "\n\n🚫 تم الحظر الدائم.", call.message.chat.id, call.message.message_id, parse_mode="HTML")
    except Exception:
        pass
    try:
        send_new(target, "🚫 تم حظرك من سحوبات هذا المنشئ.")
    except Exception:
        pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("quickjoin_"))
@check_user
def handle_quickjoin(call):
    uid = call.from_user.id
    rid = call.data[10:]

    r = get_roulette(rid)
    if not r:
        bot.answer_callback_query(call.id, "⚠️ الروليت غير موجود.", show_alert=True)
        return

    if r['is_finished']:
        bot.answer_callback_query(call.id, "⛔ هذا الروليت قد انتهى.", show_alert=True)
        return

    if not r['is_active']:
        bot.answer_callback_query(call.id, "⏸️ المشاركة متوقفة مؤقتاً.", show_alert=True)
        return

    if r['creator_id'] == uid:
        bot.answer_callback_query(call.id, "⚠️ لا يمكنك المشاركة في روليتك الخاص.", show_alert=True)
        return

    if is_banned_from_creator(r['creator_id'], uid):
        bot.answer_callback_query(call.id, "🚫 أنت محظور من سحوبات هذا المنشئ.", show_alert=True)
        return

    if get_participant(rid, uid):
        bot.answer_callback_query(call.id, "✅ أنت مشارك بالفعل في هذا السحب! حظاً موفقاً 🍀", show_alert=True)
        return

    not_subbed = []

    if r['channel_id'] and not is_ch_member(r['channel_id'], uid):
        cu = r['channel_username'] or ''
        not_subbed.append(f"@{cu}" if cu else "قناة السحب")

    cc1 = r['conditional_channel_id']
    cu1 = r['conditional_channel_username'] or ''
    if cc1 and not is_ch_member(cc1, uid):
        not_subbed.append(f"@{cu1}" if cu1 else "قناة شرط 1")

    cc2 = r['conditional_channel_id_2']
    cu2 = r['conditional_channel_username_2'] or ''
    if cc2 and not is_ch_member(cc2, uid):
        not_subbed.append(f"@{cu2}" if cu2 else "قناة شرط 2")

    if not_subbed:
        channels_txt = "\n".join([f"• {ch}" for ch in not_subbed])
        bot.answer_callback_query(call.id, f"📢 يجب الاشتراك في هذه القنوات أولاً:\n\n{channels_txt}", show_alert=True)
        try:
            rows = []
            all_chs = []
            if r['channel_id'] and not is_ch_member(r['channel_id'], uid):
                cu = r['channel_username'] or ''
                if cu:
                    all_chs.append({'username': cu, 'title': f"@{cu}"})
            if cc1 and not is_ch_member(cc1, uid) and cu1:
                all_chs.append({'username': cu1, 'title': f"@{cu1}"})
            if cc2 and not is_ch_member(cc2, uid) and cu2:
                all_chs.append({'username': cu2, 'title': f"@{cu2}"})
            for ch in all_chs:
                rows.append([btn(f"📢 اشترك في {ch['title']}", url=f"https://t.me/{ch['username']}", color='green')])
            rows.append([btn("✅ اشتركت، عُد واضغط المشاركة", cbd=f"rcheck_sub_{rid}", color='green')])
            send_new(uid, "📢 اشترك في القنوات التالية ثم اضغط زر المشاركة مجدداً:", markup=kb(*rows))
        except Exception:
            pass
        return

    added = add_participant(rid, uid)
    if not added:
        bot.answer_callback_query(call.id, "✅ أنت مشارك بالفعل في هذا السحب! حظاً موفقاً 🍀", show_alert=True)
        return

    bot.answer_callback_query(call.id, "🎉 تم تسجيل مشاركتك بنجاح! حظاً موفقاً 🍀", show_alert=True)

    update_roulette_msg(rid)
    count = get_part_count(rid)

    if get_notify_setting(r['creator_id']):
        try:
            u_info = bot.get_chat(uid)
            uname = f"@{u_info.username}" if u_info.username else "لا يوجد"
            uname_display = u_info.first_name or f"مستخدم {uid}"
            if u_info.last_name:
                uname_display += f" {u_info.last_name}"
        except Exception:
            uname = "لا يوجد"
            uname_display = f"مستخدم {uid}"
        try:
            send_new(r['creator_id'], f"👤 مشارك جديد في روليتك!\n\nالاسم: {uname_display}\nاليوزر: {uname}\nالآيدي: <code>{uid}</code>\nإجمالي المشاركين: <b>{count}</b>", markup=part_kb(rid, uid))
        except Exception:
            pass

    clear_user_state(uid)

    if r['max_participants'] and count >= r['max_participants']:
        _execute_draw(rid, auto=True)

@bot.callback_query_handler(func=lambda c: c.data.startswith("remind_"))
@check_user
def handle_remind(call):
    uid = call.from_user.id
    rid = call.data[7:]
    r = get_roulette(rid)
    if not r:
        bot.answer_callback_query(call.id, "⚠️ الروليت غير موجود.", show_alert=True)
        return
    add_reminder(rid, uid)
    bot.answer_callback_query(call.id, "🔔 تم! سيتم إشعارك عند انتهاء الروليت.", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data.startswith("view_part_"))
@check_user
def handle_view_part(call):
    uid = call.from_user.id
    rid = call.data[10:]
    r = get_roulette(rid)
    if not r:
        bot.answer_callback_query(call.id, "⚠️ غير موجود.", show_alert=True)
        return
    if uid != r['creator_id'] and uid != ADMIN_ID:
        bot.answer_callback_query(call.id, NO_PERM, show_alert=True)
        return
    bot.answer_callback_query(call.id)
    parts = get_participants(rid)
    if not parts:
        send_new(uid, "📊 لا يوجد مشاركون بعد.")
        return
    lines = [f"📊 قائمة المشاركين ({len(parts)}):\n"]
    for i, p in enumerate(parts, 1):
        n = get_dname(p['user_id'])
        t = f" 🎫×{p['tickets']}" if p['tickets'] > 1 else ""
        jt = fmt_dt(p['joined_at'])
        lines.append(f"{i}. {n}{t}\n    📅 {jt}")
    full = "\n".join(lines)
    for i in range(0, len(full), 4000):
        try:
            send_new(uid, full[i:i + 4000])
        except Exception:
            pass

@bot.callback_query_handler(func=lambda c: c.data == "my_roulettes")
@check_user
def handle_my_roulettes(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id)
    roulettes = get_creator_roulettes(uid)
    if not roulettes:
        send_or_edit(call.message.chat.id, "📊 روليتاتي\n\nلا توجد روليتات نشطة حالياً.", markup=back_kb(), user_id=uid)
        return
    send_or_edit(call.message.chat.id, f"📊 روليتاتي النشطة ({len(roulettes)})", markup=my_roulettes_kb(roulettes), user_id=uid)

@bot.callback_query_handler(func=lambda c: c.data.startswith("my_r_"))
@check_user
def handle_my_r_detail(call):
    uid = call.from_user.id
    rid = call.data[5:]
    bot.answer_callback_query(call.id)
    r = get_roulette(rid)
    if not r or r['creator_id'] != uid:
        bot.answer_callback_query(call.id, NO_PERM, show_alert=True)
        return
    count = get_part_count(rid)
    ch = f"@{r['channel_username']}" if r['channel_username'] else "قناة"
    send_or_edit(call.message.chat.id, f"🎯 تفاصيل الروليت\n\n📝 النص: {r['text'][:80]}...\n📢 القناة: {ch}\n👥 المشاركون: <b>{count}</b>\n🏆 الفائزون: <b>{r['winners_count']}</b>\n📊 الحالة: {'✅ نشط' if r['is_active'] else '⛔ موقوف'}\n📅 تاريخ الإنشاء: {fmt_dt(r['created_at'])}", markup=my_roulette_detail_kb(rid, bool(r['is_active']), r['channel_username'], r['channel_message_id']), user_id=uid)

@bot.callback_query_handler(func=lambda c: c.data == "my_tickets")
@check_user
def handle_my_tickets(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id)
    conn = get_db()
    try:
        tickets = conn.execute('''
            SELECT p.roulette_id, p.tickets, r.text,
                   r.channel_username, r.is_finished,
                   r.winners_count
            FROM participants p
            JOIN roulettes r
            ON p.roulette_id = r.roulette_id
            WHERE p.user_id = ? AND r.is_finished = 0
            ORDER BY p.joined_at DESC
        ''', (uid,)).fetchall()
    finally:
        conn.close()

    if not tickets:
        send_or_edit(call.message.chat.id, "🎫 تذاكري\n\nلا تملك تذاكر في روليتات نشطة حالياً.\n\nشارك في روليت للحصول على تذاكر! 🎯", markup=back_kb(), user_id=uid)
        return

    total_tickets = sum(t['tickets'] for t in tickets)
    lines = [f"🎫 تذاكري\n\nإجمالي التذاكر: <b>{total_tickets}</b> 🎫\n"]
    for t in tickets:
        ch = f"@{t['channel_username']}" if t['channel_username'] else "قناة"
        txt = (t['text'][:35] + "..." if len(t['text']) > 35 else t['text'])
        lines.append(f"🎯 {txt}\n   {ch} | 🎫 <b>{t['tickets']}</b> تذكرة")
    send_or_edit(call.message.chat.id, "\n".join(lines), markup=back_kb(), user_id=uid)

@bot.callback_query_handler(func=lambda c: c.data == "my_reminders")
@check_user
def handle_my_reminders(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id)
    conn = get_db()
    try:
        rems = conn.execute('''
            SELECT r.roulette_id, ro.text,
                   ro.channel_username, ro.is_finished
            FROM reminders r
            JOIN roulettes ro
            ON r.roulette_id = ro.roulette_id
            WHERE r.user_id = ?
            ORDER BY ro.is_finished ASC
        ''', (uid,)).fetchall()
    finally:
        conn.close()

    if not rems:
        send_or_edit(call.message.chat.id, "🔔 تذكيراتي\n\nلا توجد تذكيرات.", markup=back_kb(), user_id=uid)
        return
    lines = ["🔔 تذكيراتي:\n"]
    for rem in rems:
        ch = f"@{rem['channel_username']}" if rem['channel_username'] else "قناة"
        status = "✅ نشط" if not rem['is_finished'] else "🔴 انتهى"
        txt = (rem['text'][:35] + "..." if len(rem['text']) > 35 else rem['text'])
        lines.append(f"🎯 {txt}\n   {ch} | {status}")
    send_or_edit(call.message.chat.id, "\n".join(lines), markup=back_kb(), user_id=uid)

@bot.callback_query_handler(func=lambda c: c.data == "my_stats")
@check_user
def handle_my_stats(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id)
    s = get_user_stats(uid)
    send_or_edit(call.message.chat.id, f"📈 إحصائياتي\n\n👑 كمنشئ:\n🎯 روليتاتي: <b>{s['my_roulettes']}</b>\n🏅 مسابقاتي: <b>{s['my_contests']}</b>\n👥 إجمالي المشاركين: <b>{s['total_my_parts']}</b>\n🏆 إجمالي الفائزين: <b>{s['total_my_winners']}</b>\n\n🎮 كمشارك:\n🎲 روليتات شاركت: <b>{s['joined_roulettes']}</b>\n🏆 مرات الفوز: <b>{s['wins']}</b>\n🎫 إجمالي التذاكر: <b>{s['total_tickets']}</b>\n🗳️ مسابقات شاركت: <b>{s['joined_contests']}</b>", markup=back_kb(), user_id=uid)

def _publish_contest(msg, uid, temp):
    cid = str(uuid.uuid4())
    text = _build_contest_text(temp, 0)
    markup = contest_ch_kb(cid)
    try:
        if temp.get('contest_photo'):
            sent = bot.send_photo(temp['contest_channel_id'], temp['contest_photo'], caption=text, parse_mode="HTML", reply_markup=markup)
        else:
            sent = bot.send_message(temp['contest_channel_id'], text, parse_mode="HTML", reply_markup=markup)
        create_contest(cid, uid, temp['contest_channel_id'], temp.get('contest_channel_username', ''), temp['contest_title'], temp['contest_description'], temp.get('contest_photo', ''), temp['contest_max_p'], temp['contest_ranks'], temp['auto_accept'])
        conn = get_db()
        try:
            conn.execute('UPDATE contests SET channel_message_id=? WHERE contest_id=?', (sent.message_id, cid))
            conn.commit()
        finally:
            conn.close()

        clear_user_state(uid)

        ch_link = None
        if temp.get('contest_channel_username') and sent.message_id:
            ch_link = f"https://t.me/{temp['contest_channel_username']}/{sent.message_id}"
        rows = []
        if ch_link:
            rows.append([btn("📢 اذهب للمسابقة", url=ch_link, color='blue')])
        send_new(uid, f"🎉 تم نشر المسابقة بنجاح!\n\n🏆 العنوان: <b>{temp['contest_title']}</b>\n👥 الحد الأقصى: <b>{temp['contest_max_p']}</b>\n🥇 المراكز: <b>{temp['contest_ranks']}</b>\n👤 القبول: <b>{'تلقائي ✅' if temp['auto_accept'] else 'يدوي 👤'}</b>", markup=kb(*rows) if rows else None)

        bot_name = get_bot_name()
        send_or_edit(msg.chat.id, f"👋 أهلاً بك في {bot_name}!\n\nاختر من القائمة:", markup=main_menu_kb(uid), user_id=uid)
    except Exception as e:
        send_new(msg.chat.id, f"⚠️ فشل النشر: {str(e)}")
        clear_user_state(uid)

def _auto_join_contest(chat_id, uid, cid, c):
    try:
        u_info = bot.get_chat(uid)
        display_name = u_info.first_name or f"مستخدم {uid}"
        if u_info.last_name:
            display_name += f" {u_info.last_name}"
        username = u_info.username or ''
    except Exception:
        display_name = f"مستخدم {uid}"
        username = ''

    name_display = display_name
    if username:
        name_display += f" — @{username}"

    if bool(c['auto_accept']):
        e = random.choice(POSITIVE_EMOJIS)
        try:
            if c['photo_id']:
                sent = bot.send_photo(c['channel_id'], c['photo_id'], caption=f"{e} <b>{name_display}</b>\nدعمه بتصويتك! 👇", parse_mode="HTML", reply_markup=vote_kb_build(cid, uid, 0))
            else:
                sent = bot.send_message(c['channel_id'], f"{e} <b>{name_display}</b>\nدعمه بتصويتك! 👇", parse_mode="HTML", reply_markup=vote_kb_build(cid, uid, 0))
            add_contest_part(cid, uid, display_name, username, sent.message_id, 'accepted')
            conn = get_db()
            try:
                cnt = conn.execute("SELECT COUNT(*) FROM contest_participants WHERE contest_id=? AND status='accepted'", (cid,)).fetchone()[0]
                contest_row = conn.execute('SELECT channel_message_id FROM contests WHERE contest_id=?', (cid,)).fetchone()
            finally:
                conn.close()

            if contest_row and contest_row['channel_message_id']:
                data_for_text = {'contest_title': c['title'], 'contest_description': c['description'], 'contest_max_p': c['max_participants'], 'contest_ranks': c['ranks_count']}
                try:
                    if c['photo_id']:
                        bot.edit_message_caption(caption=_build_contest_text(data_for_text, cnt), chat_id=c['channel_id'], message_id=contest_row['channel_message_id'], parse_mode="HTML", reply_markup=contest_ch_kb(cid))
                    else:
                        bot.edit_message_text(_build_contest_text(data_for_text, cnt), c['channel_id'], contest_row['channel_message_id'], parse_mode="HTML", reply_markup=contest_ch_kb(cid))
                except Exception:
                    pass

            send_new(chat_id, f"✅ تم قبول مشاركتك في المسابقة!\n\n👤 اسمك: <b>{name_display}</b>\n\nيمكنك سحب مشاركتك في أي وقت.", markup=withdraw_contest_kb(cid))
        except Exception as ex:
            send_new(chat_id, f"⚠️ خطأ: {str(ex)}")
    else:
        add_contest_part(cid, uid, display_name, username, 0, 'pending')
        try:
            send_new(c['creator_id'], f"👤 طلب مشاركة جديد\n\nالاسم: <b>{name_display}</b>\nالآيدي: <code>{uid}</code>", markup=contest_accept_kb(cid, uid))
        except Exception:
            pass
        send_new(chat_id, "⏳ تم إرسال طلب مشاركتك!\n\nسيتم إشعارك عند قبول طلبك.")

def _handle_join_contest_start(msg, uid, cid):
    c = get_contest(cid)
    if not c:
        send_or_edit(msg.chat.id, "⚠️ المسابقة غير موجودة.", markup=main_menu_kb(uid), user_id=uid)
        return
    if c['is_finished']:
        send_or_edit(msg.chat.id, "⛔ المسابقة انتهت.", markup=main_menu_kb(uid), user_id=uid)
        return
    if not c['is_active']:
        send_or_edit(msg.chat.id, "⛔ المشاركة متوقفة.", markup=main_menu_kb(uid), user_id=uid)
        return
    if c['creator_id'] == uid:
        send_or_edit(msg.chat.id, "⚠️ لا يمكنك المشاركة في مسابقتك.", markup=main_menu_kb(uid), user_id=uid)
        return
    conn = get_db()
    try:
        ex = conn.execute('SELECT id FROM contest_participants WHERE contest_id=? AND user_id=?', (cid, uid)).fetchone()
    finally:
        conn.close()
    if ex:
        send_or_edit(msg.chat.id, "✅ أنت مشارك بالفعل!", markup=main_menu_kb(uid), user_id=uid)
        return
    if len(get_contest_parts(cid, 'accepted')) >= c['max_participants']:
        send_or_edit(msg.chat.id, "⚠️ اكتمل عدد المشاركين.", markup=main_menu_kb(uid), user_id=uid)
        return
    set_user_state(uid, 'contest_join_captcha', {'joining_contest_id': cid})
    _send_contest_captcha(msg.chat.id, uid, cid)

def _handle_vote_deeplink(msg, uid, cid, pid):
    c = get_contest(cid)
    if not c or c['is_finished'] or not c['is_active']:
        send_new(uid, "⛔ التصويت غير متاح حالياً.")
        return
    if c['channel_id']:
        if not is_ch_member(c['channel_id'], uid):
            cu = c['channel_username']
            markup = kb([btn("📢 اشترك في القناة", url=f"https://t.me/{cu}", color='green')]) if cu else None
            send_new(uid, "📛 يجب الاشتراك في قناة المسابقة أولاً!", markup=markup)
            return
    if has_voted_for(cid, uid, pid):
        send_new(uid, "✅ لقد صوّتَ لهذا المشارك بالفعل!\n\nيمكنك التصويت لمشاركين آخرين.")
        return
    if uid == c['creator_id'] or uid == pid:
        send_new(uid, "⚠️ لا يمكنك التصويت لنفسك.")
        return
    set_user_state(uid, 'vote_captcha', {'vote_contest_id': cid, 'vote_for': pid})
    _send_vote_captcha(uid, cid, pid)

@bot.callback_query_handler(func=lambda c: c.data == "create_contest")
@check_user
@check_forced
def handle_create_contest(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id)
    chs = get_user_channels(uid)
    if not chs:
        send_or_edit(call.message.chat.id, "⚠️ يجب ربط قناة أولاً!", markup=my_channels_kb([]), user_id=uid)
        return
    if len(chs) == 1:
        set_user_state(uid, 'await_contest_title', {'contest_channel_id': chs[0]['channel_id'], 'contest_channel_username': chs[0]['channel_username'] or ''})
        send_or_edit(call.message.chat.id, "🏆 إنشاء مسابقة جديدة\n\nأرسل عنوان المسابقة:", markup=cancel_kb(), user_id=uid)
        return
    send_or_edit(call.message.chat.id, "📢 اختر القناة للمسابقة:", markup=choose_channel_kb(chs, "contest"), user_id=uid)

@bot.callback_query_handler(func=lambda c: c.data.startswith("sel_ch_contest_"))
@check_user
def handle_sel_ch_contest(call):
    uid = call.from_user.id
    ch_id = int(call.data.replace("sel_ch_contest_", ""))
    bot.answer_callback_query(call.id)
    if not can_use_channel(ch_id, uid):
        bot.answer_callback_query(call.id, NO_PERM, show_alert=True)
        return
    ch = get_channel(ch_id)
    set_user_state(uid, 'await_contest_title', {'contest_channel_id': ch_id, 'contest_channel_username': ch['channel_username'] or ''})
    send_or_edit(call.message.chat.id, "🏆 أرسل عنوان المسابقة:", markup=cancel_kb(), user_id=uid)

@bot.callback_query_handler(func=lambda c: c.data in ["c_auto_yes", "c_auto_no"])
@check_user
def handle_contest_auto(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id)
    _, temp = get_user_state(uid)
    temp['auto_accept'] = call.data == "c_auto_yes"
    set_user_state(uid, 'await_contest_photo', temp)
    send_or_edit(call.message.chat.id, "🖼️ هل تريد إضافة صورة للمسابقة؟\nأرسل الصورة أو اضغط تخطي:", markup=kb([btn("⏭️ تخطي بدون صورة", cbd="skip_contest_photo", color='green')], [btn("❌ إلغاء", cbd="back_main", color='red')]), user_id=uid)

@bot.callback_query_handler(func=lambda c: c.data == "skip_contest_photo")
@check_user
def handle_skip_contest_photo(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id)
    _, temp = get_user_state(uid)
    temp['contest_photo'] = ''
    set_user_state(uid, 'await_confirm_pub_c', temp)
    preview = _build_contest_preview(temp)
    send_or_edit(call.message.chat.id, preview, markup=confirm_publish_contest_kb(), user_id=uid)

@bot.callback_query_handler(func=lambda c: c.data == "confirm_pub_c")
@check_user
def handle_confirm_pub_c(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id)
    _, temp = get_user_state(uid)
    _publish_contest(call.message, uid, temp)

@bot.callback_query_handler(func=lambda c: c.data.startswith("join_contest_"))
@check_user
@check_forced
def handle_join_contest(call):
    uid = call.from_user.id
    cid = call.data.replace("join_contest_", "")
    c = get_contest(cid)
    if not c:
        bot.answer_callback_query(call.id, "⚠️ المسابقة غير موجودة.", show_alert=True)
        return
    if c['is_finished']:
        bot.answer_callback_query(call.id, "⛔ المسابقة انتهت.", show_alert=True)
        return
    if not c['is_active']:
        bot.answer_callback_query(call.id, "⛔ المشاركة متوقفة.", show_alert=True)
        return
    if c['creator_id'] == uid:
        bot.answer_callback_query(call.id, "⚠️ لا يمكنك المشاركة في مسابقتك.", show_alert=True)
        return
    conn = get_db()
    try:
        ex = conn.execute('SELECT id FROM contest_participants WHERE contest_id=? AND user_id=?', (cid, uid)).fetchone()
    finally:
        conn.close()
    if ex:
        bot.answer_callback_query(call.id, "✅ أنت مشارك بالفعل!", show_alert=True)
        return
    if len(get_contest_parts(cid, 'accepted')) >= c['max_participants']:
        bot.answer_callback_query(call.id, "⚠️ اكتمل عدد المشاركين.", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    set_user_state(uid, 'contest_join_captcha', {'joining_contest_id': cid})
    _send_contest_captcha(uid, uid, cid)

@bot.callback_query_handler(func=lambda c: c.data.startswith("ccap_"))
@check_user
def handle_contest_captcha(call):
    uid = call.from_user.id
    parts = call.data.split("_", 2)
    if len(parts) < 3:
        return
    try:
        idx = int(parts[1])
    except ValueError:
        return
    cid = parts[2]

    cap = get_captcha(uid, f"contest_{cid}")
    if not cap:
        bot.answer_callback_query(call.id, "⏰ انتهت صلاحية الكابتشا.\nاضغط مشاركة مجدداً.", show_alert=True)
        del_msg(call.message.chat.id, call.message.message_id)
        return

    chosen = cap['options'][idx]
    if chosen != cap['correct']:
        clear_captcha(uid, f"contest_{cid}")
        bot.answer_callback_query(call.id, "❌ إجابة خاطئة!\nاضغط المشاركة مجدداً.", show_alert=True)
        del_msg(call.message.chat.id, call.message.message_id)
        return

    clear_captcha(uid, f"contest_{cid}")
    bot.answer_callback_query(call.id, "✅ إجابة صحيحة!")
    del_msg(call.message.chat.id, call.message.message_id)

    c = get_contest(cid)
    if not c:
        send_new(uid, "⚠️ المسابقة غير موجودة.")
        return

    try:
        u_info = bot.get_chat(uid)
        display_name = u_info.first_name or f"مستخدم {uid}"
        if u_info.last_name:
            display_name += f" {u_info.last_name}"
        username = u_info.username or ''
    except Exception:
        display_name = f"مستخدم {uid}"
        username = ''

    name_display = display_name
    if username:
        name_display += f" — @{username}"

    set_user_state(uid, 'contest_join_confirm', {'joining_contest_id': cid})

    send_new(uid, f"👤 تأكيد المشاركة في المسابقة\n\n🏆 المسابقة: <b>{c['title']}</b>\n\nسيظهر اسمك كالتالي:\n<b>{name_display}</b>\n\nهل تريد المشاركة؟", markup=contest_join_confirm_kb(cid))

@bot.callback_query_handler(func=lambda c: c.data.startswith("confirm_join_c_"))
@check_user
def handle_confirm_join_contest(call):
    uid = call.from_user.id
    cid = call.data.replace("confirm_join_c_", "")
    bot.answer_callback_query(call.id)
    del_msg(call.message.chat.id, call.message.message_id)
    c = get_contest(cid)
    if not c:
        send_new(uid, "⚠️ المسابقة غير موجودة.")
        return
    conn = get_db()
    try:
        ex = conn.execute('SELECT id FROM contest_participants WHERE contest_id=? AND user_id=?', (cid, uid)).fetchone()
    finally:
        conn.close()
    if ex:
        send_new(uid, "✅ أنت مشارك بالفعل!")
        return
    if len(get_contest_parts(cid, 'accepted')) >= c['max_participants']:
        send_new(uid, "⚠️ اكتمل عدد المشاركين.")
        return
    clear_user_state(uid)
    _auto_join_contest(uid, uid, cid, c)

@bot.callback_query_handler(func=lambda c: c.data.startswith("withdraw_contest_"))
@check_user
def handle_withdraw_contest(call):
    uid = call.from_user.id
    cid = call.data.replace("withdraw_contest_", "")
    c = get_contest(cid)
    if not c:
        bot.answer_callback_query(call.id, "⚠️ المسابقة غير موجودة.", show_alert=True)
        return
    if c['is_finished']:
        bot.answer_callback_query(call.id, "⚠️ المسابقة انتهت بالفعل.", show_alert=True)
        return
    conn = get_db()
    try:
        p = conn.execute('SELECT * FROM contest_participants WHERE contest_id=? AND user_id=?', (cid, uid)).fetchone()
    finally:
        conn.close()
    if not p:
        bot.answer_callback_query(call.id, "⚠️ أنت لست مشاركاً.", show_alert=True)
        return
    if p['channel_message_id']:
        try:
            bot.delete_message(c['channel_id'], p['channel_message_id'])
        except Exception:
            pass
    conn = get_db()
    try:
        conn.execute('DELETE FROM contest_participants WHERE contest_id=? AND user_id=?', (cid, uid))
        conn.execute('DELETE FROM contest_votes WHERE contest_id=? AND voter_id=?', (cid, uid))
        conn.commit()
    finally:
        conn.close()

    bot.answer_callback_query(call.id, "✅ تم سحب مشاركتك.", show_alert=True)
    del_msg(call.message.chat.id, call.message.message_id)

    conn = get_db()
    try:
        cnt = conn.execute("SELECT COUNT(*) FROM contest_participants WHERE contest_id=? AND status='accepted'", (cid,)).fetchone()[0]
        contest_row = conn.execute('SELECT channel_message_id FROM contests WHERE contest_id=?', (cid,)).fetchone()
    finally:
        conn.close()

    if contest_row and contest_row['channel_message_id']:
        data_for_text = {'contest_title': c['title'], 'contest_description': c['description'], 'contest_max_p': c['max_participants'], 'contest_ranks': c['ranks_count']}
        try:
            if c['photo_id']:
                bot.edit_message_caption(caption=_build_contest_text(data_for_text, cnt), chat_id=c['channel_id'], message_id=contest_row['channel_message_id'], parse_mode="HTML", reply_markup=contest_ch_kb(cid))
            else:
                bot.edit_message_text(_build_contest_text(data_for_text, cnt), c['channel_id'], contest_row['channel_message_id'], parse_mode="HTML", reply_markup=contest_ch_kb(cid))
        except Exception:
            pass

    send_new(uid, "✅ تم سحب مشاركتك من المسابقة.\n\nيمكنك المشاركة مجدداً إذا أردت.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("vcap_"))
@check_user
def handle_vote_captcha(call):
    uid = call.from_user.id
    parts = call.data.split("_", 3)
    if len(parts) < 4:
        return
    try:
        idx = int(parts[1])
    except ValueError:
        return
    cid, pid = parts[2], int(parts[3])
    cap_key = f"vote_{cid}_{pid}"
    cap = get_captcha(uid, cap_key)
    if not cap:
        bot.answer_callback_query(call.id, "⏰ انتهت صلاحية الكابتشا.", show_alert=True)
        del_msg(call.message.chat.id, call.message.message_id)
        return

    chosen = cap['options'][idx]
    if chosen != cap['correct']:
        clear_captcha(uid, cap_key)
        bot.answer_callback_query(call.id, "❌ إجابة خاطئة! حاول مجدداً.", show_alert=True)
        del_msg(call.message.chat.id, call.message.message_id)
        return

    clear_captcha(uid, cap_key)
    bot.answer_callback_query(call.id, "✅ إجابة صحيحة!")
    del_msg(call.message.chat.id, call.message.message_id)

    success, reason = add_vote_new(cid, uid, pid)
    if success:
        c = get_contest(cid)
        conn = get_db()
        try:
            p = conn.execute('SELECT * FROM contest_participants WHERE contest_id=? AND user_id=?', (cid, pid)).fetchone()
        finally:
            conn.close()

        if p and p['channel_message_id'] and c:
            new_votes = p['votes'] + 1
            e = random.choice(POSITIVE_EMOJIS)
            name_display = p['display_name']
            if p['username']:
                name_display += f" — @{p['username']}"
            try:
                if c['photo_id']:
                    bot.edit_message_caption(caption=f"{e} <b>{name_display}</b>\nدعمه بتصويتك! 👇", chat_id=c['channel_id'], message_id=p['channel_message_id'], parse_mode="HTML", reply_markup=vote_kb_build(cid, pid, new_votes))
                else:
                    bot.edit_message_text(f"{e} <b>{name_display}</b>\nدعمه بتصويتك! 👇", c['channel_id'], p['channel_message_id'], parse_mode="HTML", reply_markup=vote_kb_build(cid, pid, new_votes))
            except Exception:
                pass

        send_new(uid, "🗳️ تم تسجيل صوتك بنجاح!\n\nيمكنك التصويت لمشاركين آخرين أيضاً! 🏆")
    else:
        send_new(uid, "✅ لقد صوّتَ لهذا المشارك بالفعل!\n\nيمكنك التصويت لمشاركين آخرين.")

@bot.callback_query_handler(func=lambda c: c.data.startswith("end_contest_confirm_"))
@check_user
def handle_end_contest_confirm(call):
    uid = call.from_user.id
    cid = call.data.replace("end_contest_confirm_", "")
    c = get_contest(cid)
    if not c:
        bot.answer_callback_query(call.id, "⚠️ المسابقة غير موجودة.", show_alert=True)
        return
    if uid != c['creator_id'] and uid != ADMIN_ID:
        bot.answer_callback_query(call.id, NO_PERM, show_alert=True)
        return
    if c['is_finished']:
        bot.answer_callback_query(call.id, "⚠️ المسابقة انتهت مسبقاً.", show_alert=True)
        return
    bot.answer_callback_query(call.id)
    send_or_edit(call.message.chat.id, f"⚠️ تأكيد إنهاء المسابقة\n\n🏆 {c['title']}\n\nهل أنت متأكد من إنهاء المسابقة وإعلان النتائج؟", markup=end_contest_confirm_kb(cid), user_id=uid)

@bot.callback_query_handler(func=lambda c: c.data.startswith("end_contest_") and not c.data.startswith("end_contest_confirm_"))
@check_user
def handle_end_contest(call):
    uid = call.from_user.id
    cid = call.data.replace("end_contest_", "")
    c = get_contest(cid)
    if not c:
        bot.answer_callback_query(call.id, "⚠️ المسابقة غير موجودة.", show_alert=True)
        return
    if uid != c['creator_id'] and uid != ADMIN_ID:
        bot.answer_callback_query(call.id, NO_PERM, show_alert=True)
        return
    if c['is_finished']:
        bot.answer_callback_query(call.id, "⚠️ المسابقة انتهت مسبقاً.", show_alert=True)
        return
    bot.answer_callback_query(call.id, "🏁 جاري إعلان النتائج...", show_alert=True)

    parts = get_contest_parts(cid, 'accepted')
    if not parts:
        send_new(c['creator_id'], "⚠️ لا يوجد مشاركون في المسابقة.")
        return

    sorted_p = sorted(parts, key=lambda x: x['votes'], reverse=True)
    ranks_e = {1: "🥇", 2: "🥈", 3: "🥉"}
    rc = c['ranks_count']

    lines = [f"🏆 نتائج مسابقة: {c['title']}\n\n"]
    for i, p in enumerate(sorted_p[:rc], 1):
        mention = get_mention(p['user_id'])
        name_display = p['display_name']
        if p['username']:
            name_display += f" — @{p['username']}"
        lines.append(f"{ranks_e.get(i, f'#{i}')} <b>{name_display}</b>\n   {mention} | 🗳️ {p['votes']} صوت\n")

    text = "\n".join(lines) + "\n🎊 مبروك للفائزين!" + _build_footer()
    finish_contest(cid)

    try:
        send_new(c['channel_id'], text)
    except Exception:
        pass

    for i, p in enumerate(sorted_p[:rc], 1):
        try:
            send_new(p['user_id'], f"🎊 مبروك! فزت في المسابقة!\n\n🏆 المسابقة: {c['title']}\n{ranks_e.get(i, f'#{i}')} المركز {i}\n🗳️ الأصوات: {p['votes']}")
        except Exception:
            pass

    for p in sorted_p[rc:]:
        try:
            send_new(p['user_id'], f"🔔 انتهت المسابقة!\n\n🏆 {c['title']}\n\nللأسف لم تفز هذه المرة.\nحظاً أوفر في المرة القادمة! 🍀")
        except Exception:
            pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("toggle_contest_"))
@check_user
def handle_toggle_contest(call):
    uid = call.from_user.id
    cid = call.data.replace("toggle_contest_", "")
    c = get_contest(cid)
    if not c or (uid != c['creator_id'] and uid != ADMIN_ID):
        bot.answer_callback_query(call.id, NO_PERM, show_alert=True)
        return
    new_val = not bool(c['is_active'])
    conn = get_db()
    try:
        conn.execute('UPDATE contests SET is_active=? WHERE contest_id=?', (1 if new_val else 0, cid))
        conn.commit()
    finally:
        conn.close()
    bot.answer_callback_query(call.id, "✅ تم التشغيل." if new_val else "⛔ تم الإيقاف.", show_alert=True)
    c2 = get_contest(cid)
    send_or_edit(call.message.chat.id, f"🏆 تفاصيل المسابقة\n\nالعنوان: {c2['title']}\nالحالة: {'✅ نشطة' if c2['is_active'] else '⛔ موقوفة'}", markup=my_contest_detail_kb(cid, bool(c2['is_active']), c2['channel_username'], c2['channel_message_id']), user_id=uid)

@bot.callback_query_handler(func=lambda c: c.data.startswith("exclude_cp_"))
@check_user
def handle_exclude_cp(call):
    uid = call.from_user.id
    cid = call.data.replace("exclude_cp_", "")
    c = get_contest(cid)
    if not c or (uid != c['creator_id'] and uid != ADMIN_ID):
        bot.answer_callback_query(call.id, NO_PERM, show_alert=True)
        return
    bot.answer_callback_query(call.id)
    set_user_state(uid, 'await_exclude_cp_id', {'exclude_contest_id': cid})
    send_or_edit(call.message.chat.id, "أرسل آيدي المشارك للاستبعاد:", markup=cancel_kb(), user_id=uid)

@bot.callback_query_handler(func=lambda c: c.data.startswith("cp_accept_"))
@check_user
def handle_cp_accept(call):
    uid = call.from_user.id
    parts = call.data.replace("cp_accept_", "").split("_", 1)
    if len(parts) < 2:
        return
    cid, tid = parts[0], int(parts[1])
    c = get_contest(cid)
    if not c or uid != c['creator_id']:
        bot.answer_callback_query(call.id, NO_PERM, show_alert=True)
        return
    conn = get_db()
    try:
        p = conn.execute('SELECT * FROM contest_participants WHERE contest_id=? AND user_id=?', (cid, tid)).fetchone()
    finally:
        conn.close()
    if not p:
        bot.answer_callback_query(call.id, "⚠️ غير موجود.", show_alert=True)
        return
    e = random.choice(POSITIVE_EMOJIS)
    name_display = p['display_name']
    if p['username']:
        name_display += f" — @{p['username']}"
    try:
        if c['photo_id']:
            sent = bot.send_photo(c['channel_id'], c['photo_id'], caption=f"{e} <b>{name_display}</b>\nدعمه بتصويتك! 👇", parse_mode="HTML", reply_markup=vote_kb_build(cid, tid, 0))
        else:
            sent = bot.send_message(c['channel_id'], f"{e} <b>{name_display}</b>\nدعمه بتصويتك! 👇", parse_mode="HTML", reply_markup=vote_kb_build(cid, tid, 0))
        conn = get_db()
        try:
            conn.execute('UPDATE contest_participants SET status=?,channel_message_id=? WHERE contest_id=? AND user_id=?', ('accepted', sent.message_id, cid, tid))
            conn.commit()
        finally:
            conn.close()
        bot.answer_callback_query(call.id, "✅ تم القبول!", show_alert=True)
        try:
            bot.edit_message_text(call.message.text + "\n\n✅ تم القبول.", call.message.chat.id, call.message.message_id, parse_mode="HTML")
        except Exception:
            pass
        send_new(tid, f"✅ تم قبول مشاركتك في المسابقة!\n\n🏆 {c['title']}\n\nيمكنك سحب مشاركتك في أي وقت.", markup=withdraw_contest_kb(cid))
    except Exception as ex:
        bot.answer_callback_query(call.id, f"⚠️ خطأ: {str(ex)}", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data.startswith("cp_reject_"))
@check_user
def handle_cp_reject(call):
    uid = call.from_user.id
    parts = call.data.replace("cp_reject_", "").split("_", 1)
    if len(parts) < 2:
        return
    cid, tid = parts[0], int(parts[1])
    c = get_contest(cid)
    if not c or uid != c['creator_id']:
        bot.answer_callback_query(call.id, NO_PERM, show_alert=True)
        return
    conn = get_db()
    try:
        conn.execute("UPDATE contest_participants SET status='rejected' WHERE contest_id=? AND user_id=?", (cid, tid))
        conn.commit()
    finally:
        conn.close()
    bot.answer_callback_query(call.id, "✅ تم الرفض.", show_alert=True)
    try:
        bot.edit_message_text(call.message.text + "\n\n❌ تم الرفض.", call.message.chat.id, call.message.message_id, parse_mode="HTML")
    except Exception:
        pass
    send_new(tid, "❌ لم يتم قبول مشاركتك في المسابقة.")

@bot.callback_query_handler(func=lambda c: c.data == "my_contests")
@check_user
def handle_my_contests(call):
    uid = call.from_user.id
    bot.answer_callback_query(call.id)
    conn = get_db()
    try:
        contests = conn.execute('SELECT * FROM contests WHERE creator_id=? AND is_finished=0 ORDER BY created_at DESC', (uid,)).fetchall()
    finally:
        conn.close()
    if not contests:
        send_or_edit(call.message.chat.id, "🏅 مسابقاتي\n\nلا توجد مسابقات نشطة حالياً.", markup=back_kb(), user_id=uid)
        return
    send_or_edit(call.message.chat.id, f"🏅 مسابقاتي النشطة ({len(contests)})", markup=my_contests_kb(contests), user_id=uid)

@bot.callback_query_handler(func=lambda c: c.data.startswith("my_c_"))
@check_user
def handle_my_c_detail(call):
    uid = call.from_user.id
    cid = call.data[5:]
    bot.answer_callback_query(call.id)
    c = get_contest(cid)
    if not c or c['creator_id'] != uid:
        bot.answer_callback_query(call.id, NO_PERM, show_alert=True)
        return
    parts_count = len(get_contest_parts(cid, 'accepted'))
    ch = f"@{c['channel_username']}" if c['channel_username'] else "قناة"
    send_or_edit(call.message.chat.id, f"🏆 تفاصيل المسابقة\n\n📝 العنوان: {c['title']}\n📢 القناة: {ch}\n👥 المشاركون: <b>{parts_count}</b>\n🥇 المراكز: <b>{c['ranks_count']}</b>\n📊 الحالة: {'✅ نشطة' if c['is_active'] else '⛔ موقوفة'}", markup=my_contest_detail_kb(cid, bool(c['is_active']), c['channel_username'], c['channel_message_id']), user_id=uid)

@bot.message_handler(content_types=['text', 'photo', 'video', 'document', 'audio', 'voice'])
@check_user
def handle_msgs(msg):
    uid = msg.from_user.id
    state, temp = get_user_state(uid)
    text = extract_text(msg)
    is_photo = msg.content_type == 'photo'

    if text and not text.startswith('/'):
        del_msg(msg.chat.id, msg.message_id)

    if state == 'adm_ban' and uid == ADMIN_ID:
        try:
            tid = int(text.strip())
            if tid == ADMIN_ID:
                send_new(msg.chat.id, "⚠️ لا يمكن حظر المطور!")
                return
            conn = get_db()
            try:
                conn.execute('UPDATE users SET is_banned=1 WHERE user_id=?', (tid,))
                conn.commit()
            finally:
                conn.close()
            clear_user_state(uid)
            try:
                send_new(tid, "🚫 تم حظرك من البوت.")
            except Exception:
                pass
            send_new(msg.chat.id, f"✅ تم حظر <code>{tid}</code>")
        except ValueError:
            send_new(msg.chat.id, "⚠️ أرسل آيدي رقمي.")

    elif state == 'adm_unban' and uid == ADMIN_ID:
        try:
            tid = int(text.strip())
            conn = get_db()
            try:
                conn.execute('UPDATE users SET is_banned=0 WHERE user_id=?', (tid,))
                conn.commit()
            finally:
                conn.close()
            clear_user_state(uid)
            try:
                send_new(tid, "✅ تم رفع الحظر عنك!")
            except Exception:
                pass
            send_new(msg.chat.id, f"✅ تم فك حظر <code>{tid}</code>")
        except ValueError:
            send_new(msg.chat.id, "⚠️ أرسل آيدي رقمي.")

    elif state == 'adm_broadcast' and uid == ADMIN_ID:
        raw = msg.text or msg.caption or ""
        if not raw.strip():
            send_new(msg.chat.id, "⚠️ النص فارغ.")
            return
        clear_user_state(uid)
        users = get_all_users()
        send_new(msg.chat.id, f"⏳ جاري الإذاعة لـ {len(users)} مستخدم...")
        ok, fail = 0, 0
        for u in users:
            try:
                bot.send_message(u['user_id'], f"📢 رسالة من المطور:\n\n{raw}", parse_mode="HTML")
                ok += 1
                time.sleep(0.05)
            except Exception:
                fail += 1
        send_new(msg.chat.id, f"✅ اكتملت الإذاعة\n\nنجح: {ok}\nفشل: {fail}")

    elif state == 'adm_photo' and uid == ADMIN_ID:
        raw = msg.text or msg.caption or ""
        if raw.strip() == 'حذف':
            set_setting('bot_photo', '')
            clear_user_state(uid)
            send_new(msg.chat.id, "✅ تم حذف صورة البوت.")
        elif is_photo:
            photo_id = msg.photo[-1].file_id
            set_setting('bot_photo', photo_id)
            clear_user_state(uid)
            del_msg(msg.chat.id, msg.message_id)
            send_new(msg.chat.id, "✅ تم تعيين صورة البوت!")
        else:
            send_new(msg.chat.id, "⚠️ أرسل صورة أو اكتب 'حذف'.")

    elif state == 'adm_add_forced' and uid == ADMIN_ID:
        raw = msg.text or ""
        m = re.match(r'^(?:https?://t\.me/)?@?([a-zA-Z0-9_]+)$', raw.strip())
        if not m:
            send_new(msg.chat.id, "⚠️ رابط غير صالح.")
            return
        try:
            chat = bot.get_chat("@" + m.group(1))
            if chat.type != 'channel':
                send_new(msg.chat.id, "⚠️ ليس قناة.")
                return
            add_forced_channel(chat.id, chat.username or '', chat.title or '')
            clear_user_state(uid)
            fcs = get_forced_channels()
            send_or_edit(msg.chat.id, f"✅ تم إضافة القناة: @{chat.username or chat.title}", markup=forced_channels_kb(fcs), user_id=uid)
        except Exception as e:
            send_new(msg.chat.id, f"⚠️ خطأ: {str(e)}")

    elif state == 'await_ch_link':
        _process_ch_link(msg, uid)

    elif state == 'await_r_text':
        raw = msg.text or msg.caption or ""
        if not raw.strip():
            send_or_edit(msg.chat.id, "⚠️ النص فارغ.", markup=cancel_kb(), user_id=uid)
            return
        if contains_link(raw):
            send_or_edit(msg.chat.id, "🚫 النص يحتوي على روابط!\nأرسل النص بدون روابط:", markup=cancel_kb(), user_id=uid)
            return
        temp['roulette_text'] = text if text else raw
        set_user_state(uid, 'await_r_options', temp)
        send_or_edit(msg.chat.id, "✅ تم حفظ النص!\n\nهل تريد إضافة قناة شرط؟", markup=roulette_options_kb(), user_id=uid)

    elif state == 'await_cond_1':
        _process_cond_ch(msg, uid, 1)

    elif state == 'await_cond_2':
        _process_cond_ch(msg, uid, 2)

    elif state == 'await_winner_count':
        try:
            count = int(text.strip())
            if count <= 0 or count > 100:
                raise ValueError
            temp['winners_count'] = count
            set_user_state(uid, 'await_max_p', temp)
            send_or_edit(msg.chat.id, "👥 الحد الأقصى للمشاركين؟", markup=max_part_kb(), user_id=uid)
        except ValueError:
            send_or_edit(msg.chat.id, "⚠️ أرسل رقماً صحيحاً بين 1 و 100.", markup=cancel_kb(), user_id=uid)

    elif state == 'await_max_p':
        try:
            count = int(text.strip())
            if count <= 0:
                raise ValueError
            temp['max_participants'] = count
            set_user_state(uid, 'await_end_time', temp)
            send_or_edit(msg.chat.id, "⏰ متى ينتهي الروليت؟", markup=end_time_kb(), user_id=uid)
        except ValueError:
            send_or_edit(msg.chat.id, "⚠️ أرسل رقماً موجباً.", markup=cancel_kb(), user_id=uid)

    elif state == 'await_et_custom':
        try:
            hours = float(text.strip())
            if hours <= 0:
                raise ValueError
            temp['end_time'] = (datetime.now() + timedelta(hours=hours)).isoformat()
            set_user_state(uid, 'await_join_type', temp)
            send_or_edit(msg.chat.id, "🚪 اختر نظام الانضمام للروليت:\n\n🔐 كابتشا: يحل المستخدم تحققاً بسيطاً قبل التسجيل\n⚡ مباشر: يتسجل المستخدم فوراً بعد التحقق من الاشتراك", markup=join_type_kb(), user_id=uid)
        except ValueError:
            send_or_edit(msg.chat.id, "⚠️ أرسل عدد ساعات صحيح (مثال: 24).", markup=cancel_kb(), user_id=uid)

    elif state == 'await_photo':
        if is_photo:
            temp['photo_id'] = msg.photo[-1].file_id
            del_msg(msg.chat.id, msg.message_id)
            set_user_state(uid, 'await_confirm_pub_r', temp)
            r_data = {
                'text': temp.get('roulette_text', ''),
                'conditional_channel_username': temp.get('cond_ch_username_1', ''),
                'conditional_channel_username_2': temp.get('cond_ch_username_2', ''),
                'winners_count': temp.get('winners_count', 1),
                'max_participants': temp.get('max_participants'),
                'end_time': temp.get('end_time'),
                'photo_id': temp['photo_id'],
                'join_type': temp.get('join_type', 'captcha')
            }
            preview = _build_roulette_preview(r_data, uid)
            send_or_edit(msg.chat.id, preview, markup=confirm_publish_roulette_kb(), user_id=uid)
        else:
            send_or_edit(msg.chat.id, "⚠️ أرسل صورة أو اضغط تخطي.", markup=kb([btn("⏭️ تخطي بدون صورة", cbd="skip_photo", color='green')]), user_id=uid)

    elif state == 'await_contest_title':
        raw = msg.text or msg.caption or ""
        if not raw.strip():
            send_or_edit(msg.chat.id, "⚠️ العنوان فارغ.", markup=cancel_kb(), user_id=uid)
            return
        if contains_link(raw):
            send_or_edit(msg.chat.id, "🚫 يحتوي على روابط!", markup=cancel_kb(), user_id=uid)
            return
        temp['contest_title'] = raw.strip()
        set_user_state(uid, 'await_contest_desc', temp)
        send_or_edit(msg.chat.id, "📝 أرسل وصف المسابقة:", markup=cancel_kb(), user_id=uid)

    elif state == 'await_contest_desc':
        raw = msg.text or msg.caption or ""
        if not raw.strip():
            send_or_edit(msg.chat.id, "⚠️ الوصف فارغ.", markup=cancel_kb(), user_id=uid)
            return
        if contains_link(raw):
            send_or_edit(msg.chat.id, "🚫 يحتوي على روابط!", markup=cancel_kb(), user_id=uid)
            return
        temp['contest_description'] = raw.strip()
        set_user_state(uid, 'await_contest_max_p', temp)
        send_or_edit(msg.chat.id, "👥 الحد الأقصى للمشاركين؟ (رقم)", markup=cancel_kb(), user_id=uid)

    elif state == 'await_contest_max_p':
        try:
            count = int(text.strip())
            if count <= 0:
                raise ValueError
            temp['contest_max_p'] = count
            set_user_state(uid, 'await_contest_ranks', temp)
            send_or_edit(msg.chat.id, "🥇 كم عدد المراكز الفائزة؟ (رقم)", markup=cancel_kb(), user_id=uid)
        except ValueError:
            send_or_edit(msg.chat.id, "⚠️ أرسل رقماً موجباً.", markup=cancel_kb(), user_id=uid)

    elif state == 'await_contest_ranks':
        try:
            ranks = int(text.strip())
            if ranks <= 0 or ranks > 100:
                raise ValueError
            temp['contest_ranks'] = ranks
            set_user_state(uid, 'await_contest_accept', temp)
            send_or_edit(msg.chat.id, "👤 نظام القبول:", markup=contest_creation_kb(), user_id=uid)
        except ValueError:
            send_or_edit(msg.chat.id, "⚠️ أرسل رقماً بين 1 و 100.", markup=cancel_kb(), user_id=uid)

    elif state == 'await_contest_photo':
        if is_photo:
            temp['contest_photo'] = msg.photo[-1].file_id
            del_msg(msg.chat.id, msg.message_id)
            set_user_state(uid, 'await_confirm_pub_c', temp)
            preview = _build_contest_preview(temp)
            send_or_edit(msg.chat.id, preview, markup=confirm_publish_contest_kb(), user_id=uid)
        else:
            send_or_edit(msg.chat.id, "⚠️ أرسل صورة أو اضغط تخطي.", markup=kb([btn("⏭️ تخطي بدون صورة", cbd="skip_contest_photo", color='green')]), user_id=uid)

    elif state == 'await_exclude_cp_id':
        cid = temp.get('exclude_contest_id')
        try:
            tid = int(text.strip())
            conn = get_db()
            try:
                p = conn.execute('SELECT channel_message_id FROM contest_participants WHERE contest_id=? AND user_id=?', (cid, tid)).fetchone()
                if p and p['channel_message_id']:
                    c = get_contest(cid)
                    if c:
                        try:
                            bot.delete_message(c['channel_id'], p['channel_message_id'])
                        except Exception:
                            pass
                conn.execute("UPDATE contest_participants SET status='rejected' WHERE contest_id=? AND user_id=?", (cid, tid))
                conn.commit()
            finally:
                conn.close()
            clear_user_state(uid)
            try:
                send_new(tid, "⚠️ تم استبعادك من المسابقة.")
            except Exception:
                pass
            send_new(msg.chat.id, f"✅ تم استبعاد <code>{tid}</code>")
        except ValueError:
            send_or_edit(msg.chat.id, "⚠️ أرسل آيدي رقمي.", markup=cancel_kb(), user_id=uid)

    else:
        if not text.startswith('/'):
            bot_name = get_bot_name()
            send_or_edit(msg.chat.id, f"👋 أهلاً بك في {bot_name}!\n\nاختر من القائمة:", markup=main_menu_kb(uid), user_id=uid)

def main():
    print("🚀 جاري تشغيل البوت...")
    init_db()
    print("✅ تم تهيئة قاعدة البيانات.")
    migrate_db()
    print("✅ تم فحص قاعدة البيانات.")

    threading.Thread(target=_roulette_timer_worker, daemon=True, name="RouletteTimer").start()
    print("✅ تم تشغيل مؤقت الروليتات.")

    threading.Thread(target=_captcha_cleanup_worker, daemon=True, name="CaptchaCleanup").start()
    print("✅ تم تشغيل منظف الكابتشا.")

    bot_name = get_bot_name()
    print(f"✅ {bot_name} يعمل!\n👤 الأدمن: {ADMIN_ID}\n📢 القناة: {DEVELOPER_CHANNEL}")

    while True:
        try:
            bot.infinity_polling(timeout=25, long_polling_timeout=20, skip_pending=True)
        except ConnectionError:
            print("⚠️ انقطاع شبكة، إعادة الاتصال...")
            time.sleep(3)
        except Exception as e:
            print(f"⚠️ خطأ: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
