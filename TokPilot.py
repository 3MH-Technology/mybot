import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import json
import datetime
import re
import os
import random
import time
import urllib.parse
import binascii
import uuid
import secrets
import string
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Thread
import queue
import threading
import sys

BOT_TOKEN = "8919063624:AAGX8dBhiztLnMkxnhxRFJytw7cBwAONpZA"
BOT_OWNER = 6812997550
bot = telebot.TeleBot(BOT_TOKEN)

try:
    from MedoSigner import Argus, Gorgon, Ladon, md5
    MEDOSIGNER_AVAILABLE = True
except:
    MEDOSIGNER_AVAILABLE = False

user_states = {}
user_sessions = {}
user_progress_messages = {}

users_db = {
    "total_users": 0,
    "private_users": 0,
    "channels_groups": 0,
    "banned_users": 0,
    "daily_stats": {},
    "user_data": {},
    "subscribed_users": {},
    "active_subscriptions": {}
}

CHANNELS = ["F7_7G", "H_U_VB", "seed_1k", "TERBO_CODE", "BQBOOB1", "bshshshkk", "EQJ_1", "HAMO_X_OT3"]

def is_subscribed(user_id):
    if user_id == BOT_OWNER:
        return True, []
    missing = []
    for ch in CHANNELS:
        try:
            member = bot.get_chat_member(f"@{ch}", user_id)
            if member.status in ["member", "administrator", "creator"]:
                continue
            else:
                missing.append(ch)
        except:
            missing.append(ch)
    return len(missing) == 0, missing

def get_subscription_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = []
    for ch in CHANNELS:
        buttons.append(InlineKeyboardButton(f"@{ch}", url=f"https://t.me/{ch}", style="primary"))
    markup.add(*buttons)
    markup.add(InlineKeyboardButton("تحقق من الاشتراك", callback_data="check_sub", style="success"))
    return markup

def conv(ts):
    return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

def get_user_info(chat_id):
    try:
        user = bot.get_chat(chat_id)
        return {
            "name": user.first_name,
            "username": user.username,
            "id": user.id
        }
    except:
        return {"name": "غير معروف", "username": "غير معروف", "id": chat_id}

def notify_new_user(chat_id):
    if chat_id == BOT_OWNER:
        return

    user_info = get_user_info(chat_id)
    users_db["total_users"] += 1
    users_db["user_data"][chat_id] = {
        "join_date": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "name": user_info["name"],
        "username": user_info["username"]
    }

    today = datetime.datetime.now().strftime('%Y-%m-%d')
    if today not in users_db["daily_stats"]:
        users_db["daily_stats"][today] = {"users": 0, "messages": 0, "starts": 0}
    users_db["daily_stats"][today]["users"] += 1

    message = f"""
تم دخول شخص جديد إلى البوت الخاص بك
--------------------------------
الاسم: {user_info['name']}
معرف: @{user_info['username'] if user_info['username'] else 'لا يوجد'}
الايدي: {user_info['id']}
--------------------------------
عدد الأعضاء الكلي: {users_db['total_users']}
"""
    try:
        bot.send_message(BOT_OWNER, message)
    except:
        pass

def balance(session):
    url = "https://webcast.tiktok.com/webcast/wallet_api/fs/diamond_buy/permission_v2"
    params = {"aid": "1988"}
    headers = {
        "Cookie": f"sessionid={session}",
        "User-Agent": "Mozilla/5.0"
    }
    try:
        return requests.get(url, headers=headers, params=params, timeout=10)
    except:
        return None

def generalinfo(session):
    url = "https://www.tiktok.com/passport/web/account/info/"
    headers = {
        "accept": "*/*",
        "cookie": f"sessionid={session}",
        "user-agent": "Mozilla/5.0"
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        return r.json()
    except:
        return {"message": "error"}

def get_tiktok_user_id(username):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(f'https://www.tiktok.com/@{username}', headers=headers, timeout=10)
        if response.status_code == 200:
            html = response.text

            pattern1 = r'"userId":"(\d+)"'
            match1 = re.search(pattern1, html)
            if match1:
                return match1.group(1)

            pattern2 = r'"user_id":"(\d+)"'
            match2 = re.search(pattern2, html)
            if match2:
                return match2.group(1)

            pattern3 = r'user_id[\\"]*:[\\"]*(\d+)[\\"]*'
            match3 = re.search(pattern3, html)
            if match3:
                return match3.group(1)
    except:
        pass

    return None

def get_tiktok_level(username):
    user_id = get_tiktok_user_id(username)
    if not user_id:
        return None, "لم يتم العثور على المستخدم"

    url = f"https://webcast.tiktok.com/webcast/room/user_info/?aid=1988&user_id={user_id}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ar,en-US;q=0.9,en;q=0.8",
        "Origin": "https://www.tiktok.com",
        "Referer": "https://www.tiktok.com/"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)

        if response.status_code != 200:
            return None, f"خطأ في الاتصال: {response.status_code}"

        response_text = response.text

        try:
            data = response.json()
            if isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, dict):
                        if "level" in value:
                            return str(value["level"]), None
                        if "user_level" in value:
                            return str(value["user_level"]), None
        except:
            pass

        patterns = [
            r'"level":\s*"?(\d+)"?',
            r'"user_level":\s*"?(\d+)"?',
            r'"support_level":\s*"?(\d+)"?',
            r'level["\']?\s*:\s*["\']?(\d+)["\']?',
            r'userLevel["\']?\s*:\s*["\']?(\d+)["\']?'
        ]

        for pattern in patterns:
            match = re.search(pattern, response_text)
            if match:
                return match.group(1), None

        return None, "لم يتم العثور على مستوى الدعم"

    except requests.exceptions.Timeout:
        return None, "انتهت مهلة الاتصال"
    except requests.exceptions.ConnectionError:
        return None, "خطأ في الاتصال بالخادم"
    except Exception as e:
        return None, f"حدث خطأ: {str(e)}"

