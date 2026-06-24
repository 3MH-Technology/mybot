import telebot
import marshal
import zlib
import base64
import random
import os
import string
import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = '8783362240:AAFUTxqpsSgJCYpXYU2GIoIUVXkJCuHWEjM'
bot = telebot.TeleBot(TOKEN)

CHANNELS = [
    '@F7_7G',
    '@H_U_VB',
    '@seed_1k',
    '@TERBO_CODE',
    '@BQBOOB1',
    '@bshshshkk',
    '@EQJ_1',
    '@HAMO_X_OT3'
]

class ObfuscationBot:
    def __init__(self):
        self.bot = bot
        self.waiting_for_file = {}

    @staticmethod
    def generate_variable_name(length=8):
        return ''.join(random.choices(string.ascii_letters, k=length))

    @staticmethod
    def xor_bytes(data, key):
        return bytes([b ^ key for b in data])

    def is_user_subscribed(self, user_id):
        try:
            for channel in CHANNELS:
                member = self.bot.get_chat_member(channel, user_id)
                if member.status not in ['member', 'administrator', 'creator']:
                    return False
            return True
        except:
            return False

    def get_subscription_keyboard(self):
        keyboard = InlineKeyboardMarkup(row_width=1)
        styles = ["primary", "success", "danger"]
        for i, channel in enumerate(CHANNELS):
            style = styles[i % len(styles)]
            keyboard.add(InlineKeyboardButton(
                text=f"📢 اشترك في {channel}",
                url=f"https://t.me/{channel[1:]}",
                style=style
            ))
        keyboard.add(InlineKeyboardButton(
            text="✅ تحقق من الاشتراك",
            callback_data="check_subscription",
            style="success"
        ))
        return keyboard

    def get_main_keyboard(self):
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(InlineKeyboardButton(
            text="🔐 تشفير ملف",
            callback_data="encrypt_file",
            style="primary"
        ))
        keyboard.add(InlineKeyboardButton(
            text="📋 قنوات البوت",
            callback_data="show_channels",
            style="primary"
        ))
        return keyboard

    def build_payload(self, source_code):
        compiled = compile(source_code, '<obfuscated>', 'exec')
        marshaled = marshal.dumps(compiled)
        xor_key = random.randint(1, 255)
        xored = self.xor_bytes(marshaled, xor_key)
        compressed = zlib.compress(xored)
        encoded = base64.b64encode(compressed).decode()

        var_names = [self.generate_variable_name() for _ in range(20)]

        payload = f"""
import base64 as {var_names[0]}, zlib as {var_names[1]}, marshal as {var_names[2]}, types as {var_names[19]}, sys as {var_names[16]}, os as {var_names[17]}, platform as {var_names[18]}

def {var_names[3]}():
    {var_names[4]} = {var_names[17]}.getpid()
    {var_names[5]} = {var_names[16]}.gettrace()
    {var_names[6]} = {var_names[18]}.system()
    return {var_names[5]} or {var_names[6]} == 'QEMU'

if {var_names[3]}():
    {var_names[16]}.exit()

{var_names[7]} = '{encoded}'
{var_names[8]} = {var_names[0]}.b64decode({var_names[7]})
{var_names[9]} = {var_names[1]}.decompress({var_names[8]})
{var_names[10]} = {xor_key}
{var_names[11]} = bytes([b ^ {var_names[10]} for b in {var_names[9]}])

def {var_names[12]}():
    return {random.randint(10, 99)}

def {var_names[13]}():
    return [{random.randint(1, 5)} for _ in range(3)]

{var_names[19]}.FunctionType({var_names[2]}.loads({var_names[11]}), globals())()
"""
        return payload

    def start_handler(self, message):
        user_id = message.from_user.id
        if self.is_user_subscribed(user_id):
            self.bot.reply_to(
                message,
                "مرحباً بك في بوت التشفير! اختر الخيار المناسب:",
                reply_markup=self.get_main_keyboard()
            )
        else:
            self.bot.reply_to(
                message,
                "🔒 يرجى الاشتراك في القنوات التالية لاستخدام البوت:",
                reply_markup=self.get_subscription_keyboard()
            )

    def document_handler(self, message):
        user_id = message.from_user.id
        if not self.waiting_for_file.get(user_id, False):
            self.bot.reply_to(message, "يرجى الضغط على زر 'تشفير ملف' أولاً.")
            return

        if not self.is_user_subscribed(user_id):
            self.bot.reply_to(
                message,
                "🔒 أنت غير مشترك في جميع القنوات، يرجى الاشتراك أولاً.",
                reply_markup=self.get_subscription_keyboard()
            )
            self.waiting_for_file[user_id] = False
            return

        try:
            file_info = self.bot.get_file(message.document.file_id)
            downloaded = self.bot.download_file(file_info.file_path)
            source = downloaded.decode('utf-8')

            payload = self.build_payload(source)

            filename = f"obfuscated_{message.document.file_name}"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(payload)

            with open(filename, 'rb') as f:
                self.bot.send_document(message.chat.id, f)

            os.remove(filename)
            self.waiting_for_file[user_id] = False
            self.bot.send_message(
                message.chat.id,
                "✅ تم التشفير بنجاح! يمكنك تشفير ملف آخر بالضغط على الزر.",
                reply_markup=self.get_main_keyboard()
            )

        except Exception as e:
            self.bot.reply_to(message, f"❌ حدث خطأ: {e}")
            self.waiting_for_file[user_id] = False

    def callback_handler(self, call):
        user_id = call.from_user.id
        data = call.data

        if data == "check_subscription":
            if self.is_user_subscribed(user_id):
                self.bot.edit_message_text(
                    "✅ تم التحقق، يمكنك الآن استخدام البوت.",
                    call.message.chat.id,
                    call.message.message_id
                )
                self.bot.send_message(
                    call.message.chat.id,
                    "مرحباً بك! اختر الخيار المناسب:",
                    reply_markup=self.get_main_keyboard()
                )
            else:
                self.bot.answer_callback_query(
                    call.id,
                    "❌ لم تشترك في جميع القنوات بعد.",
                    show_alert=True
                )

        elif data == "encrypt_file":
            if not self.is_user_subscribed(user_id):
                self.bot.answer_callback_query(
                    call.id,
                    "❌ يجب الاشتراك في القنوات أولاً.",
                    show_alert=True
                )
                self.bot.edit_message_text(
                    "🔒 يرجى الاشتراك في القنوات التالية:",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=self.get_subscription_keyboard()
                )
                return

            self.waiting_for_file[user_id] = True
            self.bot.edit_message_text(
                "📤 أرسل ملف Python (.py) الآن لتشفيره.",
                call.message.chat.id,
                call.message.message_id
            )
            self.bot.answer_callback_query(call.id)

        elif data == "show_channels":
            channels_text = "\n".join([f"• {ch}" for ch in CHANNELS])
            back_button = InlineKeyboardButton(
                "🔙 رجوع",
                callback_data="back_to_main",
                style="primary"
            )
            self.bot.edit_message_text(
                f"📋 قنوات البوت الرسمية:\n{channels_text}",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(back_button)
            )
            self.bot.answer_callback_query(call.id)

        elif data == "back_to_main":
            self.bot.edit_message_text(
                "مرحباً بك! اختر الخيار المناسب:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=self.get_main_keyboard()
            )
            self.bot.answer_callback_query(call.id)

obf_bot = ObfuscationBot()

@bot.message_handler(commands=['start'])
def start_handler(message):
    obf_bot.start_handler(message)

@bot.message_handler(content_types=['document'])
def document_handler(message):
    obf_bot.document_handler(message)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    obf_bot.callback_handler(call)

if __name__ == '__main__':
    bot.polling()