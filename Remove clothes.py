import os
import time
import uuid
import requests
import logging
import sys
import subprocess
import sqlite3
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    PreCheckoutQueryHandler,
)
from telegram.constants import ChatMemberStatus

def _ensure_package(pkg: str) -> None:
    try:
        __import__(pkg)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

_ensure_package("requests")

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

for _dir in ("images", "results"):
    os.makedirs(_dir, exist_ok=True)

BOT_TOKEN = "8509488730:AAH1lvjDJt133igOhWpNHZJoUcgnYWXoCRk"
DEVELOPER_IDS: list[int] = [8186262418, 6812997550]

CHANNELS: list[dict] = [
    {"display": "@seed_1k",     "url": "https://t.me/seed_1k",     "check_id": "@seed_1k"},
    {"display": "@EQJ_1",       "url": "https://t.me/EQJ_1",       "check_id": "@EQJ_1"},
    {"display": "@bshshshkk",   "url": "https://t.me/bshshshkk",   "check_id": "@bshshshkk"},
    {"display": "@BQBOOB1",     "url": "https://t.me/BQBOOB1",     "check_id": "@BQBOOB1"},
    {"display": "@TERBO_CODE",  "url": "https://t.me/TERBO_CODE",  "check_id": "@TERBO_CODE"},
    {"display": "@HAMO_X_OT3",  "url": "https://t.me/HAMO_X_OT3",  "check_id": "@HAMO_X_OT3"},
]

DB_PATH = "wolf_system.db"
_CREDIT_LOCK = asyncio.Lock()

STAR_PACKAGES: dict[str, dict] = {
    "buy_7":  {"points": 7,  "stars": 15},
    "buy_15": {"points": 15, "stars": 30},
    "buy_30": {"points": 30, "stars": 55},
}