def extract_ids(username):
    cookies2 = {
        '_ttp': '2vgirjOnuSrSOnprbKT4f6H0h4U',
        'tt_chain_token': 'aI+tyWRBH/hxDwK2jQqVFg==',
    }
    headers2 = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    url = f"https://www.tiktok.com/@{username}"
    try:
        response = requests.get(url, cookies=cookies2, headers=headers2, timeout=10)
        if response.status_code == 200:
            html = response.text

            user_id_patterns = [
                r'"userId":"(\d+)"',
                r'"user_id":"(\d+)"',
                r'user_id["\']?\s*:\s*["\']?(\d+)["\']?',
                r'"id":"(\d+)"'
            ]

            user_id = None
            for pattern in user_id_patterns:
                match = re.search(pattern, html)
                if match:
                    user_id = match.group(1)
                    break

            sec_uid_patterns = [
                r'"secUid":"([^"]+)"',
                r'"sec_uid":"([^"]+)"',
                r'secUid["\']?\s*:\s*["\']?([^"\']+)["\']?'
            ]

            sec_uid = None
            for pattern in sec_uid_patterns:
                match = re.search(pattern, html)
                if match:
                    sec_uid = match.group(1)
                    break

            return user_id, sec_uid
    except:
        pass

    return None, None

def fetch_followings(user_id, sec_user_id, chat_id=None, message_id=None, username_display=""):
    if not user_id or not sec_user_id:
        return []

    c = '0123456789abcdef'
    session = ''.join(random.choices(c, k=32))
    cookies = {
        'sessionid': session,
        'sessionid_ss': session,
        'sid_tt': session,
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'ar,en-US;q=0.9,en;q=0.8',
        'Referer': f'https://www.tiktok.com/@{username_display}'
    }

    cursor = "0"
    followings = []
    max_pages = 10

    for page in range(max_pages):
        url = f"https://api19-normal-c-alisg.tiktokv.com/lite/v2/relation/following/list/?user_id={user_id}&count=50&page_token={cursor}&sec_user_id={sec_user_id}"
        try:
            response = requests.get(url, headers=headers, cookies=cookies, timeout=20)
            if response.status_code != 200:
                break

            data = response.json()
            follow_list = data.get("followings", [])

            if not follow_list:
                break

            for user in follow_list:
                username = user.get("unique_id")
                if username:
                    follower_count = user.get("follower_count", 0)
                    followings.append((username, follower_count))

            if chat_id and message_id:
                try:
                    bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=f"- 🕜 ¦ - سحب {len(followings)} متابع من [ @{username_display} ]...."
                    )
                except:
                    pass

            has_more = data.get("rec_has_more", False)
            cursor = data.get("next_page_token", "")

            if not has_more or not cursor:
                break

        except:
            break

    return followings

def run_privater(sessionid, user_id):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    cookies = {
        'sessionid': sessionid,
        'sessionid_ss': sessionid,
        'sid_tt': sessionid,
    }

    try:
        r = requests.get("https://www.tiktok.com/passport/web/account/info/", headers=headers, cookies=cookies, timeout=10)
        r.raise_for_status()
        data = r.json().get("data", {})
        sec_user_id = data.get("sec_user_id")
        user_id_api = data.get("user_id")
        if not sec_user_id or not user_id_api:
            bot.send_message(user_id, "- ❌ ¦ - لم يتم العثور على user_id أو sec_user_id.")
            return
    except Exception as e:
        bot.send_message(user_id, f"خطأ في الحصول على بيانات الحساب: {e}")
        return

    converted_total = 0
    cursor = 0
    status_message = bot.send_message(user_id, f"- ✅ ¦-  تم تحويل 0 فيديو إلى خاص")

    try:
        while True:
            url = f'https://api16-normal-c-alisg.tiktokv.com/lite/v2/public/item/list/?source=0&sec_user_id={sec_user_id}&user_id={user_id_api}&count=100&filter_private=1&cursor={cursor}'

            r = requests.get(url, headers=headers, cookies=cookies, timeout=15)
            r.raise_for_status()
            json_data = r.json()
            aweme_list = json_data.get("aweme_list", [])
            has_more = json_data.get("has_more", False)
            cursor = json_data.get("cursor", 0)

            if not aweme_list:
                break

            aweme_ids = [item.get("aweme_id") for item in aweme_list if item.get("aweme_id")]

            for aweme_id in aweme_ids:
                mod_url = f'https://api19-normal-c-alisg.tiktokv.com/aweme/v1/aweme/modify/visibility/?aweme_id={aweme_id}&type=2'
                mod_res = requests.get(mod_url, headers=headers, cookies=cookies, timeout=10)

                if mod_res.status_code == 200:
                    converted_total += 1
                    if converted_total % 5 == 0:
                        new_text = f"- ✅ ¦- تم تحويل {converted_total} فيديو إلى خاص"
                        try:
                            bot.edit_message_text(
                                chat_id=user_id,
                                message_id=status_message.message_id,
                                text=new_text
                            )
                        except:
                            pass

            if not has_more:
                break

    except Exception as e:
        bot.send_message(user_id, f"- ❌ ¦ - خطأ أثناء المعالجة: {e}")

    final_text = f"- ✅ ¦- تم تحويل {converted_total} فيديو إلى خاص"
    try:
        bot.edit_message_text(
            chat_id=user_id,
            message_id=status_message.message_id,
            text=final_text
        )
    except:
        bot.send_message(user_id, final_text)

