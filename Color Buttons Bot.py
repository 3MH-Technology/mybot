import telebot
import re
import ast
import os
import uuid
import json
import time
from pathlib import Path
from telebot import types
from typing import Dict, List, Optional
from datetime import datetime

API_KEY = '8397047829:AAG75CmhpF6p_pZXaFgR1qaONUNsLN3KAGg'
ADMIN_ID = 6812997550

WORK_DIR = Path("workdir")
DATA_DIR = Path("data")
WORK_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

OWNER_NAME = "الذئب الأبيض"
OWNER_HANDLE = "@j49_c"
CHANNEL_HANDLE = "@bshshshkk"

USERS_FILE = DATA_DIR / "users.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
STATS_FILE = DATA_DIR / "stats.json"

REQUIRED_CHANNELS = [
    'F7_7G', 'H_U_VB', 'seed_1k', 'TERBO_CODE',
    'BQBOOB1', 'bshshshkk', 'EQJ_1'
]

EMOJI = {
    'fire':      '5424972470023104089',
    'check':     '5206607081334906820',
    'sparkles':  '5325547803936572038',
    'gem':       '5427168083074628963',
    'pencil':    '5395444784611480792',
    'settings':  '5341715473882955310',
    'crown':     '5217822164362739968',
    'chart':     '5231200819986047254',
    'warning':   '5447644880824181073',
    'trophy':    '5188344996356448758',
    'people':    '5258513401784573443',
    'link':      '5271604874419647061',
    'picture':   '5375074927252621134',
    'arrow':     '5416117059207572332',
    'cross':     '5210952531676504517',
    'bulb':      '5422439311196834318',
    'bell':      '5458603043203327669',
    'python':    '5260480440971570446',
    '1':         '5141109049114232089',
    '2':         '5140871649091912628',
    '3':         '5141399818400170896',
    '4':         '5138822752123225428',
    '5':         '5141062672057369534',
}

COLOR_STYLES = {'blue': 'primary', 'green': 'success', 'red': 'danger'}
COLOR_CYCLE  = ['blue', 'green', 'red']
COLOR_AR     = {'blue': 'أزرق', 'green': 'أخضر', 'red': 'أحمر'}
COLOR_EMOJI  = {'blue': '🔵', 'green': '🟢', 'red': '🔴'}

DEFAULT_SETTINGS = {'welcome_photo': None}

bot = telebot.TeleBot(API_KEY, parse_mode='HTML')

_user_states: Dict[int, Optional[str]] = {}
_user_sessions: Dict[int, dict] = {}

_EMOJI_RE = re.compile(
    r'[\U00010000-\U0010ffff]|[\u2600-\u27BF]|[\uFE00-\uFE0F]|[\u2300-\u23FF]'
)


def _load(path: Path, default=None):
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return default if default is not None else {}