class Database:
    @staticmethod
    def connect() -> sqlite3.Connection:
        return sqlite3.connect(DB_PATH)

    @classmethod
    def initialize(cls) -> None:
        conn = cls.connect()
        c = conn.cursor()
        c.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id             INTEGER PRIMARY KEY,
                points              INTEGER DEFAULT 0,
                invited_by          INTEGER DEFAULT NULL,
                is_invited_verified BOOLEAN DEFAULT 0,
                refer_code          TEXT UNIQUE,
                created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS invites (
                inviter_id  INTEGER,
                invited_id  INTEGER UNIQUE,
                verified    BOOLEAN DEFAULT 0,
                timestamp   REAL,
                PRIMARY KEY (inviter_id, invited_id)
            );
            CREATE TABLE IF NOT EXISTS stats (
                id              INTEGER PRIMARY KEY CHECK (id = 1),
                total_processed INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS point_links (
                link_code   TEXT PRIMARY KEY,
                points      INTEGER DEFAULT 5,
                created_by  INTEGER,
                max_uses    INTEGER DEFAULT 1,
                used_count  INTEGER DEFAULT 0,
                expires_at  TIMESTAMP,
                is_active   BOOLEAN DEFAULT 1,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS payments (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER,
                amount      INTEGER,
                stars_paid  INTEGER,
                payment_id  TEXT,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            INSERT OR IGNORE INTO stats (id, total_processed) VALUES (1, 0);
        """)
        conn.commit()
        conn.close()

    @classmethod
    def get_user(cls, user_id: int) -> tuple | None:
        conn = cls.connect()
        c = conn.cursor()
        c.execute(
            "SELECT points, invited_by, is_invited_verified, refer_code, created_at "
            "FROM users WHERE user_id = ?",
            (user_id,),
        )
        row = c.fetchone()
        conn.close()
        return row

    @classmethod
    def create_user(cls, user_id: int, inviter_id: int | None = None) -> None:
        refer_code = str(uuid.uuid4())[:8]
        conn = cls.connect()
        c = conn.cursor()
        try:
            c.execute(
                "INSERT INTO users (user_id, points, invited_by, is_invited_verified, refer_code) "
                "VALUES (?, 0, ?, 0, ?)",
                (user_id, inviter_id, refer_code),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        finally:
            conn.close()

    @classmethod
    def get_refer_code(cls, user_id: int) -> str:
        row = cls.get_user(user_id)
        if row and row[3]:
            return row[3]
        refer_code = str(uuid.uuid4())[:8]
        conn = cls.connect()
        c = conn.cursor()
        c.execute("UPDATE users SET refer_code = ? WHERE user_id = ?", (refer_code, user_id))
        conn.commit()
        conn.close()
        return refer_code

    @classmethod
    def record_invite(cls, inviter_id: int, invited_id: int) -> bool:
        conn = cls.connect()
        c = conn.cursor()
        try:
            c.execute(
                "INSERT INTO invites (inviter_id, invited_id, verified, timestamp) VALUES (?, ?, 0, ?)",
                (inviter_id, invited_id, time.time()),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    @classmethod
    def log_payment(cls, user_id: int, amount: int, stars_paid: int, payment_id: str) -> None:
        conn = cls.connect()
        c = conn.cursor()
        c.execute(
            "INSERT INTO payments (user_id, amount, stars_paid, payment_id) VALUES (?, ?, ?, ?)",
            (user_id, amount, stars_paid, payment_id),
        )
        conn.commit()
        conn.close()

    @classmethod
    def increment_processed(cls) -> None:
        conn = cls.connect()
        c = conn.cursor()
        c.execute("UPDATE stats SET total_processed = total_processed + 1 WHERE id = 1")
        conn.commit()
        conn.close()

    @classmethod
    def get_stats(cls) -> tuple[int, int]:
        conn = cls.connect()
        c = conn.cursor()
        c.execute("SELECT total_processed FROM stats WHERE id = 1")
        processed = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM users")
        users_count = c.fetchone()[0]
        conn.close()
        return users_count, processed

    @classmethod
    def get_all_user_ids(cls) -> list[int]:
        conn = cls.connect()
        c = conn.cursor()
        c.execute("SELECT user_id FROM users")
        users = [row[0] for row in c.fetchall()]
        conn.close()
        return users

    @classmethod
    def create_point_link(
        cls,
        created_by: int,
        points: int,
        max_uses: int = 1,
        expiry_hours: int = 0,
    ) -> str:
        code = str(uuid.uuid4())[:8]
        expires_at = None
        if expiry_hours > 0:
            expires_at = (datetime.now() + timedelta(hours=expiry_hours)).strftime("%Y-%m-%d %H:%M:%S")
        conn = cls.connect()
        c = conn.cursor()
        c.execute(
            "INSERT INTO point_links (link_code, points, created_by, max_uses, expires_at, is_active) "
            "VALUES (?, ?, ?, ?, ?, 1)",
            (code, points, created_by, max_uses, expires_at),
        )
        conn.commit()
        conn.close()
        return code

    @classmethod
    def consume_point_link(cls, link_code: str, user_id: int) -> int | None | bool:
        conn = cls.connect()
        c = conn.cursor()
        c.execute(
            "SELECT points, max_uses, used_count, expires_at, is_active FROM point_links WHERE link_code = ?",
            (link_code,),
        )
        row = c.fetchone()
        if not row:
            conn.close()
            return None
        points, max_uses, used_count, expires_at, is_active = row
        if not is_active:
            conn.close()
            return False
        if expires_at:
            if datetime.now() > datetime.fromisoformat(expires_at.replace(" ", "T")):
                conn.close()
                return False
        if used_count >= max_uses:
            conn.close()
            return False
        c.execute(
            "UPDATE point_links SET used_count = used_count + 1 WHERE link_code = ?",
            (link_code,),
        )
        if used_count + 1 >= max_uses:
            c.execute("UPDATE point_links SET is_active = 0 WHERE link_code = ?", (link_code,))
        conn.commit()
        conn.close()
        return points

    @classmethod
    def delete_inactive_users(cls, days: int = 30) -> int:
        limit_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        conn = cls.connect()
        c = conn.cursor()
        c.execute(
            "DELETE FROM users WHERE created_at < ? AND points = 0 AND invited_by IS NULL",
            (limit_date,),
        )
        deleted = c.rowcount
        conn.commit()
        conn.close()
        return deleted


class PointsManager:
    @staticmethod
    async def add(user_id: int, amount: int) -> None:
        async with _CREDIT_LOCK:
            conn = Database.connect()
            c = conn.cursor()
            c.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (amount, user_id))
            conn.commit()
            conn.close()

    @staticmethod
    async def deduct_one(user_id: int) -> bool:
        async with _CREDIT_LOCK:
            conn = Database.connect()
            c = conn.cursor()
            c.execute(
                "UPDATE users SET points = points - 1 WHERE user_id = ? AND points > 0",
                (user_id,),
            )
            affected = c.rowcount
            conn.commit()
            conn.close()
            return affected > 0

    @staticmethod
    async def verify_invite(inviter_id: int, invited_id: int) -> bool:
        async with _CREDIT_LOCK:
            conn = Database.connect()
            c = conn.cursor()
            c.execute(
                "UPDATE invites SET verified = 1 WHERE inviter_id = ? AND invited_id = ?",
                (inviter_id, invited_id),
            )
            affected = c.rowcount
            conn.commit()
            conn.close()
        if affected:
            await PointsManager.add(inviter_id, 2)
            conn2 = Database.connect()
            c2 = conn2.cursor()
            c2.execute(
                "UPDATE users SET is_invited_verified = 1 WHERE user_id = ?",
                (invited_id,),
            )
            conn2.commit()
            conn2.close()
        return affected > 0


class ImageProcessor:
    MAX_DIMENSION = 2000
    JPEG_QUALITY = 90

    @classmethod
    def enhance(cls, src_path: str, dst_path: str) -> bool:
        if not PIL_AVAILABLE:
            return cls._copy_raw(src_path, dst_path)
        try:
            img = Image.open(src_path)
            if img.mode in ("RGBA", "LA", "P"):
                rgb = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                if img.mode == "RGBA":
                    rgb.paste(img, mask=img.split()[3])
                else:
                    rgb.paste(img)
                img = rgb
            if img.size[0] > cls.MAX_DIMENSION or img.size[1] > cls.MAX_DIMENSION:
                img.thumbnail((cls.MAX_DIMENSION, cls.MAX_DIMENSION), Image.Resampling.LANCZOS)
            img.save(dst_path, "JPEG", quality=cls.JPEG_QUALITY, optimize=True)
            return True
        except Exception as err:
            logger.error("Image enhancement error: %s", err)
            return cls._copy_raw(src_path, dst_path)

    @staticmethod
    def _copy_raw(src: str, dst: str) -> bool:
        try:
            with open(src, "rb") as fi, open(dst, "wb") as fo:
                fo.write(fi.read())
            return True
        except Exception:
            return False


class ApiClient:
    BASE_URL = "https://pornworks.com/api/v2"
    _HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    _DONE_STATES = {"done", "completed", "success", "finished", "succeeded"}

    def upload_image(self, file_path: str) -> str | None:
        try:
            with open(file_path, "rb") as f:
                resp = requests.put(
                    f"{self.BASE_URL}/uploads/undress",
                    headers=self._HEADERS,
                    files={"file": (os.path.basename(file_path), f, "image/jpeg")},
                    timeout=60,
                )
            logger.info("Upload status: %s", resp.status_code)
            if resp.status_code == 400:
                if any(kw in resp.text.lower() for kw in ("child", "adolescent")):
                    return "CHILD_DETECTED"
                return None
            if resp.status_code in (200, 201, 202):
                data = resp.json()
                return data.get("url") or data.get("data", {}).get("url")
        except requests.exceptions.Timeout:
            logger.error("Upload timed out")
        except requests.exceptions.ConnectionError:
            logger.error("Upload connection error")
        except Exception as err:
            logger.error("Upload error: %s", err)
        return None

    def start_generation(self, img_url: str) -> str | None:
        try:
            resp = requests.post(
                f"{self.BASE_URL}/generate/undress",
                headers={**self._HEADERS, "Content-Type": "application/json"},
                json={"image": img_url, "gender": "auto"},
                timeout=60,
            )
            if resp.status_code in (200, 201, 202):
                data = resp.json()
                return data.get("id") or data.get("data", {}).get("id")
        except Exception as err:
            logger.error("Generation start error: %s", err)
        return None

    def wait_for_completion(self, gen_id: str, max_attempts: int = 60) -> bool:
        for _ in range(max_attempts):
            try:
                resp = requests.get(
                    f"{self.BASE_URL}/generations/{gen_id}/state",
                    headers=self._HEADERS,
                    timeout=30,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    state = data.get("state") or data.get("data", {}).get("state", "")
                    if state in self._DONE_STATES:
                        return True
                time.sleep(2)
            except Exception as err:
                logger.error("State check error: %s", err)
                time.sleep(2)
        return False

    def fetch_result_url(self, gen_id: str) -> str | None:
        try:
            resp = requests.get(
                f"{self.BASE_URL}/generations/{gen_id}",
                headers=self._HEADERS,
                timeout=60,
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results") or data.get("data", {}).get("results", {})
                url = (
                    results.get("image")
                    or results.get("output")
                    or results.get("url")
                    or results.get("result")
                )
                if url:
                    if url.startswith("//"):
                        url = f"https:{url}"
                    elif url.startswith("/"):
                        url = f"https://pornworks.com{url}"
                    return url
        except Exception as err:
            logger.error("Result fetch error: %s", err)
        return None


async def _check_subscriptions(user_id: int, bot) -> tuple[bool, list[str]]:
    missing = []
    for ch in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=ch["check_id"], user_id=user_id)
            if member.status not in (
                ChatMemberStatus.MEMBER,
                ChatMemberStatus.ADMINISTRATOR,
                ChatMemberStatus.OWNER,
            ):
                missing.append(ch["display"])
        except Exception as err:
            logger.error("Subscription check failed for %s: %s", ch["display"], err)
            missing.append(ch["display"])
    return len(missing) == 0, missing


def _build_subscription_keyboard() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(ch["display"], url=ch["url"])] for ch in CHANNELS]
    rows.append([InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="force_check")])
    return InlineKeyboardMarkup(rows)


def _build_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📷 معالجة صورة", callback_data="use"),
            InlineKeyboardButton("👥 الدعوات", callback_data="referral"),
        ],
        [
            InlineKeyboardButton("⭐ نقاطي", callback_data="points"),
            InlineKeyboardButton("🛒 شراء نقاط", callback_data="buy_points"),
        ],
        [
            InlineKeyboardButton("ℹ️ المعلومات", callback_data="info"),
            InlineKeyboardButton("👨‍💻 المطور", url="https://t.me/j49_c"),
        ],
    ])


def _build_admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("📢 إذاعة", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🗑️ حذف غير النشطين", callback_data="admin_clean")],
        [InlineKeyboardButton("🔗 إنشاء رابط نقاط", callback_data="admin_create_point_link")],
        [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back")],
    ])


_SUBSCRIPTION_MESSAGE = (
    "⚠️ يجب الاشتراك في جميع القنوات التالية للمتابعة:\n\n"
    + "\n".join(ch["display"] for ch in CHANNELS)
    + "\n\nبعد الاشتراك اضغط على زر التحقق."
)


async def _show_subscription_screen(update: Update, message=None) -> None:
    kb = _build_subscription_keyboard()
    if message:
        await message.edit_text(_SUBSCRIPTION_MESSAGE, reply_markup=kb)
    else:
        await update.message.reply_text(_SUBSCRIPTION_MESSAGE, reply_markup=kb)


async def _show_main_menu(update: Update, user_id: int, message=None) -> None:
    row = Database.get_user(user_id)
    points = row[0] if row else 0
    kb = _build_main_keyboard()
    text = (
        f"مرحباً {update.effective_user.first_name}! 👋\n\n"
        f"⭐ رصيدك: {points} نقطة\n"
        f"🔹 كل نقطة = معالجة صورة واحدة\n\n"
        "⚠️ هذا البوت مخصص للبالغين فقط\n\n"
        "📌 آلية العمل:\n"
        "• كل معالجة تستهلك نقطة واحدة\n"
        "• ادعُ أصدقاءك للحصول على نقاط مجانية\n"
        "• يجب على المدعو الاشتراك في جميع القنوات\n"
        "• تحصل على نقطتين عند تفعيل كل دعوة\n"
        "• 7 معالجات مقابل 15 نجمة فقط!"
    )
    if message:
        await message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    args = context.args or []
    inviter_id: int | None = None
    point_code: str | None = None

    if args:
        if args[0].startswith("ref_"):
            try:
                candidate = int(args[0].split("_")[1])
                inviter_id = candidate if candidate != user_id else None
            except (ValueError, IndexError):
                pass
        elif args[0].startswith("point_"):
            point_code = args[0].split("_")[1]

    if Database.get_user(user_id) is None:
        Database.create_user(user_id, inviter_id)
        if inviter_id:
            Database.record_invite(inviter_id, user_id)

    if point_code:
        result = Database.consume_point_link(point_code, user_id)
        if result is None:
            await update.message.reply_text("❌ رابط النقاط غير موجود.")
        elif result is False:
            await update.message.reply_text("❌ هذا الرابط منتهي الصلاحية أو تم استنفاده.")
        else:
            await PointsManager.add(user_id, result)
            await update.message.reply_text(f"✅ تمت إضافة {result} نقطة إلى حسابك!")

    subscribed, _ = await _check_subscriptions(user_id, context.bot)
    if subscribed:
        await _show_main_menu(update, user_id)
    else:
        await _show_subscription_screen(update)


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in DEVELOPER_IDS:
        await update.message.reply_text("❌ هذا الأمر للمطور فقط.")
        return
    users_count, processed = Database.get_stats()
    text = (
        f"👑 لوحة التحكم\n\n"
        f"👥 المستخدمون: {users_count}\n"
        f"🖼️ الصور المعالجة: {processed}"
    )
    await update.message.reply_text(text, reply_markup=_build_admin_keyboard(), parse_mode="Markdown")


async def _send_stars_invoice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    points: int,
    stars: int,
) -> None:
    try:
        await context.bot.send_invoice(
            chat_id=user_id,
            title=f"شراء {points} نقطة",
            description=f"ستحصل على {points} نقطة — كل نقطة تعادل معالجة صورة واحدة.",
            payload=f"points_{points}_{user_id}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label=f"{points} نقطة", amount=stars)],
            start_parameter="buy_points",
        )
    except Exception as err:
        logger.error("Invoice error: %s", err)
        await update.effective_message.reply_text("❌ تعذر إنشاء الفاتورة. حاول مرة أخرى.")


async def pre_checkout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.pre_checkout_query.answer(ok=True)


async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    payment = update.message.successful_payment
    try:
        parts = payment.invoice_payload.split("_")
        if parts[0] == "points":
            points = int(parts[1])
            user_id = int(parts[2])
            await PointsManager.add(user_id, points)
            Database.log_payment(user_id, points, payment.total_amount, payment.telegram_payment_charge_id)
            current = Database.get_user(user_id)
            balance = current[0] if current else 0
            await update.message.reply_text(
                f"✅ تمت عملية الشراء بنجاح!\n"
                f"تمت إضافة {points} نقطة.\n"
                f"رصيدك الحالي: {balance} نقطة"
            )
    except Exception as err:
        logger.error("Payment processing error: %s", err)
        await update.message.reply_text("❌ خطأ في معالجة الدفع. تواصل مع المطور.")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    try:
        await query.answer()
    except Exception as err:
        logger.warning("Callback answer failed: %s", err)

    user_id = query.from_user.id
    data = query.data

    if data == "force_check":
        subscribed, _ = await _check_subscriptions(user_id, context.bot)
        if subscribed:
            await _show_main_menu(update, user_id, query.message)
        else:
            await query.answer("❌ لا تزال غير مشترك في جميع القنوات.", show_alert=False)
        return

    if data == "back":
        await _show_main_menu(update, user_id, query.message)
        return

    if data == "points":
        row = Database.get_user(user_id)
        pts = row[0] if row else 0
        await query.edit_message_text(
            f"⭐ رصيدك الحالي: {pts} نقطة\n\n"
            "كل نقطة = معالجة صورة واحدة.\n"
            "ادعُ أصدقاءك أو اشترِ نقاطاً للحصول على المزيد."
        )
        return

    if data == "buy_points":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⭐ 7 معالجات = 15 نجمة",  callback_data="buy_7")],
            [InlineKeyboardButton("⭐ 15 معالجة = 30 نجمة", callback_data="buy_15")],
            [InlineKeyboardButton("⭐ 30 معالجة = 55 نجمة", callback_data="buy_30")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back")],
        ])
        await query.edit_message_text(
            "🛒 شراء نقاط\n\n"
            "اختر الباقة المناسبة:\n"
            "• 7 معالجات = 15 نجمة\n"
            "• 15 معالجة = 30 نجمة\n"
            "• 30 معالجة = 55 نجمة\n\n"
            "سيتم خصم النجوم من رصيدك في تيليجرام.",
            reply_markup=kb,
        )
        return

    if data in STAR_PACKAGES:
        pkg = STAR_PACKAGES[data]
        await _send_stars_invoice(update, context, user_id, pkg["points"], pkg["stars"])
        return

    if user_id in DEVELOPER_IDS:
        handled = await _handle_admin_callback(update, context, query, user_id, data)
        if handled:
            return

    subscribed, _ = await _check_subscriptions(user_id, context.bot)
    if not subscribed:
        await _show_subscription_screen(update, query.message)
        return

    await _handle_user_callback(update, context, query, user_id, data)


async def _handle_admin_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    query,
    user_id: int,
    data: str,
) -> bool:
    if data == "admin_stats":
        users_count, processed = Database.get_stats()
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")]])
        await query.edit_message_text(
            f"📊 الإحصائيات\n\n"
            f"👥 المستخدمون: {users_count}\n"
            f"🖼️ الصور المعالجة: {processed}\n"
            f"👑 White Wolf | @j49_c | @bshshshkk",
            reply_markup=kb,
            parse_mode="Markdown",
        )
        return True

    if data == "admin_back":
        users_count, processed = Database.get_stats()
        await query.edit_message_text(
            f"👑 لوحة التحكم\n\n👥 المستخدمون: {users_count}\n🖼️ الصور المعالجة: {processed}",
            reply_markup=_build_admin_keyboard(),
            parse_mode="Markdown",
        )
        return True

    if data == "admin_broadcast":
        context.user_data["broadcast_mode"] = True
        await query.edit_message_text("📢 أرسل الرسالة المراد إذاعتها.\nللإلغاء أرسل /cancel")
        return True

    if data == "admin_clean":
        deleted = Database.delete_inactive_users()
        await query.edit_message_text(f"✅ تم حذف {deleted} مستخدم غير نشط.")
        return True

    if data == "admin_create_point_link":
        context.user_data["waiting_for_points"] = True
        context.user_data["point_link_step"] = "points"
        await query.edit_message_text("أرسل عدد النقاط للرابط (رقم فقط):")
        return True

    return False


async def _handle_user_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    query,
    user_id: int,
    data: str,
) -> None:
    if data == "use":
        row = Database.get_user(user_id)
        if row is None:
            await query.edit_message_text("يرجى استخدام /start أولاً.")
            return
        if row[0] <= 0:
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("👥 الدعوات", callback_data="referral")],
                [InlineKeyboardButton("🛒 شراء نقاط", callback_data="buy_points")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="back")],
            ])
            await query.edit_message_text(
                "⚠️ رصيدك صفر\n\n"
                "طرق الحصول على نقاط:\n"
                "• دعوة صديق = نقطتان مجاناً\n"
                "• شراء نقاط بنجوم تيليجرام",
                reply_markup=kb,
                parse_mode="Markdown",
            )
        else:
            await query.edit_message_text(
                "📤 أرسل الصورة الآن\n\n"
                "سيتم خصم نقطة واحدة تلقائياً.\n"
                "يمكنك إرسالها كصورة أو كملف للجودة العالية.\n"
                "⏱️ وقت المعالجة: 30–60 ثانية\n\n"
                "🔙 للرجوع أرسل /start"
            )
        return

    if data == "referral":
        ref_link = f"https://t.me/{context.bot.username}?start=ref_{user_id}"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 القنوات المطلوبة", callback_data="show_channels")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back")],
        ])
        await query.edit_message_text(
            f"🔗 رابط دعوتك الخاص:\n\n`{ref_link}`\n\n"
            "كيفية الربح:\n"
            "1. شارك الرابط مع أصدقائك\n"
            "2. يجب على المدعو الاشتراك في جميع القنوات\n"
            "3. تحصل على نقطتين فور تفعيل الدعوة",
            reply_markup=kb,
            parse_mode="Markdown",
        )
        return

    if data == "show_channels":
        rows = [[InlineKeyboardButton(ch["display"], url=ch["url"])] for ch in CHANNELS]
        rows.append([InlineKeyboardButton("🔙 رجوع", callback_data="back")])
        await query.edit_message_text(
            "📢 القنوات المطلوبة\n\naضغط على القناة للاشتراك ثم ارجع.",
            reply_markup=InlineKeyboardMarkup(rows),
            parse_mode="Markdown",
        )
        return

    if data == "info":
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back")]])
        await query.edit_message_text(
            "ℹ️ معلومات البوت\n\n"
            "المميزات:\n"
            "• معالجة ذكية للصور عبر خادم متخصص\n"
            "• دعم JPG و PNG بجودة عالية\n"
            "• تحسين تلقائي للصور الناتجة\n\n"
            "نظام النقاط:\n"
            "• كل نقطة = معالجة واحدة\n"
            "• مستخدم جديد: يحتاج شراءً أو دعوة\n"
            "• كل دعوة ناجحة: نقطتان مجاناً\n"
            "• 7 معالجات = 15 نجمة\n"
            "• 15 معالجة = 30 نجمة\n"
            "• 30 معالجة = 55 نجمة\n\n"
            "شروط تفعيل الدعوة:\n"
            "• اشتراك المدعو في جميع القنوات\n"
            "• لا يمكن دعوة نفسك\n\n"
            "White Wolf | @j49_c | @bshshshkk",
            reply_markup=kb,
            parse_mode="Markdown",
        )
        return


async def _process_image_pipeline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    status = await update.message.reply_text("⏳ جاري التجهيز...")
    uid = str(uuid.uuid4())[:8]
    raw_path = f"images/{uid}.jpg"

    try:
        msg = update.message
        if msg.photo:
            file = await msg.photo[-1].get_file()
            await status.edit_text("✅ تم استلام الصورة")
        elif msg.document:
            if not msg.document.mime_type.startswith("image/"):
                await status.edit_text("❌ الملف المرسل ليس صورة.")
                return
            file = await msg.document.get_file()
            await status.edit_text("✅ تم استلام الملف (جودة عالية)")
        else:
            return

        await status.edit_text("📥 جاري تحميل الصورة...")
        await file.download_to_drive(raw_path)
        if not os.path.exists(raw_path):
            await status.edit_text("❌ فشل تحميل الصورة.")
            return

        await status.edit_text("📤 رفع الصورة للخادم...")
        api = ApiClient()
        upload_result = api.upload_image(raw_path)

        if upload_result == "CHILD_DETECTED":
            await status.edit_text("❌ الصورة مرفوضة — لا يُسمح بصور القاصرين.")
            return
        if not upload_result:
            await status.edit_text("❌ فشل رفع الصورة. تحقق من صيغتها واتصالك بالإنترنت.")
            return

        await status.edit_text("⚙️ جاري المعالجة... قد تستغرق حتى 60 ثانية.")
        gen_id = api.start_generation(upload_result)
        if not gen_id:
            await status.edit_text("❌ تعذر بدء المعالجة على الخادم.")
            return

        if not api.wait_for_completion(gen_id):
            await status.edit_text("❌ انتهت المهلة. الخادم بطيء حالياً، أعد المحاولة لاحقاً.")
            return

        await status.edit_text("📥 جاري استرجاع النتيجة...")
        result_url = api.fetch_result_url(gen_id)
        if not result_url:
            await status.edit_text("❌ فشل استرجاع الصورة الناتجة.")
            return

        resp = requests.get(result_url, timeout=60)
        resp.raise_for_status()

        temp_path = f"results/temp_{uid}.jpg"
        final_path = f"results/final_{uid}.jpg"

        with open(temp_path, "wb") as f:
            f.write(resp.content)

        ImageProcessor.enhance(temp_path, final_path)

        with open(final_path, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=f"result_{uid}.jpg",
                caption="✅ اكتملت المعالجة بنجاح!",
            )

        await status.delete()
        Database.increment_processed()

        row = Database.get_user(update.effective_user.id)
        balance = row[0] if row else 0
        await update.message.reply_text(f"📊 رصيدك المتبقي: {balance} نقطة")

    except Exception as err:
        logger.error("Pipeline error: %s", err, exc_info=True)
        await status.edit_text("❌ حدث خطأ غير متوقع. أعد المحاولة.")
    finally:
        for path in (raw_path, f"results/temp_{uid}.jpg", f"results/final_{uid}.jpg"):
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass


async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user:
        return
    user_id = update.effective_user.id
    row = Database.get_user(user_id)
    if row is None:
        await update.message.reply_text("يرجى استخدام /start أولاً.")
        return
    subscribed, _ = await _check_subscriptions(user_id, context.bot)
    if not subscribed:
        await _show_subscription_screen(update)
        return
    if row[0] <= 0:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("👥 الدعوات", callback_data="referral")],
            [InlineKeyboardButton("🛒 شراء نقاط", callback_data="buy_points")],
        ])
        await update.message.reply_text(
            "⚠️ رصيدك صفر. ادعُ أصدقاءك أو اشترِ نقاطاً.",
            reply_markup=kb,
        )
        return
    if not await PointsManager.deduct_one(user_id):
        await update.message.reply_text("❌ خطأ في خصم النقطة. أعد المحاولة.")
        return
    await _process_image_pipeline(update, context)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user:
        return
    user_id = update.effective_user.id

    if context.user_data.get("waiting_for_points") and user_id in DEVELOPER_IDS:
        await _handle_point_link_input(update, context)
        return

    if context.user_data.get("broadcast_mode") and user_id in DEVELOPER_IDS:
        await _handle_broadcast_message(update, context)
        return

    await update.message.reply_text(
        "❌ رسالة غير مفهومة.\n\nأرسل صورة أو استخدم الأزرار.\n/start للبدء"
    )


async def _handle_point_link_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    step = context.user_data.get("point_link_step", "points")
    text = update.message.text.strip()

    try:
        if step == "points":
            pts = int(text)
            if pts <= 0:
                await update.message.reply_text("❌ يجب أن يكون العدد أكبر من صفر.")
                return
            context.user_data["link_points"] = pts
            context.user_data["point_link_step"] = "uses"
            await update.message.reply_text("أرسل عدد مرات الاستخدام المسموحة:")

        elif step == "uses":
            uses = int(text)
            if uses <= 0:
                await update.message.reply_text("❌ يجب أن يكون العدد أكبر من صفر.")
                return
            context.user_data["link_uses"] = uses
            context.user_data["point_link_step"] = "expiry"
            await update.message.reply_text("أرسل مدة الصلاحية بالساعات (0 = غير محدود):")

        elif step == "expiry":
            hours = int(text)
            if hours < 0:
                await update.message.reply_text("❌ يجب أن يكون الرقم صفراً أو أكثر.")
                return
            pts = context.user_data.get("link_points", 5)
            uses = context.user_data.get("link_uses", 1)
            code = Database.create_point_link(user_id, pts, uses, hours)
            link = f"https://t.me/{context.bot.username}?start=point_{code}"
            expiry_label = "غير محدودة" if hours == 0 else f"{hours} ساعة"
            await update.message.reply_text(
                f"✅ تم إنشاء الرابط!\n"
                f"الرابط: {link}\n"
                f"النقاط: {pts}\n"
                f"الاستخدامات: {uses}\n"
                f"الصلاحية: {expiry_label}"
            )
            context.user_data["waiting_for_points"] = False
            context.user_data["point_link_step"] = None

    except ValueError:
        await update.message.reply_text("❌ أرسل رقماً صحيحاً.")


async def _handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.user_data.get("broadcast_mode"):
        return
    users = Database.get_all_user_ids()
    if not users:
        await update.message.reply_text("لا يوجد مستخدمون لإرسال الإذاعة.")
        context.user_data["broadcast_mode"] = False
        return

    await update.message.reply_text(f"⏳ جاري الإرسال إلى {len(users)} مستخدم...")
    success = fail = 0
    msg = update.message

    for uid in users:
        try:
            if msg.text:
                await context.bot.send_message(chat_id=uid, text=msg.text)
            elif msg.photo:
                await context.bot.send_photo(
                    chat_id=uid,
                    photo=msg.photo[-1].file_id,
                    caption=msg.caption or "",
                )
            elif msg.document:
                await context.bot.send_document(
                    chat_id=uid,
                    document=msg.document.file_id,
                    caption=msg.caption or "",
                )
            else:
                await update.message.reply_text("❌ نوع الرسالة غير مدعوم.")
                context.user_data["broadcast_mode"] = False
                return
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            fail += 1

    await update.message.reply_text(f"✅ اكتملت الإذاعة.\nنجاح: {success} | فشل: {fail}")
    context.user_data["broadcast_mode"] = False


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get("broadcast_mode"):
        context.user_data["broadcast_mode"] = False
        await update.message.reply_text("❌ تم إلغاء الإذاعة.")
    elif context.user_data.get("waiting_for_points"):
        context.user_data["waiting_for_points"] = False
        context.user_data["point_link_step"] = None
        await update.message.reply_text("❌ تم إلغاء إنشاء رابط النقاط.")
    else:
        await update.message.reply_text("لا توجد عملية نشطة للإلغاء.")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user:
        return
    user_id = update.effective_user.id
    row = Database.get_user(user_id)
    if row is None:
        await update.message.reply_text("يرجى استخدام /start أولاً.")
        return
    points, invited_by, is_verified, _, _ = row
    subscribed, missing = await _check_subscriptions(user_id, context.bot)
    text = (
        f"📊 حالة حسابك\n\n"
        f"🆔 المعرّف: {user_id}\n"
        f"⭐ النقاط: {points}\n"
        f"👥 مدعو من: {invited_by or 'لا أحد'}\n"
        f"✅ تفعيل الدعوة: {'نعم' if is_verified else 'لا'}\n"
        f"🔔 الاشتراك: {'✅ مكتمل' if subscribed else '❌ ناقص'}\n"
    )
    if not subscribed:
        text += "\n📢 القنوات الناقصة:\n" + "\n".join(f"• {ch}" for ch in missing)
    await update.message.reply_text(text)


async def global_error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Update %s caused error: %s", update, context.error)
    if update and update.effective_message and update.effective_message.chat.type == "private":
        try:
            await update.effective_message.reply_text(
                "⚠️ حدث خطأ داخلي. يرجى المحاولة مرة أخرى لاحقاً."
            )
        except Exception:
            pass


def main() -> None:
    Database.initialize()

    if not BOT_TOKEN:
        print("⚠️ توكن البوت مطلوب.")
        return

    print("=" * 55)
    print("White Wolf | t.me/j49_c | t.me/bshshshkk")
    print(f"📱 التوكن: {BOT_TOKEN[:10]}...")
    print(f"📦 Pillow: {'✅ متاحة' if PIL_AVAILABLE else '❌ غير متاحة'}")
    print("📢 القنوات المطلوبة:")
    for ch in CHANNELS:
        print(f"   - {ch['display']}")
    print(f"👑 المطورون: {', '.join(str(i) for i in DEVELOPER_IDS)}")
    print("=" * 55)

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",  start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("admin",  admin_panel))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_error_handler(global_error_handler)

    print("🚀 البوت يعمل الآن... اضغط Ctrl+C للإيقاف")
    print("=" * 55)
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