def fetch_aweme_ids(sessionid):
    cookies = {
        'sessionid': sessionid,
        'sessionid_ss': sessionid,
        'sid_tt': sessionid,
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    try:
        resp = requests.get('https://api16-normal-c-alisg.tiktokv.com/lite/v2/public/item/list/?max_cursor=0&count=100', headers=headers, cookies=cookies, timeout=10)
        if resp.status_code == 200:
            html = resp.text
            aweme_ids = sorted(set(re.findall(r'"aweme_id"\s*:\s*"(\d+)"', html)))
            return aweme_ids
    except Exception as e:
        print(f"خطأ في جلب صفحة المستخدم: {e}")

    return set()

def delete_aweme(sessionid, aweme_id):
    cookies = {
        'sessionid': sessionid,
        'sessionid_ss': sessionid,
        'sid_tt': sessionid,
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Content-Type': 'application/json',
    }

    url = f'https://www.tiktok.com/api/aweme/delete/?aweme_id={aweme_id}'
    try:
        resp = requests.post(url, headers=headers, cookies=cookies, timeout=20)
        return resp.status_code == 200
    except Exception as e:
        print(f"- ❌ ¦- خطأ في حذف الفيديو {aweme_id}: {e}")
        return False

def delete_videos_loop(chat_id, sessionid):
    deleted_count = 0
    try:
        while True:
            aweme_ids = fetch_aweme_ids(sessionid)
            if not aweme_ids:
                bot.send_message(chat_id, "- ✅ ¦- تم الانتهاء من حذف جميع الفيديوهات")
                break

            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(delete_aweme, sessionid, aweme_id) for aweme_id in aweme_ids]
                for future in as_completed(futures):
                    if future.result():
                        deleted_count += 1
                        if deleted_count % 5 == 0:
                            try:
                                bot.edit_message_text(
                                    chat_id=chat_id,
                                    message_id=user_progress_messages[chat_id],
                                    text=f"- ✅¦- عدد الفيديوهات المحذوفة: [ {deleted_count} ]"
                                )
                            except:
                                pass
    except Exception as e:
        bot.send_message(chat_id, f"- ❌ ¦- خطأ: {e}")