def _save(path: Path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_users() -> dict:
    return _load(USERS_FILE)


def save_users(users: dict):
    _save(USERS_FILE, users)


def add_user(uid: int, username: str, first_name: str) -> bool:
    users = get_users()
    key = str(uid)
    if key in users:
        return False
    users[key] = {
        'username': username,
        'first_name': first_name,
        'joined_at': datetime.now().isoformat(),
    }
    save_users(users)
    return True


def get_settings() -> dict:
    return _load(SETTINGS_FILE, dict(DEFAULT_SETTINGS))


def save_settings(settings: dict):
    _save(SETTINGS_FILE, settings)


def get_stats() -> dict:
    return _load(STATS_FILE, {'total_files': 0, 'total_buttons': 0})


def increment_stats(files: int = 0, buttons: int = 0):
    stats = get_stats()
    stats['total_files'] += files
    stats['total_buttons'] += buttons
    _save(STATS_FILE, stats)


def notify_admin(text: str):
    try:
        bot.send_message(ADMIN_ID, text, parse_mode='HTML')
    except Exception:
        pass


def is_admin(uid: int) -> bool:
    return uid == ADMIN_ID


def strip_emoji(text: str) -> str:
    return _EMOJI_RE.sub('', text).strip()


def check_subscriptions(uid: int) -> List[str]:
    missing = []
    for ch in REQUIRED_CHANNELS:
        try:
            member = bot.get_chat_member(f'@{ch}', uid)
            if member.status not in ('member', 'administrator', 'creator'):
                missing.append(ch)
        except Exception:
            missing.append(ch)
    return missing


def make_btn(text: str, callback: str = None, url: str = None,
             emoji_id: str = None, color: str = None) -> types.InlineKeyboardButton:
    if emoji_id:
        text = strip_emoji(text)
    btn = types.InlineKeyboardButton(text=text, callback_data=callback, url=url)
    if emoji_id:
        try:
            btn.icon_custom_emoji_id = emoji_id
        except Exception:
            pass
    if color:
        btn.style = color
    return btn


def send_subscription_wall(chat_id: int, missing: List[str], msg_id: int = None):
    lines = '\n'.join(f"• <a href='https://t.me/{ch}'>{ch}</a>" for ch in missing)
    text = (
        f"<blockquote><b>اشتراك إجباري</b></blockquote>\n\n"
        f"<blockquote>اشترك في القنوات التالية للمتابعة:\n{lines}</blockquote>\n\n"
        f"<blockquote>بعد الاشتراك اضغط <b>تحقق</b>.</blockquote>"
    )
    styles = ['primary', 'success', 'danger']
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, ch in enumerate(missing):
        markup.add(make_btn(ch, url=f'https://t.me/{ch}',
                            emoji_id=EMOJI['link'], color=styles[i % 3]))
    markup.add(make_btn('✅ تحقق من الاشتراك', callback='check_sub',
                        emoji_id=EMOJI['check'], color='success'))
    if msg_id:
        _edit(chat_id, msg_id, text, markup)
    else:
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')


def require_subscription(func):
    def wrapper(obj, *args, **kwargs):
        if isinstance(obj, types.Message):
            uid, chat_id = obj.from_user.id, obj.chat.id
            is_call = False
        elif isinstance(obj, types.CallbackQuery):
            uid, chat_id = obj.from_user.id, obj.message.chat.id
            is_call = True
        else:
            return func(obj, *args, **kwargs)

        missing = check_subscriptions(uid)
        if missing:
            if is_call:
                send_subscription_wall(chat_id, missing, msg_id=obj.message.id)
                bot.answer_callback_query(obj.id)
            else:
                send_subscription_wall(chat_id, missing)
            return
        return func(obj, *args, **kwargs)
    return wrapper


def _edit(chat_id: int, msg_id: int, text: str, markup=None):
    try:
        bot.edit_message_caption(chat_id=chat_id, message_id=msg_id,
                                 caption=text, reply_markup=markup, parse_mode='HTML')
    except Exception:
        try:
            bot.edit_message_text(text, chat_id, msg_id,
                                  reply_markup=markup, parse_mode='HTML')
        except Exception:
            pass


def _send_main(chat_id: int, text: str, markup=None):
    settings = get_settings()
    photo = settings.get('welcome_photo')
    if photo:
        try:
            return bot.send_photo(chat_id, photo, caption=text,
                                  reply_markup=markup, parse_mode='HTML')
        except Exception:
            pass
    return bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')


def _welcome_text(first_name: str) -> str:
    return (
        f"<blockquote><b>مرحباً {first_name}</b> "
        f"<tg-emoji emoji-id='{EMOJI['fire']}'>🔥</tg-emoji></blockquote>\n\n"
        f"<blockquote><b>بوت تلوين الأزرار الاحترافي</b> "
        f"<tg-emoji emoji-id='{EMOJI['sparkles']}'>✨</tg-emoji></blockquote>\n\n"
        f"<blockquote>"
        f"<tg-emoji emoji-id='{EMOJI['python']}'>💻</tg-emoji> دعم Python\n"
        f"<tg-emoji emoji-id='{EMOJI['pencil']}'>✍️</tg-emoji> تلوين يدوي وعشوائي\n"
        f"<tg-emoji emoji-id='{EMOJI['gem']}'>💎</tg-emoji> إيموجيات Premium\n"
        f"<tg-emoji emoji-id='{EMOJI['trophy']}'>🏆</tg-emoji> معالجة ذكية للكود"
        f"</blockquote>\n\n"
        f"<blockquote><b>اضغط ابدأ الآن للبدء</b> "
        f"<tg-emoji emoji-id='{EMOJI['arrow']}'>➡️</tg-emoji></blockquote>\n\n"
        f"<blockquote>المطور: <a href='https://t.me/{OWNER_HANDLE[1:]}'>{OWNER_NAME}</a></blockquote>"
    )


def _main_markup() -> types.InlineKeyboardMarkup:
    m = types.InlineKeyboardMarkup(row_width=1)
    m.add(
        make_btn('ابدأ الآن', callback='start_now', emoji_id=EMOJI['sparkles'], color='success'),
        make_btn('كيفية الاستخدام', callback='how_to_use', emoji_id=EMOJI['bulb'], color='primary'),
    )
    m.row(
        make_btn('المطور', url=f'https://t.me/{OWNER_HANDLE[1:]}', emoji_id=EMOJI['crown'], color='danger'),
        make_btn('القناة', url=f'https://t.me/{CHANNEL_HANDLE[1:]}', emoji_id=EMOJI['link'], color='primary'),
    )
    m.add(make_btn('لوحة التحكم', callback='admin_panel', emoji_id=EMOJI['settings'], color='primary'))
    return m


def _admin_markup() -> types.InlineKeyboardMarkup:
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(
        make_btn('الإحصائيات', callback='admin:stats', emoji_id=EMOJI['chart'], color='success'),
        make_btn('المستخدمين', callback='admin:users', emoji_id=EMOJI['people'], color='primary'),
    )
    m.add(
        make_btn('تعيين صورة', callback='admin:set_photo', emoji_id=EMOJI['picture'], color='primary'),
        make_btn('إذاعة', callback='admin:broadcast', emoji_id=EMOJI['bell'], color='danger'),
    )
    m.add(make_btn('رجوع', callback='back_to_home', emoji_id=EMOJI['arrow'], color='primary'))
    return m


def _color_mode_markup() -> types.InlineKeyboardMarkup:
    m = types.InlineKeyboardMarkup(row_width=2)
    m.row(
        make_btn('يدوي', callback='color:manual', emoji_id=EMOJI['pencil'], color='primary'),
        make_btn('عشوائي', callback='color:random', emoji_id=EMOJI['sparkles'], color='success'),
    )
    m.add(make_btn('رجوع', callback='back_to_home', emoji_id=EMOJI['arrow'], color='primary'))
    return m


def _emoji_question_markup() -> types.InlineKeyboardMarkup:
    m = types.InlineKeyboardMarkup(row_width=2)
    m.add(
        make_btn('نعم', callback='emoji_ask:yes', emoji_id=EMOJI['check'], color='success'),
        make_btn('لا', callback='emoji_ask:no', emoji_id=EMOJI['cross'], color='danger'),
    )
    return m


def _color_picker_markup(btn_idx: int, btn_text: str,
                         current_color: str = None,
                         current_emoji_id: str = None) -> types.InlineKeyboardMarkup:
    m = types.InlineKeyboardMarkup(row_width=3)
    preview = make_btn(
        strip_emoji(btn_text[:20]),
        callback='preview',
        emoji_id=current_emoji_id,
        color=COLOR_STYLES.get(current_color) if current_color else None,
    )
    m.add(preview)
    m.row(
        make_btn('أحمر', callback=f'pick_color:red:{btn_idx}', color='danger'),
        make_btn('أزرق', callback=f'pick_color:blue:{btn_idx}', color='primary'),
        make_btn('أخضر', callback=f'pick_color:green:{btn_idx}', color='success'),
    )
    if current_color and current_emoji_id:
        m.add(make_btn('التالي', callback=f'next_btn:{btn_idx}', emoji_id=EMOJI['arrow'], color='success'))
    elif current_color:
        m.add(make_btn('تخطي الإيموجي', callback=f'skip_emoji:{btn_idx}', emoji_id=EMOJI['arrow'], color='primary'))
    return m


class ButtonInfo:
    __slots__ = (
        'text', 'original_text', 'row_index', 'col_index',
        'button_index', 'line_start', 'line_end', 'full_line',
        'indent', 'col_offset', 'chosen_color', 'chosen_emoji_id',
    )

    def __init__(self, text: str, row_index: int, col_index: int,
                 button_index: int, line_start: int, line_end: int,
                 full_line: str, indent: str, col_offset: int = 0):
        self.text = text
        self.original_text = text
        self.row_index = row_index
        self.col_index = col_index
        self.button_index = button_index
        self.line_start = line_start
        self.line_end = line_end
        self.full_line = full_line
        self.indent = indent
        self.col_offset = col_offset
        self.chosen_color: Optional[str] = None
        self.chosen_emoji_id: Optional[str] = None


class _ButtonASTVisitor(ast.NodeVisitor):
    def __init__(self):
        self.buttons: List[ButtonInfo] = []
        self._row = 0
        self._col = 0
        self._idx = 0
        self._in_markup = False

    def visit_Call(self, node: ast.Call):
        if self._is_button_call(node):
            text = self._extract_text(node)
            if text:
                self.buttons.append(ButtonInfo(
                    text=text,
                    row_index=self._row,
                    col_index=self._col,
                    button_index=self._idx,
                    line_start=node.lineno - 1,
                    line_end=getattr(node, 'end_lineno', node.lineno) - 1,
                    full_line='',
                    indent='',
                    col_offset=node.col_offset,
                ))
                self._col += 1
                self._idx += 1
        self.generic_visit(node)

    def visit_List(self, node: ast.List):
        if self._in_markup and any(isinstance(e, ast.Call) for e in node.elts):
            self._col = 0
            self._row += 1
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        if (isinstance(node.value, ast.Call) and
                isinstance(node.value.func, ast.Attribute) and
                node.value.func.attr == 'InlineKeyboardMarkup'):
            self._in_markup = True
            self._row = 0
        self.generic_visit(node)
        self._in_markup = False

    def visit_Expr(self, node: ast.Expr):
        if (isinstance(node.value, ast.Call) and
                isinstance(node.value.func, ast.Attribute) and
                node.value.func.attr in ('add', 'row')):
            self._col = 0
            self._row += 1
        self.generic_visit(node)

    @staticmethod
    def _is_button_call(node: ast.Call) -> bool:
        if isinstance(node.func, ast.Attribute):
            attr = node.func.attr
            val = node.func.value
            if attr == 'InlineKeyboardButton' and isinstance(val, ast.Name):
                return True
            if attr == 'create_emoji_btn' and isinstance(val, ast.Name):
                return True
        if isinstance(node.func, ast.Name):
            return node.func.id in ('create_emoji_btn', 'InlineKeyboardButton', 'make_btn')
        return False

    @staticmethod
    def _extract_text(node: ast.Call) -> Optional[str]:
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                return arg.value
        for kw in node.keywords:
            if kw.arg == 'text' and isinstance(kw.value, ast.Constant):
                return kw.value.value
        return None


class ButtonExtractor:
    @staticmethod
    def from_source(content: str) -> List[ButtonInfo]:
        try:
            tree = ast.parse(content)
            visitor = _ButtonASTVisitor()
            visitor.visit(tree)
            return visitor.buttons
        except Exception:
            return []


class CodePatcher:
    @staticmethod
    def patch(content: str, buttons: List[ButtonInfo]) -> str:
        lines = content.split('\n')
        line_map: Dict[int, List[ButtonInfo]] = {}
        for btn in buttons:
            line_map.setdefault(btn.line_start, []).append(btn)

        for line_idx in sorted(line_map, reverse=True):
            bucket = sorted(line_map[line_idx], key=lambda b: b.col_offset, reverse=True)
            current = lines[line_idx]
            for btn in bucket:
                if not btn.chosen_color and not btn.chosen_emoji_id:
                    continue
                clean = strip_emoji(btn.original_text)
                if clean != btn.original_text:
                    current = (current
                               .replace(f'"{btn.original_text}"', f'"{clean}"')
                               .replace(f"'{btn.original_text}'", f"'{clean}'"))
                current = re.sub(r',?\s*style\s*=\s*["\'][^"\']*["\']', '', current)
                current = re.sub(r',?\s*icon_custom_emoji_id\s*=\s*["\'][^"\']*["\']', '', current)
                additions = ''
                if btn.chosen_color:
                    additions += f', style="{COLOR_STYLES.get(btn.chosen_color, "primary")}"'
                if btn.chosen_emoji_id:
                    additions += f', icon_custom_emoji_id="{btn.chosen_emoji_id}"'
                paren = current.find(')', btn.col_offset)
                if paren != -1:
                    current = current[:paren] + additions + current[paren:]
            lines[line_idx] = current
        return '\n'.join(lines)

    @staticmethod
    def apply_auto_colors(buttons: List[ButtonInfo]):
        row_color: Dict[int, str] = {}
        for btn in buttons:
            if btn.row_index not in row_color:
                row_color[btn.row_index] = COLOR_CYCLE[btn.row_index % len(COLOR_CYCLE)]
            btn.chosen_color = row_color[btn.row_index]


@bot.message_handler(commands=['start'])
@require_subscription
def cmd_start(message: types.Message):
    uid = message.from_user.id
    username = message.from_user.username or 'unknown'
    first_name = message.from_user.first_name or 'مستخدم'

    is_new = add_user(uid, username, first_name)
    if is_new:
        users = get_users()
        notify_admin(
            f"<blockquote><b>مستخدم جديد</b> "
            f"<tg-emoji emoji-id='{EMOJI['fire']}'>🔥</tg-emoji></blockquote>\n\n"
            f"<blockquote><b>الاسم:</b> {first_name}\n"
            f"<b>اليوزر:</b> @{username}\n"
            f"<b>الآيدي:</b> <code>{uid}</code></blockquote>\n\n"
            f"<blockquote><b>الإجمالي:</b> {len(users)}</blockquote>"
        )

    _user_states[uid] = None
    _user_sessions.pop(uid, None)

    msg = _send_main(message.chat.id, _welcome_text(first_name), _main_markup())
    _user_sessions[uid] = {'main_msg_id': msg.message_id}


@bot.callback_query_handler(func=lambda c: c.data == 'check_sub')
def cb_check_sub(call: types.CallbackQuery):
    uid = call.from_user.id
    missing = check_subscriptions(uid)
    if missing:
        bot.answer_callback_query(call.id, '❌ لا تزال بعض القنوات غير مشترك بها')
        send_subscription_wall(call.message.chat.id, missing, msg_id=call.message.id)
        return

    bot.answer_callback_query(call.id, '✅ تم التحقق، أنت مشترك في جميع القنوات')
    try:
        bot.delete_message(call.message.chat.id, call.message.id)
    except Exception:
        pass

    first_name = call.from_user.first_name or 'مستخدم'
    _send_main(call.message.chat.id, _welcome_text(first_name), _main_markup())


@bot.callback_query_handler(func=lambda c: c.data == 'how_to_use')
@require_subscription
def cb_how_to_use(call: types.CallbackQuery):
    text = (
        f"<blockquote><b>كيفية الاستخدام</b> "
        f"<tg-emoji emoji-id='{EMOJI['bulb']}'>💡</tg-emoji></blockquote>\n\n"
        f"<blockquote>"
        f"<tg-emoji emoji-id='{EMOJI['1']}'>1️⃣</tg-emoji> اضغط <b>ابدأ الآن</b>\n"
        f"<tg-emoji emoji-id='{EMOJI['2']}'>2️⃣</tg-emoji> أرسل ملف البوت (.py)\n"
        f"<tg-emoji emoji-id='{EMOJI['3']}'>3️⃣</tg-emoji> اختر وضع التلوين\n"
        f"<tg-emoji emoji-id='{EMOJI['4']}'>4️⃣</tg-emoji> حدد الألوان والإيموجيات\n"
        f"<tg-emoji emoji-id='{EMOJI['5']}'>5️⃣</tg-emoji> استلم الملف المعدّل"
        f"</blockquote>\n\n"
        f"<blockquote><b>يدوي:</b> تختار لون وإيموجي لكل زر\n"
        f"<b>عشوائي:</b> ألوان تلقائية + اختيار الإيموجيات</blockquote>\n\n"
        f"<blockquote><b>الألوان:</b> 🔵 أزرق · 🟢 أخضر · 🔴 أحمر</blockquote>\n\n"
        f"<blockquote><tg-emoji emoji-id='{EMOJI['warning']}'>⚠️</tg-emoji> "
        f"الإيموجيات المميزة تعمل فقط مع بوتات Premium</blockquote>"
    )
    m = types.InlineKeyboardMarkup()
    m.add(make_btn('رجوع', callback='back_to_home', emoji_id=EMOJI['arrow'], color='primary'))
    _edit(call.message.chat.id, call.message.id, text, m)
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data == 'back_to_home')
@require_subscription
def cb_back_home(call: types.CallbackQuery):
    uid = call.from_user.id
    _user_states[uid] = None
    _user_sessions.pop(uid, None)
    first_name = call.from_user.first_name or 'مستخدم'
    _edit(call.message.chat.id, call.message.id, _welcome_text(first_name), _main_markup())
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data == 'admin_panel')
@require_subscription
def cb_admin_panel(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, '⛔ غير مصرح', show_alert=True)
        return
    users = get_users()
    stats = get_stats()
    text = (
        f"<blockquote><b>لوحة التحكم</b> "
        f"<tg-emoji emoji-id='{EMOJI['settings']}'>⚙️</tg-emoji></blockquote>\n\n"
        f"<blockquote><b>المستخدمين:</b> {len(users)}\n"
        f"<b>الملفات:</b> {stats.get('total_files', 0)}\n"
        f"<b>الأزرار:</b> {stats.get('total_buttons', 0)}</blockquote>"
    )
    _edit(call.message.chat.id, call.message.id, text, _admin_markup())
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data.startswith('admin:'))
@require_subscription
def cb_admin_actions(call: types.CallbackQuery):
    uid = call.from_user.id
    if not is_admin(uid):
        bot.answer_callback_query(call.id, '⛔ غير مصرح', show_alert=True)
        return

    action = call.data.split(':')[1]
    chat_id, msg_id = call.message.chat.id, call.message.id

    if action == 'stats':
        users = get_users()
        stats = get_stats()
        text = (
            f"<blockquote><b>الإحصائيات</b> "
            f"<tg-emoji emoji-id='{EMOJI['chart']}'>📊</tg-emoji></blockquote>\n\n"
            f"<blockquote><b>المستخدمين:</b> {len(users)}\n"
            f"<b>الملفات:</b> {stats.get('total_files', 0)}\n"
            f"<b>الأزرار الملوّنة:</b> {stats.get('total_buttons', 0)}</blockquote>"
        )
        _edit(chat_id, msg_id, text, _admin_markup())

    elif action == 'users':
        users = get_users()
        preview = '\n'.join(
            f"<b>{u['first_name']}</b> (@{u['username']})"
            for u in list(users.values())[:10]
        )
        text = (
            f"<blockquote><b>المستخدمين</b> "
            f"<tg-emoji emoji-id='{EMOJI['people']}'>👥</tg-emoji></blockquote>\n\n"
            f"<blockquote><b>الإجمالي:</b> {len(users)}</blockquote>\n\n"
            f"<blockquote>{preview}</blockquote>"
        )
        _edit(chat_id, msg_id, text, _admin_markup())

    elif action == 'set_photo':
        _user_states[uid] = 'admin_waiting_photo'
        text = (
            f"<blockquote><b>تعيين صورة الترحيب</b> "
            f"<tg-emoji emoji-id='{EMOJI['picture']}'>🖼</tg-emoji></blockquote>\n\n"
            f"<blockquote>أرسل الصورة الآن.</blockquote>"
        )
        _edit(chat_id, msg_id, text, _admin_markup())

    elif action == 'broadcast':
        _user_states[uid] = 'admin_waiting_broadcast'
        text = (
            f"<blockquote><b>إذاعة</b> "
            f"<tg-emoji emoji-id='{EMOJI['bell']}'>🔔</tg-emoji></blockquote>\n\n"
            f"<blockquote>أرسل الرسالة الآن وسيتم توزيعها على جميع المستخدمين.</blockquote>"
        )
        _edit(chat_id, msg_id, text, _admin_markup())

    bot.answer_callback_query(call.id)


