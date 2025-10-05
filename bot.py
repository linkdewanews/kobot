import logging
import sqlite3
import asyncio
import json
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, BotCommandScopeChat
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    CallbackQueryHandler, 
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
    Application
)
from telegram.error import BadRequest, Forbidden

# Konfigurasi logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Konfigurasi Bot ---
TOKEN = "GANTI DENGAN TOKEN BOT ANDA"
CHANNEL_WAJIB_ID = CHANNELID  # Ganti dengan ID Channel Wajib Anda
GRUP_UTAMA_ID = GROUPID      # Ganti dengan ID Grup Utama Anda
INITIAL_ADMIN_ID = ADMINID      # ID Admin awal untuk inisialisasi

# --- States untuk Conversation Handlers ---
(WAITING_MEDIA, WAITING_TEXT, WAITING_BUTTONS, WAITING_CONFIRMATION) = range(4)
(WAITING_WELCOME_TEXT, WAITING_WELCOME_BUTTONS, WAITING_WELCOME_CONFIRM) = range(4, 7)
(WAITING_TEMPLATE_MEDIA, WAITING_TEMPLATE_TEXT, WAITING_TEMPLATE_BUTTONS, WAITING_TEMPLATE_CONFIRM) = range(7, 11)

# --- Fungsi Inisialisasi Perintah Bot ---
async def post_init(application: Application):
    user_commands = [
        BotCommand("start", "Memulai bot & verifikasi"),
        BotCommand("help", "Menampilkan pesan bantuan")
    ]
    await application.bot.set_my_commands(user_commands)

    admin_commands = user_commands + [
        BotCommand("admin", "Membuka panel kontrol admin"),
        BotCommand("broadcast", "Mengirim pesan ke semua user"),
        BotCommand("setwelcome", "Mengatur pesan sambutan"),
        BotCommand("gantichannel", "Mengatur ID Channel"),
        BotCommand("setchannellink", "Mengatur Link Channel"),
        BotCommand("gantigroup", "Mengatur ID Grup"),
        BotCommand("listusers", "Menampilkan daftar user"),
        BotCommand("verifikasiulang", "Verifikasi ulang seorang user"),
        BotCommand("settemplate", "Mengatur template broadcast"),
        BotCommand("broadcasttemplate", "Mengirim broadcast dari template"),
        BotCommand("addadmin", "Menambah admin baru"),
        BotCommand("deladmin", "Menghapus admin"),
        BotCommand("listadmins", "Menampilkan daftar admin")
    ]
    
    all_admins = get_all_admins()
    for admin_id in all_admins:
        try:
            await application.bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
        except Exception as e:
            logger.warning(f"Gagal mengatur perintah untuk admin {admin_id}: {e}")
    logger.info(f"Perintah bot kustom telah diatur untuk {len(all_admins)} admin.")

# --- Fungsi Database ---
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
    cursor.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)")
    
    # Tambahkan admin awal jika tabel admin kosong
    cursor.execute("SELECT COUNT(*) FROM admins")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (INITIAL_ADMIN_ID,))
        logger.info(f"Admin awal {INITIAL_ADMIN_ID} ditambahkan ke database.")

    conn.commit()
    conn.close()
    logger.info("Database 'users.db' dengan tabel 'users', 'config', dan 'admins' berhasil diinisialisasi.")

def add_user(user_id: int):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users

def is_user_in_db(user_id: int) -> bool:
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def get_config(key: str):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def set_config(key: str, value: str):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

# --- Fungsi Manajemen Admin ---
def is_admin(user_id: int) -> bool:
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
    is_admin_user = cursor.fetchone() is not None
    conn.close()
    return is_admin_user

def add_admin_to_db(user_id: int):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def remove_admin_from_db(user_id: int):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_all_admins():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM admins")
    admins = [row[0] for row in cursor.fetchall()]
    conn.close()
    return admins