class TikTokUnfollowBot:
    def __init__(self, session_id):
        self.unfollowed = 0
        self.failed = 0
        self.total = 0
        self.stop_threads = False
        self.queue = queue.Queue()
        self.session_id = session_id

    def sig(self, prm, pl=None, aid=1340):
        if not MEDOSIGNER_AVAILABLE:
            return {}

        t = int(time.time())
        ps = urllib.parse.urlencode(prm)

        if pl:
            pls = urllib.parse.urlencode(pl)
            xst = md5(pls.encode('utf-8')).hexdigest().upper()
        else:
            pls = ""
            xst = None

        gd = Gorgon(ps, t, pls, None).get_value()
        ln = Ladon.encrypt(t, 1611921764, aid)

        ag = Argus.get_sign(
            ps,
            xst,
            t,
            platform=19,
            aid=aid,
            license_id=1611921764,
            sec_device_id="",
            sdk_version="2.3.15.i18n",
            sdk_version_int=2
        )

        sigs = {
            "x-ladon": ln,
            "x-khronos": str(t),
            "x-argus": ag,
            "x-gorgon": gd.get("x-gorgon", ""),
            "x-ss-req-ticket": str(int(time.time() * 1000))
        }

        if xst:
            sigs["x-ss-stub"] = xst

        return sigs

    def get_user(self, name):
        url = f"https://www.tiktok.com/@{name}"
        hd = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }

        try:
            r = requests.get(url, headers=hd, timeout=15)
            if r.status_code != 200:
                return None

            ht = r.text

            pat1 = r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">(.*?)</script>'
            pat2 = r'{"props":{"pageProps":.*?}}'

            data = None
            for pat in [pat1, pat2]:
                m = re.search(pat, ht, re.DOTALL)
                if m:
                    try:
                        data = json.loads(m.group(1) if pat == pat1 else m.group(0))
                        break
                    except:
                        continue

            if not data:
                return None

            def find(d):
                if isinstance(d, dict):
                    if 'user' in d and 'id' in d['user']:
                        return d['user']
                    for v in d.values():
                        res = find(v)
                        if res:
                            return res
                elif isinstance(d, list):
                    for i in d:
                        res = find(i)
                        if res:
                            return res
                return None

            u = find(data)
            if u:
                return {
                    'uid': str(u.get('id', '')),
                    'sec': u.get('secUid', ''),
                    'name': u.get('nickname', ''),
                }

            return None

        except:
            return None

    def get_page(self, uid, sec, tok=""):
        url = "https://api16-normal-c-alisg.tiktokv.com/lite/v2/relation/following/list/"

        prm = {
            'user_id': uid,
            'count': "100",
            'page_token': tok,
            'source_type': "4",
            'request_tag_from': "h5",
            'sec_user_id': sec,
            'manifest_version_code': "400603",
            '_rticket': str(int(time.time() * 1000)),
            'app_language': "ar",
            'app_type': "normal",
            'iid': "7583278212717954823",
            'app_package': "com.zhiliaoapp.musically.go",
            'channel': "googleplay",
            'device_type': "RMX3834",
            'language': "ar",
            'host_abi': "arm64-v8a",
            'locale': "ar",
            'resolution': "720*1454",
            'openudid': "b57299cf6a5bb211",
            'update_version_code': "400603",
            'ac2': "wifi",
            'cdid': "f7e5f9fe-bce4-48d5-8857-7caa1b0d34b8",
            'sys_region': "EG",
            'os_api': "34",
            'timezone_name': "Asia/Baghdad",
            'dpi': "272",
            'carrier_region': "IQ",
            'ac': "wifi",
            'device_id': "7456376313159714309",
            'os': "android",
            'os_version': "14",
            'timezone_offset': "10800",
            'version_code': "400603",
            'app_name': "musically_go",
            'ab_version': "40.6.3",
            'version_name': "40.6.3",
            'device_brand': "realme",
            'op_region': "IQ",
            'ssmix': "a",
            'device_platform': "android",
            'build_number': "40.6.3",
            'region': "EG",
            'aid': "1340",
            'ts': str(int(time.time()))
        }

        s = self.sig(prm)

        hd = {
            'User-Agent': "com.zhiliaoapp.musically.go/400603 (Linux; U; Android 14; ar; RMX3834; Build/UP1A.231005.007;tt-ok/3.12.13.44.lite-ul)",
            'Cookie': f"sessionid={self.session_id};"
        }

        if s:
            hd.update({
                'x-ladon': s.get("x-ladon", ""),
                'x-khronos': s.get("x-khronos", ""),
                'x-argus': s.get("x-argus", ""),
                'x-gorgon': s.get("x-gorgon", ""),
                'x-ss-req-ticket': s.get("x-ss-req-ticket", "")
            })
            if 'x-ss-stub' in s:
                hd['x-ss-stub'] = s['x-ss-stub']

        try:
            r = requests.get(url, params=prm, headers=hd, timeout=10)
            if r.status_code == 200:
                return r.json()
            else:
                return None
        except:
            return None

    def get_all(self, uid, sec):
        all_users = []
        page = 0
        more = True
        token = ""
        max_pages = 50

        while more and page < max_pages:
            page += 1

            d = self.get_page(uid, sec, token)

            if not d:
                break

            if d.get('status_code') != 0:
                break

            users = d.get('followings', [])
            all_users.extend(users)

            more = d.get('has_more', False)
            token = d.get('next_page_token', "")

            if more:
                time.sleep(0.3)

        return all_users

    def unfollow(self, target_id):
        url = "https://api16-normal-c-alisg.tiktokv.com/lite/v2/relation/follow/"

        prm = {
            'request_tag_from': "h5",
            'manifest_version_code': "400603",
            '_rticket': str(int(time.time() * 1000)),
            'app_language': "ar",
            'app_type': "normal",
            'iid': "7583278212717954823",
            'app_package': "com.zhiliaoapp.musically.go",
            'channel': "googleplay",
            'device_type': "RMX3834",
            'language': "ar",
            'host_abi': "arm64-v8a",
            'locale': "ar",
            'resolution': "720*1454",
            'openudid': "b57299cf6a5bb211",
            'update_version_code': "400603",
            'ac2': "wifi",
            'cdid': "f7e5f9fe-bce4-48d5-8857-7caa1b0d34b8",
            'sys_region': "EG",
            'os_api': "34",
            'timezone_name': "Asia/Baghdad",
            'dpi': "272",
            'carrier_region': "IQ",
            'ac': "wifi",
            'device_id': "7456376313159714309",
            'os': "android",
            'os_version': "14",
            'timezone_offset': "10800",
            'version_code': "400603",
            'app_name': "musically_go",
            'ab_version': "40.6.3",
            'version_name': "40.6.3",
            'device_brand': "realme",
            'op_region': "IQ",
            'ssmix': "a",
            'device_platform': "android",
            'build_number': "40.6.3",
            'region': "EG",
            'aid': "1340",
            'ts': str(int(time.time()))
        }

        pl = {
            'user_id': str(target_id),
            'from_page': "following_list",
            'from': "34",
            'type': "0"
        }

        s = self.sig(prm, pl)

        hd = {
            'User-Agent': "com.zhiliaoapp.musically.go/400603 (Linux; U; Android 14; ar; RMX3834; Build/UP1A.231005.007;tt-ok/3.12.13.44.lite-ul)",
            'Cookie': f"sessionid={self.session_id};",
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        if s:
            hd.update({
                'x-ladon': s.get("x-ladon", ""),
                'x-khronos': s.get("x-khronos", ""),
                'x-argus': s.get("x-argus", ""),
                'x-gorgon': s.get("x-gorgon", ""),
                'x-ss-req-ticket': s.get("x-ss-req-ticket", "")
            })
            if 'x-ss-stub' in s:
                hd['x-ss-stub'] = s['x-ss-stub']

        try:
            r = requests.post(url, params=prm, data=pl, headers=hd, timeout=10)
            if r.status_code == 200:
                res = r.json()
                return res.get('status_code') == 0
            else:
                return False
        except:
            return False

    def worker(self):
        while not self.stop_threads:
            try:
                u = self.queue.get(timeout=1)
                uid = u.get('uid', '')
                uname = u.get('unique_id', 'N/A')

                if uid:
                    ok = self.unfollow(uid)
                    if ok:
                        self.unfollowed += 1
                    else:
                        self.failed += 1

                self.queue.task_done()

            except queue.Empty:
                break
            except:
                self.queue.task_done()
                continue

    def unfollow_all(self, users):
        if not users:
            return False, "- ❌ ¦- لا يوجد مستخدمين"

        self.total = len(users)
        self.unfollowed = 0
        self.failed = 0

        for u in users:
            self.queue.put(u)

        threads_count = 5
        threads = []
        for i in range(threads_count):
            t = threading.Thread(target=self.worker)
            t.daemon = True
            t.start()
            threads.append(t)

        self.queue.join()

        self.stop_threads = True
        for t in threads:
            t.join(timeout=2)

        return True, f"- ✅ ¦- تم الغاء متابعة  [ {self.unfollowed} ]حساب"

def process_unfollow(chat_id, session_id, username):
    try:
        bot.send_message(chat_id, f"- 🕜 ¦- جاري البحث عن الحساب @{username}...")

        tiktok_bot = TikTokUnfollowBot(session_id)
        user_info = tiktok_bot.get_user(username)

        if not user_info:
            bot.send_message(chat_id, "- ❌ ¦- لم استطع العثور على الحساب")
            return

        bot.send_message(chat_id,
            f"- ✅ ¦- تم العثور على الحساب\n"
            f"- ✅ ¦- الاسم =  {user_info['name']}\n"
            f"- ✅ ¦- الايدي : {user_info['uid']}\n\n"
            f"جاري استخراج المتابعين..."
        )

        users_list = tiktok_bot.get_all(user_info['uid'], user_info['sec'])

        if not users_list:
            bot.send_message(chat_id, "- ❌ ¦- لا يوجد متابعين في هذا الحساب")
            return

        bot.send_message(chat_id, f"- ✅ ¦- تم استخراج {len(users_list)} متابع\nجاري الغاء المتابعة... )")

        progress_msg = bot.send_message(chat_id, f"0/{len(users_list)}")

        def update_progress():
            while tiktok_bot.unfollowed + tiktok_bot.failed < tiktok_bot.total:
                try:
                    current = tiktok_bot.unfollowed + tiktok_bot.failed
                    bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=progress_msg.message_id,
                        text=f"{current}/{len(users_list)}"
                    )
                except:
                    pass
                time.sleep(2)

        progress_thread = threading.Thread(target=update_progress)
        progress_thread.daemon = True
        progress_thread.start()

        success, result = tiktok_bot.unfollow_all(users_list)

        if success:
            bot.send_message(chat_id, f"- ✅ ¦-تمت العملية بنجاح\n\n{result}")

            filename = f"karbo_{username}_{ts}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(karbo_content)

            with open(filename, "rb") as f:
                bot.send_document(chat_id, f)

            try:
                os.remove(filename)
            except:
                pass

        else:
            bot.send_message(chat_id, f"- ❌ ¦-فشلت العملية: {result}")

    except Exception as e:
        bot.send_message(chat_id, f"- ❌ ¦-حدث خطأ: {str(e)}")