@bot.message_handler(content_types=['photo'])
@require_subscription
def handle_photo(message: types.Message):
    uid = message.from_user.id
    if _user_states.get(uid) == 'admin_waiting_photo' and is_admin(uid):
        photo_id = message.photo[-1].file_id
        settings = get_settings()
        settings['welcome_photo'] = photo_id
        save_settings(settings)
        bot.reply_to(
            message,
            f"<blockquote><b>تم تعيين الصورة</b> "
            f"<tg-emoji emoji-id='{EMOJI['check']}'>✅</tg-emoji></blockquote>",
            parse_mode='HTML',
        )
        _user_states[uid] = None


@bot.callback_query_handler(func=lambda c: c.data == 'start_now')
@require_subscription
def cb_start_now(call: types.CallbackQuery):
    uid = call.from_user.id
    _user_states[uid] = 'waiting_file'
    text = (
        f"<blockquote><b>تلوين الأزرار</b> "
        f"<tg-emoji emoji-id='{EMOJI['sparkles']}'>🎨</tg-emoji></blockquote>\n\n"
        f"<blockquote>أرسل ملف البوت (.py) الآن.\n"
        f"سيتم تحليله واستخراج الأزرار تلقائياً.</blockquote>"
    )
    _edit(call.message.chat.id, call.message.id, text)
    _user_sessions.setdefault(uid, {})['main_msg_id'] = call.message.id
    bot.answer_callback_query(call.id)