# --- Handler Perintah ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user:
        add_user(user.id)

    custom_text = get_config('welcome_text')
    custom_buttons_json = get_config('welcome_buttons')

    if custom_text:
        text = custom_text.replace('{mention}', user.mention_html())
        buttons_data = json.loads(custom_buttons_json) if custom_buttons_json else []
        buttons = [[InlineKeyboardButton(b['text'], url=b['url'])] for row in buttons_data for b in row]
        reply_markup = InlineKeyboardMarkup(buttons) if buttons else None
    else:
        # Fallback ke pesan default
        text = f"""<b>🔥 Selamat Datang di Gerbang Kenikmatan, {user.mention_html()}! 🔥</b>

<i>Satu langkah lagi menuju surga dunia...</i>

Pastikan kamu sudah bergabung di <b>Channel Pemanasan</b> kami untuk mendapatkan akses.
Klik tombol di bawah ini, lalu verifikasi dirimu."""
        
        # Gunakan link invite yang sudah di-set, bukan generate dari ID
        channel_url = get_config('channel_invite_link')
        if not channel_url:
            logger.warning("Link undangan channel (channel_invite_link) belum diatur!")
            channel_url = "https://t.me/telegram" # Fallback URL jika belum di-set

        buttons = [
            [InlineKeyboardButton("➡️ JOIN CHANNEL PEMANASAN", url=channel_url)],
            [InlineKeyboardButton("🔞 VERIFIKASI & AKSES VVIP", callback_data="VERIFY_MEMBER")],
        ]
        reply_markup = InlineKeyboardMarkup(buttons)

    await update.message.reply_html(text, reply_markup=reply_markup)

# --- Handler Callback & Verifikasi ---
async def verify_member_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer("😈 Mengecek apakah kamu siap...", show_alert=False)
    await run_verification_logic(user.id, context, query)

async def run_verification_logic(user_id: int, context: ContextTypes.DEFAULT_TYPE, query: Update.callback_query = None):
    channel_id_str = get_config('channel_wajib_id')
    grup_id_str = get_config('grup_utama_id')
    
    channel_id = int(channel_id_str) if channel_id_str else CHANNEL_WAJIB_ID
    grup_id = int(grup_id_str) if grup_id_str else GRUP_UTAMA_ID
    try:
        member = await context.bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        if member.status not in ['member', 'administrator', 'creator']:
            raise BadRequest(f"User status is '{member.status}'")
    except BadRequest as e:
        error_text = """<b>❌ AKSES DITOLAK! ❌</b>

Kamu belum bergabung di <i>Channel Pemanasan</i>.
Jangan coba-coba menyelinap! 😉

<blockquote>Join dulu, baru minta akses lagi.</blockquote>"""
        if query: await query.edit_message_text(error_text, parse_mode='HTML')
        return

    try:
        if query: await query.edit_message_text("✅ <b>Siap!</b>\n\n<i>Gerbang surga sedang dibuka khusus untukmu...</i>", parse_mode='HTML')
        invite_link = await context.bot.create_chat_invite_link(chat_id=grup_id, member_limit=1, name=f"Undangan untuk {user_id}")
        final_text = f"""<b>🔞 AKSES VVIP DIBERIKAN! 🔞</b>

Selamat! Kamu berhasil mendapatkan tiket masuk ke surga kenikmatan.

Gunakan tautan spesial di bawah ini untuk masuk:
<a href="{invite_link.invite_link}"><b>💋 -- KLIK UNTUK MASUK GRUP VVIP -- 💋</b></a>

<blockquote>⚠️ <b>Peringatan Penting</b> ⚠️
Tautan ini bersifat <i>pribadi</i> dan <i>hanya untukmu seorang</i>. Tautan akan hangus setelah digunakan. Dilarang keras menyebarkannya!</blockquote>"""
        if query: await query.edit_message_text(final_text, parse_mode='HTML', disable_web_page_preview=True)
        else: await context.bot.send_message(user_id, final_text, parse_mode='HTML', disable_web_page_preview=True)
    except BadRequest as e:
        error_text = """<b>💦 Oops! Ada yang basah... 💦</b>

Ada sedikit kendala teknis saat membuat link khusus untukmu.
<code>ERR_INVITE_LINK_GENERATION</code>

Coba lagi beberapa saat, atau hubungi admin jika masalah berlanjut."""
        if query: await query.edit_message_text(error_text, parse_mode='HTML')