def get_stats():
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')

    today_stats = users_db["daily_stats"].get(today, {"users": 0, "messages": 0, "starts": 0})
    yesterday_stats = users_db["daily_stats"].get(yesterday, {"users": 0, "messages": 0, "starts": 0})

    new_today = today_stats["users"]
    new_yesterday = yesterday_stats["users"]

    current_month = datetime.datetime.now().strftime('%Y-%m')
    new_this_month = sum(stats["users"] for date, stats in users_db["daily_stats"].items()
                        if date.startswith(current_month))

    last_month = (datetime.datetime.now().replace(day=1) - datetime.timedelta(days=1)).strftime('%Y-%m')
    new_last_month = sum(stats["users"] for date, stats in users_db["daily_stats"].items()
                        if date.startswith(last_month))

    stats_message = f"""
احصائيات البوت:

المستخدمون:
- العدد الإجمالي للمستخدمين: {users_db['total_users']}
- عدد المستخدمين في الخاص: {users_db['private_users']}
- عدد القنوات والمجموعات: {users_db['channels_groups']}
- عدد المحظورين: {users_db['banned_users']}

التفاعل:
- اليوم ({today}):
  - المستخدمون: {today_stats['users']}
  - المستخدمون النشطون: {today_stats['users']}
  - بداية الاشتراك: {today_stats['starts']}
  - الرسائل: {today_stats['messages']}

- في الأمس ({yesterday}):
  - المستخدمون: {yesterday_stats['users']}
  - المستخدمون النشطون: {yesterday_stats['users']}
  - بداية الاشتراك: {yesterday_stats['starts']}
  - الرسائل: {yesterday_stats['messages']}

- عدد المستخدمين الجدد اليوم: {new_today}
- عدد المستخدمين الجدد بالأمس: {new_yesterday}
- عدد المستخدمين الجدد هذا الشهر: {new_this_month}
- عدد المستخدمين الجدد في الشهر الماضي: {new_last_month}
"""
    return stats_message

def broadcast_message(text, exclude_users=None):
    if exclude_users is None:
        exclude_users = []

    sent_count = 0
    failed_count = 0

    for user_id in users_db["user_data"].keys():
        if user_id in exclude_users or user_id == BOT_OWNER:
            continue

        try:
            bot.send_message(user_id, text)
            sent_count += 1
            time.sleep(0.2)
        except:
            failed_count += 1

    return sent_count, failed_count