@bot.message_handler(content_types=['document'])
@require_subscription
def handle_document(message: types.Message):
    uid = message.from_user.id
    if _user_states.get(uid) != 'waiting_file':
        return

    filename = message.document.file_name or 'file'
    if Path(filename).suffix.lower() != '.py':
        bot.reply_to(
            message,
            f"<blockquote><b>نوع غير مدعوم</b> "
            f"<tg-emoji emoji-id='{EMOJI['cross']}'>❌</tg-emoji></blockquote>\n\n"
            f"<blockquote>أرسل ملف <b>.py</b> فقط.</blockquote>",
            parse_mode='HTML',
        )
        return

    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass

    session = _user_sessions.get(uid, {})
    main_msg_id = session.get('main_msg_id')
    if main_msg_id:
        _edit(message.chat.id, main_msg_id,
              f"<blockquote><b>جاري التحليل...</b> "
              f"<tg-emoji emoji-id='{EMOJI['sparkles']}'>⏳</tg-emoji></blockquote>")

    try:
        file_info = bot.get_file(message.document.file_id)
        local_path = WORK_DIR / f"{uuid.uuid4().hex}_{filename}"
        raw = bot.download_file(file_info.file_path)
        local_path.write_bytes(raw)

        content = local_path.read_text(encoding='utf-8', errors='ignore')
        buttons = ButtonExtractor.from_source(content)

        if not buttons:
            if main_msg_id:
                _edit(message.chat.id, main_msg_id,
                      f"<blockquote><b>لم أجد أزرار في هذا الملف</b> "
                      f"<tg-emoji emoji-id='{EMOJI['warning']}'>⚠️</tg-emoji></blockquote>")
            local_path.unlink(missing_ok=True)
            return

        _user_sessions[uid] = {
            'content': content,
            'buttons': buttons,
            'filename': filename,
            'file_path': str(local_path),
            'main_msg_id': main_msg_id,
        }

        rows = len({b.row_index for b in buttons})
        summary = (
            f"<blockquote><b>تم التحليل بنجاح</b> "
            f"<tg-emoji emoji-id='{EMOJI['check']}'>✅</tg-emoji></blockquote>\n\n"
            f"<blockquote><b>الملف:</b> {filename}\n"
            f"<b>الأزرار:</b> {len(buttons)}\n"
            f"<b>الصفوف:</b> {rows}</blockquote>\n\n"
            f"<blockquote><b>اختر وضع التلوين:</b> "
            f"<tg-emoji emoji-id='{EMOJI['arrow']}'>➡️</tg-emoji></blockquote>"
        )
        if main_msg_id:
            _edit(message.chat.id, main_msg_id, summary, _color_mode_markup())
        _user_states[uid] = 'choosing_color_mode'

    except Exception as exc:
        if main_msg_id:
            _edit(message.chat.id, main_msg_id,
                  f"<blockquote><b>خطأ</b> "
                  f"<tg-emoji emoji-id='{EMOJI['cross']}'>❌</tg-emoji></blockquote>\n\n"
                  f"<blockquote><code>{exc}</code></blockquote>")


