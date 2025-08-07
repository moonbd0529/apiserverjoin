import sqlite3
import os
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room
from telegram import Update, Bot, InputMediaPhoto, InputMediaVideo
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, ChatJoinRequestHandler
from datetime import datetime, timedelta
import logging
from db import init_db
import config  # Assumes config.py has BOT_TOKEN, CHANNEL_ID, CHANNEL_URL, WELCOME_TEXT

# Set up logging
logging.basicConfig(level=logging.INFO, filename='app.log', format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))
CORS(app, origins=["https://admin-aa3r.onrender.com", "http://localhost:3000"], supports_credentials=True)
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins=["https://admin-aa3r.onrender.com", "http://localhost:3000"])

DB_NAME = 'users.db'
init_db()  # Ensure database tables exist (including label column)

# --- Database Helpers ---
def add_user(user_id, full_name, username, join_date, invite_link=None, photo_url=None, label=None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO users (user_id, full_name, username, join_date, invite_link, photo_url, label) VALUES (?, ?, ?, ?, ?, ?, ?)',
              (user_id, full_name, username, join_date, invite_link, photo_url, label))
    conn.commit()
    conn.close()

def save_message(user_id, sender, message):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('INSERT INTO messages (user_id, sender, message, timestamp) VALUES (?, ?, ?, ?)',
              (user_id, sender, message, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()

def get_messages_for_user(user_id, limit=100):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT sender, message, timestamp FROM messages WHERE user_id = ? ORDER BY id ASC LIMIT ?', (user_id, limit))
    messages = c.fetchall()
    conn.close()
    return messages

def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT user_id, full_name, username, join_date, invite_link, photo_url, label FROM users')
    users = c.fetchall()
    conn.close()
    return users

def get_total_users():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    total = c.fetchone()[0]
    conn.close()
    return total

def get_active_users(minutes=60):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    since = (datetime.now() - timedelta(minutes=minutes)).strftime('%Y-%m-%d %H:%M:%S')
    c.execute('SELECT COUNT(DISTINCT user_id) FROM messages WHERE timestamp >= ?', (since,))
    count = c.fetchone()[0]
    conn.close()
    return count

def get_total_messages():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM messages')
    count = c.fetchone()[0]
    conn.close()
    return count

def get_new_joins_today():
    today = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users WHERE join_date LIKE ?', (f'{today}%',))
    count = c.fetchone()[0]
    conn.close()
    return count

def get_user_online_status(user_id, minutes=5):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    since = (datetime.now() - timedelta(minutes=minutes)).strftime('%Y-%m-%d %H:%M:%S')
    c.execute('SELECT 1 FROM messages WHERE user_id = ? AND timestamp >= ? LIMIT 1', (user_id, since))
    is_online = c.fetchone() is not None
    conn.close()
    return is_online

# --- Telegram Bot Handlers ---
async def approve_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.chat_join_request.from_user
        await update.chat_join_request.approve()
        logger.info(f"Approved join request for user {user.id}")

        # Store user info
        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        username = user.username or ''
        join_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        invite_link = update.chat_join_request.invite_link.invite_link if update.chat_join_request.invite_link else config.CHANNEL_URL
        photo_url = None
        try:
            photos = await context.bot.get_user_profile_photos(user.id, limit=1)
            if photos.total_count > 0:
                file = await context.bot.get_file(photos.photos[0][0].file_id)
                photo_url = f"https://api.telegram.org/file/bot{context.bot.token}/{file.file_path}"
        except Exception as e:
            logger.error(f"Could not fetch profile photo for user {user.id}: {e}")

        add_user(user.id, full_name, username, join_date, invite_link, photo_url)

        # Send welcome DM
        welcome_message = getattr(config, "WELCOME_TEXT", f"🎉 Welcome, {full_name}! You are now a member of our channel. Feel free to chat with me!")
        try:
            await context.bot.send_message(chat_id=user.id, text=welcome_message)
            logger.info(f"Sent welcome DM to user {user.id}")
        except Exception as e:
            if "Forbidden" in str(e) or "chat not found" in str(e):
                logger.warning(f"Cannot send DM to user {user.id}: User may have blocked the bot or restricted DMs")
                socketio.emit('dm_failed', {'user_id': user.id, 'error': 'User may have blocked the bot or restricted DMs'})
            else:
                logger.error(f"Error sending welcome DM to user {user.id}: {e}")

        # Notify frontend
        socketio.emit('new_user', {'user_id': user.id, 'full_name': full_name, 'username': username, 'photo_url': photo_url})
    except Exception as e:
        if "User_already_participant" in str(e):
            logger.info(f"User {user.id} is already a participant")
        else:
            logger.error(f"Error approving join request for user {user.id}: {e}")

async def user_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        return
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    username = user.username or ''

    # Handle media groups
    if update.message.media_group_id:
        if update.message.photo:
            file = await context.bot.get_file(update.message.photo[-1].file_id)
            file_url = f"https://api.telegram.org/file/bot{context.bot.token}/{file.file_path}"
            is_gif = 'gif' in file.file_path.lower() or (update.message.caption and 'gif' in update.message.caption.lower())
            save_message(user.id, 'user', f"[{'gif' if is_gif else 'image'}]{file_url}")
        elif update.message.video:
            file = await context.bot.get_file(update.message.video.file_id)
            file_url = f"https://api.telegram.org/file/bot{context.bot.token}/{file.file_path}"
            save_message(user.id, 'user', f"[video]{file_url}")
    elif update.message.photo:
        file = await context.bot.get_file(update.message.photo[-1].file_id)
        file_url = f"https://api.telegram.org/file/bot{context.bot.token}/{file.file_path}"
        is_gif = 'gif' in file.file_path.lower() or (update.message.caption and 'gif' in update.message.caption.lower())
        save_message(user.id, 'user', f"[{'gif' if is_gif else 'image'}]{file_url}")
    elif update.message.video:
        file = await context.bot.get_file(update.message.video.file_id)
        file_url = f"https://api.telegram.org/file/bot{context.bot.token}/{file.file_path}"
        save_message(user.id, 'user', f"[video]{file_url}")
    elif update.message.voice:
        file = await context.bot.get_file(update.message.voice.file_id)
        file_url = f"https://api.telegram.org/file/bot{context.bot.token}/{file.file_path}"
        save_message(user.id, 'user', f"[voice]{file_url}")
    elif update.message.audio:
        file = await context.bot.get_file(update.message.audio.file_id)
        file_url = f"https://api.telegram.org/file/bot{context.bot.token}/{file.file_path}"
        save_message(user.id, 'user', f"[audio]{file_url}")
    elif update.message.text:
        save_message(user.id, 'user', update.message.text)

    socketio.emit('new_message', {'user_id': user.id, 'full_name': full_name, 'username': username}, room=f'chat_{user.id}')

# --- Flask API Endpoints ---
@app.route('/dashboard-users')
def dashboard_users():
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 10))
    offset = (page - 1) * page_size
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users')
    total = c.fetchone()[0]
    c.execute('SELECT user_id, full_name, username, join_date, invite_link, photo_url, label FROM users ORDER BY join_date DESC LIMIT ? OFFSET ?', (page_size, offset))
    users = c.fetchall()
    conn.close()
    users_with_status = [
        {
            'user_id': u[0], 'full_name': u[1], 'username': u[2], 'join_date': u[3],
            'invite_link': u[4], 'photo_url': u[5], 'label': u[6],
            'is_online': get_user_online_status(u[0], 5)
        } for u in users
    ]
    return jsonify({
        'users': users_with_status,
        'total': total,
        'page': page,
        'page_size': page_size
    })