def parse_duration(duration_str):
    duration_str = duration_str.lower().strip()

    if duration_str.endswith('h'):
        hours = int(duration_str[:-1])
        return hours * 3600, f"{hours} ساعة"
    elif duration_str.endswith('m'):
        minutes = int(duration_str[:-1])
        return minutes * 60, f"{minutes} دقيقة"
    elif duration_str.endswith('d'):
        days = int(duration_str[:-1])
        return days * 86400, f"{days} يوم"
    else:
        try:
            hours = int(duration_str)
            return hours * 3600, f"{hours} ساعة"
        except:
            return 3600, "ساعة واحدة"

def send_subscription_notification(user_id, duration_text, expiry_date):
    try:
        message = f"""
- ✅ ¦- تم تفعيل الاشتراك لك

- 🕜 ¦- مدة اشتراكك: {duration_text}
- 🕜 ¦- اشتراكك صالح لغاية: {expiry_date}

"""
        bot.send_message(user_id, message)
    except:
        pass

def show_main_menu(chat_id, user_id, message_id=None):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("إخفاء الفيديوهات", callback_data="make_private", style="primary"),
        InlineKeyboardButton("حذف الفيديوهات", callback_data="delete_videos", style="danger"),
        InlineKeyboardButton("إلغاء المتابعة", callback_data="unfollow_users", style="danger"),
    )
    markup.add(
        InlineKeyboardButton("فحص السيشن", callback_data="check_session", style="primary"),
    )
    markup.add(
        InlineKeyboardButton("سحب لستة", callback_data="get_followings", style="primary"),
        InlineKeyboardButton("معلومات حساب", callback_data="account_info", style="primary")
    )
    markup.add(
        InlineKeyboardButton("سحب سيشن", url="https://vt.tiktok.com/ZSkUaFXQf/", style="primary")
    )
    markup.add(
        InlineKeyboardButton("المطور", url="https://t.me/j49_c", style="primary"),
        InlineKeyboardButton("القناة", url="https://t.me/bshshshkk", style="primary")
    )
    markup.add(
        InlineKeyboardButton("F7_7G", url="https://t.me/F7_7G", style="primary"),
        InlineKeyboardButton("H_U_VB", url="https://t.me/H_U_VB", style="primary")
    )
    markup.add(
        InlineKeyboardButton("seed_1k", url="https://t.me/seed_1k", style="primary"),
        InlineKeyboardButton("TERBO_CODE", url="https://t.me/TERBO_CODE", style="primary")
    )
    markup.add(
        InlineKeyboardButton("BQBOOB1", url="https://t.me/BQBOOB1", style="primary"),
        InlineKeyboardButton("EQJ_1", url="https://t.me/EQJ_1", style="primary")
    )
    markup.add(
        InlineKeyboardButton("HAMO_X_OT3", url="https://t.me/HAMO_X_OT3", style="primary")
    )

    if user_id == BOT_OWNER:
        markup.add(
            InlineKeyboardButton("اذاعة في البوت", callback_data="broadcast", style="danger"),
            InlineKeyboardButton("احصائيات البوت", callback_data="stats", style="primary")
        )
        markup.add(
            InlineKeyboardButton("حظر مستخدم", callback_data="ban_user", style="danger"),
            InlineKeyboardButton("إلغاء حظر", callback_data="unban_user", style="success")
        )
        markup.add(
            InlineKeyboardButton("تفعيل لمستخدم", callback_data="activate_user", style="success")
        )

    welcome_message = f"""
- مرحباً
- البوت متخصص في خدمات تيك توك
- البوت مدفوع
- المطور: White Wolf
- القناة: t.me/bshshshkk
"""
    if message_id:
        bot.edit_message_text(welcome_message, chat_id=chat_id, message_id=message_id, reply_markup=markup)
    else:
        bot.send_message(chat_id, welcome_message, reply_markup=markup)