@bot.callback_query_handler(func=lambda c: c.data.startswith('color:'))
@require_subscription
def cb_color_mode(call: types.CallbackQuery):
    uid = call.from_user.id
    if uid not in _user_sessions:
        bot.answer_callback_query(call.id, '❌ انتهت الجلسة', show_alert=True)
        return

    mode = call.data.split(':')[1]
    session = _user_sessions[uid]
    session['color_mode'] = mode
    chat_id, msg_id = call.message.chat.id, call.message.id

    if mode == 'random':
        CodePatcher.apply_auto_colors(session['buttons'])
        text = (
            f"<blockquote><b>تم تطبيق الألوان التلقائية</b> "
            f"<tg-emoji emoji-id='{EMOJI['check']}'>✅</tg-emoji></blockquote>\n\n"
            f"<blockquote>هل تريد إضافة إيموجيات مميزة للأزرار؟ "
            f"<tg-emoji emoji-id='{EMOJI['gem']}'>💎</tg-emoji></blockquote>"
        )
        _edit(chat_id, msg_id, text, _emoji_question_markup())
        _user_states[uid] = 'emoji_question'
    else:
        _edit(chat_id, msg_id,
              f"<blockquote><b>التلوين اليدوي</b> "
              f"<tg-emoji emoji-id='{EMOJI['pencil']}'>✍️</tg-emoji></blockquote>\n\n"
              f"<blockquote>جاري البدء...</blockquote>")
        time.sleep(0.8)
        _user_states[uid] = 'manual_coloring'
        session['current_btn_idx'] = 0
        _show_manual_step(chat_id, msg_id, uid, session, 0)

    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data.startswith('emoji_ask:'))