@app.route('/dashboard-stats')
def dashboard_stats():
    total_users = get_total_users()
    active_users = get_active_users()
    total_messages = get_total_messages()
    new_joins_today = get_new_joins_today()
    return jsonify({
        'total_users': total_users,
        'active_users': active_users,
        'total_messages': total_messages,
        'new_joins_today': new_joins_today
    })

@app.route('/chat/<int:user_id>/messages')
def chat_messages(user_id):
    messages = get_messages_for_user(user_id)
    return jsonify([[sender, message, timestamp] for sender, message, timestamp in messages])

@app.route('/get_channel_invite_link', methods=['GET'])
def get_channel_invite_link():
    try:
        return jsonify({'invite_link': config.CHANNEL_URL})
    except Exception as e:
        logger.error(f"Error getting invite link: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/user-status/<int:user_id>')
def user_status(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT timestamp FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT 1', (user_id,))
    last_message = c.fetchone()
    is_online = get_user_online_status(user_id, 5)
    c.execute('SELECT full_name, username, photo_url FROM users WHERE user_id = ?', (user_id,))
    user_info = c.fetchone()
    conn.close()
    return jsonify({
        'user_id': user_id,
        'full_name': user_info[0] if user_info else '',
        'username': user_info[1] if user_info else '',
        'photo_url': user_info[2] if user_info else None,
        'is_online': is_online,
        'last_activity': last_message[0] if last_message else None
    })

@app.route('/chat/<int:user_id>', methods=['POST'])
async def chat_send(user_id):
    message = request.form.get('message')
    files = request.files.getlist('files')
    sent = False
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_PHOTO_SIZE = 20 * 1024 * 1024  # 20MB
    bot = Bot(token=config.BOT_TOKEN)

    # Handle text message
    if message:
        save_message(user_id, 'admin', message)
        try:
            await bot.send_message(chat_id=user_id, text=message)
            sent = True
        except Exception as e:
            logger.error(f"Error sending message to {user_id}: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

    # Handle media (single or group)
    if files:
        temp_paths = []
        media_group = []
        for file in files:
            file.seek(0, 2)
            file_size = file.tell()
            file.seek(0)
            if file.mimetype.startswith('image/') and file_size > MAX_PHOTO_SIZE:
                return jsonify({'status': 'error', 'message': f'Image {file.filename} is too large'}), 400
            if file_size > MAX_FILE_SIZE:
                return jsonify({'status': 'error', 'message': f'File {file.filename} is too large'}), 400

            temp_path = f'temp_{file.filename}'
            file.save(temp_path)
            temp_paths.append(temp_path)
            is_gif = 'gif' in file.filename.lower() or file.mimetype == 'image/gif'
            is_voice = file.mimetype == 'audio/mp4' or file.filename.lower().endswith('.m4a')

            try:
                if is_voice:
                    await bot.send_voice(chat_id=user_id, voice=open(temp_path, 'rb'))
                    save_message(user_id, 'admin', '[voice]sent')
                    sent = True
                elif file.mimetype.startswith('image/'):
                    media_group.append(InputMediaPhoto(media=open(temp_path, 'rb')))
                    save_message(user_id, 'admin', f"[{'gif' if is_gif else 'image'}]sent")
                elif file.mimetype.startswith('video/'):
                    media_group.append(InputMediaVideo(media=open(temp_path, 'rb')))
                    save_message(user_id, 'admin', '[video]sent')
                elif file.mimetype.startswith('audio/') and not is_voice:
                    await bot.send_audio(chat_id=user_id, audio=open(temp_path, 'rb'))
                    save_message(user_id, 'admin', '[audio]sent')
                    sent = True
            except Exception as e:
                logger.error(f"Error processing file {file.filename} for {user_id}: {e}")
                return jsonify({'status': 'error', 'message': str(e)}), 500

        # Send media group if multiple images/videos
        if media_group:
            try:
                await bot.send_media_group(chat_id=user_id, media=media_group)
                sent = True
            except Exception as e:
                logger.error(f"Error sending media group to {user_id}: {e}")
                return jsonify({'status': 'error', 'message': str(e)}), 500

        # Clean up temporary files
        for temp_path in temp_paths:
            try:
                os.remove(temp_path)
            except Exception as e:
                logger.error(f"Error removing temp file {temp_path}: {e}")

    if sent:
        socketio.emit('new_message', {'user_id': user_id}, room=f'chat_{user_id}')
        socketio.emit('admin_message_sent', {'user_id': user_id}, room=f'chat_{user_id}')
        return jsonify({'status': 'success', 'message': 'Message sent'}), 200
    return jsonify({'status': 'error', 'message': 'No message or files sent'}), 400

@app.route('/send_one', methods=['POST'])
def send_one():
    user_id = request.form.get('user_id')
    message = request.form.get('message')
    if not user_id or not message:
        return jsonify({'status': 'error', 'msg': 'Missing user_id or message'}), 400
    save_message(int(user_id), 'admin', message)
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage",
            data={'chat_id': int(user_id), 'text': message}
        )
        if response.status_code == 200:
            socketio.emit('new_message', {'user_id': int(user_id)}, room=f'chat_{user_id}')
            socketio.emit('admin_message_sent', {'user_id': int(user_id)}, room=f'chat_{user_id}')
            return jsonify({'status': 'ok'})
        else:
            logger.error(f"Telegram API error: {response.text}")
            return jsonify({'status': 'error', 'msg': 'Telegram API error'}), 500
    except Exception as e:
        logger.error(f"Telegram send error for user {user_id}: {e}")
        return jsonify({'status': 'error', 'msg': str(e)}), 500

@app.route('/send_all', methods=['POST'])
def send_all():
    message = request.form.get('message')
    if not message:
        return jsonify({'status': 'error', 'msg': 'Missing message'}), 400
    users = get_all_users()
    for u in users:
        save_message(u[0], 'admin', message)
        try:
            response = requests.post(
                f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage",
                data={'chat_id': u[0], 'text': message}
            )
            if response.status_code != 200:
                logger.error(f"Telegram API error for user {u[0]}: {response.text}")
            socketio.emit('new_message', {'user_id': u[0]}, room=f'chat_{u[0]}')
            socketio.emit('admin_message_sent', {'user_id': u[0]}, room=f'chat_{u[0]}')
        except Exception as e:
            logger.error(f"Telegram send error for user {u[0]}: {e}")
    return jsonify({'status': 'ok', 'count': len(users)})

@app.route('/user/<int:user_id>/label', methods=['POST'])
def set_user_label(user_id):
    label = request.json.get('label')
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('UPDATE users SET label = ? WHERE user_id = ?', (label, user_id))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok', 'user_id': user_id, 'label': label})

@socketio.on('join')
def on_join(data):
    room = data.get('room')
    join_room(room)

# --- Run Application ---
if __name__ == '__main__':
    import multiprocessing
    import time

    logger.info("Starting AutoJOIN Bot Application...")
    logger.info(f"CHAT_ID: {config.CHANNEL_ID}, BOT_TOKEN: {config.BOT_TOKEN[:10]}...")

    def run_telegram_bot():
        logger.info("Starting Telegram bot...")
        application = ApplicationBuilder().token(config.BOT_TOKEN).build()
        application.add_handler(ChatJoinRequestHandler(approve_join))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, user_message_handler))
        application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, user_message_handler))
        application.add_handler(MessageHandler(filters.VOICE, user_message_handler))
        application.add_handler(MessageHandler(filters.AUDIO, user_message_handler))
        application.run_polling(drop_pending_updates=True)

    telegram_process = multiprocessing.Process(target=run_telegram_bot, daemon=True)
    telegram_process.start()
    time.sleep(3)
    logger.info("Starting Flask app...")
    socketio.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=False)