def send_subscription_required(chat_id, user_id):
    text = "يرجى الاشتراك في القنوات التالية لاستخدام البوت:"
    markup = get_subscription_keyboard()
    bot.send_message(chat_id, text, reply_markup=markup)

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if user_id != BOT_OWNER and user_id not in users_db["user_data"]:
        notify_new_user(user_id)

    user_states[chat_id] = "started"

    today = datetime.datetime.now().strftime('%Y-%m-%d')
    if today in users_db["daily_stats"]:
        users_db["daily_stats"][today]["messages"] += 1
        users_db["daily_stats"][today]["starts"] += 1

    subscribed, missing = is_subscribed(user_id)
    if not subscribed:
        send_subscription_required(chat_id, user_id)
        return

    show_main_menu(chat_id, user_id)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    today = datetime.datetime.now().strftime('%Y-%m-%d')
    if today in users_db["daily_stats"]:
        users_db["daily_stats"][today]["messages"] += 1

    if call.data == "check_sub":
        subscribed, missing = is_subscribed(user_id)
        if subscribed:
            bot.answer_callback_query(call.id, "تم الاشتراك بنجاح!")
            bot.delete_message(chat_id, message_id)
            show_main_menu(chat_id, user_id)
        else:
            bot.answer_callback_query(call.id, "لم تقم بالاشتراك في جميع القنوات")
            send_subscription_required(chat_id, user_id)
        return

    subscribed, _ = is_subscribed(user_id)
    if not subscribed and user_id != BOT_OWNER:
        bot.answer_callback_query(call.id, "يرجى الاشتراك في القنوات أولاً")
        send_subscription_required(chat_id, user_id)
        return

    if call.data == "make_private":
        user_states[user_id] = "waiting_session_for_private"
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="- أرسل السيشن : "
        )

    elif call.data == "delete_videos":
        user_states[user_id] = "waiting_session_for_delete"
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="- أرسل السيشن : "
        )

    elif call.data == "check_session":
        user_states[user_id] = "waiting_session_for_check"
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="أرسل sessionid للفحص:"
        )

    elif call.data == "check_level":
        user_states[user_id] = "waiting_username_for_level"
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="أرسل اسم المستخدم (بدون @) لفحص مستوى الدعم:"
        )

    elif call.data == "get_followings":
        user_states[user_id] = "waiting_username_for_followings"
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="أرسل اسم المستخدم (بدون @) لسحب قائمة المتابعين:"
        )

    elif call.data == "account_info":
        user_states[user_id] = "waiting_session_for_account"
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="- أرسل السيشن : "
        )

    elif call.data == "unfollow_users":
        user_states[user_id] = "waiting_unfollow_info"
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="أرسل sessionid واليوزر (مثال: sessionid username):"
        )

    elif call.data == "broadcast" and user_id == BOT_OWNER:
        user_states[user_id] = "waiting_broadcast_message"
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="أرسل نص الرسالة التي تريد بثها:"
        )

    elif call.data == "stats" and user_id == BOT_OWNER:
        stats = get_stats()
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=stats
        )

    elif call.data == "ban_user" and user_id == BOT_OWNER:
        user_states[user_id] = "waiting_user_id_for_ban"
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="أرسل ID المستخدم الذي تريد حظره:"
        )

    elif call.data == "unban_user" and user_id == BOT_OWNER:
        user_states[user_id] = "waiting_user_id_for_unban"
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="أرسل ID المستخدم الذي تريد إلغاء حظره:"
        )

    elif call.data == "activate_user" and user_id == BOT_OWNER:
        user_states[user_id] = "waiting_user_id_for_activate"
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text="أرسل الايدي ثم المدة (مثال: 123456789 3h):"
        )

    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    text = message.text.strip()

    today = datetime.datetime.now().strftime('%Y-%m-%d')
    if today in users_db["daily_stats"]:
        users_db["daily_stats"][today]["messages"] += 1
    else:
        users_db["daily_stats"][today] = {"users": 0, "messages": 1, "starts": 0}

    if user_id in user_states:
        state = user_states[user_id]

        if state == "waiting_session_for_private":
            bot.send_message(chat_id, "جاري إخفاء الفيديوهات...")
            Thread(target=run_privater, args=(text, chat_id)).start()
            user_states.pop(user_id, None)

        elif state == "waiting_session_for_delete":
            user_sessions[chat_id] = text
            sent_msg = bot.send_message(chat_id, "- ✅ ¦- عدد الفيديوهات المحذوفة: 0")
            user_progress_messages[chat_id] = sent_msg.message_id
            Thread(target=delete_videos_loop, args=(chat_id, text)).start()
            user_states.pop(user_id, None)

        elif state == "waiting_session_for_check":
            try:
                info = generalinfo(text)
                bal = balance(text)

                if info.get("message") != "success" or not bal:
                    bot.send_message(chat_id, "- ❌ ¦- السيشن غير صالح أو منتهي")
                    return

                karb2 = info.get("data", {})
                Karb1 = {}
                try:
                    Karb1 = bal.json().get("data", {})
                except:
                    pass

                created = karb2.get("create_time", 0)

                msg = f"""
Username: {karb2.get('username', '')}
User ID: {karb2.get('user_id', '')}
Sec User ID: {karb2.get('sec_user_id', '')}
Screen Name: {karb2.get('screen_name', '')}
Bio: {karb2.get('description', '')}
Mobile: {karb2.get('mobile', '')}
Email: {karb2.get('email', '')}
Created At: {conv(created) if created else "N/A"}
Coins: {Karb1.get("coins", "")}
Frozen Coins: {Karb1.get("frozen_coins", "")}
Allow Status: {Karb1.get("is_allow", "")}
Email Confirmed: {Karb1.get("is_email_confirmed", "")}
Quick Payment: {Karb1.get("quick_payment_available", "")}
"""
                bot.send_message(chat_id, msg)
            except Exception as e:
                bot.send_message(chat_id, f"خطأ: {e}")
            finally:
                user_states.pop(user_id, None)

        elif state == "waiting_username_for_level":
            if not text:
                bot.send_message(chat_id, "يجب إرسال اسم مستخدم")
                user_states.pop(user_id, None)
                return

            bot.send_message(chat_id, f"جاري فحص @{text}...")
            level, error = get_tiktok_level(text)

            if error:
                bot.send_message(chat_id, f"خطأ: {error}")
            else:
                bot.send_message(chat_id, f"""
Username: @{text}
Level: {level}
""")
            user_states.pop(user_id, None)

        elif state == "waiting_username_for_followings":
            if not text:
                bot.send_message(chat_id, "يجب إرسال اسم مستخدم")
                user_states.pop(user_id, None)
                return

            bot.send_message(chat_id, f"- 🕜 ¦-جاري سحب متابعات @{text}...")
            user_id_tik, sec_uid = extract_ids(text)

            if not user_id_tik or not sec_uid:
                bot.send_message(chat_id, "- ❌ ¦-لم يتم العثور على المستخدم")
                user_states.pop(user_id, None)
                return

            followings = fetch_followings(user_id_tik, sec_uid, username_display=text)

            if followings:
                with open("followings.txt", "w", encoding="utf-8") as f:
                    for username, count in followings:
                        f.write(f"{username}\n")

                with open("followings.txt", "rb") as f:
                    bot.send_document(
                        chat_id,
                        f,
                        caption=f"- ✅ ¦- تم سحب {len(followings)} متابع من @{text}"
                    )

                try:
                    os.remove("followings.txt")
                except:
                    pass
            else:
                bot.send_message(chat_id, "- ❌ ¦-لم يتم العثور على متابعين")

            user_states.pop(user_id, None)

        elif state == "waiting_session_for_account":
            info = extract_account_info(text)
            if info:
                msg = f"""
ID: {info['user_id']}
Name: {info['screen_name']}
Username: {info['username']}
Email: {info['email']}
Phone: {info['mobile']}
Bio: {info['description']}
Created: {info['create_time']}
"""
                bot.send_message(chat_id, msg)
            else:
                bot.send_message(chat_id, "- ❌ ¦- السيشن غير صالح")
            user_states.pop(user_id, None)

        elif state == "waiting_unfollow_info":
            try:
                parts = text.split()
                if len(parts) != 2:
                    bot.send_message(chat_id, "- ❌ ¦-  استخدم: sessionid username")
                    return

                session_id = parts[0]
                username = parts[1]

                bot.send_message(chat_id, f"- 🕜 ¦-جاري بدء عملية الغاء المتابعة لـ @{username}...")
                Thread(target=process_unfollow, args=(chat_id, session_id, username)).start()

            except Exception as e:
                bot.send_message(chat_id, f"- ❌¦- خطأ: {str(e)}")
            finally:
                user_states.pop(user_id, None)

        elif state == "waiting_broadcast_message" and user_id == BOT_OWNER:
            bot.send_message(chat_id, "جاري الاذاعة...")
            sent, failed = broadcast_message(text)
            bot.send_message(chat_id, f"""
تم إرسال الاذاعة :
تم الإرسال: {sent}
فشل الإرسال: {failed}
""")
            user_states.pop(user_id, None)

        elif state == "waiting_user_id_for_ban" and user_id == BOT_OWNER:
            try:
                target_id = int(text)
                users_db["banned_users"] += 1
                bot.send_message(chat_id, f"تم حظر المستخدم {target_id}")
            except:
                bot.send_message(chat_id, "ID غير صالح")
            user_states.pop(user_id, None)

        elif state == "waiting_user_id_for_unban" and user_id == BOT_OWNER:
            try:
                target_id = int(text)
                if users_db["banned_users"] > 0:
                    users_db["banned_users"] -= 1
                bot.send_message(chat_id, f"تم إلغاء حظر المستخدم {target_id}")
            except:
                bot.send_message(chat_id, "ID غير صالح")
            user_states.pop(user_id, None)

        elif state == "waiting_user_id_for_activate" and user_id == BOT_OWNER:
            try:
                parts = text.split()
                if len(parts) != 2:
                    bot.send_message(chat_id, "صيغة غير صحيحة. استخدم: الايدي ثم المدة (مثال: 123456789 3h)")
                    return

                target_id = None
                duration_str = None

                try:
                    target_id = int(parts[0])
                    duration_str = parts[1]
                except:
                    try:
                        duration_str = parts[0]
                        target_id = int(parts[1])
                    except:
                        bot.send_message(chat_id, "صيغة غير صحيحة. تأكد من كتابة الأرقام بشكل صحيح")
                        return

                duration_seconds, duration_text = parse_duration(duration_str)
                expiry_time = datetime.datetime.now() + datetime.timedelta(seconds=duration_seconds)

                users_db["active_subscriptions"][target_id] = {
                    "duration": duration_text,
                    "expires": expiry_time.strftime('%Y-%m-%d %H:%M:%S'),
                    "activated_by": user_id,
                    "activated_at": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }

                activation_info = f"""
- ✅ ¦- تم التفعيل للمستخدم = {target_id}
🕓 ¦ - المدة: {duration_text}
- 🕜 ¦- وقت التفعيل: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🕜 ¦- وقت الانتهاء: {expiry_time.strftime('%Y-%m-%d %H:%M:%S')}
"""
                bot.send_message(chat_id, activation_info)

                send_subscription_notification(target_id, duration_text, expiry_time.strftime('%Y-%m-%d %H:%M:%S'))

            except Exception as e:
                bot.send_message(chat_id, f"خطأ: {str(e)}")
            finally:
                user_states.pop(user_id, None)

    else:
        if user_id != BOT_OWNER:
            subscribed, _ = is_subscribed(user_id)
            if not subscribed:
                send_subscription_required(chat_id, user_id)
                return
        start_command(message)

def extract_account_info(session_id):
    cookies = {
        'sessionid': session_id,
        'sessionid_ss': session_id,
        'sid_tt': session_id,
    }

    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    url = "https://www.tiktok.com/passport/web/account/info/"

    try:
        response = requests.get(url, headers=headers, cookies=cookies, timeout=10)
        if response.status_code == 200:
            data = response.json().get("data", {})
            return {
                "user_id": data.get("user_id_str", ""),
                "screen_name": data.get("screen_name", ""),
                "username": data.get("username", ""),
                "email": data.get("email", ""),
                "mobile": data.get("mobile", ""),
                "description": data.get("description") or "nothing",
                "create_time": datetime.datetime.fromtimestamp(data.get("create_time", 0)).strftime('%Y-%m-%d %H:%M:%S'),
            }
        else:
            return None
    except:
        return None

if __name__ == "__main__":
    print("البوت يعمل الآن!")

    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"- ❌ ¦- Error: {e}")