@require_subscription
def cb_emoji_ask(call: types.CallbackQuery):
    uid = call.from_user.id
    if uid not in _user_sessions:
        bot.answer_callback_query(call.id, '❌ انتهت الجلسة', show_alert=True)
        return

    answer = call.data.split(':')[1]
    session = _user_sessions[uid]

    if answer == 'no':
        _finish(call.message.chat.id, uid, session)
    else:
        _edit(call.message.chat.id, call.message.id,
              f"<blockquote><b>إضافة إيموجيات مميزة</b> "
              f"<tg-emoji emoji-id='{EMOJI['gem']}'>💎</tg-emoji></blockquote>\n\n"
              f"<blockquote>جاري البدء...</blockquote>")
        time.sleep(0.8)
        _user_states[uid] = 'asking_emoji_random'
        session['current_btn_idx'] = 0
        _show_emoji_step_random(call.message.chat.id, call.message.id, uid, session, 0)

    bot.answer_callback_query(call.id)


def _show_emoji_step_random(chat_id: int, msg_id: int, uid: int, session: dict, idx: int):
    buttons = session['buttons']
    btn = buttons[idx]
    text = (
        f"<blockquote><b>الزر {idx + 1} / {len(buttons)}</b> "
        f"<tg-emoji emoji-id='{EMOJI['sparkles']}'>🎨</tg-emoji></blockquote>\n\n"
        f"<blockquote><b>النص:</b> {strip_emoji(btn.text[:40])}\n"
        f"<b>اللون:</b> {COLOR_EMOJI[btn.chosen_color]} {COLOR_AR[btn.chosen_color]}</blockquote>\n\n"
        f"<blockquote>أرسل إيموجياً مميزاً أو اضغط <b>تخطي</b>.</blockquote>"
    )
    m = types.InlineKeyboardMarkup()
    m.add(make_btn(strip_emoji(btn.text[:20]), callback='preview',
                   emoji_id=btn.chosen_emoji_id,
                   color=COLOR_STYLES.get(btn.chosen_color)))
    if btn.chosen_emoji_id:
        m.add(make_btn('التالي', callback=f'next_random:{idx}', emoji_id=EMOJI['arrow'], color='success'))
    else:
        m.add(make_btn('تخطي', callback=f'skip_random_emoji:{idx}', emoji_id=EMOJI['arrow']))
    _edit(chat_id, msg_id, text, m)