# --- Fitur Admin ---
async def reverify_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return

    try:
        target_user_id = int(context.args[0])
        if not is_user_in_db(target_user_id):
            await update.message.reply_text(f"User ID {target_user_id} tidak ditemukan di database.")
            return

        await update.message.reply_text(f"Memulai verifikasi ulang untuk user ID: {target_user_id}...")
        await run_verification_logic(target_user_id, context)
        await update.message.reply_text(f"Proses verifikasi ulang untuk {target_user_id} selesai.")

    except (IndexError, ValueError):
        await update.message.reply_text("Gunakan format: /verifikasiulang <user_id>")
    except Exception as e:
        await update.message.reply_text(f"Gagal menjalankan verifikasi ulang: {e}")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    user = update.effective_user
    text = f"""<b>===== ⚙️ PANEL KONTROL ADMIN =====</b>

Selamat datang, {user.mention_html()}!

Pilih salah satu perintah di bawah ini untuk mengelola bot."""
    keyboard = [
        [InlineKeyboardButton("📢 Broadcast Pesan", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🚀 Kirim Template", callback_data="admin_broadcasttemplate")],
        [InlineKeyboardButton("📝 Set Template Broadcast", callback_data="admin_settemplate")],
        [InlineKeyboardButton("✏️ Set Welcome Message", callback_data="admin_setwelcome")],
        [InlineKeyboardButton("👑 Kelola Admin", callback_data="admin_manage_admins")],
        [InlineKeyboardButton("🆔 Atur ID Channel/Grup", callback_data="admin_manage_ids")],
        [InlineKeyboardButton("🔄 Verifikasi Ulang User", callback_data="admin_reverify")],
        [InlineKeyboardButton("👥 List Users", callback_data="admin_listusers")]
    ]
    await update.message.reply_html(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    command = query.data
    text = ""

    if command == 'admin_broadcast':
        text = """<b>📢 Perintah Broadcast</b>

Untuk memulai sesi broadcast, ketik perintah:
<code>/broadcast</code>"""
    elif command == 'admin_broadcasttemplate':
        text = """<b>🚀 Perintah Kirim Template</b>

Untuk mengirim pesan massal menggunakan template, ketik:
<code>/broadcasttemplate</code>"""
    elif command == 'admin_settemplate':
        text = """<b>📝 Perintah Set Template</b>

Untuk membuat atau mengubah template broadcast, ketik:
<code>/settemplate</code>"""
    elif command == 'admin_manage_admins':
        text = """<b>👑 Manajemen Admin</b>

Perintah yang tersedia:
<code>/listadmins</code> - Melihat daftar admin
<code>/addadmin [USER_ID]</code> - Menambah admin
<code>/deladmin [USER_ID]</code> - Menghapus admin"""
    elif command == 'admin_manage_ids':
        text = """<b>🆔 Manajemen ID & Link</b>

Perintah yang tersedia:
<code>/gantichannel [ID_CHANNEL]</code>
<code>/setchannellink [LINK_CHANNEL]</code>
<code>/gantigroup [ID_GRUP]</code>"""
    elif command == 'admin_reverify':
        text = """<b>🔄 Perintah Verifikasi Ulang</b>

Format:
<code>/verifikasiulang [USER_ID]</code>"""
    elif command == 'admin_setwelcome':
        text = """<b>✏️ Perintah Set Welcome</b>

Untuk mengatur pesan selamat datang, ketik:
<code>/setwelcome</code>"""
    elif command == 'admin_listusers':
        text = """<b>👥 Perintah List Users</b>

Untuk menampilkan semua ID pengguna, ketik:
<code>/listusers</code>"""
    
    if text:
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=query.message.reply_markup)

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    users = get_all_users()
    if not users:
        await update.message.reply_text("Database pengguna masih kosong.")
        return

    if len(users) > 200:
        user_list_file = BytesIO('\n'.join(map(str, users)).encode('utf-8'))
        await update.message.reply_document(document=user_list_file, filename='user_ids.txt', caption=f"👥 Total Pengguna: {len(users)}")
    else:
        message = f"👥 *Total Pengguna: {len(users)}*\n\n`" + "`\n`".join(map(str, users)) + "`"
        await update.message.reply_html(message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        """<b>❓ Tersesat, Sayang? ❓</b>

Berikut beberapa petunjuk untukmu:

- Gunakan <code>/start</code> untuk memulai petualanganmu & mendapatkan akses VVIP.
- Jika ada masalah, coba ulangi dari awal.

<i>Kesabaran adalah kunci kenikmatan...</i> 😉"""
    )

# --- Handler Perintah Manajemen Admin ---
async def add_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    try:
        new_admin_id = int(context.args[0])
        if is_admin(new_admin_id):
            await update.message.reply_text(f"User {new_admin_id} sudah menjadi admin.")
            return
        add_admin_to_db(new_admin_id)
        await update.message.reply_text(f"✅ User {new_admin_id} berhasil ditambahkan sebagai admin.")
        # Coba atur command untuk admin baru
        await post_init(context.application)
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Gunakan format: /addadmin <user_id>")

async def del_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    try:
        target_admin_id = int(context.args[0])
        if not is_admin(target_admin_id):
            await update.message.reply_text(f"User {target_admin_id} bukan admin.")
            return
        
        all_admins = get_all_admins()
        if len(all_admins) <= 1 and target_admin_id in all_admins:
            await update.message.reply_text("❌ Tidak bisa menghapus satu-satunya admin.")
            return

        remove_admin_from_db(target_admin_id)
        await update.message.reply_text(f"✅ User {target_admin_id} berhasil dihapus dari daftar admin.")
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Gunakan format: /deladmin <user_id>")

async def list_admins_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    admins = get_all_admins()
    if not admins:
        await update.message.reply_text("Tidak ada admin yang terdaftar.")
        return
    message = "👑 *Daftar Admin Saat Ini:*\n\n`" + "`\n`".join(map(str, admins)) + "`"
    await update.message.reply_html(message)

# --- Conversation Handler untuk /setwelcome ---
async def set_welcome_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    context.user_data['welcome'] = {}
    await update.message.reply_html("📝 *Setup Pesan Sambutan*\n\n*Langkah 1/2:* Kirim teks untuk pesan sambutan. Anda bisa menggunakan `{mention}`.")
    return WAITING_WELCOME_TEXT

async def handle_welcome_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['welcome']['text'] = update.message.text_html
    await update.message.reply_html("✅ Teks diterima.\n*Langkah 2/2:* Kirim tombol dgn format `Teks | URL` (satu per baris), atau /skip.")
    return WAITING_WELCOME_BUTTONS

async def handle_welcome_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = update.message.text.split('\n')
    buttons = []
    for line in lines:
        parts = line.split('|')
        if len(parts) == 2:
            buttons.append([{'text': parts[0].strip(), 'url': parts[1].strip()}])
    context.user_data['welcome']['buttons_json'] = json.dumps(buttons)
    await update.message.reply_html("✅ Tombol diterima. Berikut pratinjaunya:")
    await show_welcome_preview(update, context)
    return WAITING_WELCOME_CONFIRM

async def skip_welcome_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['welcome']['buttons_json'] = '[]'
    await update.message.reply_html("⏭️ Tombol dilewati. Berikut pratinjaunya:")
    await show_welcome_preview(update, context)
    return WAITING_WELCOME_CONFIRM

async def show_welcome_preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data['welcome']
    text = data.get('text', '').replace('{mention}', update.effective_user.mention_html())
    buttons_data = json.loads(data.get('buttons_json', '[]'))
    buttons = [[InlineKeyboardButton(b['text'], url=b['url'])] for row in buttons_data for b in row]
    reply_markup = InlineKeyboardMarkup(buttons) if buttons else None
    await update.message.reply_html("📋 *--- PRATINJAU PESAN SAMBUTAN ---*", disable_web_page_preview=True)
    await update.message.reply_html(text, reply_markup=reply_markup, disable_web_page_preview=True)
    await update.message.reply_html("Ketik /save untuk menyimpan atau /cancel.")

async def save_welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    data = context.user_data['welcome']
    set_config('welcome_text', data['text'])
    set_config('welcome_buttons', data['buttons_json'])
    await update.message.reply_html("💾 *Pesan sambutan berhasil disimpan!* Bot akan menggunakan pesan ini untuk pengguna baru.")
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Setup pesan sambutan dibatalkan.")
    return ConversationHandler.END

# --- Fitur Anti-Spam Grup ---
async def anti_link_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    grup_id_str = get_config('grup_utama_id')
    grup_id = int(grup_id_str) if grup_id_str else GRUP_UTAMA_ID
    if not message or message.chat.id != grup_id: return
    user = message.from_user
    
    # Izinkan admin untuk mengirim link
    if is_admin(user.id): return

    chat_admins = await context.bot.get_chat_administrators(message.chat.id)
    if user.id in {admin.user.id for admin in chat_admins}: return

    if any(e.type in ['url', 'text_link'] for e in message.entities or []):
        try:
            await message.delete()
        except Exception as e:
            logger.error(f"Gagal menghapus pesan dari {user.id}: {e}")

import html

# --- Logika Inti Broadcast ---
async def _execute_broadcast(context: ContextTypes.DEFAULT_TYPE, data: dict, admin_id: int):
    users = get_all_users()
    if not users:
        await context.bot.send_message(admin_id, "Tidak ada pengguna di database untuk dikirimi broadcast.")
        return

    success, fail = 0, 0
    await context.bot.send_message(admin_id, f"Mengirim broadcast ke {len(users)} pengguna...")

    # Unescape teks sekali saja sebelum loop
    raw_text = data.get('text', ' ')
    text_to_send = html.unescape(raw_text)

    for user_id in users:
        try:
            buttons_list = data.get('buttons')
            reply_markup = InlineKeyboardMarkup(buttons_list) if buttons_list else None
            
            media_type = data.get('media_type')
            file_id = data.get('file_id')

            if media_type == 'photo':
                await context.bot.send_photo(user_id, photo=file_id, caption=text_to_send, reply_markup=reply_markup, parse_mode='HTML')
            elif media_type == 'video':
                await context.bot.send_video(user_id, video=file_id, caption=text_to_send, reply_markup=reply_markup, parse_mode='HTML')
            else:
                await context.bot.send_message(user_id, text=text_to_send, reply_markup=reply_markup, parse_mode='HTML')
            
            success += 1
            await asyncio.sleep(0.1)  # Jeda untuk menghindari rate limit
        except Forbidden:
            fail += 1
        except Exception as e:
            logger.error(f"Error saat broadcast ke {user_id}: {e}")
            fail += 1
            
    await context.bot.send_message(admin_id, f"--- Laporan Broadcast ---\nBerhasil: {success}\nGagal: {fail}\nTotal: {len(users)}")

# --- Fitur Broadcast (Conversation Handler) ---
async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    context.user_data['broadcast'] = {}
    await update.message.reply_text("Langkah 1/4: Kirim Media (Foto/Video) atau /skip.")
    return WAITING_MEDIA

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if message.photo:
        context.user_data['broadcast']['media_type'] = 'photo'
        context.user_data['broadcast']['file_id'] = message.photo[-1].file_id
    elif message.video:
        context.user_data['broadcast']['media_type'] = 'video'
        context.user_data['broadcast']['file_id'] = message.video.file_id
    await message.reply_text("✅ Media diterima.\nLangkah 2/4: Kirim Teks Pesan.")
    return WAITING_TEXT

async def skip_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['broadcast']['media_type'] = None
    await update.message.reply_text("Media dilewati.\nLangkah 2/4: Kirim Teks Pesan.")
    return WAITING_TEXT

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['broadcast']['text'] = update.message.text
    await update.message.reply_text("✅ Teks diterima.\nLangkah 3/4: Kirim Tombol (Format: Teks | URL) atau /skip.")
    return WAITING_BUTTONS

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = update.message.text.split('\n')
    buttons = []
    for line in lines:
        parts = line.split('|')
        if len(parts) == 2:
            buttons.append([InlineKeyboardButton(parts[0].strip(), url=parts[1].strip())])
    context.user_data['broadcast']['buttons'] = buttons
    await update.message.reply_text("✅ Tombol diterima.\nLangkah 4/4: Pratinjau.")
    await show_preview(update, context, 'broadcast')
    return WAITING_CONFIRMATION

async def skip_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['broadcast']['buttons'] = None
    await update.message.reply_text("Tombol dilewati.\nLangkah 4/4: Pratinjau.")
    await show_preview(update, context, 'broadcast')
    return WAITING_CONFIRMATION

async def show_preview(update: Update, context: ContextTypes.DEFAULT_TYPE, data_key: str):
    data = context.user_data[data_key]
    text = data.get('text', ' ')
    reply_markup = InlineKeyboardMarkup(data.get('buttons')) if data.get('buttons') else None
    
    await update.message.reply_text(f"--- PRATINJAU ({data_key.upper()}) ---")
    
    if data.get('media_type') == 'photo':
        await update.message.reply_photo(photo=data['file_id'], caption=text, reply_markup=reply_markup)
    elif data.get('media_type') == 'video':
        await update.message.reply_video(video=data['file_id'], caption=text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)
    
    command = "/sendnow" if data_key == 'broadcast' else "/save"
    await update.message.reply_text(f"Ketik `{command}` untuk melanjutkan atau /cancel.")

async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    await _execute_broadcast(context, context.user_data['broadcast'], update.effective_user.id)
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Sesi broadcast dibatalkan.")
    return ConversationHandler.END

# --- Fitur Template Broadcast ---
async def set_template_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    context.user_data['template'] = {}
    await update.message.reply_text("📝 *Membuat Template Broadcast*\n\nLangkah 1/3: Kirim Media (Foto/Video) atau /skip.")
    return WAITING_TEMPLATE_MEDIA

async def handle_template_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    data = context.user_data['template']
    if message.photo:
        data['media_type'] = 'photo'
        data['file_id'] = message.photo[-1].file_id
    elif message.video:
        data['media_type'] = 'video'
        data['file_id'] = message.video.file_id
    await message.reply_text("✅ Media diterima.\nLangkah 2/3: Kirim Teks Pesan.")
    return WAITING_TEMPLATE_TEXT

async def skip_template_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['template']['media_type'] = None
    await update.message.reply_text("Media dilewati.\nLangkah 2/3: Kirim Teks Pesan.")
    return WAITING_TEMPLATE_TEXT

async def handle_template_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['template']['text'] = update.message.text_html
    await update.message.reply_text("✅ Teks diterima.\nLangkah 3/3: Kirim Tombol (Format: Teks | URL) atau /skip.")
    return WAITING_TEMPLATE_BUTTONS

async def handle_template_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = update.message.text.split('\n')
    buttons = []
    for line in lines:
        parts = line.split('|')
        if len(parts) == 2:
            buttons.append([{'text': parts[0].strip(), 'url': parts[1].strip()}])
    context.user_data['template']['buttons_json'] = json.dumps(buttons)
    await update.message.reply_text("✅ Tombol diterima. Berikut pratinjaunya:")
    await show_template_preview(update, context)
    return WAITING_TEMPLATE_CONFIRM

async def skip_template_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['template']['buttons_json'] = '[]'
    await update.message.reply_text("Tombol dilewati. Berikut pratinjaunya:")
    await show_template_preview(update, context)
    return WAITING_TEMPLATE_CONFIRM

async def show_template_preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data['template']
    text = data.get('text', ' ')
    buttons_data = json.loads(data.get('buttons_json', '[]'))
    buttons = [[InlineKeyboardButton(b['text'], url=b['url'])] for row in buttons_data for b in row]
    reply_markup = InlineKeyboardMarkup(buttons) if buttons else None
    
    await update.message.reply_text("--- PRATINJAU TEMPLATE ---")
    if data.get('media_type') == 'photo':
        await update.message.reply_photo(photo=data['file_id'], caption=text, reply_markup=reply_markup)
    elif data.get('media_type') == 'video':
        await update.message.reply_video(video=data['file_id'], caption=text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)
    await update.message.reply_text("Ketik /save untuk menyimpan template atau /cancel.")

async def save_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return ConversationHandler.END
    data = context.user_data['template']
    set_config('template_media_type', data.get('media_type') or 'None')
    set_config('template_file_id', data.get('file_id') or 'None')
    set_config('template_text', data.get('text') or ' ')
    set_config('template_buttons_json', data.get('buttons_json') or '[]')
    await update.message.reply_text("💾 *Template broadcast berhasil disimpan!*")
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_set_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Pembuatan template dibatalkan.")
    return ConversationHandler.END

async def broadcast_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    
    media_type = get_config('template_media_type')
    if not media_type:
        await update.message.reply_text("⚠️ Template broadcast belum diatur. Gunakan /settemplate terlebih dahulu.")
        return

    buttons_json = get_config('template_buttons_json')
    buttons_data = json.loads(buttons_json) if buttons_json else []
    buttons = [[InlineKeyboardButton(b['text'], url=b['url'])] for row in buttons_data for b in row]

    template_data = {
        'media_type': media_type if media_type != 'None' else None,
        'file_id': get_config('template_file_id'),
        'text': get_config('template_text'),
        'buttons': buttons if buttons else None
    }
    
    await _execute_broadcast(context, template_data, update.effective_user.id)

async def ganti_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    try:
        channel_id = int(context.args[0])
        set_config('channel_wajib_id', str(channel_id))
        await update.message.reply_html(f"✅ *ID Channel Wajib berhasil diatur ke:* `{channel_id}`")
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Gunakan format: /gantichannel <channel_id>")

async def ganti_grup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    try:
        grup_id = int(context.args[0])
        set_config('grup_utama_id', str(grup_id))
        await update.message.reply_html(f"✅ *ID Grup Utama berhasil diatur ke:* `{grup_id}`")
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Gunakan format: /gantigroup <grup_id>")

async def set_channel_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    try:
        link = context.args[0]
        if not (link.startswith("https://t.me/+") or link.startswith("https://t.me/joinchat/")):
            await update.message.reply_text("⚠️ Link tidak valid. Harap gunakan link undangan channel privat (contoh: https://t.me/+...)")
            return
        set_config('channel_invite_link', link)
        await update.message.reply_html(f"✅ *Link Undangan Channel berhasil diatur ke:* {link}")
    except (IndexError):
        await update.message.reply_text("⚠️ Gunakan format: /setchannellink <link_undangan>")

# --- Fungsi Utama ---
def main():
    init_db()
    application = ApplicationBuilder().token(TOKEN).post_init(post_init).build()

    broadcast_conv = ConversationHandler(
        entry_points=[CommandHandler('broadcast', broadcast_start)],
        states={
            WAITING_MEDIA: [MessageHandler(filters.PHOTO | filters.VIDEO, handle_media), CommandHandler('skip', skip_media)],
            WAITING_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)],
            WAITING_BUTTONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons), CommandHandler('skip', skip_buttons)],
            WAITING_CONFIRMATION: [CommandHandler('sendnow', send_broadcast)],
        },
        fallbacks=[CommandHandler('cancel', cancel_broadcast)],
        conversation_timeout=300
    )

    setwelcome_conv = ConversationHandler(
        entry_points=[CommandHandler('setwelcome', set_welcome_start)],
        states={
            WAITING_WELCOME_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_welcome_text)],
            WAITING_WELCOME_BUTTONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_welcome_buttons), CommandHandler('skip', skip_welcome_buttons)],
            WAITING_WELCOME_CONFIRM: [CommandHandler('save', save_welcome_message)]
        },
        fallbacks=[CommandHandler('cancel', cancel_set_welcome)],
        conversation_timeout=300
    )

    settemplate_conv = ConversationHandler(
        entry_points=[CommandHandler('settemplate', set_template_start)],
        states={
            WAITING_TEMPLATE_MEDIA: [MessageHandler(filters.PHOTO | filters.VIDEO, handle_template_media), CommandHandler('skip', skip_template_media)],
            WAITING_TEMPLATE_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_template_text)],
            WAITING_TEMPLATE_BUTTONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_template_buttons), CommandHandler('skip', skip_template_buttons)],
            WAITING_TEMPLATE_CONFIRM: [CommandHandler('save', save_template)]
        },
        fallbacks=[CommandHandler('cancel', cancel_set_template)],
        conversation_timeout=300
    )

    application.add_handler(broadcast_conv)
    application.add_handler(setwelcome_conv)
    application.add_handler(settemplate_conv)
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CommandHandler("listusers", list_users))
    application.add_handler(CommandHandler("verifikasiulang", reverify_user))
    application.add_handler(CommandHandler("gantichannel", ganti_channel))
    application.add_handler(CommandHandler("setchannellink", set_channel_link))
    application.add_handler(CommandHandler("gantigroup", ganti_grup))
    application.add_handler(CommandHandler("broadcasttemplate", broadcast_template))
    application.add_handler(CommandHandler("addadmin", add_admin_command))
    application.add_handler(CommandHandler("deladmin", del_admin_command))
    application.add_handler(CommandHandler("listadmins", list_admins_command))
    
    application.add_handler(CallbackQueryHandler(verify_member_callback, pattern="^VERIFY_MEMBER$"))
    application.add_handler(CallbackQueryHandler(admin_button_callback, pattern="^admin_"))
    
    application.add_handler(MessageHandler(filters.ChatType.SUPERGROUP & (filters.Entity("url") | filters.Entity("text_link")), anti_link_handler))

    logger.info("Bot siap dijalankan...")
    application.run_polling()

if __name__ == '__main__':
    main()
