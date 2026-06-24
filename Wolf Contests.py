import asyncio
import logging
import sqlite3
import re
import random
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from pyrogram import Client, filters, enums
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, ChatPermissions
)
from pyrogram.errors import (
    UserNotParticipant, ChannelPrivate, ChatAdminRequired,
    FloodWait, UserIsBlocked, PeerIdInvalid, MessageNotModified,
    RPCError
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

API_ID = os.getenv("API_ID", "39162758")
API_HASH = os.getenv("API_HASH", "bbbb9d93724561ec8b8a26cb457eb770")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8307560710:AAFNRpzh141cq7rKt_OmPR0A823dxEaOZVU")
ADMIN_ID = int(os.getenv("ADMIN_ID", 7259620384))

OWNER_CHANNEL = "https://t.me/bshshshkk"
UPDATES_CHANNEL = "https://t.me/bshshshkk"
OWNER_CONTACT = "https://t.me/j49_c"

VOTE_EMOJIS = [
    "❤️", "🔥", "⭐", "🎯", "🏆", "👑", "💎", "✨",
    "🌟", "💥", "🫶🏻", "😈", "💯", "👍", "👏"
]

FORBIDDEN_NAME_KEYWORDS = [
    "http://", "https://", "www.", ".com", ".org", ".net", ".me", ".io", ".xyz",
    "t.me/", "telegram.me/", "bit.ly/", "tinyurl.com/", "goo.gl/", "ow.ly/",
    "@", "/c/", "/joinchat/", "+", "join?", "t.me/+", "telegram.me/+",
    "كسم", "كس", "احا", "بضان", "كذاب", "نصاب", "حرامي", "سرق", "شغل نصب",
    "ياص", "يلعن", "لعنة", "لعنه", "يتناك", "ينيك", "منيوك", "منايك", "خول", "قحبة",
    "كسمك", "زبي امك", "ابوك", "متناك", "خخخخ", "هههه", "سكس", "شرموط", "كس امك",
    "طيزك", "كسك", "زبي", "لص", "السفاح المصري", "السفاحين", "زغرفه", "ڪسم",
    "صلي على النبي", "صلوا على النبي", "عليه وسلم", "بحب النبي", "بتحب النبي",
    "يارب", "ربنا", "اللهم", "استغفر الله", "سبحان الله",
    "الحمد لله", "الله اكبر", "لا اله الا الله", "محمد رسول الله", "الله",
    "ع النبي", "علي النبي", "صلي", "صلي على النبي", "صلي علي النبي",
    "نفسي اكسب", "انا كسبت", "هكسب", "هاخد الجائزة", "راح اجيب",
    "المسابقه", "المسابقة", "انضم", "الي يصوت", "اسكرين", "دب نجوم",
    "صوت لي", "صوتولي", "صوتو", "صوتوا", "صوتوالي", "تصويت", "صوت",
    "انضمام", "شروط", "جوائز", "جائزة", "مكافأة", "جائزه", "مكافاه",
    "جيب اسكرين", "خد اسكرين", "روح اصوت", "روح صوت", "خش صوت",
    "كلو", "كله", "ينضم", "يلحق", "اسرع", "هتخسر", "محتال", "نصب",
    "احتيال", "غش", "خداع", "خدعة", "مخادع", "نصابين", "محتلين",
    "ياعم", "يا جماعه", "يا شباب", "السفاح المصري", "السفاحين",
    "ڪسم جروب السفاح علي بوته"
]

FORBIDDEN_NAME_PATTERNS = [
    r"https?://\S+", r"www\.\S+", r"t\.me/\S+", r"telegram\.me/\S+",
    r"@\w+", r"\S+\.(com|org|net|me|io|xyz)\S*",
    r"joinchat/\S+", r"\+\S+", r"t\.me/\+"
]


class Database:
    def __init__(self, path: str = "wolf_contest_bot.db"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._build_schema()

    def _build_schema(self):
        statements = [
            """CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_banned BOOLEAN DEFAULT 0
            )""",
            """CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                added_by INTEGER,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS user_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                channel_id TEXT UNIQUE,
                channel_username TEXT,
                channel_title TEXT,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_blocked BOOLEAN DEFAULT 0,
                is_voting_channel BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )""",
            """CREATE TABLE IF NOT EXISTS contests (
                contest_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                description TEXT,
                channel_id TEXT,
                channel_username TEXT,
                message_id INTEGER,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                contest_type TEXT DEFAULT 'manual',
                button_url TEXT,
                auto_approve BOOLEAN DEFAULT 1,
                end_date TIMESTAMP,
                winners_count INTEGER DEFAULT 1,
                required_votes INTEGER DEFAULT 0,
                prize_channel TEXT,
                is_advanced BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )""",
            """CREATE TABLE IF NOT EXISTS participants (
                participant_id INTEGER PRIMARY KEY AUTOINCREMENT,
                contest_id INTEGER,
                user_id INTEGER,
                display_name TEXT,
                vote_emoji TEXT,
                votes INTEGER DEFAULT 0,
                message_id INTEGER,
                joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_approved BOOLEAN DEFAULT 1,
                is_winner BOOLEAN DEFAULT 0,
                prize_received BOOLEAN DEFAULT 0,
                UNIQUE(contest_id, user_id),
                FOREIGN KEY (contest_id) REFERENCES contests(contest_id)
            )""",
            """CREATE TABLE IF NOT EXISTS votes (
                vote_id INTEGER PRIMARY KEY AUTOINCREMENT,
                contest_id INTEGER,
                voter_id INTEGER,
                participant_id INTEGER,
                source_channel_id TEXT,
                vote_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(contest_id, voter_id),
                FOREIGN KEY (contest_id) REFERENCES contests(contest_id),
                FOREIGN KEY (participant_id) REFERENCES participants(participant_id)
            )""",
            """CREATE TABLE IF NOT EXISTS forced_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT UNIQUE,
                username TEXT,
                title TEXT,
                invite_link TEXT,
                is_public BOOLEAN,
                added_by INTEGER,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS forced_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id TEXT UNIQUE,
                username TEXT,
                title TEXT,
                invite_link TEXT,
                is_public BOOLEAN,
                added_by INTEGER,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS broadcasts (
                broadcast_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sent_by INTEGER,
                message_type TEXT,
                target_type TEXT,
                message_text TEXT,
                sent_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success_count INTEGER DEFAULT 0,
                fail_count INTEGER DEFAULT 0
            )""",
            """CREATE TABLE IF NOT EXISTS blocked_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE,
                blocked_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                blocked_by INTEGER,
                reason TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS daily_stats (
                date TEXT PRIMARY KEY,
                total_votes INTEGER DEFAULT 0,
                new_users INTEGER DEFAULT 0,
                new_participants INTEGER DEFAULT 0
            )""",
            """CREATE TABLE IF NOT EXISTS manual_participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contest_id INTEGER,
                participant_name TEXT,
                added_by INTEGER,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (contest_id) REFERENCES contests(contest_id),
                FOREIGN KEY (added_by) REFERENCES users(user_id)
            )""",
            """CREATE TABLE IF NOT EXISTS vote_modifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contest_id INTEGER,
                participant_id INTEGER,
                modifier_id INTEGER,
                action TEXT,
                old_votes INTEGER,
                new_votes INTEGER,
                amount INTEGER,
                modification_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (contest_id) REFERENCES contests(contest_id),
                FOREIGN KEY (participant_id) REFERENCES participants(participant_id)
            )""",
            """CREATE TABLE IF NOT EXISTS bot_admin_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT,
                channel_title TEXT,
                channel_link TEXT,
                user_id INTEGER,
                username TEXT,
                first_name TEXT,
                permissions TEXT,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_read BOOLEAN DEFAULT 0
            )""",
            """CREATE TABLE IF NOT EXISTS contest_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contest_id INTEGER,
                participant_name TEXT,
                user_id INTEGER,
                username TEXT,
                first_name TEXT,
                channel_id TEXT,
                channel_title TEXT,
                channel_link TEXT,
                notification_type TEXT,
                is_approved BOOLEAN DEFAULT 1,
                notification_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (contest_id) REFERENCES contests(contest_id)
            )""",
            """CREATE TABLE IF NOT EXISTS channel_control (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT UNIQUE,
                channel_title TEXT,
                channel_username TEXT,
                added_by INTEGER,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                bot_permissions TEXT,
                contest_count INTEGER DEFAULT 0,
                total_votes INTEGER DEFAULT 0,
                subscribers_count INTEGER DEFAULT 0
            )""",
            """CREATE TABLE IF NOT EXISTS manual_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                channel_id TEXT,
                channel_title TEXT,
                participant_name TEXT,
                post_message_id INTEGER,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )""",
            """CREATE TABLE IF NOT EXISTS pending_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contest_id INTEGER,
                participant_id INTEGER,
                user_id INTEGER,
                display_name TEXT,
                channel_id TEXT,
                channel_title TEXT,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending',
                FOREIGN KEY (contest_id) REFERENCES contests(contest_id),
                FOREIGN KEY (participant_id) REFERENCES participants(participant_id)
            )""",
            """CREATE TABLE IF NOT EXISTS daily_stats_full (
                date TEXT PRIMARY KEY,
                total_votes INTEGER DEFAULT 0,
                new_users INTEGER DEFAULT 0,
                new_participants INTEGER DEFAULT 0,
                contests_ended INTEGER DEFAULT 0,
                winners_count INTEGER DEFAULT 0
            )"""
        ]
        for stmt in statements:
            self.cursor.execute(stmt)
        self.conn.commit()

    def register_user(self, user_id: int, username: str, first_name: str, last_name: str = "") -> bool:
        try:
            self.cursor.execute(
                "INSERT OR IGNORE INTO users (user_id, username, first_name, last_name) VALUES (?, ?, ?, ?)",
                (user_id, username, first_name, last_name)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"register_user error: {e}")
            return False

    def update_user_activity(self, user_id: int):
        self.cursor.execute(
            "UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE user_id = ?",
            (user_id,)
        )
        self.conn.commit()

    def ban_user(self, user_id: int, blocked_by: int, reason: str = ""):
        self.cursor.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
        self.cursor.execute(
            "INSERT OR REPLACE INTO blocked_users (user_id, blocked_by, reason) VALUES (?, ?, ?)",
            (user_id, blocked_by, reason)
        )
        self.conn.commit()

    def unban_user(self, user_id: int):
        self.cursor.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))
        self.cursor.execute("DELETE FROM blocked_users WHERE user_id = ?", (user_id,))
        self.conn.commit()

    def is_user_banned(self, user_id: int) -> bool:
        self.cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        return bool(result and result[0] == 1)

    def get_total_users(self) -> int:
        return self.cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    def get_today_users(self) -> int:
        today = datetime.now().strftime("%Y-%m-%d")
        return self.cursor.execute(
            "SELECT COUNT(*) FROM users WHERE DATE(joined_date) = DATE(?)", (today,)
        ).fetchone()[0]

    def get_banned_users_count(self) -> int:
        return self.cursor.execute("SELECT COUNT(*) FROM users WHERE is_banned = 1").fetchone()[0]

    def get_user(self, user_id: int):
        return self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()

    def get_all_users(self):
        return self.cursor.execute(
            "SELECT user_id, username, first_name, joined_date FROM users ORDER BY joined_date DESC"
        ).fetchall()

    def get_blocked_users(self):
        return self.cursor.execute("""
            SELECT bu.user_id, bu.blocked_by, bu.blocked_date, bu.reason, u.username, u.first_name
            FROM blocked_users bu
            LEFT JOIN users u ON bu.user_id = u.user_id
            ORDER BY bu.blocked_date DESC
        """).fetchall()

    def add_admin(self, user_id: int, added_by: int):
        self.cursor.execute(
            "INSERT OR REPLACE INTO admins (user_id, added_by) VALUES (?, ?)",
            (user_id, added_by)
        )
        self.conn.commit()

    def remove_admin(self, user_id: int):
        self.cursor.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        self.conn.commit()

    def is_admin(self, user_id: int) -> bool:
        if user_id == ADMIN_ID:
            return True
        return self.cursor.execute(
            "SELECT 1 FROM admins WHERE user_id = ?", (user_id,)
        ).fetchone() is not None

    def get_all_admins(self):
        return self.cursor.execute("""
            SELECT a.user_id, a.added_by, a.added_date, u.username, u.first_name
            FROM admins a LEFT JOIN users u ON a.user_id = u.user_id
        """).fetchall()

    def add_user_channel(self, user_id: int, channel_id: str, channel_username: str, channel_title: str) -> bool:
        try:
            self.cursor.execute(
                "INSERT OR REPLACE INTO user_channels (user_id, channel_id, channel_username, channel_title) VALUES (?, ?, ?, ?)",
                (user_id, channel_id, channel_username, channel_title)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"add_user_channel error: {e}")
            return False

    def set_voting_channel(self, channel_id: str, is_voting: bool = True):
        self.cursor.execute(
            "UPDATE user_channels SET is_voting_channel = ? WHERE channel_id = ?",
            (is_voting, channel_id)
        )
        self.conn.commit()

    def get_voting_channel(self, user_id: int):
        return self.cursor.execute(
            "SELECT * FROM user_channels WHERE user_id = ? AND is_voting_channel = 1 AND is_blocked = 0",
            (user_id,)
        ).fetchone()

    def get_user_channels(self, user_id: int):
        return self.cursor.execute(
            "SELECT * FROM user_channels WHERE user_id = ? AND is_blocked = 0", (user_id,)
        ).fetchall()

    def get_channel_by_id(self, channel_id: str):
        return self.cursor.execute(
            "SELECT * FROM user_channels WHERE channel_id = ?", (channel_id,)
        ).fetchone()

    def get_all_channels_count(self) -> int:
        return self.cursor.execute(
            "SELECT COUNT(DISTINCT channel_id) FROM user_channels WHERE is_blocked = 0"
        ).fetchone()[0]

    def block_channel(self, channel_id: str):
        self.cursor.execute("UPDATE user_channels SET is_blocked = 1 WHERE channel_id = ?", (channel_id,))
        self.conn.commit()

    def unblock_channel(self, channel_id: str):
        self.cursor.execute("UPDATE user_channels SET is_blocked = 0 WHERE channel_id = ?", (channel_id,))
        self.conn.commit()

    def is_channel_blocked(self, channel_id: str) -> bool:
        result = self.cursor.execute(
            "SELECT is_blocked FROM user_channels WHERE channel_id = ?", (channel_id,)
        ).fetchone()
        return bool(result and result[0] == 1)

    def create_contest(
        self, user_id: int, description: str, channel_id: str, channel_username: str,
        message_id: int, contest_type: str = "manual", button_url: str = None,
        auto_approve: bool = True, end_date: datetime = None, winners_count: int = 1,
        required_votes: int = 0, prize_channel: str = None, is_advanced: bool = False
    ) -> Optional[int]:
        try:
            self.cursor.execute("""
                INSERT INTO contests (
                    user_id, description, channel_id, channel_username, message_id,
                    contest_type, button_url, auto_approve, end_date, winners_count,
                    required_votes, prize_channel, is_advanced
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, description, channel_id, channel_username, message_id,
                contest_type, button_url, auto_approve, end_date, winners_count,
                required_votes, prize_channel, is_advanced
            ))
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            logger.error(f"create_contest error: {e}")
            return None

    def end_contest(self, contest_id: int):
        self.cursor.execute("UPDATE contests SET is_active = 0 WHERE contest_id = ?", (contest_id,))
        self.conn.commit()

    def delete_contest(self, contest_id: int):
        for tbl in ["votes", "participants", "manual_participants", "vote_modifications", "pending_posts"]:
            self.cursor.execute(f"DELETE FROM {tbl} WHERE contest_id = ?", (contest_id,))
        self.cursor.execute("DELETE FROM contests WHERE contest_id = ?", (contest_id,))
        self.conn.commit()

    def delete_channel_contests(self, channel_id: str):
        for c in self.get_contest_by_channel_all(channel_id):
            self.delete_contest(c[0])

    def get_today_contests(self) -> int:
        today = datetime.now().strftime("%Y-%m-%d")
        return self.cursor.execute(
            "SELECT COUNT(*) FROM contests WHERE DATE(created_date) = DATE(?)", (today,)
        ).fetchone()[0]

    def get_user_contests(self, user_id: int):
        return self.cursor.execute(
            "SELECT * FROM contests WHERE user_id = ? AND is_active = 1 ORDER BY created_date DESC",
            (user_id,)
        ).fetchall()

    def get_user_all_contests(self, user_id: int):
        return self.cursor.execute(
            "SELECT * FROM contests WHERE user_id = ? ORDER BY created_date DESC", (user_id,)
        ).fetchall()

    def get_all_contests(self):
        return self.cursor.execute("SELECT * FROM contests ORDER BY created_date DESC").fetchall()

    def get_contest_by_id(self, contest_id: int):
        return self.cursor.execute(
            "SELECT * FROM contests WHERE contest_id = ?", (contest_id,)
        ).fetchone()

    def get_contest_by_channel(self, channel_id: str):
        return self.cursor.execute(
            "SELECT * FROM contests WHERE channel_id = ? AND is_active = 1", (channel_id,)
        ).fetchone()

    def get_contest_by_channel_all(self, channel_id: str):
        return self.cursor.execute(
            "SELECT * FROM contests WHERE channel_id = ?", (channel_id,)
        ).fetchall()

    def get_active_contests(self):
        return self.cursor.execute(
            "SELECT * FROM contests WHERE is_active = 1 ORDER BY created_date DESC"
        ).fetchall()

    def get_contests_to_end(self):
        now = datetime.now()
        return self.cursor.execute(
            "SELECT * FROM contests WHERE is_active = 1 AND end_date IS NOT NULL AND end_date <= ?", (now,)
        ).fetchall()

    def get_contest_participants_count(self, contest_id: int) -> int:
        return self.cursor.execute(
            "SELECT COUNT(*) FROM participants WHERE contest_id = ?", (contest_id,)
        ).fetchone()[0]

    def add_participant(self, contest_id: int, user_id: int, display_name: str, message_id: int = None, is_approved: bool = True) -> Optional[int]:
        try:
            vote_emoji = random.choice(VOTE_EMOJIS)
            self.cursor.execute("""
                INSERT OR IGNORE INTO participants
                (contest_id, user_id, display_name, vote_emoji, message_id, is_approved)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (contest_id, user_id, display_name, vote_emoji, message_id, is_approved))
            self.conn.commit()
            result = self.cursor.execute(
                "SELECT participant_id FROM participants WHERE contest_id = ? AND user_id = ?",
                (contest_id, user_id)
            ).fetchone()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"add_participant error: {e}")
            return None

    def get_participant(self, participant_id: int):
        return self.cursor.execute(
            "SELECT * FROM participants WHERE participant_id = ?", (participant_id,)
        ).fetchone()

    def get_participant_by_user(self, contest_id: int, user_id: int):
        return self.cursor.execute(
            "SELECT * FROM participants WHERE contest_id = ? AND user_id = ?",
            (contest_id, user_id)
        ).fetchone()

    def get_participant_by_message(self, channel_id: str, message_id: int):
        return self.cursor.execute("""
            SELECT p.* FROM participants p
            JOIN contests c ON p.contest_id = c.contest_id
            WHERE c.channel_id = ? AND p.message_id = ?
        """, (channel_id, message_id)).fetchone()

    def get_contest_participants(self, contest_id: int):
        return self.cursor.execute(
            "SELECT * FROM participants WHERE contest_id = ? AND is_approved = 1 ORDER BY votes DESC",
            (contest_id,)
        ).fetchall()

    def get_pending_participants(self, contest_id: int):
        return self.cursor.execute(
            "SELECT * FROM participants WHERE contest_id = ? AND is_approved = 0 ORDER BY joined_date DESC",
            (contest_id,)
        ).fetchall()

    def approve_participant(self, participant_id: int):
        self.cursor.execute(
            "UPDATE participants SET is_approved = 1 WHERE participant_id = ?", (participant_id,)
        )
        self.conn.commit()

    def reject_participant(self, participant_id: int):
        self.cursor.execute("DELETE FROM participants WHERE participant_id = ?", (participant_id,))
        self.conn.commit()

    def update_participant_votes(self, participant_id: int, amount: int = 1):
        self.cursor.execute(
            "UPDATE participants SET votes = votes + ? WHERE participant_id = ?",
            (amount, participant_id)
        )
        self.conn.commit()

    def get_participant_votes(self, participant_id: int) -> int:
        result = self.cursor.execute(
            "SELECT votes FROM participants WHERE participant_id = ?", (participant_id,)
        ).fetchone()
        return result[0] if result else 0

    def modify_participant_votes(self, participant_id: int, amount: int, modifier_id: int, action: str) -> bool:
        participant = self.get_participant(participant_id)
        if not participant:
            return False
        old_votes = participant[5]
        new_votes = max(0, old_votes + amount)
        final_amount = new_votes - old_votes
        self.cursor.execute(
            "UPDATE participants SET votes = ? WHERE participant_id = ?", (new_votes, participant_id)
        )
        self.cursor.execute("""
            INSERT INTO vote_modifications (contest_id, participant_id, modifier_id, action, old_votes, new_votes, amount)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (participant[1], participant_id, modifier_id, action, old_votes, new_votes, final_amount))
        self.conn.commit()
        return True

    def update_participant_message_id(self, participant_id: int, message_id: int):
        self.cursor.execute(
            "UPDATE participants SET message_id = ? WHERE participant_id = ?",
            (message_id, participant_id)
        )
        self.conn.commit()

    def get_participant_by_name_and_contest(self, contest_id: int, display_name: str):
        return self.cursor.execute(
            "SELECT * FROM participants WHERE contest_id = ? AND display_name = ?",
            (contest_id, display_name)
        ).fetchone()

    def mark_participant_as_winner(self, participant_id: int):
        self.cursor.execute(
            "UPDATE participants SET is_winner = 1 WHERE participant_id = ?", (participant_id,)
        )
        self.conn.commit()

    def get_contest_winners(self, contest_id: int):
        return self.cursor.execute(
            "SELECT * FROM participants WHERE contest_id = ? AND is_winner = 1 ORDER BY votes DESC",
            (contest_id,)
        ).fetchall()

    def check_and_mark_winners(self, contest_id: int) -> list:
        contest = self.get_contest_by_id(contest_id)
        if not contest:
            return []
        winners_count = contest[12] or 1
        required_votes = contest[13] or 0
        participants = self.get_contest_participants(contest_id)
        if required_votes > 0:
            winners = [p for p in participants if p[5] >= required_votes]
        else:
            winners = participants[:winners_count]
        for p in winners:
            self.mark_participant_as_winner(p[0])
        return winners

    def add_vote(self, contest_id: int, voter_id: int, participant_id: int, source_channel_id: str = "") -> bool:
        try:
            existing = self.cursor.execute(
                "SELECT vote_id FROM votes WHERE contest_id = ? AND voter_id = ?",
                (contest_id, voter_id)
            ).fetchone()
            if existing:
                return False
            self.cursor.execute(
                "INSERT INTO votes (contest_id, voter_id, participant_id, source_channel_id) VALUES (?, ?, ?, ?)",
                (contest_id, voter_id, participant_id, source_channel_id)
            )
            self.update_participant_votes(participant_id)
            today = datetime.now().strftime("%Y-%m-%d")
            self.cursor.execute("INSERT OR IGNORE INTO daily_stats (date) VALUES (?)", (today,))
            self.cursor.execute(
                "UPDATE daily_stats SET total_votes = total_votes + 1 WHERE date = ?", (today,)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"add_vote error: {e}")
            return False

    def has_voted(self, contest_id: int, voter_id: int) -> bool:
        return self.cursor.execute(
            "SELECT vote_id FROM votes WHERE contest_id = ? AND voter_id = ?",
            (contest_id, voter_id)
        ).fetchone() is not None

    def get_today_votes(self) -> int:
        today = datetime.now().strftime("%Y-%m-%d")
        result = self.cursor.execute(
            "SELECT total_votes FROM daily_stats WHERE date = ?", (today,)
        ).fetchone()
        return result[0] if result else 0

    def get_contest_votes_count(self, contest_id: int) -> int:
        return self.cursor.execute(
            "SELECT COUNT(*) FROM votes WHERE contest_id = ?", (contest_id,)
        ).fetchone()[0]

    def get_today_participants_count(self) -> int:
        today = datetime.now().strftime("%Y-%m-%d")
        return self.cursor.execute(
            "SELECT COUNT(*) FROM participants WHERE DATE(joined_date) = DATE(?)", (today,)
        ).fetchone()[0]

    def add_forced_channel(self, channel_id: str, username: str, title: str, invite_link: str, is_public: bool, added_by: int) -> bool:
        try:
            self.cursor.execute("""
                INSERT OR REPLACE INTO forced_channels
                (channel_id, username, title, invite_link, is_public, added_by)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (channel_id, username, title, invite_link, is_public, added_by))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"add_forced_channel error: {e}")
            return False

    def remove_forced_channel(self, channel_id: str):
        self.cursor.execute("DELETE FROM forced_channels WHERE channel_id = ?", (channel_id,))
        self.conn.commit()

    def get_forced_channels(self, is_public: bool = None):
        if is_public is not None:
            return self.cursor.execute(
                "SELECT * FROM forced_channels WHERE is_public = ?", (is_public,)
            ).fetchall()
        return self.cursor.execute("SELECT * FROM forced_channels").fetchall()

    def get_forced_channels_count(self) -> int:
        return self.cursor.execute("SELECT COUNT(*) FROM forced_channels").fetchone()[0]

    def add_forced_group(self, group_id: str, username: str, title: str, invite_link: str, is_public: bool, added_by: int) -> bool:
        try:
            self.cursor.execute("""
                INSERT OR REPLACE INTO forced_groups
                (group_id, username, title, invite_link, is_public, added_by)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (group_id, username, title, invite_link, is_public, added_by))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"add_forced_group error: {e}")
            return False

    def remove_forced_group(self, group_id: str):
        self.cursor.execute("DELETE FROM forced_groups WHERE group_id = ?", (group_id,))
        self.conn.commit()

    def get_forced_groups(self, is_public: bool = None):
        if is_public is not None:
            return self.cursor.execute(
                "SELECT * FROM forced_groups WHERE is_public = ?", (is_public,)
            ).fetchall()
        return self.cursor.execute("SELECT * FROM forced_groups").fetchall()

    def get_forced_groups_count(self) -> int:
        return self.cursor.execute("SELECT COUNT(*) FROM forced_groups").fetchone()[0]

    def add_broadcast(self, sent_by: int, message_type: str, target_type: str, message_text: str, success_count: int, fail_count: int) -> int:
        self.cursor.execute("""
            INSERT INTO broadcasts (sent_by, message_type, target_type, message_text, success_count, fail_count)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (sent_by, message_type, target_type, message_text, success_count, fail_count))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_recent_broadcasts(self, limit: int = 10):
        return self.cursor.execute(
            "SELECT * FROM broadcasts ORDER BY sent_date DESC LIMIT ?", (limit,)
        ).fetchall()

    def add_bot_admin_notification(self, channel_id: str, channel_title: str, channel_link: str, user_id: int, username: str, first_name: str, permissions: str) -> bool:
        try:
            self.cursor.execute("""
                INSERT INTO bot_admin_notifications
                (channel_id, channel_title, channel_link, user_id, username, first_name, permissions)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (channel_id, channel_title, channel_link, user_id, username, first_name, permissions))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"add_bot_admin_notification error: {e}")
            return False

    def get_bot_admin_notifications(self, limit: int = 20, unread_only: bool = False):
        if unread_only:
            return self.cursor.execute(
                "SELECT * FROM bot_admin_notifications WHERE is_read = 0 ORDER BY added_date DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return self.cursor.execute(
            "SELECT * FROM bot_admin_notifications ORDER BY added_date DESC LIMIT ?", (limit,)
        ).fetchall()

    def mark_notifications_read(self):
        self.cursor.execute("UPDATE bot_admin_notifications SET is_read = 1 WHERE is_read = 0")
        self.conn.commit()

    def clear_bot_admin_notifications(self):
        self.cursor.execute("DELETE FROM bot_admin_notifications")
        self.conn.commit()

    def get_unread_notifications_count(self) -> int:
        return self.cursor.execute(
            "SELECT COUNT(*) FROM bot_admin_notifications WHERE is_read = 0"
        ).fetchone()[0]

    def add_contest_notification(self, contest_id: int, participant_name: str, user_id: int, username: str, first_name: str, channel_id: str, channel_title: str, channel_link: str, notification_type: str = "new_participant", is_approved: bool = True) -> bool:
        try:
            self.cursor.execute("""
                INSERT INTO contest_notifications
                (contest_id, participant_name, user_id, username, first_name, channel_id,
                 channel_title, channel_link, notification_type, is_approved)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (contest_id, participant_name, user_id, username, first_name, channel_id,
                  channel_title, channel_link, notification_type, is_approved))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"add_contest_notification error: {e}")
            return False

    def add_channel_control(self, channel_id: str, channel_title: str, channel_username: str, added_by: int, bot_permissions: str = "") -> bool:
        try:
            self.cursor.execute("""
                INSERT OR REPLACE INTO channel_control
                (channel_id, channel_title, channel_username, added_by, bot_permissions)
                VALUES (?, ?, ?, ?, ?)
            """, (channel_id, channel_title, channel_username, added_by, bot_permissions))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"add_channel_control error: {e}")
            return False

    def update_channel_stats(self, channel_id: str, contest_count: int = None, total_votes: int = None, subscribers_count: int = None):
        updates, params = [], []
        if contest_count is not None:
            updates.append("contest_count = contest_count + ?")
            params.append(contest_count)
        if total_votes is not None:
            updates.append("total_votes = total_votes + ?")
            params.append(total_votes)
        if subscribers_count is not None:
            updates.append("subscribers_count = ?")
            params.append(subscribers_count)
        if updates:
            params.append(channel_id)
            self.cursor.execute(
                f"UPDATE channel_control SET {', '.join(updates)} WHERE channel_id = ?", params
            )
            self.conn.commit()

    def get_channel_control(self, channel_id: str):
        return self.cursor.execute(
            "SELECT * FROM channel_control WHERE channel_id = ?", (channel_id,)
        ).fetchone()

    def get_all_channels_control(self):
        return self.cursor.execute(
            "SELECT * FROM channel_control ORDER BY added_date DESC"
        ).fetchall()

    def remove_channel_control(self, channel_id: str):
        self.cursor.execute("DELETE FROM channel_control WHERE channel_id = ?", (channel_id,))
        self.conn.commit()

    def add_manual_post(self, user_id: int, channel_id: str, channel_title: str, participant_name: str, post_message_id: int) -> bool:
        try:
            self.cursor.execute("""
                INSERT INTO manual_posts (user_id, channel_id, channel_title, participant_name, post_message_id)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, channel_id, channel_title, participant_name, post_message_id))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"add_manual_post error: {e}")
            return False

    def get_daily_stats_full(self, date: str = None):
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        return self.cursor.execute("SELECT * FROM daily_stats WHERE date = ?", (date,)).fetchone()

    def get_weekly_stats(self):
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        return self.cursor.execute("""
            SELECT SUM(total_votes), SUM(new_users), SUM(new_participants)
            FROM daily_stats WHERE date >= ?
        """, (week_ago,)).fetchone()

    def get_top_channels(self, limit: int = 10):
        return self.cursor.execute("""
            SELECT channel_title, contest_count, total_votes, subscribers_count
            FROM channel_control
            ORDER BY contest_count DESC, total_votes DESC LIMIT ?
        """, (limit,)).fetchall()

    def get_top_participants(self, limit: int = 10):
        return self.cursor.execute("""
            SELECT p.display_name, p.votes, c.channel_title
            FROM participants p
            JOIN contests c ON p.contest_id = c.contest_id
            WHERE p.is_approved = 1
            ORDER BY p.votes DESC LIMIT ?
        """, (limit,)).fetchall()


db = Database()
bot = Client("wolf_contest_session", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

session_states: Dict[int, dict] = {}


def is_forbidden_name(text: str) -> bool:
    lower = text.lower().strip()
    for kw in FORBIDDEN_NAME_KEYWORDS:
        if kw.lower() in lower:
            return True
    for pat in FORBIDDEN_NAME_PATTERNS:
        if re.search(pat, lower, re.IGNORECASE):
            return True
    stripped = text.strip()
    if len(stripped) < 2 or len(stripped) > 50:
        return True
    if stripped.isdigit() or not stripped:
        return True
    return False


def build_keyboard(rows: list) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(rows)


def btn(text: str, callback: str = None, url: str = None, style: str = None) -> InlineKeyboardButton:
    if url:
        return InlineKeyboardButton(text, url=url, style=style)
    return InlineKeyboardButton(text, callback_data=callback, style=style)


def back_btn(target: str) -> InlineKeyboardButton:
    return btn("↩️ رجوع", callback=target, style="primary")


def parse_channel_link(link: str) -> Optional[dict]:
    try:
        link = link.strip()
        if "joinchat/" in link or link.startswith("+"):
            parts = link.split("/")
            return {"type": "invite", "id": parts[-1]}
        if link.startswith("https://t.me/"):
            username = link.split("/")[-1]
            return {"type": "username", "id": username}
        if link.startswith("t.me/"):
            username = link.split("/")[-1]
            return {"type": "username", "id": username}
        if link.startswith("@"):
            return {"type": "username", "id": link[1:]}
        return {"type": "username", "id": link}
    except Exception:
        return None


def parse_message_link(link: str) -> Optional[dict]:
    try:
        if "t.me/" in link:
            parts = link.split("/")
            if len(parts) >= 5:
                return {"username": parts[3], "message_id": int(parts[4]), "full_link": link}
    except Exception:
        pass
    return None


async def resolve_channel(link: str):
    info = parse_channel_link(link)
    if not info:
        return None
    if info["type"] == "invite":
        return await bot.join_chat(f"https://t.me/joinchat/{info['id']}")
    return await bot.get_chat(info["id"])


async def resolve_user(input_str: str):
    try:
        if input_str.isdigit():
            return await bot.get_users(int(input_str))
        target = input_str[1:] if input_str.startswith("@") else input_str
        return await bot.get_users(target)
    except Exception as e:
        logger.error(f"resolve_user error: {e}")
        return None


async def verify_membership(user_id: int, channel_id: str) -> bool:
    try:
        member = await bot.get_chat_member(int(channel_id), user_id)
        return member.status not in [enums.ChatMemberStatus.LEFT, enums.ChatMemberStatus.BANNED]
    except Exception:
        return False


async def verify_all_memberships(user_id: int) -> Tuple[bool, List]:
    missing = []
    for ch in db.get_forced_channels():
        if not await verify_membership(user_id, ch[1]):
            missing.append({"type": "channel", "title": ch[3], "invite_link": ch[4], "is_public": ch[5]})
    for grp in db.get_forced_groups():
        if not await verify_membership(user_id, grp[1]):
            missing.append({"type": "group", "title": grp[3], "invite_link": grp[4], "is_public": grp[5]})
    return len(missing) == 0, missing


async def is_bot_admin(channel_id: str) -> bool:
    try:
        member = await bot.get_chat_member(int(channel_id), (await bot.get_me()).id)
        return member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]
    except Exception:
        return False


async def is_user_admin_in_channel(user_id: int, channel_id: str) -> bool:
    try:
        member = await bot.get_chat_member(int(channel_id), user_id)
        return member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]
    except Exception:
        return False


async def get_bot_permissions_text(channel_id: str) -> str:
    try:
        me = (await bot.get_me()).id
        member = await bot.get_chat_member(int(channel_id), me)
        if member.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
            return "غير مشرف"
        perms = member.privileges
        labels = {
            "can_post_messages": "نشر الرسائل",
            "can_edit_messages": "تعديل الرسائل",
            "can_delete_messages": "حذف الرسائل",
            "can_restrict_members": "تقييد الأعضاء",
            "can_promote_members": "ترقية الأعضاء",
            "can_change_info": "تغيير المعلومات",
            "can_invite_users": "دعوة المستخدمين",
            "can_pin_messages": "تثبيت الرسائل",
            "can_manage_video_chats": "إدارة المكالمات",
            "can_manage_chat": "إدارة الدردشة",
        }
        active = [label for attr, label in labels.items() if getattr(perms, attr, False)]
        return "، ".join(active) if active else "لا توجد صلاحيات"
    except Exception:
        return "غير معروف"


async def get_channel_subscriber_count(channel_id: str) -> int:
    try:
        chat = await bot.get_chat(int(channel_id))
        return getattr(chat, "members_count", 0) or 0
    except Exception:
        return 0


async def get_channel_url(channel_id: str, channel_username: str = None) -> str:
    try:
        if channel_username:
            return f"https://t.me/{channel_username}"
        chat = await bot.get_chat(int(channel_id))
        if chat.username:
            return f"https://t.me/{chat.username}"
        invite = await bot.create_chat_invite_link(chat.id, member_limit=1)
        return invite.invite_link
    except Exception:
        return f"قناة خاصة (ID: {channel_id})"


async def safe_edit(cb: CallbackQuery, text: str, keyboard: InlineKeyboardMarkup = None):
    try:
        await cb.edit_message_text(text, reply_markup=keyboard)
    except MessageNotModified:
        pass
    except Exception as e:
        logger.error(f"safe_edit error: {e}")


async def update_vote_button(participant_id: int, channel_id: str, message_id: int):
    try:
        participant = db.get_participant(participant_id)
        if not participant:
            return False
        contest = db.get_contest_by_id(participant[1])
        if not contest:
            return False
        votes = participant[5]
        emoji = participant[4]
        if contest[9]:
            join_url = contest[9]
        else:
            me = await bot.get_me()
            join_url = f"https://t.me/{me.username}?start=join_{contest[0]}_{contest[3]}"
        keyboard = build_keyboard([
            [btn(f"{emoji} تصويت ({votes})", callback=f"vote_direct_{contest[0]}_{participant_id}", style="primary")],
            [btn("🎯 المشاركة في المسابقة", url=join_url, style="primary")]
        ])
        await bot.edit_message_reply_markup(int(channel_id), message_id, reply_markup=keyboard)
        return True
    except MessageNotModified:
        return True
    except Exception as e:
        logger.error(f"update_vote_button error: {e}")
        return False


async def apply_vote_modification(participant_id: int, amount: int, modifier_id: int, action: str) -> Tuple[bool, str]:
    participant = db.get_participant(participant_id)
    if not participant:
        return False, "❌ المشارك غير موجود"
    success = db.modify_participant_votes(participant_id, amount, modifier_id, action)
    if success:
        if participant[6]:
            contest = db.get_contest_by_id(participant[1])
            if contest:
                await update_vote_button(participant_id, contest[3], participant[6])
        verb = "إضافة" if amount > 0 else "خصم"
        return True, f"✅ تم {verb} {abs(amount)} صوت للمشارك {participant[3]}"
    return False, "❌ فشلت العملية"


async def find_participant_by_message_link(link: str):
    info = parse_message_link(link)
    if not info:
        return None, "❌ رابط المنشور غير صحيح"
    try:
        chat = await bot.get_chat(f"@{info['username']}")
        msg_id = info["message_id"]
        participant = db.get_participant_by_message(str(chat.id), msg_id)
        if participant:
            return participant, None
        try:
            msg = await bot.get_messages(chat.id, msg_id)
            if msg.text:
                for line in msg.text.split("\n"):
                    name_match = re.search(r"\*\*(.*?)\*\*", line)
                    if name_match:
                        name = name_match.group(1).strip()
                        contest = db.get_contest_by_channel(str(chat.id))
                        if contest:
                            participant = db.get_participant_by_name_and_contest(contest[0], name)
                            if participant:
                                return participant, None
        except Exception:
            pass
        return None, "❌ لم أتمكن من العثور على المشارك"
    except Exception as e:
        return None, f"❌ خطأ: {e}"


async def notify_admin_channel_added(channel_id: str, channel_title: str, user_id: int, username: str, first_name: str):
    try:
        perms = await get_bot_permissions_text(channel_id)
        link = await get_channel_url(channel_id)
        msg = (
            f"🔔 **تنبيه: البوت أصبح مشرفاً في قناة جديدة**\n\n"
            f"📢 **القناة:** {channel_title}\n"
            f"🆔 `{channel_id}`\n🔗 {link}\n\n"
            f"👤 **المالك:** {first_name} (@{username or 'بدون'})\n"
            f"🆔 `{user_id}`\n\n"
            f"🛠️ **الصلاحيات:** {perms}\n"
            f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        db.add_bot_admin_notification(channel_id, channel_title, link, user_id, username, first_name, perms)
        await bot.send_message(ADMIN_ID, msg)
        for admin in db.get_all_admins():
            if admin[0] != user_id:
                try:
                    await bot.send_message(admin[0], msg)
                except Exception:
                    pass
    except Exception as e:
        logger.error(f"notify_admin_channel_added error: {e}")


async def notify_contest_owner_participant(contest_id: int, participant_name: str, user_id: int, username: str, first_name: str, channel_id: str, is_approved: bool = True):
    try:
        contest = db.get_contest_by_id(contest_id)
        if not contest:
            return
        owner_id = contest[1]
        link = await get_channel_url(channel_id, contest[4])
        if is_approved:
            msg = (
                f"🔔 **مشارك جديد في مسابقتك**\n\n"
                f"👤 {participant_name} (@{username or 'بدون'})\n"
                f"🆔 `{user_id}`\n📢 {link}\n"
                f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            db.add_contest_notification(contest_id, participant_name, user_id, username, first_name, channel_id, contest[4] or "", link, "new_participant", True)
            await bot.send_message(owner_id, msg)
        else:
            msg = (
                f"🔔 **طلب مشاركة يحتاج موافقتك**\n\n"
                f"👤 {participant_name} (@{username or 'بدون'})\n"
                f"🆔 `{user_id}`\n📢 {link}\n"
                f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"اختر موافقة أو رفض:"
            )
            keyboard = build_keyboard([[
                btn("✅ موافقة", callback=f"approve_participant_{contest_id}_{user_id}", style="success"),
                btn("❌ رفض", callback=f"reject_participant_{contest_id}_{user_id}", style="danger")
            ]])
            db.add_contest_notification(contest_id, participant_name, user_id, username, first_name, channel_id, contest[4] or "", link, "new_participant", False)
            await bot.send_message(owner_id, msg, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"notify_contest_owner_participant error: {e}")


async def post_participant_to_channel(contest_id: int, participant_id: int, channel_id: str, contest_url: str) -> Optional[int]:
    participant = db.get_participant(participant_id)
    if not participant:
        return None
    emoji = participant[4]
    text = f"👤 **{participant[3]}** {emoji}\n\n👍 للتصويت اضغط الزر"
    keyboard = build_keyboard([
        [btn(f"{emoji} تصويت (0)", callback=f"vote_direct_{contest_id}_{participant_id}", style="primary")],
        [btn("🎯 المشاركة", url=contest_url, style="primary")]
    ])
    try:
        sent = await bot.send_message(int(channel_id), text, reply_markup=keyboard)
        db.update_participant_message_id(participant_id, sent.id)
        return sent.id
    except Exception as e:
        logger.error(f"post_participant_to_channel error: {e}")
        return None


async def auto_end_expired_contests() -> int:
    ended = 0
    for contest in db.get_contests_to_end():
        contest_id = contest[0]
        channel_id = contest[3]
        winners = db.check_and_mark_winners(contest_id)
        db.end_contest(contest_id)
        ended += 1
        msg = f"🎉 **انتهت المسابقة!**\n\n✨ **الفائزون:**\n"
        for i, w in enumerate(winners, 1):
            msg += f"{i}. **{w[3]}** — {w[5]} صوت\n"
        msg += f"\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n✨ شكراً لجميع المشاركين!"
        try:
            await bot.send_message(int(channel_id), msg)
        except Exception as e:
            logger.error(f"auto_end channel notify error: {e}")
        if contest[14]:
            for w in winners:
                if w[2] != 0:
                    try:
                        await bot.send_message(
                            w[2],
                            f"🎉 **مبروك! فزت في المسابقة!**\n\n"
                            f"🎯 {contest[2][:100]}\n"
                            f"👤 {w[3]}\n🗳️ {w[5]} صوت\n\n"
                            f"🎁 قناة الجوائز: {contest[14]}"
                        )
                    except Exception:
                        pass
    return ended


async def send_forced_sub_message(target, missing: list):
    text = "🔒 يجب الاشتراك في القنوات التالية أولاً:\n\n"
    btns = []
    for item in missing[:5]:
        label = "عامة" if item["is_public"] else "خاصة"
        btns.append([btn(f"📢 {item['title']} ({label})", url=item["invite_link"], style="primary")])
    btns.append([btn("✅ تحقق من الاشتراك", callback="check_subscription", style="primary")])
    keyboard = build_keyboard(btns)
    if isinstance(target, Message):
        await target.reply(text, reply_markup=keyboard)
    else:
        await safe_edit(target, text, keyboard)


async def send_main_menu(target):
    user_id = target.from_user.id if hasattr(target, "from_user") else None
    text = "🎯 **بوت المسابقات**\n\nاختر من الأدوات أدناه:"
    rows = [
        [btn("👥 نشر منشور تصويت", callback="add_manual_participant", style="primary")],
        [btn("📢 تعيين قناة تصويت", callback="create_voting_post", style="primary"), btn("🎯 إنشاء مسابقة", callback="create_contest_menu", style="primary")],
        [btn("🏆 مسابقاتي", callback="my_contests", style="primary"), btn("⚙️ إعدادات", callback="bot_settings", style="primary")],
        [btn("➕ إضافة أصوات", callback="user_add_votes", style="success"), btn("➖ خصم أصوات", callback="user_remove_votes", style="danger")],
        [btn("📖 دليل الاستخدام", callback="bot_guide", style="primary"), btn("📠 المميزات", callback="bot_features", style="primary")],
        [btn("📢 قناة المطور", url=OWNER_CHANNEL, style="primary"), btn("📢 التحديثات", url=UPDATES_CHANNEL, style="primary")],
        [btn("👨🏻‍💻 الدعم", url=OWNER_CONTACT, style="primary")],
    ]
    if user_id and db.is_admin(user_id):
        unread = db.get_unread_notifications_count()
        label = f"🎛️ لوحة التحكم" + (f" ({unread})" if unread else "")
        rows.append([btn(label, callback="admin_panel_btn", style="primary")])
    keyboard = build_keyboard(rows)
    if isinstance(target, CallbackQuery):
        await safe_edit(target, text, keyboard)
    else:
        await target.reply(text, reply_markup=keyboard)


@bot.on_message(filters.command("start") & filters.private)
async def cmd_start(client: Client, message: Message):
    user_id = message.from_user.id
    user = message.from_user
    await auto_end_expired_contests()

    if len(message.command) > 1:
        params = message.command[1].split("_")
        if params[0] == "join" and len(params) >= 3:
            contest_id = int(params[1])
            channel_id = params[2]
            contest = db.get_contest_by_id(contest_id)
            if contest:
                if not contest[7]:
                    await message.reply("❌ هذه المسابقة منتهية.")
                    return
                btns = []
                if contest[8] == "manual" and contest[9]:
                    btns.append([btn("✅ نعم، أريد المشاركة", url=contest[9], style="success")])
                else:
                    btns.append([btn("✅ نعم، أريد المشاركة", callback=f"confirm_join_{contest_id}", style="success")])
                btns.append([btn("🎯 إنشاء مسابقة", callback="create_contest_menu", style="primary"), btn("❌ إلغاء", callback="cancel_join", style="danger")])
                await message.reply(
                    f"🎯 **المشاركة في المسابقة**\n\n{contest[2][:100]}...\n\nهل أنت متأكد؟\n⚠️ يمكن المشاركة مرة واحدة فقط.",
                    reply_markup=build_keyboard(btns)
                )
            return

        if params[0] == "vote" and len(params) >= 3:
            contest_id = int(params[1])
            participant_id = int(params[2])
            contest = db.get_contest_by_id(contest_id)
            participant = db.get_participant(participant_id)
            if not contest or not participant:
                await message.reply("❌ المسابقة أو المشارك غير موجود.")
                return
            ok, missing = await verify_all_memberships(user_id)
            if not ok:
                await send_forced_sub_message(message, missing)
                return
            if db.get_participant_by_user(contest_id, user_id):
                await message.reply("❌ أنت مشارك بالفعل ولا يمكنك التصويت.")
                return
            if not await verify_membership(user_id, contest[3]):
                await message.reply("❌ اشترك في قناة المسابقة أولاً.")
                return
            if db.has_voted(contest_id, user_id):
                await message.reply("❌ لقد صوتت بالفعل.")
                return
            if db.add_vote(contest_id, user_id, participant_id, str(message.chat.id)):
                votes = db.get_participant_votes(participant_id)
                await message.reply(f"✅ تم تصويتك لـ **{participant[3]}**!\n🗳️ الأصوات: {votes}")
            else:
                await message.reply("❌ فشل التصويت.")
            return

    db.register_user(user_id, user.username or "", user.first_name or "", user.last_name or "")
    db.update_user_activity(user_id)

    if db.is_user_banned(user_id):
        await message.reply("⛔ أنت محظور من استخدام هذا البوت.")
        return

    ok, missing = await verify_all_memberships(user_id)
    if not ok:
        await send_forced_sub_message(message, missing)
        return

    await send_main_menu(message)


@bot.on_callback_query(filters.regex("^main_menu$"))
async def cb_main_menu(client: Client, cb: CallbackQuery):
    await send_main_menu(cb)


@bot.on_callback_query(filters.regex("^bot_settings$"))
async def cb_settings(client: Client, cb: CallbackQuery):
    keyboard = build_keyboard([
        [btn("⛔ حظر مستخدم", callback="ban_user_from_contests", style="danger")],
        [btn("✅ فك حظر مستخدم", callback="unban_user_from_contests", style="success")],
        [btn("📋 قائمة المحظورين", callback="list_banned_users_settings", style="primary")],
        [back_btn("main_menu")]
    ])
    await safe_edit(cb, "⚙️ **الإعدادات**\n\nاختر الإجراء:", keyboard)


@bot.on_callback_query(filters.regex("^ban_user_from_contests$"))
async def cb_ban_user(client: Client, cb: CallbackQuery):
    session_states[cb.from_user.id] = {"state": "awaiting_ban_user_contests"}
    await safe_edit(cb, "⛔ **حظر مستخدم**\n\nأرسل معرف المستخدم أو اليوزر:", build_keyboard([[back_btn("bot_settings")]]))


@bot.on_callback_query(filters.regex("^unban_user_from_contests$"))
async def cb_unban_user(client: Client, cb: CallbackQuery):
    session_states[cb.from_user.id] = {"state": "awaiting_unban_user_contests"}
    await safe_edit(cb, "✅ **فك حظر مستخدم**\n\nأرسل معرف المستخدم أو اليوزر:", build_keyboard([[back_btn("bot_settings")]]))


@bot.on_callback_query(filters.regex("^list_banned_users_settings$"))
async def cb_list_banned(client: Client, cb: CallbackQuery):
    banned = db.get_blocked_users()
    if not banned:
        text = "⛔ **المحظورون**\n\nلا يوجد مستخدمون محظورون حالياً."
    else:
        text = "⛔ **المحظورون**\n\n"
        for i, u in enumerate(banned[:10], 1):
            text += f"{i}. ID: `{u[0]}` | @{u[4] or 'بدون'} | {u[2][:10]}\n"
        if len(banned) > 10:
            text += f"\n... و{len(banned) - 10} آخرين"
    keyboard = build_keyboard([
        [back_btn("bot_settings"), btn("🔄 تحديث", callback="list_banned_users_settings", style="primary")]
    ])
    await safe_edit(cb, text, keyboard)


@bot.on_callback_query(filters.regex("^add_manual_participant$"))
async def cb_add_manual_participant(client: Client, cb: CallbackQuery):
    contests = db.get_user_contests(cb.from_user.id)
    if not contests:
        await cb.answer("❌ لا توجد مسابقات نشطة. أنشئ مسابقة أولاً.", show_alert=True)
        return
    btns = [[btn(f"🎯 {c[2][:30]}{'...' if len(c[2]) > 30 else ''}", callback=f"select_contest_manual_{c[0]}", style="primary")] for c in contests]
    btns.append([back_btn("main_menu")])
    await safe_edit(cb, "👥 **نشر منشور تصويت**\n\nاختر المسابقة:", build_keyboard(btns))


@bot.on_callback_query(filters.regex("^bot_features$"))
async def cb_features(client: Client, cb: CallbackQuery):
    text = (
        "⚡ **مميزات البوت**\n\n"
        "• إدارة كاملة للمسابقات (يدوية، تلقائية، متقدمة)\n"
        "• تسجيل تلقائي للأعضاء والمشاركين\n"
        "• حماية من الأسماء غير اللائقة والروابط\n"
        "• اشتراك إجباري للتصويت والمشاركة\n"
        "• منع التصويت المزدوج أو التصويت للنفس\n"
        "• إحصائيات تفصيلية لكل مسابقة\n"
        "• إشعارات فورية لأصحاب المسابقات\n"
        "• إدارة متقدمة للمستخدمين والقنوات\n"
        "• مسابقات متقدمة بمدة محددة وعدد فائزين\n\n"
        "White Wolf | t.me/j49_c | t.me/bshshshkk"
    )
    keyboard = build_keyboard([
        [btn("📖 دليل الاستخدام", callback="bot_guide", style="primary")],
        [btn("📢 قناة المطور", url=OWNER_CHANNEL, style="primary"), btn("📢 التحديثات", url=UPDATES_CHANNEL, style="primary")],
        [btn("👨🏻‍💻 الدعم", url=OWNER_CONTACT, style="primary")],
        [back_btn("main_menu")]
    ])
    await safe_edit(cb, text, keyboard)


@bot.on_callback_query(filters.regex("^bot_guide$"))
async def cb_guide(client: Client, cb: CallbackQuery):
    text = (
        "📖 **دليل الاستخدام**\n\n"
        "1️⃣ ارفع البوت مشرفاً في قناتك بكامل الصلاحيات.\n"
        "2️⃣ اختر «📢 تعيين قناة تصويت» وأرسل رابط قناتك.\n"
        "3️⃣ اختر «🎯 إنشاء مسابقة» واختر القناة ثم أرسل وصف الجوائز.\n"
        "4️⃣ ستُنشر المسابقة تلقائياً في القناة.\n\n"
        "**للمشاركة:** اضغط زر المشاركة وأرسل اسمك.\n"
        "**للتصويت:** اضغط زر التصويت مباشرة على منشور المشارك.\n\n"
        "White Wolf | t.me/j49_c | t.me/bshshshkk"
    )
    keyboard = build_keyboard([
        [btn("📠 المميزات", callback="bot_features", style="primary")],
        [btn("📢 تعيين قناة", callback="create_voting_post", style="primary"), btn("🎯 إنشاء مسابقة", callback="create_contest_menu", style="primary")],
        [btn("👥 نشر منشور", callback="add_manual_participant", style="primary")],
        [back_btn("main_menu")]
    ])
    await safe_edit(cb, text, keyboard)


@bot.on_callback_query(filters.regex("^create_voting_post$"))
async def cb_set_voting_channel(client: Client, cb: CallbackQuery):
    session_states[cb.from_user.id] = {"state": "awaiting_voting_channel_link"}
    await safe_edit(
        cb,
        "📢 **تعيين قناة تصويت**\n\nأرسل رابط القناة أو اليوزر:\nمثال: @channel أو https://t.me/channel\n\n⚠️ يجب أن يكون البوت مشرفاً في القناة وأنت أيضاً.",
        build_keyboard([[back_btn("main_menu")]])
    )


@bot.on_callback_query(filters.regex("^create_contest_menu$"))
async def cb_contest_menu(client: Client, cb: CallbackQuery):
    keyboard = build_keyboard([
        [btn("🎯 يدوية", callback="create_manual_contest", style="primary"), btn("⚡ تلقائية", callback="create_auto_contest", style="primary")],
        [btn("🚀 متقدمة", callback="create_advanced_contest", style="primary")],
        [btn("📋 مسابقاتي", callback="my_contests", style="primary")],
        [btn("🗑️ حذف مسابقات قناة", callback="delete_channel_contests", style="danger")],
        [btn("📢 تعيين قناة", callback="create_voting_post", style="primary")],
        [back_btn("main_menu")]
    ])
    await safe_edit(cb, "🎯 **إنشاء مسابقة**\n\nاختر نوع المسابقة:", keyboard)


@bot.on_callback_query(filters.regex("^create_advanced_contest$"))
async def cb_advanced_contest(client: Client, cb: CallbackQuery):
    channels = db.get_user_channels(cb.from_user.id)
    if not channels:
        await cb.answer("❌ أضف قناتك أولاً.", show_alert=True)
        return
    btns = [[btn(f"📢 {ch[4]}", callback=f"select_channel_advanced_{ch[2]}", style="primary")] for ch in channels]
    btns += [[btn("📢 تعيين قناة", callback="create_voting_post", style="primary")], [back_btn("create_contest_menu")]]
    await safe_edit(cb, "🚀 **مسابقة متقدمة**\n\nاختر القناة:", build_keyboard(btns))


@bot.on_callback_query(filters.regex("^select_channel_advanced_"))
async def cb_select_advanced_channel(client: Client, cb: CallbackQuery):
    uid = cb.from_user.id
    channel_id = cb.data.replace("select_channel_advanced_", "")
    channel = db.get_channel_by_id(channel_id)
    if not channel or channel[1] != uid:
        await cb.answer("❌ هذه القناة ليست لك.", show_alert=True)
        return
    if db.get_contest_by_channel(channel_id):
        await cb.answer("❌ لديك مسابقة نشطة في هذه القناة.", show_alert=True)
        return
    keyboard = build_keyboard([
        [btn("✅ موافقة تلقائية", callback=f"advanced_auto_approve_yes_{channel_id}", style="success")],
        [btn("❌ موافقة يدوية", callback=f"advanced_auto_approve_no_{channel_id}", style="danger")],
        [back_btn("create_advanced_contest")]
    ])
    await safe_edit(cb, f"🚀 **مسابقة متقدمة في {channel[4]}**\n\nنوع موافقة المشاركين؟", keyboard)


@bot.on_callback_query(filters.regex("^advanced_auto_approve_(yes|no)_"))
async def cb_advanced_approve(client: Client, cb: CallbackQuery):
    uid = cb.from_user.id
    is_auto = "_yes_" in cb.data
    channel_id = cb.data.replace("advanced_auto_approve_yes_", "").replace("advanced_auto_approve_no_", "")
    channel = db.get_channel_by_id(channel_id)
    if not channel or channel[1] != uid:
        await cb.answer("❌ هذه القناة ليست لك.", show_alert=True)
        return
    session_states[uid] = {
        "state": "awaiting_advanced_contest_duration",
        "channel_id": channel_id,
        "channel_username": channel[3],
        "channel_title": channel[4],
        "contest_type": "advanced",
        "auto_approve": is_auto
    }
    label = "✅ موافقة تلقائية" if is_auto else "❌ موافقة يدوية"
    await safe_edit(
        cb,
        f"🚀 **مسابقة متقدمة في {channel[4]}**\n{label}\n\n⏱️ أرسل مدة المسابقة بالدقائق:\nمثال: 60 (ساعة)، 1440 (يوم)",
        build_keyboard([[back_btn("create_advanced_contest")]])
    )


@bot.on_callback_query(filters.regex("^my_contests$"))
async def cb_my_contests(client: Client, cb: CallbackQuery):
    uid = cb.from_user.id
    contests = db.get_user_all_contests(uid)
    if not contests:
        await safe_edit(cb, "📋 **مسابقاتي**\n\nلا توجد مسابقات بعد.", build_keyboard([
            [btn("🎯 إنشاء مسابقة", callback="create_contest_menu", style="primary")],
            [back_btn("main_menu")]
        ]))
        return
    active = [c for c in contests if c[7] == 1]
    ended = [c for c in contests if c[7] == 0]
    text = "📋 **مسابقاتي**\n\n"
    if active:
        text += f"🟢 نشطة ({len(active)}):\n"
        for c in active:
            desc = c[2][:40] + "..." if len(c[2]) > 40 else c[2]
            text += f"• {desc} (ID: {c[0]})\n"
    if ended:
        text += f"\n🔴 منتهية ({len(ended)}):\n"
        for c in ended[:3]:
            desc = c[2][:40] + "..." if len(c[2]) > 40 else c[2]
            text += f"• {desc}\n"
    btns = []
    for c in active[:3]:
        btns.append([
            btn(f"⛔ إنهاء {c[2][:15]}", callback=f"end_contest_{c[0]}", style="danger"),
            btn("🗑️ حذف", callback=f"delete_contest_{c[0]}", style="danger")
        ])
    btns += [[btn("🎯 مسابقة جديدة", callback="create_contest_menu", style="primary")], [back_btn("main_menu")]]
    await safe_edit(cb, text, build_keyboard(btns))


@bot.on_callback_query(filters.regex("^delete_channel_contests$"))
async def cb_delete_channel_contests(client: Client, cb: CallbackQuery):
    uid = cb.from_user.id
    channels = db.get_user_channels(uid)
    if not channels:
        await cb.answer("❌ لا توجد قنوات.", show_alert=True)
        return
    btns = []
    for ch in channels:
        contests = db.get_contest_by_channel_all(ch[2])
        if contests:
            btns.append([btn(f"🗑️ {ch[4]} ({len(contests)} مسابقة)", callback=f"confirm_delete_channel_{ch[2]}", style="danger")])
    if not btns:
        await cb.answer("❌ لا توجد مسابقات لحذفها.", show_alert=True)
        return
    btns.append([back_btn("create_contest_menu")])
    await safe_edit(cb, "🗑️ **حذف مسابقات القناة**\n\nاختر القناة:", build_keyboard(btns))


@bot.on_callback_query(filters.regex("^confirm_delete_channel_"))
async def cb_confirm_delete_channel(client: Client, cb: CallbackQuery):
    uid = cb.from_user.id
    channel_id = cb.data.replace("confirm_delete_channel_", "")
    channel = db.get_channel_by_id(channel_id)
    if not channel or channel[1] != uid:
        await cb.answer("❌ هذه القناة ليست لك.", show_alert=True)
        return
    db.delete_channel_contests(channel_id)
    await cb.answer("✅ تم حذف جميع مسابقات القناة.", show_alert=True)
    await cb_contest_menu(client, cb)


@bot.on_callback_query(filters.regex("^delete_contest_"))
async def cb_delete_contest(client: Client, cb: CallbackQuery):
    contest_id = int(cb.data.replace("delete_contest_", ""))
    contest = db.get_contest_by_id(contest_id)
    if not contest:
        await cb.answer("❌ المسابقة غير موجودة.", show_alert=True)
        return
    uid = cb.from_user.id
    if contest[1] != uid and not db.is_admin(uid):
        await cb.answer("❌ هذه المسابقة ليست لك.", show_alert=True)
        return
    db.delete_contest(contest_id)
    await cb.answer("✅ تم حذف المسابقة.", show_alert=True)
    await cb_my_contests(client, cb)


@bot.on_callback_query(filters.regex("^create_manual_contest$"))
async def cb_create_manual(client: Client, cb: CallbackQuery):
    channels = db.get_user_channels(cb.from_user.id)
    if not channels:
        await cb.answer("❌ أضف قناتك أولاً.", show_alert=True)
        return
    btns = [[btn(f"📢 {ch[4]}", callback=f"select_channel_manual_{ch[2]}", style="primary")] for ch in channels]
    btns += [[btn("📢 تعيين قناة", callback="create_voting_post", style="primary")], [back_btn("create_contest_menu")]]
    await safe_edit(cb, "🎯 **مسابقة يدوية**\n\nاختر القناة:", build_keyboard(btns))


@bot.on_callback_query(filters.regex("^select_channel_manual_"))
async def cb_select_manual_channel(client: Client, cb: CallbackQuery):
    uid = cb.from_user.id
    channel_id = cb.data.replace("select_channel_manual_", "")
    channel = db.get_channel_by_id(channel_id)
    if not channel or channel[1] != uid:
        await cb.answer("❌ هذه القناة ليست لك.", show_alert=True)
        return
    if db.get_contest_by_channel(channel_id):
        await cb.answer("❌ لديك مسابقة نشطة في هذه القناة.", show_alert=True)
        return
    session_states[uid] = {
        "state": "awaiting_contest_description",
        "channel_id": channel_id,
        "channel_username": channel[3],
        "channel_title": channel[4],
        "contest_type": "manual"
    }
    await safe_edit(
        cb,
        f"🎯 **مسابقة يدوية في {channel[4]}**\n\n📝 أرسل وصف المسابقة والجوائز:",
        build_keyboard([[back_btn("create_manual_contest")]])
    )


@bot.on_callback_query(filters.regex("^create_auto_contest$"))
async def cb_create_auto(client: Client, cb: CallbackQuery):
    channels = db.get_user_channels(cb.from_user.id)
    if not channels:
        await cb.answer("❌ أضف قناتك أولاً.", show_alert=True)
        return
    btns = [[btn(f"📢 {ch[4]}", callback=f"select_channel_auto_{ch[2]}", style="primary")] for ch in channels]
    btns += [[btn("📢 تعيين قناة", callback="create_voting_post", style="primary")], [back_btn("create_contest_menu")]]
    await safe_edit(cb, "⚡ **مسابقة تلقائية**\n\nاختر القناة:", build_keyboard(btns))


@bot.on_callback_query(filters.regex("^select_channel_auto_"))
async def cb_select_auto_channel(client: Client, cb: CallbackQuery):
    uid = cb.from_user.id
    channel_id = cb.data.replace("select_channel_auto_", "")
    channel = db.get_channel_by_id(channel_id)
    if not channel or channel[1] != uid:
        await cb.answer("❌ هذه القناة ليست لك.", show_alert=True)
        return
    if db.get_contest_by_channel(channel_id):
        await cb.answer("❌ لديك مسابقة نشطة في هذه القناة.", show_alert=True)
        return
    keyboard = build_keyboard([
        [btn("✅ موافقة تلقائية", callback=f"auto_approve_yes_{channel_id}", style="success")],
        [btn("❌ موافقة يدوية", callback=f"auto_approve_no_{channel_id}", style="danger")],
        [back_btn("create_auto_contest")]
    ])
    await safe_edit(cb, f"⚡ **مسابقة تلقائية في {channel[4]}**\n\nنوع الموافقة على المشاركين؟", keyboard)


@bot.on_callback_query(filters.regex("^auto_approve_(yes|no)_"))
async def cb_auto_approve(client: Client, cb: CallbackQuery):
    uid = cb.from_user.id
    is_auto = "_yes_" in cb.data
    channel_id = cb.data.replace("auto_approve_yes_", "").replace("auto_approve_no_", "")
    channel = db.get_channel_by_id(channel_id)
    if not channel or channel[1] != uid:
        await cb.answer("❌ هذه القناة ليست لك.", show_alert=True)
        return
    session_states[uid] = {
        "state": "awaiting_contest_description",
        "channel_id": channel_id,
        "channel_username": channel[3],
        "channel_title": channel[4],
        "contest_type": "auto",
        "auto_approve": is_auto
    }
    label = "✅ موافقة تلقائية" if is_auto else "❌ موافقة يدوية"
    await safe_edit(
        cb,
        f"⚡ **مسابقة تلقائية في {channel[4]}**\n{label}\n\n📝 أرسل وصف المسابقة والجوائز:",
        build_keyboard([[back_btn("create_auto_contest")]])
    )


@bot.on_callback_query(filters.regex("^winners_(1|2|3|custom)$"))
async def cb_winners_choice(client: Client, cb: CallbackQuery):
    uid = cb.from_user.id
    if uid not in session_states:
        await cb.answer("❌ انتهت الجلسة.", show_alert=True)
        return
    choice = cb.data.replace("winners_", "")
    if choice == "custom":
        session_states[uid]["state"] = "awaiting_advanced_contest_winners_custom"
        await safe_edit(cb, "🏆 أرسل عدد الفائزين المخصص (1-100):")
        return
    count = int(choice)
    session_states[uid]["winners_count"] = count
    if count == 1:
        session_states[uid]["state"] = "awaiting_advanced_contest_required_votes"
        await safe_edit(cb, f"🏆 فائز واحد\n\n🔢 أرسل عدد الأصوات المطلوبة للفوز (0 للفوز بالترتيب):")
    else:
        session_states[uid]["state"] = "awaiting_advanced_contest_prize_channel"
        await safe_edit(cb, f"🏆 {count} فائزين\n\n📢 أرسل رابط قناة الجوائز:")


@bot.on_callback_query(filters.regex("^confirm_join_"))
async def cb_confirm_join(client: Client, cb: CallbackQuery):
    uid = cb.from_user.id
    contest_id = int(cb.data.replace("confirm_join_", ""))
    contest = db.get_contest_by_id(contest_id)
    if not contest or not contest[7]:
        await cb.answer("❌ المسابقة غير موجودة أو منتهية.", show_alert=True)
        return
    if db.get_participant_by_user(contest_id, uid):
        await cb.answer("❌ أنت مشارك بالفعل.", show_alert=True)
        return
    session_states[uid] = {"state": "awaiting_participant_name", "contest_id": contest_id}
    await safe_edit(cb, "🎯 أرسل اسمك للمشاركة:\n\n⚠️ لا تستخدم روابط أو ألفاظ غير لائقة.", build_keyboard([[back_btn("main_menu")]]))


@bot.on_callback_query(filters.regex("^cancel_join$"))
async def cb_cancel_join(client: Client, cb: CallbackQuery):
    session_states.pop(cb.from_user.id, None)
    await send_main_menu(cb)


@bot.on_callback_query(filters.regex("^vote_direct_"))
async def cb_vote_direct(client: Client, cb: CallbackQuery):
    parts = cb.data.split("_")
    if len(parts) < 4:
        await cb.answer("❌ بيانات غير صحيحة.", show_alert=True)
        return
    contest_id = int(parts[2])
    participant_id = int(parts[3])
    contest = db.get_contest_by_id(contest_id)
    participant = db.get_participant(participant_id)
    if not contest or not participant:
        await cb.answer("❌ المسابقة أو المشارك غير موجود.", show_alert=True)
        return
    uid = cb.from_user.id
    if participant[2] == uid:
        await cb.answer("❌ لا يمكنك التصويت لنفسك.", show_alert=True)
        return
    if not await verify_membership(uid, contest[3]):
        await cb.answer("❌ اشترك في قناة المسابقة أولاً.", show_alert=True)
        return
    if db.has_voted(contest_id, uid):
        await cb.answer("❌ لقد صوتت بالفعل.", show_alert=True)
        return
    source = str(cb.message.chat.id) if cb.message else ""
    if db.add_vote(contest_id, uid, participant_id, source):
        votes = db.get_participant_votes(participant_id)
        emoji = participant[4]
        join_url = contest[9] or f"https://t.me/{(await bot.get_me()).username}?start=join_{contest_id}_{contest[3]}"
        new_keyboard = build_keyboard([
            [btn(f"{emoji} تصويت ({votes})", callback=f"vote_direct_{contest_id}_{participant_id}", style="primary")],
            [btn("🎯 المشاركة", url=join_url, style="primary")]
        ])
        try:
            await cb.message.edit_reply_markup(new_keyboard)
        except Exception:
            pass
        if contest[14] and contest[13] > 0 and votes >= contest[13] and not participant[9]:
            db.mark_participant_as_winner(participant_id)
            if participant[2] != 0:
                try:
                    await bot.send_message(
                        participant[2],
                        f"🎉 مبروك! فزت في المسابقة!\n\n{contest[2][:100]}\n\n🗳️ أصواتك: {votes}\n🎁 {contest[14]}"
                    )
                except Exception:
                    pass
        await cb.answer(f"✅ تم تصويتك لـ {participant[3]}! الأصوات: {votes}", show_alert=True)
    else:
        await cb.answer("❌ فشل التصويت.", show_alert=True)


@bot.on_callback_query(filters.regex("^view_contest_"))
async def cb_view_contest(client: Client, cb: CallbackQuery):
    contest_id = int(cb.data.replace("view_contest_", ""))
    contest = db.get_contest_by_id(contest_id)
    if not contest:
        await cb.answer("❌ غير موجود.", show_alert=True)
        return
    uid = cb.from_user.id
    if contest[1] != uid and not db.is_admin(uid):
        await cb.answer("❌ ليست مسابقتك.", show_alert=True)
        return
    participants = db.get_contest_participants(contest_id)
    pending = db.get_pending_participants(contest_id)
    total_votes = db.get_contest_votes_count(contest_id)
    ctype_map = {"manual": "يدوية", "auto": "تلقائية", "advanced": "متقدمة"}
    ctype = ctype_map.get(contest[8], contest[8])
    status = "🟢 نشطة" if contest[7] == 1 else "🔴 منتهية"
    approve_type = "تلقائية" if contest[10] else "يدوية"
    text = (
        f"🏆 **تفاصيل المسابقة**\n\n"
        f"📝 {contest[2][:100]}\n"
        f"📢 {contest[4]}\n🆔 `{contest_id}`\n"
        f"{status} | 🎪 {ctype} | ✅ {approve_type}\n"
        f"👥 مشاركون: {len(participants)} | ⏳ معلق: {len(pending)} | 🗳️ أصوات: {total_votes}\n"
    )
    if contest[8] == "advanced":
        if contest[11]:
            try:
                end_dt = datetime.strptime(contest[11][:19], "%Y-%m-%d %H:%M:%S")
                left = (end_dt - datetime.now()).total_seconds()
                if left > 0:
                    text += f"⏱️ متبقي: {int(left // 3600)} ساعة و{int((left % 3600) // 60)} دقيقة\n"
            except Exception:
                pass
        if contest[12]:
            text += f"🏆 عدد الفائزين: {contest[12]}\n"
        if contest[13]:
            text += f"🎯 أصوات للفوز: {contest[13]}\n"
        if contest[14]:
            text += f"🎁 قناة الجوائز: {contest[14]}\n"
    if participants:
        text += "\n🏅 المتصدرون:\n"
        for i, p in enumerate(participants[:5], 1):
            text += f"{i}. {p[3]} — {p[5]} صوت{'🏆' if p[9] else ''}\n"
    btns = [
        [btn("👥 إدارة المشاركين", callback=f"manage_participants_contest_{contest_id}", style="primary"), btn("📊 إحصائيات", callback=f"stats_contest_{contest_id}", style="primary")],
    ]
    if contest[7] == 1:
        btns.append([btn("➕ إضافة مشارك", callback=f"add_manual_to_contest_{contest_id}", style="success"), btn("⛔ إنهاء", callback=f"end_contest_{contest_id}", style="danger")])
    btns.append([btn("➕ أصوات", callback=f"user_add_votes_contest_{contest_id}", style="success"), btn("➖ أصوات", callback=f"user_remove_votes_contest_{contest_id}", style="danger")])
    if pending:
        btns.append([btn(f"✅ {len(pending)} طلب معلق", callback=f"view_pending_{contest_id}", style="primary")])
    btns.append([back_btn("my_contests")])
    await safe_edit(cb, text, build_keyboard(btns))


@bot.on_callback_query(filters.regex("^stats_contest_"))
async def cb_stats_contest(client: Client, cb: CallbackQuery):
    contest_id = int(cb.data.replace("stats_contest_", ""))
    contest = db.get_contest_by_id(contest_id)
    if not contest:
        await cb.answer("❌ غير موجود.", show_alert=True)
        return
    uid = cb.from_user.id
    if contest[1] != uid and not db.is_admin(uid):
        await cb.answer("❌ ليست مسابقتك.", show_alert=True)
        return
    participants = db.get_contest_participants(contest_id)
    total_votes = db.get_contest_votes_count(contest_id)
    avg = round(total_votes / len(participants), 2) if participants else 0
    text = (
        f"📊 **إحصائيات المسابقة**\n{contest[2][:50]}\n\n"
        f"👥 المشاركون: {len(participants)}\n"
        f"🗳️ الأصوات: {total_votes}\n"
        f"📈 المتوسط: {avg}\n"
    )
    if participants:
        text += "\n🏆 الترتيب:\n"
        for i, p in enumerate(participants[:10], 1):
            perc = round((p[5] / total_votes) * 100, 1) if total_votes else 0
            bar = "█" * int(perc // 10) + "░" * (10 - int(perc // 10))
            text += f"{i}. {p[3]} — {p[5]} ({perc}%) {bar}\n"
    await safe_edit(cb, text, build_keyboard([[back_btn(f"view_contest_{contest_id}")]]))


@bot.on_callback_query(filters.regex("^manage_participants_contest_"))
async def cb_manage_participants(client: Client, cb: CallbackQuery):
    contest_id = int(cb.data.replace("manage_participants_contest_", ""))
    contest = db.get_contest_by_id(contest_id)
    if not contest:
        await cb.answer("❌ غير موجود.", show_alert=True)
        return
    uid = cb.from_user.id
    if contest[1] != uid and not db.is_admin(uid):
        await cb.answer("❌ ليست مسابقتك.", show_alert=True)
        return
    participants = db.get_contest_participants(contest_id)
    pending = db.get_pending_participants(contest_id)
    text = f"👥 **إدارة المشاركين**\n\nمقبول: {len(participants)} | معلق: {len(pending)}\n\n"
    for i, p in enumerate(participants[:10], 1):
        text += f"{i}. {p[3]} — {p[5]} صوت{'🏆' if p[9] else ''}\n"
    btns = []
    if participants:
        btns += [
            [btn("➕ إضافة أصوات", callback=f"add_votes_contest_{contest_id}", style="success")],
            [btn("➖ خصم أصوات", callback=f"remove_votes_contest_{contest_id}", style="danger")]
        ]
    if pending:
        btns.append([btn(f"✅ معالجة {len(pending)} طلب", callback=f"view_pending_{contest_id}", style="primary")])
    btns += [
        [btn("➕ إضافة مشارك يدوي", callback=f"add_manual_to_contest_{contest_id}", style="success")],
        [back_btn(f"view_contest_{contest_id}")]
    ]
    await safe_edit(cb, text, build_keyboard(btns))


@bot.on_callback_query(filters.regex("^view_pending_"))
async def cb_view_pending(client: Client, cb: CallbackQuery):
    contest_id = int(cb.data.replace("view_pending_", ""))
    contest = db.get_contest_by_id(contest_id)
    if not contest:
        await cb.answer("❌ غير موجود.", show_alert=True)
        return
    uid = cb.from_user.id
    if contest[1] != uid and not db.is_admin(uid):
        await cb.answer("❌ ليست مسابقتك.", show_alert=True)
        return
    pending = db.get_pending_participants(contest_id)
    if not pending:
        await cb.answer("✅ لا توجد طلبات معلقة.", show_alert=True)
        return
    text = f"⏳ **طلبات المشاركة ({len(pending)})**\n\n"
    for i, p in enumerate(pending, 1):
        text += f"{i}. {p[3]} (ID: `{p[2]}`)\n"
    btns = []
    for p in pending[:5]:
        btns.append([
            btn(f"✅ {p[3][:15]}", callback=f"approve_participant_{contest_id}_{p[2]}", style="success"),
            btn(f"❌ {p[3][:15]}", callback=f"reject_participant_{contest_id}_{p[2]}", style="danger")
        ])
    btns += [
        [btn("✅ الموافقة على الكل", callback=f"approve_all_participants_{contest_id}", style="success")],
        [back_btn(f"manage_participants_contest_{contest_id}")]
    ]
    await safe_edit(cb, text, build_keyboard(btns))


@bot.on_callback_query(filters.regex("^approve_participant_"))
async def cb_approve_participant(client: Client, cb: CallbackQuery):
    parts = cb.data.split("_")
    if len(parts) < 4:
        return
    contest_id = int(parts[2])
    user_id_p = int(parts[3])
    contest = db.get_contest_by_id(contest_id)
    if not contest:
        await cb.answer("❌ غير موجود.", show_alert=True)
        return
    uid = cb.from_user.id
    if contest[1] != uid and not db.is_admin(uid):
        await cb.answer("❌ ليست مسابقتك.", show_alert=True)
        return
    participant = db.get_participant_by_user(contest_id, user_id_p)
    if not participant:
        await cb.answer("❌ المشارك غير موجود.", show_alert=True)
        return
    if participant[8] == 1:
        await cb.answer("✅ تمت الموافقة مسبقاً.", show_alert=True)
        return
    db.approve_participant(participant[0])
    try:
        await bot.send_message(user_id_p, "✅ تمت الموافقة على مشاركتك في المسابقة!")
    except Exception:
        pass
    me = await bot.get_me()
    join_url = contest[9] or f"https://t.me/{me.username}?start=join_{contest_id}_{contest[3]}"
    await post_participant_to_channel(contest_id, participant[0], contest[3], join_url)
    await cb.answer(f"✅ تمت الموافقة على {participant[3]}", show_alert=True)
    await cb_view_pending(client, cb)


@bot.on_callback_query(filters.regex("^reject_participant_"))
async def cb_reject_participant(client: Client, cb: CallbackQuery):
    parts = cb.data.split("_")
    if len(parts) < 4:
        return
    contest_id = int(parts[2])
    user_id_p = int(parts[3])
    contest = db.get_contest_by_id(contest_id)
    if not contest:
        await cb.answer("❌ غير موجود.", show_alert=True)
        return
    uid = cb.from_user.id
    if contest[1] != uid and not db.is_admin(uid):
        await cb.answer("❌ ليست مسابقتك.", show_alert=True)
        return
    participant = db.get_participant_by_user(contest_id, user_id_p)
    if not participant:
        await cb.answer("❌ المشارك غير موجود.", show_alert=True)
        return
    db.reject_participant(participant[0])
    try:
        await bot.send_message(user_id_p, "❌ تم رفض طلب مشاركتك.")
    except Exception:
        pass
    await cb.answer(f"❌ تم رفض {participant[3]}", show_alert=True)
    await cb_view_pending(client, cb)


@bot.on_callback_query(filters.regex("^approve_all_participants_"))
async def cb_approve_all(client: Client, cb: CallbackQuery):
    contest_id = int(cb.data.replace("approve_all_participants_", ""))
    contest = db.get_contest_by_id(contest_id)
    if not contest:
        await cb.answer("❌ غير موجود.", show_alert=True)
        return
    uid = cb.from_user.id
    if contest[1] != uid and not db.is_admin(uid):
        await cb.answer("❌ ليست مسابقتك.", show_alert=True)
        return
    pending = db.get_pending_participants(contest_id)
    me = await bot.get_me()
    join_url = contest[9] or f"https://t.me/{me.username}?start=join_{contest_id}_{contest[3]}"
    count = 0
    for p in pending:
        db.approve_participant(p[0])
        try:
            await bot.send_message(p[2], "✅ تمت الموافقة على مشاركتك!")
        except Exception:
            pass
        await post_participant_to_channel(contest_id, p[0], contest[3], join_url)
        count += 1
    await cb.answer(f"✅ تمت الموافقة على {count} مشارك.", show_alert=True)
    await cb_view_pending(client, cb)


@bot.on_callback_query(filters.regex("^add_manual_to_contest_"))
async def cb_add_manual_to_contest(client: Client, cb: CallbackQuery):
    contest_id = int(cb.data.replace("add_manual_to_contest_", ""))
    contest = db.get_contest_by_id(contest_id)
    if not contest:
        await cb.answer("❌ غير موجود.", show_alert=True)
        return
    uid = cb.from_user.id
    if contest[1] != uid and not db.is_admin(uid):
        await cb.answer("❌ ليست مسابقتك.", show_alert=True)
        return
    session_states[uid] = {"state": "awaiting_manual_participant_name", "contest_id": contest_id}
    await safe_edit(cb, "👥 **إضافة مشارك يدوي**\n\nأرسل اسم المشارك:", build_keyboard([[back_btn(f"manage_participants_contest_{contest_id}")]]))


@bot.on_callback_query(filters.regex("^add_votes_contest_"))
async def cb_add_votes_contest(client: Client, cb: CallbackQuery):
    contest_id = int(cb.data.replace("add_votes_contest_", ""))
    contest = db.get_contest_by_id(contest_id)
    if not contest:
        await cb.answer("❌ غير موجود.", show_alert=True)
        return
    uid = cb.from_user.id
    if contest[1] != uid and not db.is_admin(uid):
        await cb.answer("❌ ليست مسابقتك.", show_alert=True)
        return
    participants = db.get_contest_participants(contest_id)
    if not participants:
        await cb.answer("❌ لا يوجد مشاركون.", show_alert=True)
        return
    btns = [[btn(f"{p[3]} — {p[5]} صوت", callback=f"add_votes_to_{p[0]}", style="primary")] for p in participants[:10]]
    btns.append([back_btn(f"manage_participants_contest_{contest_id}")])
    await safe_edit(cb, "➕ **إضافة أصوات**\n\nاختر المشارك:", build_keyboard(btns))


@bot.on_callback_query(filters.regex("^add_votes_to_"))
async def cb_add_votes_to_participant(client: Client, cb: CallbackQuery):
    participant_id = int(cb.data.replace("add_votes_to_", ""))
    participant = db.get_participant(participant_id)
    if not participant:
        await cb.answer("❌ غير موجود.", show_alert=True)
        return
    contest = db.get_contest_by_id(participant[1])
    if not contest:
        await cb.answer("❌ غير موجود.", show_alert=True)
        return
    uid = cb.from_user.id
    if contest[1] != uid and not db.is_admin(uid):
        await cb.answer("❌ ليست مسابقتك.", show_alert=True)
        return
    session_states[uid] = {"state": "awaiting_add_votes_amount_specific", "participant_id": participant_id, "contest_id": contest[0]}
    await safe_edit(
        cb,
        f"➕ **إضافة أصوات لـ {participant[3]}**\n\nالأصوات الحالية: {participant[5]}\n\nأرسل عدد الأصوات:",
        build_keyboard([[back_btn(f"add_votes_contest_{contest[0]}")]])
    )


@bot.on_callback_query(filters.regex("^remove_votes_contest_"))
async def cb_remove_votes_contest(client: Client, cb: CallbackQuery):
    contest_id = int(cb.data.replace("remove_votes_contest_", ""))
    contest = db.get_contest_by_id(contest_id)
    if not contest:
        await cb.answer("❌ غير موجود.", show_alert=True)
        return
    uid = cb.from_user.id
    if contest[1] != uid and not db.is_admin(uid):
        await cb.answer("❌ ليست مسابقتك.", show_alert=True)
        return
    participants = db.get_contest_participants(contest_id)
    if not participants:
        await cb.answer("❌ لا يوجد مشاركون.", show_alert=True)
        return
    btns = [[btn(f"{p[3]} — {p[5]} صوت", callback=f"remove_votes_from_{p[0]}", style="primary")] for p in participants[:10]]
    btns.append([back_btn(f"manage_participants_contest_{contest_id}")])
    await safe_edit(cb, "➖ **خصم أصوات**\n\nاختر المشارك:", build_keyboard(btns))


@bot.on_callback_query(filters.regex("^remove_votes_from_"))
async def cb_remove_votes_from_participant(client: Client, cb: CallbackQuery):
    participant_id = int(cb.data.replace("remove_votes_from_", ""))
    participant = db.get_participant(participant_id)
    if not participant:
        await cb.answer("❌ غير موجود.", show_alert=True)
        return
    contest = db.get_contest_by_id(participant[1])
    if not contest:
        await cb.answer("❌ غير موجود.", show_alert=True)
        return
    uid = cb.from_user.id
    if contest[1] != uid and not db.is_admin(uid):
        await cb.answer("❌ ليست مسابقتك.", show_alert=True)
        return
    session_states[uid] = {"state": "awaiting_remove_votes_amount_specific", "participant_id": participant_id, "contest_id": contest[0]}
    await safe_edit(
        cb,
        f"➖ **خصم أصوات من {participant[3]}**\n\nالأصوات الحالية: {participant[5]}\n\nأرسل عدد الأصوات:",
        build_keyboard([[back_btn(f"remove_votes_contest_{contest[0]}")]])
    )


@bot.on_callback_query(filters.regex("^user_add_votes$|^user_add_votes_contest_"))
async def cb_user_add_votes(client: Client, cb: CallbackQuery):
    uid = cb.from_user.id
    if not db.get_user_contests(uid):
        await cb.answer("❌ لا توجد مسابقات نشطة.", show_alert=True)
        return
    session_states[uid] = {"state": "awaiting_add_votes_link"}
    await safe_edit(cb, "➕ **إضافة أصوات**\n\nأرسل رابط منشور المشارك:", build_keyboard([[back_btn("main_menu")]]))


@bot.on_callback_query(filters.regex("^user_remove_votes$|^user_remove_votes_contest_"))
async def cb_user_remove_votes(client: Client, cb: CallbackQuery):
    uid = cb.from_user.id
    if not db.get_user_contests(uid):
        await cb.answer("❌ لا توجد مسابقات نشطة.", show_alert=True)
        return
    session_states[uid] = {"state": "awaiting_remove_votes_link"}
    await safe_edit(cb, "➖ **خصم أصوات**\n\nأرسل رابط منشور المشارك:", build_keyboard([[back_btn("main_menu")]]))


@bot.on_callback_query(filters.regex("^end_contest_"))
async def cb_end_contest(client: Client, cb: CallbackQuery):
    contest_id = int(cb.data.replace("end_contest_", ""))
    contest = db.get_contest_by_id(contest_id)
    if not contest:
        await cb.answer("❌ غير موجود.", show_alert=True)
        return
    uid = cb.from_user.id
    if contest[1] != uid and not db.is_admin(uid):
        await cb.answer("❌ ليست مسابقتك.", show_alert=True)
        return
    if contest[7] == 0:
        await cb.answer("❌ المسابقة منتهية بالفعل.", show_alert=True)
        return
    winners = db.check_and_mark_winners(contest_id)
    db.end_contest(contest_id)
    msg = f"🎉 **انتهت المسابقة!**\n\n{contest[2]}\n\n✨ الفائزون:\n"
    for i, w in enumerate(winners, 1):
        msg += f"{i}. {w[3]} — {w[5]} صوت\n"
    if contest[14]:
        msg += f"\n🎁 قناة الجوائز: {contest[14]}"
    try:
        await bot.send_message(int(contest[3]), msg)
    except Exception:
        pass
    await cb.answer(f"✅ انتهت المسابقة — {len(winners)} فائز.", show_alert=True)
    await cb_view_contest(client, cb)


@bot.on_callback_query(filters.regex("^select_contest_manual_"))
async def cb_select_contest_manual(client: Client, cb: CallbackQuery):
    contest_id = int(cb.data.replace("select_contest_manual_", ""))
    contest = db.get_contest_by_id(contest_id)
    if not contest:
        await cb.answer("❌ غير موجود.", show_alert=True)
        return
    uid = cb.from_user.id
    if contest[1] != uid:
        await cb.answer("❌ ليست مسابقتك.", show_alert=True)
        return
    session_states[uid] = {"state": "awaiting_manual_participant_name", "contest_id": contest_id}
    await safe_edit(
        cb,
        f"👥 **نشر منشور يدوي**\n{contest[2][:50]}\n\nأرسل اسم المشارك:",
        build_keyboard([[back_btn("add_manual_participant")]])
    )


@bot.on_callback_query(filters.regex("^check_subscription$"))
async def cb_check_subscription(client: Client, cb: CallbackQuery):
    ok, _ = await verify_all_memberships(cb.from_user.id)
    if ok:
        await cb.answer("✅ أنت مشترك في جميع القنوات.", show_alert=True)
        await send_main_menu(cb)
    else:
        await cb.answer("❌ لم تشترك بعد في جميع القنوات.", show_alert=True)


@bot.on_callback_query(filters.regex("^admin_panel_btn$"))
async def cb_admin_panel(client: Client, cb: CallbackQuery):
    uid = cb.from_user.id
    if not db.is_admin(uid):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    unread = db.get_unread_notifications_count()
    text = (
        f"🎛️ **لوحة التحكم**\n\n"
        f"👥 المستخدمون: {db.get_total_users()} (اليوم: {db.get_today_users()})\n"
        f"🗳️ أصوات اليوم: {db.get_today_votes()}\n"
        f"🎯 المسابقات: {len(db.get_all_contests())} (اليوم: {db.get_today_contests()})\n"
        f"🔔 تنبيهات جديدة: {unread}"
    )
    btns = [
        [btn("👥 المستخدمون", callback="admin_users", style="primary"), btn("📢 الإذاعة", callback="admin_broadcast", style="primary")],
        [btn("📊 الإحصائيات", callback="admin_stats", style="primary"), btn("🎯 المسابقات", callback="admin_contests", style="primary")],
        [btn("🛠️ التصويتات", callback="admin_votes", style="primary"), btn("📢 القنوات", callback="admin_channels", style="primary")],
        [btn("🔒 الاشتراك الإجباري", callback="admin_forced_sub", style="primary"), btn("⚙️ المشرفون", callback="admin_manage_admins", style="primary")],
        [btn("📝 نشر يدوي", callback="admin_manual_post", style="primary"), btn("📋 تحكم القنوات", callback="admin_channel_control", style="primary")],
    ]
    if unread:
        btns.append([btn(f"🔔 التنبيهات ({unread})", callback="admin_notifications", style="primary")])
    btns.append([back_btn("main_menu")])
    await safe_edit(cb, text, build_keyboard(btns))


def admin_check(func):
    async def wrapper(client, cb):
        if not db.is_admin(cb.from_user.id):
            await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
            return
        return await func(client, cb)
    wrapper.__name__ = func.__name__
    return wrapper


@bot.on_callback_query(filters.regex("^admin_users$"))
async def cb_admin_users(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    keyboard = build_keyboard([
        [btn("👁️ عرض الكل", callback="admin_view_users", style="primary"), btn("⛔ حظر", callback="admin_ban_user", style="danger")],
        [btn("✅ فك حظر", callback="admin_unban_user", style="success"), btn("📋 المحظورون", callback="admin_banned_users", style="primary")],
        [btn("🔍 بحث", callback="admin_search_user", style="primary"), btn("📊 إحصائيات", callback="admin_users_stats", style="primary")],
        [back_btn("admin_panel_btn")]
    ])
    await safe_edit(cb, "👥 **إدارة المستخدمين**", keyboard)


@bot.on_callback_query(filters.regex("^admin_broadcast$"))
async def cb_admin_broadcast(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    keyboard = build_keyboard([
        [btn("👥 كل المستخدمين", callback="admin_broadcast_all", style="primary"), btn("📢 القنوات فقط", callback="admin_broadcast_channels", style="primary")],
        [btn("👤 مستخدم محدد", callback="admin_broadcast_user", style="primary"), btn("📢 قناة محددة", callback="admin_broadcast_specific_channel", style="primary")],
        [btn("📢 كل القنوات", callback="admin_broadcast_all_channels", style="primary"), btn("📋 السابقة", callback="admin_previous_broadcasts", style="primary")],
        [back_btn("admin_panel_btn")]
    ])
    await safe_edit(cb, "📢 **الإذاعة**\n\nاختر الهدف:", keyboard)


@bot.on_callback_query(filters.regex("^admin_stats$"))
async def cb_admin_stats(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    today = db.get_daily_stats_full()
    weekly = db.get_weekly_stats()
    top_ch = db.get_top_channels(5)
    top_par = db.get_top_participants(5)
    text = (
        f"📊 **الإحصائيات**\n\n"
        f"اليوم: {today[1] if today else 0} تصويت | {today[2] if today else 0} مستخدم جديد\n"
        f"الأسبوع: {weekly[0] if weekly else 0} تصويت\n\n"
        f"🏆 أفضل القنوات:\n"
    )
    for i, ch in enumerate(top_ch, 1):
        text += f"{i}. {ch[0]} — {ch[1]} مسابقة\n"
    text += "\n🥇 أفضل المشاركين:\n"
    for i, p in enumerate(top_par, 1):
        text += f"{i}. {p[0]} — {p[1]} صوت\n"
    await safe_edit(cb, text, build_keyboard([
        [btn("🔄 تحديث", callback="admin_stats", style="primary"), back_btn("admin_panel_btn")]
    ]))


@bot.on_callback_query(filters.regex("^admin_contests$"))
async def cb_admin_contests(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    keyboard = build_keyboard([
        [btn("📋 كل المسابقات", callback="admin_view_contests", style="primary"), btn("🟢 النشطة", callback="admin_active_contests", style="primary")],
        [btn("⛔ إنهاء مسابقة", callback="admin_end_contest", style="danger"), btn("🗑️ حذف مسابقة", callback="admin_delete_contest", style="danger")],
        [back_btn("admin_panel_btn")]
    ])
    await safe_edit(cb, "🎯 **إدارة المسابقات**", keyboard)


@bot.on_callback_query(filters.regex("^admin_votes$"))
async def cb_admin_votes(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    keyboard = build_keyboard([
        [btn("➕ إضافة أصوات", callback="admin_add_votes", style="success"), btn("➖ خصم أصوات", callback="admin_remove_votes", style="danger")],
        [btn("📊 الإحصائيات", callback="admin_votes_stats", style="primary"), btn("📋 السجل", callback="admin_votes_log", style="primary")],
        [back_btn("admin_panel_btn")]
    ])
    await safe_edit(cb, "🗳️ **إدارة التصويتات**", keyboard)


@bot.on_callback_query(filters.regex("^admin_channels$"))
async def cb_admin_channels(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    keyboard = build_keyboard([
        [btn("📋 عرض الكل", callback="admin_view_channels", style="primary"), btn("⛔ حظر", callback="admin_block_channel", style="danger")],
        [btn("✅ فك حظر", callback="admin_unblock_channel", style="success"), btn("📊 إحصائيات", callback="admin_channels_stats", style="primary")],
        [btn("🔍 بحث", callback="admin_search_channel", style="primary"), btn("🗑️ حذف", callback="admin_delete_channel", style="danger")],
        [back_btn("admin_panel_btn")]
    ])
    await safe_edit(cb, "📢 **إدارة القنوات**", keyboard)


@bot.on_callback_query(filters.regex("^admin_forced_sub$"))
async def cb_admin_forced_sub(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    keyboard = build_keyboard([
        [btn("📢 قناة عامة", callback="admin_add_public_channel", style="primary"), btn("🔒 قناة خاصة", callback="admin_add_private_channel", style="primary")],
        [btn("👥 جروب عام", callback="admin_add_public_group", style="primary"), btn("🔒 جروب خاص", callback="admin_add_private_group", style="primary")],
        [btn("📋 القنوات", callback="admin_view_forced_channels", style="primary"), btn("📋 الجروبات", callback="admin_view_forced_groups", style="primary")],
        [btn("🗑️ حذف قناة", callback="admin_delete_forced_channel", style="danger"), btn("🗑️ حذف جروب", callback="admin_delete_forced_group", style="danger")],
        [back_btn("admin_panel_btn")]
    ])
    await safe_edit(cb, "🔒 **الاشتراك الإجباري**", keyboard)


@bot.on_callback_query(filters.regex("^admin_manage_admins$"))
async def cb_admin_manage_admins(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    admins = db.get_all_admins()
    text = "👨‍💼 **المشرفون**\n\n"
    for a in admins:
        text += f"• {a[4] or 'غير معروف'} (@{a[3] or 'بدون'})\n"
    keyboard = build_keyboard([
        [btn("➕ إضافة مشرف", callback="admin_add_admin", style="success"), btn("➖ إزالة مشرف", callback="admin_remove_admin", style="danger")],
        [back_btn("admin_panel_btn")]
    ])
    await safe_edit(cb, text, keyboard)


@bot.on_callback_query(filters.regex("^admin_manual_post$"))
async def cb_admin_manual_post(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    keyboard = build_keyboard([
        [btn("📢 نشر في قناة", callback="admin_manual_post_channel", style="primary")],
        [btn("📋 المنشورات السابقة", callback="admin_view_manual_posts", style="primary")],
        [back_btn("admin_panel_btn")]
    ])
    await safe_edit(cb, "📝 **نشر يدوي (أدمن)**", keyboard)


@bot.on_callback_query(filters.regex("^admin_channel_control$"))
async def cb_admin_channel_control(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    keyboard = build_keyboard([
        [btn("➕ إضافة قناة", callback="admin_add_channel_control", style="success"), btn("📋 القنوات", callback="admin_view_controlled_channels", style="primary")],
        [btn("🛠️ التحكم بقناة", callback="admin_control_channel", style="primary"), btn("📊 إحصائيات", callback="admin_controlled_channels_stats", style="primary")],
        [btn("🗑️ حذف", callback="admin_remove_channel_control", style="danger")],
        [back_btn("admin_panel_btn")]
    ])
    await safe_edit(cb, "📋 **تحكم بالقنوات**", keyboard)


@bot.on_callback_query(filters.regex("^admin_notifications$"))
async def cb_admin_notifications(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    notifs = db.get_bot_admin_notifications(20, unread_only=True)
    text = f"🔔 **تنبيهات جديدة ({len(notifs)})**\n\n" if notifs else "🔔 لا توجد تنبيهات جديدة."
    for i, n in enumerate(notifs[:10], 1):
        text += f"{i}. {n[2]} — {n[6]}\n"
    keyboard = build_keyboard([
        [btn("✅ تحديد كمقروء", callback="admin_mark_all_notifications_read", style="success"), btn("🗑️ مسح الكل", callback="admin_clear_all_notifications", style="danger")],
        [back_btn("admin_panel_btn")]
    ])
    await safe_edit(cb, text, keyboard)


@bot.on_callback_query(filters.regex("^admin_mark_all_notifications_read$"))
async def cb_mark_notifications_read(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    db.mark_notifications_read()
    await cb.answer("✅ تم تحديد الكل كمقروء.", show_alert=True)
    await cb_admin_notifications(client, cb)


@bot.on_callback_query(filters.regex("^admin_clear_all_notifications$"))
async def cb_clear_notifications(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    db.clear_bot_admin_notifications()
    await cb.answer("✅ تم مسح جميع التنبيهات.", show_alert=True)
    await cb_admin_notifications(client, cb)


@bot.on_callback_query(filters.regex("^admin_broadcast_all$"))
async def cb_broadcast_all_prompt(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    session_states[cb.from_user.id] = {"state": "awaiting_broadcast_all"}
    await safe_edit(cb, "📢 أرسل نص الإذاعة لجميع المستخدمين:", build_keyboard([[back_btn("admin_broadcast")]]))


@bot.on_callback_query(filters.regex("^admin_broadcast_channels$"))
async def cb_broadcast_channels_prompt(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    session_states[cb.from_user.id] = {"state": "awaiting_broadcast_channels"}
    await safe_edit(cb, "📢 أرسل نص الإذاعة للقنوات فقط:", build_keyboard([[back_btn("admin_broadcast")]]))


@bot.on_callback_query(filters.regex("^admin_broadcast_user$"))
async def cb_broadcast_user_prompt(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    session_states[cb.from_user.id] = {"state": "awaiting_broadcast_user"}
    await safe_edit(cb, "👤 أرسل معرف المستخدم أو اليوزر:", build_keyboard([[back_btn("admin_broadcast")]]))


@bot.on_callback_query(filters.regex("^admin_broadcast_specific_channel$"))
async def cb_broadcast_specific_channel_prompt(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    session_states[cb.from_user.id] = {"state": "awaiting_broadcast_specific_channel"}
    await safe_edit(cb, "📢 أرسل رابط القناة:", build_keyboard([[back_btn("admin_broadcast")]]))


@bot.on_callback_query(filters.regex("^admin_broadcast_all_channels$"))
async def cb_broadcast_all_channels_prompt(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    session_states[cb.from_user.id] = {"state": "awaiting_broadcast_all_channels"}
    await safe_edit(cb, "📢 أرسل نص الإذاعة لكل القنوات:", build_keyboard([[back_btn("admin_broadcast")]]))


@bot.on_callback_query(filters.regex("^confirm_broadcast_all$"))
async def cb_confirm_broadcast_all(client: Client, cb: CallbackQuery):
    uid = cb.from_user.id
    state = session_states.get(uid, {})
    if state.get("state") != "awaiting_broadcast_message_all":
        await cb.answer("❌ انتهت الجلسة.", show_alert=True)
        return
    msg_txt = state["message"]
    session_states.pop(uid, None)
    await safe_edit(cb, "⏳ جاري الإرسال...")
    users = db.get_all_users()
    success = fail = 0
    for u in users:
        try:
            await bot.send_message(u[0], msg_txt)
            success += 1
            await asyncio.sleep(0.1)
        except Exception:
            fail += 1
    db.add_broadcast(uid, "text", "all_users", msg_txt, success, fail)
    await safe_edit(cb, f"✅ اكتمل الإرسال\n\nنجح: {success} | فشل: {fail} | الإجمالي: {len(users)}", build_keyboard([[back_btn("admin_broadcast")]]))


@bot.on_callback_query(filters.regex("^confirm_broadcast_channels$"))
async def cb_confirm_broadcast_channels(client: Client, cb: CallbackQuery):
    uid = cb.from_user.id
    state = session_states.get(uid, {})
    if state.get("state") != "awaiting_broadcast_message_channels":
        await cb.answer("❌ انتهت الجلسة.", show_alert=True)
        return
    msg_txt = state["message"]
    session_states.pop(uid, None)
    await safe_edit(cb, "⏳ جاري الإرسال للقنوات...")
    channels = db.cursor.execute("SELECT DISTINCT channel_id FROM user_channels WHERE is_blocked = 0").fetchall()
    success = fail = 0
    for ch in channels:
        try:
            await bot.send_message(int(ch[0]), msg_txt)
            success += 1
            await asyncio.sleep(0.1)
        except Exception:
            fail += 1
    db.add_broadcast(uid, "text", "channels_only", msg_txt, success, fail)
    await safe_edit(cb, f"✅ اكتمل الإرسال\n\nنجح: {success} | فشل: {fail}", build_keyboard([[back_btn("admin_broadcast")]]))


@bot.on_callback_query(filters.regex("^confirm_broadcast_all_channels$"))
async def cb_confirm_broadcast_all_channels(client: Client, cb: CallbackQuery):
    uid = cb.from_user.id
    state = session_states.get(uid, {})
    if state.get("state") != "awaiting_broadcast_message_all_channels":
        await cb.answer("❌ انتهت الجلسة.", show_alert=True)
        return
    msg_txt = state["message"]
    session_states.pop(uid, None)
    await safe_edit(cb, "⏳ جاري الإرسال لكل القنوات...")
    channels = db.cursor.execute("SELECT DISTINCT channel_id FROM user_channels WHERE is_blocked = 0").fetchall()
    success = fail = 0
    for ch in channels:
        try:
            await bot.send_message(int(ch[0]), msg_txt)
            success += 1
            await asyncio.sleep(0.1)
        except Exception:
            fail += 1
    db.add_broadcast(uid, "text", "all_channels", msg_txt, success, fail)
    await safe_edit(cb, f"✅ اكتمل الإرسال\n\nنجح: {success} | فشل: {fail}", build_keyboard([[back_btn("admin_broadcast")]]))


@bot.on_callback_query(filters.regex("^cancel_broadcast$"))
async def cb_cancel_broadcast(client: Client, cb: CallbackQuery):
    session_states.pop(cb.from_user.id, None)
    await cb_admin_broadcast(client, cb)


@bot.on_callback_query(filters.regex("^admin_previous_broadcasts$"))
async def cb_previous_broadcasts(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    broadcasts = db.get_recent_broadcasts(10)
    if not broadcasts:
        text = "📋 لا توجد إذاعات سابقة."
    else:
        text = "📋 **آخر 10 إذاعات:**\n\n"
        for i, b in enumerate(broadcasts, 1):
            text += f"{i}. {b[4][:30]} — ✅{b[6]} ❌{b[7]} | {b[5][:19]}\n"
    await safe_edit(cb, text, build_keyboard([[back_btn("admin_broadcast")]]))


@bot.on_callback_query(filters.regex("^admin_ban_user$"))
async def cb_admin_ban_user(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    session_states[cb.from_user.id] = {"state": "awaiting_ban_user"}
    await safe_edit(cb, "⛔ أرسل معرف المستخدم أو اليوزر لحظره:", build_keyboard([[back_btn("admin_users")]]))


@bot.on_callback_query(filters.regex("^admin_unban_user$"))
async def cb_admin_unban_user(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    session_states[cb.from_user.id] = {"state": "awaiting_unban_user"}
    await safe_edit(cb, "✅ أرسل معرف المستخدم أو اليوزر لفك حظره:", build_keyboard([[back_btn("admin_users")]]))


@bot.on_callback_query(filters.regex("^admin_banned_users$"))
async def cb_admin_banned_users(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    banned = db.get_blocked_users()
    text = f"⛔ **المحظورون ({len(banned)})**\n\n" if banned else "⛔ لا يوجد مستخدمون محظورون."
    for i, u in enumerate(banned[:10], 1):
        text += f"{i}. ID: `{u[0]}` | @{u[4] or 'بدون'}\n"
    await safe_edit(cb, text, build_keyboard([
        [btn("🔄 تحديث", callback="admin_banned_users", style="primary"), back_btn("admin_users")]
    ]))


@bot.on_callback_query(filters.regex("^admin_view_users$"))
async def cb_admin_view_users(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    users = db.get_all_users()
    text = f"👥 **المستخدمون ({len(users)})**\n\n"
    for i, u in enumerate(users[:20], 1):
        text += f"{i}. {u[2]} (@{u[1] or 'بدون'}) | {u[3][:10]}\n"
    await safe_edit(cb, text, build_keyboard([[back_btn("admin_users")]]))


@bot.on_callback_query(filters.regex("^admin_users_stats$"))
async def cb_admin_users_stats(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    text = (
        f"📊 **إحصائيات المستخدمين**\n\n"
        f"الإجمالي: {db.get_total_users()}\n"
        f"اليوم: {db.get_today_users()}\n"
        f"المحظورون: {db.get_banned_users_count()}"
    )
    await safe_edit(cb, text, build_keyboard([[back_btn("admin_users")]]))


@bot.on_callback_query(filters.regex("^admin_search_user$"))
async def cb_admin_search_user(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    session_states[cb.from_user.id] = {"state": "awaiting_search_user"}
    await safe_edit(cb, "🔍 أرسل معرف أو يوزر المستخدم:", build_keyboard([[back_btn("admin_users")]]))


@bot.on_callback_query(filters.regex("^admin_add_votes$"))
async def cb_admin_add_votes(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    session_states[cb.from_user.id] = {"state": "awaiting_admin_add_votes_link"}
    await safe_edit(cb, "➕ أرسل رابط منشور المشارك لإضافة أصوات:", build_keyboard([[back_btn("admin_votes")]]))


@bot.on_callback_query(filters.regex("^admin_remove_votes$"))
async def cb_admin_remove_votes(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    session_states[cb.from_user.id] = {"state": "awaiting_admin_remove_votes_link"}
    await safe_edit(cb, "➖ أرسل رابط منشور المشارك لخصم أصوات:", build_keyboard([[back_btn("admin_votes")]]))


@bot.on_callback_query(filters.regex("^admin_votes_stats$"))
async def cb_admin_votes_stats(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    total = db.cursor.execute("SELECT COUNT(*) FROM votes").fetchone()[0]
    text = f"🗳️ **إحصائيات التصويتات**\n\nاليوم: {db.get_today_votes()}\nالإجمالي: {total}"
    await safe_edit(cb, text, build_keyboard([[back_btn("admin_votes")]]))


@bot.on_callback_query(filters.regex("^admin_votes_log$"))
async def cb_admin_votes_log(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    logs = db.cursor.execute("""
        SELECT vm.*, u.username, p.display_name
        FROM vote_modifications vm
        LEFT JOIN users u ON vm.modifier_id = u.user_id
        LEFT JOIN participants p ON vm.participant_id = p.participant_id
        ORDER BY vm.modification_date DESC LIMIT 20
    """).fetchall()
    if not logs:
        text = "📋 لا توجد تعديلات على التصويتات."
    else:
        text = "📋 **آخر 20 تعديل:**\n\n"
        for i, log in enumerate(logs, 1):
            text += f"{i}. {log[4]} | {abs(log[7])} صوت → {log[11] or 'مجهول'}\n"
    await safe_edit(cb, text, build_keyboard([[back_btn("admin_votes")]]))


@bot.on_callback_query(filters.regex("^admin_block_channel$"))
async def cb_admin_block_channel(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    session_states[cb.from_user.id] = {"state": "awaiting_block_channel"}
    await safe_edit(cb, "⛔ أرسل رابط القناة لحظرها:", build_keyboard([[back_btn("admin_channels")]]))


@bot.on_callback_query(filters.regex("^admin_unblock_channel$"))
async def cb_admin_unblock_channel(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    session_states[cb.from_user.id] = {"state": "awaiting_unblock_channel"}
    await safe_edit(cb, "✅ أرسل رابط القناة لفك حظرها:", build_keyboard([[back_btn("admin_channels")]]))


@bot.on_callback_query(filters.regex("^admin_view_channels$"))
async def cb_admin_view_channels(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    channels = db.cursor.execute(
        "SELECT * FROM user_channels WHERE is_blocked = 0 ORDER BY added_date DESC LIMIT 20"
    ).fetchall()
    text = f"📢 **القنوات ({len(channels)})**\n\n"
    for i, ch in enumerate(channels, 1):
        text += f"{i}. {ch[4]} (@{ch[3] or 'بدون'}) | {ch[5][:10]}\n"
    await safe_edit(cb, text or "📢 لا توجد قنوات.", build_keyboard([[back_btn("admin_channels")]]))


@bot.on_callback_query(filters.regex("^admin_channels_stats$"))
async def cb_admin_channels_stats(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    total = db.get_all_channels_count()
    blocked = db.cursor.execute("SELECT COUNT(*) FROM user_channels WHERE is_blocked = 1").fetchone()[0]
    text = f"📊 **إحصائيات القنوات**\n\nالإجمالي: {total}\nمحظورة: {blocked}"
    await safe_edit(cb, text, build_keyboard([[back_btn("admin_channels")]]))


@bot.on_callback_query(filters.regex("^admin_search_channel$"))
async def cb_admin_search_channel(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    session_states[cb.from_user.id] = {"state": "awaiting_search_channel"}
    await safe_edit(cb, "🔍 أرسل رابط القناة أو يوزرها:", build_keyboard([[back_btn("admin_channels")]]))


@bot.on_callback_query(filters.regex("^admin_delete_channel$"))
async def cb_admin_delete_channel(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    session_states[cb.from_user.id] = {"state": "awaiting_delete_channel"}
    await safe_edit(cb, "🗑️ أرسل رابط القناة لحذفها:", build_keyboard([[back_btn("admin_channels")]]))


@bot.on_callback_query(filters.regex("^admin_add_public_channel$"))
async def cb_admin_add_public_channel(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    session_states[cb.from_user.id] = {"state": "awaiting_public_channel"}
    await safe_edit(cb, "📢 أرسل رابط القناة العامة:", build_keyboard([[back_btn("admin_forced_sub")]]))


@bot.on_callback_query(filters.regex("^admin_add_private_channel$"))
async def cb_admin_add_private_channel(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    session_states[cb.from_user.id] = {"state": "awaiting_private_channel"}
    await safe_edit(cb, "🔒 أرسل رابط دعوة القناة الخاصة:", build_keyboard([[back_btn("admin_forced_sub")]]))


@bot.on_callback_query(filters.regex("^admin_add_public_group$"))
async def cb_admin_add_public_group(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    session_states[cb.from_user.id] = {"state": "awaiting_public_group"}
    await safe_edit(cb, "👥 أرسل رابط الجروب العام:", build_keyboard([[back_btn("admin_forced_sub")]]))


@bot.on_callback_query(filters.regex("^admin_add_private_group$"))
async def cb_admin_add_private_group(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    session_states[cb.from_user.id] = {"state": "awaiting_private_group"}
    await safe_edit(cb, "🔒 أرسل رابط دعوة الجروب الخاص:", build_keyboard([[back_btn("admin_forced_sub")]]))


@bot.on_callback_query(filters.regex("^admin_view_forced_channels$"))
async def cb_admin_view_forced_channels(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    channels = db.get_forced_channels()
    if not channels:
        text = "📢 لا توجد قنوات اشتراك إجباري."
    else:
        text = f"📢 **القنوات الإجبارية ({len(channels)})**\n\n"
        for i, ch in enumerate(channels, 1):
            text += f"{i}. {ch[3]} — {ch[4]}\n"
    await safe_edit(cb, text, build_keyboard([[back_btn("admin_forced_sub")]]))


@bot.on_callback_query(filters.regex("^admin_view_forced_groups$"))
async def cb_admin_view_forced_groups(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    groups = db.get_forced_groups()
    if not groups:
        text = "👥 لا توجد جروبات اشتراك إجباري."
    else:
        text = f"👥 **الجروبات الإجبارية ({len(groups)})**\n\n"
        for i, g in enumerate(groups, 1):
            text += f"{i}. {g[3]} — {g[4]}\n"
    await safe_edit(cb, text, build_keyboard([[back_btn("admin_forced_sub")]]))


@bot.on_callback_query(filters.regex("^admin_delete_forced_channel$"))
async def cb_admin_delete_forced_channel(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    session_states[cb.from_user.id] = {"state": "awaiting_delete_forced_channel"}
    await safe_edit(cb, "🗑️ أرسل رابط القناة لإزالتها من الاشتراك الإجباري:", build_keyboard([[back_btn("admin_forced_sub")]]))


@bot.on_callback_query(filters.regex("^admin_delete_forced_group$"))
async def cb_admin_delete_forced_group(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    session_states[cb.from_user.id] = {"state": "awaiting_delete_forced_group"}
    await safe_edit(cb, "🗑️ أرسل رابط الجروب لإزالته من الاشتراك الإجباري:", build_keyboard([[back_btn("admin_forced_sub")]]))


@bot.on_callback_query(filters.regex("^admin_add_admin$"))
async def cb_admin_add_admin(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    session_states[cb.from_user.id] = {"state": "awaiting_add_admin"}
    await safe_edit(cb, "➕ أرسل معرف المستخدم لإضافته كمشرف:", build_keyboard([[back_btn("admin_manage_admins")]]))


@bot.on_callback_query(filters.regex("^admin_remove_admin$"))
async def cb_admin_remove_admin(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    session_states[cb.from_user.id] = {"state": "awaiting_remove_admin"}
    await safe_edit(cb, "➖ أرسل معرف المستخدم لإزالة صلاحياته:", build_keyboard([[back_btn("admin_manage_admins")]]))


@bot.on_callback_query(filters.regex("^admin_manual_post_channel$"))
async def cb_admin_manual_post_channel(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    session_states[cb.from_user.id] = {"state": "awaiting_manual_post_channel"}
    await safe_edit(cb, "📢 أرسل رابط القناة للنشر فيها:", build_keyboard([[back_btn("admin_manual_post")]]))


@bot.on_callback_query(filters.regex("^admin_view_manual_posts$"))
async def cb_admin_view_manual_posts(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    posts = db.cursor.execute(
        "SELECT * FROM manual_posts ORDER BY added_date DESC LIMIT 20"
    ).fetchall()
    if not posts:
        text = "📝 لا توجد منشورات يدوية."
    else:
        text = f"📝 **المنشورات اليدوية ({len(posts)})**\n\n"
        for i, p in enumerate(posts, 1):
            text += f"{i}. {p[4]} في {p[3]} | {p[6][:19]}\n"
    await safe_edit(cb, text, build_keyboard([[back_btn("admin_manual_post")]]))


@bot.on_callback_query(filters.regex("^admin_add_channel_control$"))
async def cb_admin_add_channel_control(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    session_states[cb.from_user.id] = {"state": "awaiting_channel_control"}
    await safe_edit(cb, "➕ أرسل رابط القناة لإضافتها للتحكم:", build_keyboard([[back_btn("admin_channel_control")]]))


@bot.on_callback_query(filters.regex("^admin_view_controlled_channels$"))
async def cb_admin_view_controlled_channels(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    channels = db.get_all_channels_control()
    if not channels:
        text = "📋 لا توجد قنوات مُضافة للتحكم."
    else:
        text = f"📋 **قنوات التحكم ({len(channels)})**\n\n"
        for i, ch in enumerate(channels, 1):
            text += f"{i}. {ch[2]} | مسابقات: {ch[7]} | أصوات: {ch[8]}\n"
    await safe_edit(cb, text, build_keyboard([[back_btn("admin_channel_control")]]))


@bot.on_callback_query(filters.regex("^admin_control_channel$"))
async def cb_admin_control_channel(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    session_states[cb.from_user.id] = {"state": "awaiting_channel_control_admin"}
    await safe_edit(cb, "🛠️ أرسل رابط القناة للتحكم بها:", build_keyboard([[back_btn("admin_channel_control")]]))


@bot.on_callback_query(filters.regex("^admin_controlled_channels_stats$"))
async def cb_admin_controlled_channels_stats(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    channels = db.get_all_channels_control()
    total_contests = sum(c[7] or 0 for c in channels)
    total_votes = sum(c[8] or 0 for c in channels)
    text = (
        f"📊 **إحصائيات قنوات التحكم**\n\n"
        f"عدد القنوات: {len(channels)}\n"
        f"إجمالي المسابقات: {total_contests}\n"
        f"إجمالي الأصوات: {total_votes}"
    )
    await safe_edit(cb, text, build_keyboard([[back_btn("admin_channel_control")]]))


@bot.on_callback_query(filters.regex("^admin_remove_channel_control$"))
async def cb_admin_remove_channel_control(client: Client, cb: CallbackQuery):
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    session_states[cb.from_user.id] = {"state": "awaiting_remove_channel_control"}
    await safe_edit(cb, "🗑️ أرسل رابط القناة لإزالتها من التحكم:", build_keyboard([[back_btn("admin_channel_control")]]))


@bot.on_callback_query(filters.regex("^admin_list_members_"))
async def cb_admin_list_members(client: Client, cb: CallbackQuery):
    channel_id = cb.data.replace("admin_list_members_", "")
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    try:
        chat = await bot.get_chat(int(channel_id))
        subs = await get_channel_subscriber_count(channel_id)
        text = f"👥 **{chat.title}**\n\nالمشتركون: {subs}"
        keyboard = build_keyboard([
            [btn("⛔ حظر عضو", callback=f"admin_ban_member_{channel_id}", style="danger"), btn("✅ فك حظر", callback=f"admin_unban_member_{channel_id}", style="success")],
            [btn("🔇 كتم", callback=f"admin_mute_member_{channel_id}", style="danger"), btn("🔊 فك كتم", callback=f"admin_unmute_member_{channel_id}", style="success")],
            [btn("👑 ترقية", callback=f"admin_promote_member_{channel_id}", style="primary"), btn("👢 طرد", callback=f"admin_kick_member_{channel_id}", style="danger")],
            [back_btn("admin_control_channel")]
        ])
        await safe_edit(cb, text, keyboard)
    except Exception as e:
        await cb.answer(f"❌ خطأ: {e}", show_alert=True)


@bot.on_callback_query(filters.regex("^admin_pin_message_"))
async def cb_admin_pin_message(client: Client, cb: CallbackQuery):
    channel_id = cb.data.replace("admin_pin_message_", "")
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    session_states[cb.from_user.id] = {"state": "awaiting_pin_message", "channel_id": channel_id}
    await safe_edit(cb, "📌 أرسل معرف الرسالة لتثبيتها:", build_keyboard([[back_btn(f"admin_list_members_{channel_id}")]]))


@bot.on_callback_query(filters.regex("^admin_unpin_message_"))
async def cb_admin_unpin_message(client: Client, cb: CallbackQuery):
    channel_id = cb.data.replace("admin_unpin_message_", "")
    if not db.is_admin(cb.from_user.id):
        await cb.answer("❌ ليس لديك صلاحية.", show_alert=True)
        return
    session_states[cb.from_user.id] = {"state": "awaiting_unpin_message", "channel_id": channel_id}
    await safe_edit(cb, "📌 أرسل معرف الرسالة لإلغاء تثبيتها:", build_keyboard([[back_btn(f"admin_list_members_{channel_id}")]]))


async def _handle_manual_participant_name(uid: int, text: str, state: dict, message: Message):
    contest_id = state["contest_id"]
    if is_forbidden_name(text):
        await message.reply("❌ الاسم يحتوي على محتوى محظور (روابط، شتائم، إلخ). أرسل اسماً مناسباً.")
        return
    del session_states[uid]
    contest = db.get_contest_by_id(contest_id)
    if not contest:
        await message.reply("❌ المسابقة غير موجودة.")
        return
    pid = db.add_participant(contest_id, 0, text.strip())
    if not pid:
        await message.reply("❌ فشل إضافة المشارك.")
        return
    me = await bot.get_me()
    join_url = contest[9] or f"https://t.me/{me.username}?start=join_{contest_id}_{contest[3]}"
    sent_id = await post_participant_to_channel(contest_id, pid, contest[3], join_url)
    if sent_id:
        ch_url = await get_channel_url(contest[3], contest[4])
        post_link = f"{ch_url}/{sent_id}"
        db.add_manual_post(uid, contest[3], contest[4] or "", text.strip(), sent_id)
        try:
            await bot.send_message(
                uid,
                f"📢 **تم النشر!**\n\n👤 {text.strip()}\n🔗 {post_link}"
            )
        except Exception:
            pass
        await message.reply(f"✅ تم النشر!\n👤 {text.strip()}\n🔗 {post_link}")
    else:
        await message.reply(f"✅ تمت الإضافة لكن فشل النشر في القناة.")


async def _handle_voting_channel_link(uid: int, text: str, message: Message):
    del session_states[uid]
    try:
        chat = await resolve_channel(text)
        if not chat:
            await message.reply("❌ رابط القناة غير صحيح.")
            return
        if not await is_bot_admin(str(chat.id)):
            await message.reply("❌ البوت غير مشرف في هذه القناة.")
            return
        if not await is_user_admin_in_channel(uid, str(chat.id)):
            await message.reply("❌ أنت لست مشرفاً في هذه القناة.")
            return
        if db.is_channel_blocked(str(chat.id)):
            await message.reply("❌ هذه القناة محظورة. تواصل مع الدعم.")
            return
        if db.add_user_channel(uid, str(chat.id), chat.username or "", chat.title):
            await notify_admin_channel_added(str(chat.id), chat.title, uid, message.from_user.username or "", message.from_user.first_name or "")
            perms = await get_bot_permissions_text(str(chat.id))
            subs = await get_channel_subscriber_count(str(chat.id))
            db.add_channel_control(str(chat.id), chat.title, chat.username or "", uid, perms)
            db.update_channel_stats(str(chat.id), subscribers_count=subs)
            try:
                await bot.send_message(int(chat.id), f"مرحباً بأعضاء {chat.title} 👋\nأنا هنا لإدارة مسابقاتكم 🏆")
            except Exception:
                pass
            await message.reply(
                f"✅ تمت إضافة القناة بنجاح!\n\n"
                f"📢 {chat.title}\n👥 {subs} مشترك\n🛠️ الصلاحيات: {perms}"
            )
        else:
            await message.reply("❌ حدث خطأ أثناء الإضافة.")
    except Exception as e:
        await message.reply(f"❌ فشل: {e}")


async def _handle_contest_description(uid: int, text: str, state: dict, message: Message):
    channel_id = state["channel_id"]
    channel_username = state["channel_username"]
    channel_title = state["channel_title"]
    ctype = state.get("contest_type", "manual")
    auto_approve = state.get("auto_approve", True)
    if ctype == "manual":
        session_states[uid] = {
            "state": "awaiting_contest_button_url",
            "channel_id": channel_id,
            "channel_username": channel_username,
            "channel_title": channel_title,
            "contest_type": ctype,
            "description": text,
            "auto_approve": auto_approve
        }
        await message.reply("✅ تم حفظ الوصف.\n\n🔗 أرسل رابط زر المشاركة:", reply_markup=build_keyboard([[back_btn("create_manual_contest")]]))
    else:
        del session_states[uid]
        try:
            me = await bot.get_me()
            placeholder_url = f"https://t.me/{me.username}?start=join_{channel_id}"
            keyboard = build_keyboard([[btn("🎯 المشاركة", url=placeholder_url, style="primary")]])
            sent = await bot.send_message(int(channel_id), f"{text}\n\n🔗 للمشاركة اضغط الزر 👇", reply_markup=keyboard)
            cid = db.create_contest(uid, text, channel_id, channel_username, sent.id, "auto", None, auto_approve)
            if cid:
                db.update_channel_stats(channel_id, contest_count=1)
                new_url = f"https://t.me/{me.username}?start=join_{cid}_{channel_id}"
                await sent.edit_reply_markup(build_keyboard([[btn("🎯 المشاركة", url=new_url, style="primary")]]))
                await message.reply(f"✅ تم إنشاء المسابقة التلقائية!\n📢 {channel_title}")
            else:
                await message.reply("❌ حدث خطأ أثناء الحفظ.")
        except Exception as e:
            await message.reply(f"❌ فشل: {e}")


async def _handle_contest_button_url(uid: int, text: str, state: dict, message: Message):
    channel_id = state["channel_id"]
    channel_username = state["channel_username"]
    channel_title = state["channel_title"]
    desc = state["description"]
    auto_approve = state.get("auto_approve", True)
    del session_states[uid]
    try:
        keyboard = build_keyboard([[btn("🎯 المشاركة", url=text, style="primary")]])
        sent = await bot.send_message(int(channel_id), f"{desc}\n\n🔗 للمشاركة اضغط الزر 👇", reply_markup=keyboard)
        cid = db.create_contest(uid, desc, channel_id, channel_username, sent.id, "manual", text, auto_approve)
        if cid:
            db.update_channel_stats(channel_id, contest_count=1)
            await message.reply(f"✅ تم إنشاء المسابقة اليدوية!\n📢 {channel_title}")
        else:
            await message.reply("❌ حدث خطأ أثناء الحفظ.")
    except Exception as e:
        await message.reply(f"❌ فشل: {e}")


async def _handle_participant_name(uid: int, text: str, state: dict, message: Message):
    contest_id = state["contest_id"]
    if is_forbidden_name(text):
        await message.reply("❌ الاسم يحتوي على محتوى محظور. أرسل اسماً مناسباً.")
        return
    del session_states[uid]
    contest = db.get_contest_by_id(contest_id)
    if not contest or not contest[7]:
        await message.reply("❌ المسابقة غير موجودة أو منتهية.")
        return
    if db.get_participant_by_user(contest_id, uid):
        await message.reply("❌ أنت مشارك بالفعل.")
        return
    auto_approve = bool(contest[10])
    pid = db.add_participant(contest_id, uid, text.strip(), is_approved=auto_approve)
    if not pid:
        await message.reply("❌ فشلت المشاركة.")
        return
    await notify_contest_owner_participant(contest_id, text.strip(), uid, message.from_user.username or "", message.from_user.first_name or "", contest[3], contest[4] or "", is_approved=auto_approve)
    if auto_approve:
        me = await bot.get_me()
        join_url = contest[9] or f"https://t.me/{me.username}?start=join_{contest_id}_{contest[3]}"
        sent_id = await post_participant_to_channel(contest_id, pid, contest[3], join_url)
        if sent_id:
            await message.reply(f"✅ شاركت بنجاح!\n👤 {text.strip()}\nتم نشر منشورك في القناة.")
        else:
            await message.reply(f"✅ تمت المشاركة، لكن فشل النشر في القناة.")
    else:
        await message.reply("✅ تم إرسال طلب مشاركتك. بانتظار موافقة المسؤول.")


async def _handle_votes_link_and_amount(uid: int, text: str, state: dict, message: Message, is_add: bool, is_admin_action: bool = False):
    state_key = state["state"]
    if "link" in state_key:
        part, err = await find_participant_by_message_link(text)
        if err or not part:
            await message.reply(err or "❌ لم أجد المشارك.")
            return
        if not is_admin_action:
            contest = db.get_contest_by_id(part[1])
            if not contest or contest[1] != uid:
                await message.reply("❌ هذه المسابقة ليست لك.")
                return
        next_state = "awaiting_add_votes_amount" if is_add else "awaiting_remove_votes_amount"
        if is_admin_action:
            next_state = "awaiting_admin_add_votes_amount" if is_add else "awaiting_admin_remove_votes_amount"
        session_states[uid] = {"state": next_state, "participant_id": part[0]}
        verb = "إضافة" if is_add else "خصم"
        await message.reply(f"{'➕' if is_add else '➖'} {verb} أصوات لـ **{part[3]}** (الحالي: {part[5]})\n\nأرسل العدد:")
    elif "amount" in state_key or "specific" in state_key:
        pid = state.get("participant_id")
        del session_states[uid]
        try:
            amt = int(text)
            max_amt = 10000 if is_admin_action else 1000
            if amt <= 0 or amt > max_amt:
                await message.reply(f"❌ الرقم غير صالح (1-{max_amt}).")
                return
            final_amt = amt if is_add else -amt
            success, result = await apply_vote_modification(pid, final_amt, uid, ("admin" if is_admin_action else "user"))
            await message.reply(result)
        except ValueError:
            await message.reply("❌ أرسل رقماً صحيحاً.")


@bot.on_message(filters.private & filters.text)
async def handle_text_messages(client: Client, message: Message):
    uid = message.from_user.id
    text = message.text.strip()

    if uid not in session_states:
        await message.reply("❓ استخدم /start للبدء.")
        return

    state_data = session_states[uid]
    state = state_data.get("state", "")

    if state == "awaiting_manual_participant_name":
        await _handle_manual_participant_name(uid, text, state_data, message)

    elif state == "awaiting_ban_user_contests":
        del session_states[uid]
        user = await resolve_user(text)
        if user:
            db.ban_user(user.id, uid, "من الإعدادات")
            await message.reply(f"✅ تم حظر {user.first_name}.")
        else:
            await message.reply("❌ لم يُعثر على المستخدم.")

    elif state == "awaiting_unban_user_contests":
        del session_states[uid]
        user = await resolve_user(text)
        if user:
            db.unban_user(user.id)
            await message.reply(f"✅ تم فك حظر {user.first_name}.")
        else:
            await message.reply("❌ لم يُعثر على المستخدم.")

    elif state == "awaiting_voting_channel_link":
        await _handle_voting_channel_link(uid, text, message)

    elif state == "awaiting_contest_description":
        await _handle_contest_description(uid, text, state_data, message)

    elif state == "awaiting_contest_button_url":
        await _handle_contest_button_url(uid, text, state_data, message)

    elif state == "awaiting_participant_name":
        await _handle_participant_name(uid, text, state_data, message)

    elif state in ("awaiting_add_votes_link", "awaiting_add_votes_amount", "awaiting_add_votes_amount_specific"):
        await _handle_votes_link_and_amount(uid, text, state_data, message, is_add=True)

    elif state in ("awaiting_remove_votes_link", "awaiting_remove_votes_amount", "awaiting_remove_votes_amount_specific"):
        await _handle_votes_link_and_amount(uid, text, state_data, message, is_add=False)

    elif state in ("awaiting_admin_add_votes_link", "awaiting_admin_add_votes_amount"):
        await _handle_votes_link_and_amount(uid, text, state_data, message, is_add=True, is_admin_action=True)

    elif state in ("awaiting_admin_remove_votes_link", "awaiting_admin_remove_votes_amount"):
        await _handle_votes_link_and_amount(uid, text, state_data, message, is_add=False, is_admin_action=True)

    elif state == "awaiting_block_channel":
        del session_states[uid]
        try:
            chat = await resolve_channel(text)
            if chat:
                db.block_channel(str(chat.id))
                await message.reply(f"✅ تم حظر القناة: {chat.title}")
            else:
                await message.reply("❌ رابط غير صحيح.")
        except Exception as e:
            await message.reply(f"❌ فشل: {e}")

    elif state == "awaiting_unblock_channel":
        del session_states[uid]
        try:
            chat = await resolve_channel(text)
            if chat:
                db.unblock_channel(str(chat.id))
                await message.reply(f"✅ تم فك حظر القناة: {chat.title}")
            else:
                await message.reply("❌ رابط غير صحيح.")
        except Exception as e:
            await message.reply(f"❌ فشل: {e}")

    elif state == "awaiting_broadcast_user":
        del session_states[uid]
        user = await resolve_user(text)
        if user:
            session_states[uid] = {"state": "awaiting_broadcast_message_user", "target_user_id": user.id, "target_name": user.first_name}
            await message.reply(f"👤 إرسال رسالة إلى {user.first_name}\n\nأرسل نص الرسالة:")
        else:
            await message.reply("❌ لم يُعثر على المستخدم.")

    elif state == "awaiting_broadcast_message_user":
        target_id = state_data["target_user_id"]
        target_name = state_data["target_name"]
        del session_states[uid]
        try:
            await bot.send_message(target_id, text)
            await message.reply(f"✅ تم الإرسال إلى {target_name}.")
        except Exception as e:
            await message.reply(f"❌ فشل: {e}")

    elif state == "awaiting_broadcast_all":
        del session_states[uid]
        session_states[uid] = {"state": "awaiting_broadcast_message_all", "message": text}
        await message.reply(
            f"📢 إذاعة لكل المستخدمين ({db.get_total_users()})\n\nتأكيد الإرسال؟",
            reply_markup=build_keyboard([[btn("✅ إرسال", callback="confirm_broadcast_all", style="success"), btn("❌ إلغاء", callback="cancel_broadcast", style="danger")]])
        )

    elif state == "awaiting_broadcast_channels":
        del session_states[uid]
        session_states[uid] = {"state": "awaiting_broadcast_message_channels", "message": text}
        await message.reply(
            f"📢 إذاعة للقنوات ({db.get_all_channels_count()})\n\nتأكيد الإرسال؟",
            reply_markup=build_keyboard([[btn("✅ إرسال", callback="confirm_broadcast_channels", style="success"), btn("❌ إلغاء", callback="cancel_broadcast", style="danger")]])
        )

    elif state == "awaiting_broadcast_specific_channel":
        del session_states[uid]
        try:
            chat = await resolve_channel(text)
            if chat:
                session_states[uid] = {"state": "awaiting_broadcast_message_specific_channel", "channel_id": str(chat.id), "channel_title": chat.title}
                await message.reply(f"📢 إرسال إلى {chat.title}\n\nأرسل نص الرسالة:")
            else:
                await message.reply("❌ رابط غير صحيح.")
        except Exception as e:
            await message.reply(f"❌ فشل: {e}")

    elif state == "awaiting_broadcast_message_specific_channel":
        ch_id = state_data["channel_id"]
        ch_title = state_data["channel_title"]
        del session_states[uid]
        try:
            await bot.send_message(int(ch_id), text)
            await message.reply(f"✅ تم الإرسال إلى {ch_title}.")
        except Exception as e:
            await message.reply(f"❌ فشل: {e}")

    elif state == "awaiting_broadcast_all_channels":
        del session_states[uid]
        session_states[uid] = {"state": "awaiting_broadcast_message_all_channels", "message": text}
        await message.reply(
            f"📢 إذاعة لكل القنوات ({db.get_all_channels_count()})\n\nتأكيد الإرسال؟",
            reply_markup=build_keyboard([[btn("✅ إرسال", callback="confirm_broadcast_all_channels", style="success"), btn("❌ إلغاء", callback="cancel_broadcast", style="danger")]])
        )

    elif state == "awaiting_ban_user":
        del session_states[uid]
        user = await resolve_user(text)
        if user:
            db.ban_user(user.id, uid)
            await message.reply(f"✅ تم حظر {user.first_name}.")
        else:
            await message.reply("❌ لم يُعثر على المستخدم.")

    elif state == "awaiting_unban_user":
        del session_states[uid]
        user = await resolve_user(text)
        if user:
            db.unban_user(user.id)
            await message.reply(f"✅ تم فك حظر {user.first_name}.")
        else:
            await message.reply("❌ لم يُعثر على المستخدم.")

    elif state == "awaiting_add_admin":
        del session_states[uid]
        user = await resolve_user(text)
        if user:
            db.add_admin(user.id, uid)
            await message.reply(f"✅ تمت إضافة {user.first_name} كمشرف.")
        else:
            await message.reply("❌ لم يُعثر على المستخدم.")

    elif state == "awaiting_remove_admin":
        del session_states[uid]
        user = await resolve_user(text)
        if user:
            if user.id == ADMIN_ID:
                await message.reply("❌ لا يمكن إزالة المشرف الرئيسي.")
            else:
                db.remove_admin(user.id)
                await message.reply(f"✅ تمت إزالة {user.first_name} من المشرفين.")
        else:
            await message.reply("❌ لم يُعثر على المستخدم.")

    elif state == "awaiting_public_channel":
        del session_states[uid]
        await _register_forced_channel(message, text, is_public=True)

    elif state == "awaiting_private_channel":
        del session_states[uid]
        await _register_forced_channel(message, text, is_public=False)

    elif state == "awaiting_public_group":
        del session_states[uid]
        await _register_forced_group(message, text, is_public=True)

    elif state == "awaiting_private_group":
        del session_states[uid]
        await _register_forced_group(message, text, is_public=False)

    elif state == "awaiting_delete_forced_channel":
        del session_states[uid]
        await _remove_forced_channel(message, text)

    elif state == "awaiting_delete_forced_group":
        del session_states[uid]
        await _remove_forced_group(message, text)

    elif state == "awaiting_channel_control":
        del session_states[uid]
        try:
            chat = await resolve_channel(text)
            if not chat:
                await message.reply("❌ رابط غير صحيح.")
                return
            if not await is_bot_admin(str(chat.id)):
                await message.reply("❌ البوت غير مشرف في هذه القناة.")
                return
            perms = await get_bot_permissions_text(str(chat.id))
            subs = await get_channel_subscriber_count(str(chat.id))
            if db.add_channel_control(str(chat.id), chat.title, chat.username or "", uid, perms):
                db.update_channel_stats(str(chat.id), subscribers_count=subs)
                await message.reply(f"✅ تمت إضافة القناة للتحكم.\n📢 {chat.title}\n👥 {subs} مشترك")
            else:
                await message.reply("❌ حدث خطأ أثناء الإضافة.")
        except Exception as e:
            await message.reply(f"❌ فشل: {e}")

    elif state == "awaiting_channel_control_admin":
        del session_states[uid]
        try:
            chat = await resolve_channel(text)
            if not chat:
                await message.reply("❌ رابط غير صحيح.")
                return
            if not await is_bot_admin(str(chat.id)):
                await message.reply("❌ البوت غير مشرف في هذه القناة.")
                return
            keyboard = build_keyboard([
                [btn("👥 الأعضاء", callback=f"admin_list_members_{chat.id}", style="primary"), btn("📌 تثبيت رسالة", callback=f"admin_pin_message_{chat.id}", style="primary")],
                [btn("📌 إلغاء تثبيت", callback=f"admin_unpin_message_{chat.id}", style="primary")],
                [back_btn("admin_channel_control")]
            ])
            await message.reply(f"🛠️ **التحكم في {chat.title}**", reply_markup=keyboard)
        except Exception as e:
            await message.reply(f"❌ فشل: {e}")

    elif state == "awaiting_manual_post_channel":
        del session_states[uid]
        try:
            chat = await resolve_channel(text)
            if not chat:
                await message.reply("❌ رابط غير صحيح.")
                return
            if not await is_bot_admin(str(chat.id)):
                await message.reply("❌ البوت غير مشرف في هذه القناة.")
                return
            session_states[uid] = {
                "state": "awaiting_manual_post_name",
                "channel_id": str(chat.id),
                "channel_title": chat.title,
                "channel_username": chat.username or ""
            }
            await message.reply(f"📝 نشر يدوي في **{chat.title}**\n\nأرسل اسم المشارك:", reply_markup=build_keyboard([[back_btn("admin_manual_post")]]))
        except Exception as e:
            await message.reply(f"❌ فشل: {e}")

    elif state == "awaiting_manual_post_name":
        ch_id = state_data["channel_id"]
        ch_title = state_data["channel_title"]
        ch_username = state_data["channel_username"]
        if is_forbidden_name(text):
            await message.reply("❌ الاسم يحتوي على محتوى محظور.")
            return
        del session_states[uid]
        try:
            emoji = random.choice(VOTE_EMOJIS)
            join_url = f"https://t.me/{ch_username}" if ch_username else "https://t.me/"
            keyboard = build_keyboard([
                [btn(f"{emoji} تصويت (0)", callback="vote_direct_0_0", style="primary")],
                [btn("🎯 المشاركة", url=join_url, style="primary")]
            ])
            sent = await bot.send_message(int(ch_id), f"👤 **{text.strip()}** {emoji}\n\n👍 للتصويت اضغط الزر", reply_markup=keyboard)
            db.add_manual_post(uid, ch_id, ch_title, text.strip(), sent.id)
            ch_url = await get_channel_url(ch_id, ch_username)
            post_link = f"{ch_url}/{sent.id}"
            await message.reply(f"✅ تم النشر!\n👤 {text.strip()}\n🔗 {post_link}")
        except Exception as e:
            await message.reply(f"❌ فشل: {e}")

    elif state == "awaiting_advanced_contest_duration":
        channel_id = state_data["channel_id"]
        channel_username = state_data["channel_username"]
        channel_title = state_data["channel_title"]
        ctype = state_data["contest_type"]
        auto_approve = state_data["auto_approve"]
        try:
            dur = int(text)
            if dur <= 0:
                await message.reply("❌ المدة غير صالحة. أرسل رقماً موجباً.")
                return
            end_date = datetime.now() + timedelta(minutes=dur)
            session_states[uid] = {
                "state": "awaiting_advanced_contest_description",
                "channel_id": channel_id,
                "channel_username": channel_username,
                "channel_title": channel_title,
                "contest_type": ctype,
                "auto_approve": auto_approve,
                "duration": dur,
                "end_date": end_date
            }
            await message.reply(f"⏱️ المدة: {dur} دقيقة\n\n📝 أرسل وصف المسابقة والجوائز:")
        except ValueError:
            await message.reply("❌ أرسل رقماً صحيحاً.")

    elif state == "awaiting_advanced_contest_description":
        session_states[uid].update({"state": "awaiting_advanced_contest_winners", "description": text})
        keyboard = build_keyboard([
            [btn("🥇 فائز واحد", callback="winners_1", style="primary")],
            [btn("🥇🥈 فائزان", callback="winners_2", style="primary")],
            [btn("🥇🥈🥉 ثلاثة فائزين", callback="winners_3", style="primary")],
            [btn("🎯 عدد مخصص", callback="winners_custom", style="primary")],
            [back_btn("create_advanced_contest")]
        ])
        await message.reply("🏆 اختر عدد الفائزين:", reply_markup=keyboard)

    elif state == "awaiting_advanced_contest_winners_custom":
        try:
            cnt = int(text)
            if cnt <= 0 or cnt > 100:
                await message.reply("❌ العدد غير صالح (1-100).")
                return
            session_states[uid]["winners_count"] = cnt
            session_states[uid]["state"] = "awaiting_advanced_contest_prize_channel"
            await message.reply(f"🏆 {cnt} فائز\n\n📢 أرسل رابط قناة الجوائز:")
        except ValueError:
            await message.reply("❌ أرسل رقماً صحيحاً.")

    elif state == "awaiting_advanced_contest_required_votes":
        try:
            req = int(text)
            if req < 0 or req > 10000:
                await message.reply("❌ العدد غير صالح (0-10000).")
                return
            session_states[uid]["required_votes"] = req
            session_states[uid]["state"] = "awaiting_advanced_contest_prize_channel"
            await message.reply(f"🎯 الأصوات المطلوبة: {req}\n\n📢 أرسل رابط قناة الجوائز:")
        except ValueError:
            await message.reply("❌ أرسل رقماً صحيحاً.")

    elif state == "awaiting_advanced_contest_prize_channel":
        s = state_data
        channel_id = s["channel_id"]
        channel_username = s["channel_username"]
        channel_title = s["channel_title"]
        auto_approve = s["auto_approve"]
        dur = s["duration"]
        end_date = s["end_date"]
        desc = s["description"]
        winners_cnt = s.get("winners_count", 1)
        req_votes = s.get("required_votes", 0)
        prize_ch = text
        del session_states[uid]
        try:
            me = await bot.get_me()
            win_desc = f"أول {winners_cnt} حسب الترتيب" if req_votes == 0 else f"كل من يحصل على {req_votes} صوت"
            contest_text = (
                f"{desc}\n\n"
                f"⏱️ المدة: {dur} دقيقة\n"
                f"🏆 نظام الفوز: {win_desc}\n\n"
                f"🔗 للمشاركة اضغط الزر 👇"
            )
            placeholder_url = f"https://t.me/{me.username}?start=join_{channel_id}"
            sent = await bot.send_message(int(channel_id), contest_text, reply_markup=build_keyboard([[btn("🎯 المشاركة", url=placeholder_url, style="primary")]]))
            cid = db.create_contest(uid, desc, channel_id, channel_username, sent.id, "advanced", None, auto_approve, end_date, winners_cnt, req_votes, prize_ch, True)
            if cid:
                db.update_channel_stats(channel_id, contest_count=1)
                new_url = f"https://t.me/{me.username}?start=join_{cid}_{channel_id}"
                await sent.edit_reply_markup(build_keyboard([[btn("🎯 المشاركة", url=new_url, style="primary")]]))
                await message.reply(
                    f"✅ تم إنشاء المسابقة المتقدمة!\n\n"
                    f"📢 {channel_title}\n"
                    f"⏱️ {dur} دقيقة\n"
                    f"🏆 {win_desc}"
                )
            else:
                await message.reply("❌ حدث خطأ أثناء الحفظ.")
        except Exception as e:
            await message.reply(f"❌ فشل: {e}")

    elif state == "awaiting_remove_channel_control":
        del session_states[uid]
        try:
            chat = await resolve_channel(text)
            if chat:
                db.remove_channel_control(str(chat.id))
                await message.reply(f"✅ تمت إزالة {chat.title} من التحكم.")
            else:
                await message.reply("❌ رابط غير صحيح.")
        except Exception as e:
            await message.reply(f"❌ فشل: {e}")

    elif state == "awaiting_search_user":
        del session_states[uid]
        user = await resolve_user(text)
        if user:
            db_user = db.get_user(user.id)
            banned = db.is_user_banned(user.id)
            is_adm = db.is_admin(user.id)
            text_out = (
                f"🔍 **معلومات المستخدم**\n\n"
                f"👤 {user.first_name} (@{user.username or 'بدون'})\n"
                f"🆔 `{user.id}`\n"
                f"⛔ محظور: {'نعم' if banned else 'لا'}\n"
                f"🎛️ مشرف: {'نعم' if is_adm else 'لا'}\n"
                f"📅 انضم: {db_user[4][:10] if db_user else 'غير مسجل'}"
            )
            await message.reply(text_out)
        else:
            await message.reply("❌ لم يُعثر على المستخدم.")

    elif state == "awaiting_search_channel":
        del session_states[uid]
        try:
            chat = await resolve_channel(text)
            if chat:
                ch_data = db.get_channel_by_id(str(chat.id))
                is_blocked = db.is_channel_blocked(str(chat.id))
                subs = await get_channel_subscriber_count(str(chat.id))
                text_out = (
                    f"🔍 **معلومات القناة**\n\n"
                    f"📢 {chat.title} (@{chat.username or 'خاصة'})\n"
                    f"🆔 `{chat.id}`\n"
                    f"👥 {subs} مشترك\n"
                    f"⛔ محظورة: {'نعم' if is_blocked else 'لا'}\n"
                    f"✅ مسجلة: {'نعم' if ch_data else 'لا'}"
                )
                await message.reply(text_out)
            else:
                await message.reply("❌ رابط غير صحيح.")
        except Exception as e:
            await message.reply(f"❌ فشل: {e}")

    elif state == "awaiting_delete_channel":
        del session_states[uid]
        try:
            chat = await resolve_channel(text)
            if chat:
                db.cursor.execute("DELETE FROM user_channels WHERE channel_id = ?", (str(chat.id),))
                db.conn.commit()
                await message.reply(f"✅ تمت إزالة {chat.title} من القائمة.")
            else:
                await message.reply("❌ رابط غير صحيح.")
        except Exception as e:
            await message.reply(f"❌ فشل: {e}")

    elif state == "awaiting_pin_message":
        channel_id = state_data["channel_id"]
        del session_states[uid]
        try:
            msg_id = int(text)
            await bot.pin_chat_message(int(channel_id), msg_id)
            await message.reply("✅ تم تثبيت الرسالة.")
        except ValueError:
            await message.reply("❌ أرسل معرف الرسالة كرقم صحيح.")
        except Exception as e:
            await message.reply(f"❌ فشل: {e}")

    elif state == "awaiting_unpin_message":
        channel_id = state_data["channel_id"]
        del session_states[uid]
        try:
            msg_id = int(text) if text else None
            if msg_id:
                await bot.unpin_chat_message(int(channel_id), msg_id)
            else:
                await bot.unpin_chat_message(int(channel_id))
            await message.reply("✅ تم إلغاء تثبيت الرسالة.")
        except Exception as e:
            await message.reply(f"❌ فشل: {e}")

    else:
        await message.reply("❓ استخدم /start للبدء.")


async def _register_forced_channel(message: Message, text: str, is_public: bool):
    try:
        if is_public:
            target = text[1:] if text.startswith("@") else text
            chat = await bot.get_chat(target)
            link = f"https://t.me/{chat.username}" if chat.username else f"ID: {chat.id}"
        else:
            chat = await bot.join_chat(text)
            link = text
        if db.add_forced_channel(str(chat.id), chat.username or "", chat.title, link, is_public, message.from_user.id):
            await message.reply(f"✅ تمت إضافة {'القناة العامة' if is_public else 'القناة الخاصة'}: {chat.title}")
        else:
            await message.reply("❌ فشل الإضافة.")
    except Exception as e:
        await message.reply(f"❌ فشل: {e}")


async def _register_forced_group(message: Message, text: str, is_public: bool):
    try:
        if is_public:
            target = text[1:] if text.startswith("@") else text
            chat = await bot.get_chat(target)
            link = f"https://t.me/{chat.username}" if chat.username else f"ID: {chat.id}"
        else:
            chat = await bot.join_chat(text)
            link = text
        if db.add_forced_group(str(chat.id), chat.username or "", chat.title, link, is_public, message.from_user.id):
            await message.reply(f"✅ تمت إضافة {'الجروب العام' if is_public else 'الجروب الخاص'}: {chat.title}")
        else:
            await message.reply("❌ فشل الإضافة.")
    except Exception as e:
        await message.reply(f"❌ فشل: {e}")


async def _remove_forced_channel(message: Message, text: str):
    try:
        chat = await resolve_channel(text)
        if chat:
            db.remove_forced_channel(str(chat.id))
            await message.reply(f"✅ تمت إزالة {chat.title} من الاشتراك الإجباري.")
        else:
            await message.reply("❌ رابط غير صحيح.")
    except Exception as e:
        await message.reply(f"❌ فشل: {e}")


async def _remove_forced_group(message: Message, text: str):
    try:
        chat = await resolve_channel(text)
        if chat:
            db.remove_forced_group(str(chat.id))
            await message.reply(f"✅ تمت إزالة {chat.title} من الاشتراك الإجباري.")
        else:
            await message.reply("❌ رابط غير صحيح.")
    except Exception as e:
        await message.reply(f"❌ فشل: {e}")


async def _periodic_contest_checker():
    while True:
        try:
            count = await auto_end_expired_contests()
            if count:
                logger.info(f"Auto-ended {count} expired contest(s).")
        except Exception as e:
            logger.error(f"_periodic_contest_checker error: {e}")
        await asyncio.sleep(300)


async def main():
    await bot.start()
    me = await bot.get_me()
    logger.info(f"Bot started: @{me.username}")
    asyncio.create_task(_periodic_contest_checker())
    await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        bot.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