@bot.callback_query_handler(func=lambda c: c.data.startswith(('skip_random_emoji:', 'next_random:')))
@require_subscription
def cb_skip_next_random(call: types.CallbackQuery):
    uid = call.from_user.id
    if uid not in _user_sessions:
        bot.answer_callback_query(call.id, '❌ انتهت الجلسة', show_alert=True)
        return

    idx = int(call.data.split(':')[1])
    session = _user_sessions[uid]
    next_idx = idx + 1

    if next_idx >= len(session['buttons']):
        _finish(call.message.chat.id, uid, session)
    else:
        session['current_btn_idx'] = next_idx
        _show_emoji_step_random(call.message.chat.id, call.message.id, uid, session, next_idx)
    bot.answer_callback_query(call.id)


def _show_manual_step(chat_id: int, msg_id: int, uid: int, session: dict, idx: int):
    buttons = session['buttons']
    btn = buttons[idx]
    text = (
        f"<blockquote><b>الزر {idx + 1} / {len(buttons)}</b> "
        f"<tg-emoji emoji-id='{EMOJI['sparkles']}'>🎨</tg-emoji></blockquote>\n\n"
        f"<blockquote><b>الصف:</b> {btn.row_index + 1}\n"
        f"<b>النص:</b> {strip_emoji(btn.text[:40])}</blockquote>\n\n"
        f"<blockquote>اختر اللون:</blockquote>"
    )
    _edit(chat_id, msg_id, text, _color_picker_markup(idx, btn.text, btn.chosen_color, btn.chosen_emoji_id))


@bot.callback_query_handler(func=lambda c: c.data.startswith('pick_color:'))
@require_subscription
def cb_pick_color(call: types.CallbackQuery):
    uid = call.from_user.id
    if uid not in _user_sessions:
        bot.answer_callback_query(call.id, '❌ انتهت الجلسة', show_alert=True)
        return

    _, color, raw_idx = call.data.split(':')
    idx = int(raw_idx)
    session = _user_sessions[uid]
    session['buttons'][idx].chosen_color = color

    bot.answer_callback_query(call.id, f"تم: {COLOR_AR[color]} {COLOR_EMOJI[color]}", show_alert=True)

    btn = session['buttons'][idx]
    text = (
        f"<blockquote><b>الزر {idx + 1} / {len(session['buttons'])}</b> "
        f"<tg-emoji emoji-id='{EMOJI['sparkles']}'>🎨</tg-emoji></blockquote>\n\n"
        f"<blockquote><b>النص:</b> {strip_emoji(btn.text[:40])}\n"
        f"<b>اللون:</b> {COLOR_EMOJI[color]} {COLOR_AR[color]}</blockquote>\n\n"
        f"<blockquote>أرسل إيموجياً مميزاً أو اضغط <b>تخطي</b>.</blockquote>"
    )
    _edit(call.message.chat.id, call.message.id, text,
          _color_picker_markup(idx, btn.text, color, btn.chosen_emoji_id))
    _user_states[uid] = 'waiting_emoji_for_button'
    session['current_btn_idx'] = idx


@bot.callback_query_handler(func=lambda c: c.data.startswith('skip_emoji:'))
@require_subscription
def cb_skip_emoji(call: types.CallbackQuery):
    uid = call.from_user.id
    if uid not in _user_sessions:
        bot.answer_callback_query(call.id, '❌ انتهت الجلسة', show_alert=True)
        return

    idx = int(call.data.split(':')[1])
    session = _user_sessions[uid]
    next_idx = idx + 1

    if next_idx >= len(session['buttons']):
        _finish(call.message.chat.id, uid, session)
    else:
        _user_states[uid] = 'manual_coloring'
        session['current_btn_idx'] = next_idx
        _show_manual_step(call.message.chat.id, call.message.id, uid, session, next_idx)
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda c: c.data.startswith('next_btn:'))
@require_subscription
def cb_next_btn(call: types.CallbackQuery):
    uid = call.from_user.id
    if uid not in _user_sessions:
        bot.answer_callback_query(call.id, '❌ انتهت الجلسة', show_alert=True)
        return

    idx = int(call.data.split(':')[1])
    session = _user_sessions[uid]
    next_idx = idx + 1

    if next_idx >= len(session['buttons']):
        _finish(call.message.chat.id, uid, session)
    else:
        _user_states[uid] = 'manual_coloring'
        session['current_btn_idx'] = next_idx
        _show_manual_step(call.message.chat.id, call.message.id, uid, session, next_idx)
    bot.answer_callback_query(call.id, '✅ التالي')


@bot.callback_query_handler(func=lambda c: c.data == 'preview')
@require_subscription
def cb_preview(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)


@bot.message_handler(func=lambda m: True, content_types=['text'])
@require_subscription
def handle_text(message: types.Message):
    uid = message.from_user.id
    state = _user_states.get(uid)

    if state == 'admin_waiting_broadcast' and is_admin(uid):
        users = get_users()
        sent = 0
        for user_id in users:
            try:
                bot.send_message(int(user_id), message.text, parse_mode='HTML')
                sent += 1
            except Exception:
                pass
        bot.reply_to(
            message,
            f"<blockquote><b>تم الإرسال إلى {sent} مستخدم</b> "
            f"<tg-emoji emoji-id='{EMOJI['check']}'>✅</tg-emoji></blockquote>",
            parse_mode='HTML',
        )
        _user_states[uid] = None
        return

    if state not in ('asking_emoji_random', 'waiting_emoji_for_button'):
        return

    session = _user_sessions.get(uid)
    if not session:
        return

    emoji_id = None
    for ent in (message.entities or []):
        if ent.type == 'custom_emoji':
            emoji_id = ent.custom_emoji_id
            break

    if not emoji_id:
        bot.reply_to(
            message,
            f"<blockquote><b>لم يُتعرف على إيموجي مميز</b> "
            f"<tg-emoji emoji-id='{EMOJI['warning']}'>⚠️</tg-emoji></blockquote>",
            parse_mode='HTML',
        )
        return

    current_idx = session.get('current_btn_idx', 0)
    session['buttons'][current_idx].chosen_emoji_id = emoji_id

    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass

    main_msg_id = session.get('main_msg_id')
    if not main_msg_id:
        return

    if state == 'asking_emoji_random':
        _show_emoji_step_random(message.chat.id, main_msg_id, uid, session, current_idx)
    else:
        btn = session['buttons'][current_idx]
        color = btn.chosen_color
        text = (
            f"<blockquote><b>الزر {current_idx + 1} / {len(session['buttons'])}</b> "
            f"<tg-emoji emoji-id='{EMOJI['check']}'>✅</tg-emoji></blockquote>\n\n"
            f"<blockquote><b>النص:</b> {strip_emoji(btn.text[:40])}\n"
            f"<b>اللون:</b> {COLOR_EMOJI[color]} {COLOR_AR[color]}\n"
            f"<b>الإيموجي:</b> <tg-emoji emoji-id='{emoji_id}'>💎</tg-emoji> تم</blockquote>"
        )
        _edit(message.chat.id, main_msg_id, text,
              _color_picker_markup(current_idx, btn.text, color, emoji_id))


def _finish(chat_id: int, uid: int, session: dict):
    buttons: List[ButtonInfo] = session['buttons']
    content: str = session['content']
    filename: str = session['filename']

    patched = CodePatcher.patch(content, buttons)
    header = f"# الذئب الأبيض | t.me/j49_c | t.me/bshshshkk\n"
    final_content = header + patched

    out_path = WORK_DIR / f"colored_{filename}"
    out_path.write_text(final_content, encoding='utf-8')

    colored = sum(1 for b in buttons if b.chosen_color)
    with_emoji = sum(1 for b in buttons if b.chosen_emoji_id)

    color_tally: Dict[str, int] = {}
    for btn in buttons:
        if btn.chosen_color:
            color_tally[btn.chosen_color] = color_tally.get(btn.chosen_color, 0) + 1

    color_summary = ' · '.join(
        f"{COLOR_EMOJI[c]} {count}" for c, count in color_tally.items()
    ) or 'بدون'

    report = (
        f"<blockquote><b>اكتمل التعديل</b> "
        f"<tg-emoji emoji-id='{EMOJI['trophy']}'>🏆</tg-emoji></blockquote>\n\n"
        f"<blockquote><b>الملف:</b> {filename}\n"
        f"<b>ملوّن:</b> {colored} · <b>بإيموجي:</b> {with_emoji} · <b>الكل:</b> {len(buttons)}</blockquote>\n\n"
        f"<blockquote><b>الألوان:</b> {color_summary}</blockquote>\n\n"
        f"<blockquote>المطور: <a href='https://t.me/{OWNER_HANDLE[1:]}'>{OWNER_NAME}</a></blockquote>"
    )

    with open(out_path, 'rb') as f:
        bot.send_document(chat_id, f, caption=report, parse_mode='HTML')

    out_path.unlink(missing_ok=True)
    increment_stats(files=1, buttons=len(buttons))
    _user_sessions.pop(uid, None)
    _user_states[uid] = None


if __name__ == '__main__':
    print(f'[{OWNER_NAME}] البوت يعمل...')
    bot.infinity_polling(skip_pending=True)
