import sqlite3
import asyncio
import os
import requests
from flask import Flask, jsonify, request, session, redirect, url_for, flash
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from threading import Thread
from config import BOT_TOKEN, DASHBOARD_PASSWORD, CHANNEL_ID, GROUP_INVITE_LINK, CHANNEL_URL
import datetime
import traceback

from db import init_db

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
from telegram.ext import ChatJoinRequestHandler

from pyrogram import Client, filters
from pyrogram.types import ChatJoinRequest
import config  # config.py should have BOT_TOKEN, API_ID, API_HASH, CHAT_ID, WELCOME_TEXT

from telegram.ext import filters as tg_filters
from pyrogram import filters as pyro_filters
from telegram import InputMediaPhoto, InputMediaVideo, InputMediaAudio
from telegram.request import HTTPXRequest as Request

app = Flask(__name__)
app.secret_key = 'change_this_secret_key'

# Render CORS configuration
CORS(app, origins=[
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://admin-o7ei.onrender.com",
    "https://admin-o7ei.onrender.com/",
    "https://apiserverjoin.onrender.com",
    "https://apiserverjoin.onrender.com",
    "https://apiserverjoin.onrender.com"
], supports_credentials=True)

# Use eventlet for better compatibility
socketio = SocketIO(app, async_mode='eventlet', cors_allowed_origins=[
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://admin-o7ei.onrender.com",
    "https://admin-o7ei.onrender.com/",
    "https://apiserverjoin.onrender.com",
    "https://apiserverjoin.onrender.com",
    "https://apiserverjoin.onrender.com"
])

DB_NAME = 'users.db'

# Ensure DB tables exist
init_db()

# Helper function to detect GIF files
def is_gif_file(file_path, mimetype=None, original_filename=None):
    """Detect if a file is a GIF based on path, mimetype, and original filename"""
    if not file_path:
        return False
    
    # Check original filename first (most reliable for Telegram)
    if original_filename and original_filename.lower().endswith('.gif'):
        return True
    
    # Check mimetype
    if mimetype and 'image/gif' in mimetype.lower():
        return True
    
    # Check file extension
    if file_path.lower().endswith('.gif'):
        return True
    
    # Check if filename contains gif
    if 'gif' in file_path.lower():
        return True
    
    return False

def is_gif_by_header(file_path):
    """Detect GIF by reading the file header bytes"""
    try:
        with open(file_path, 'rb') as f:
            header = f.read(6)
            # GIF files start with "GIF87a" or "GIF89a"
            return header.startswith(b'GIF87a') or header.startswith(b'GIF89a')
    except:
        return False

def is_gif_by_url(url):
    """Download file and check if it's a GIF by examining the header"""
    try:
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            # Read first 6 bytes to check GIF header
            header = response.raw.read(6)
            return header.startswith(b'GIF87a') or header.startswith(b'GIF89a')
    except:
        pass
    return False

# --- Database helpers ---
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

def get_messages_for_user(user_id, limit=100):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT sender, message, timestamp FROM messages WHERE user_id = ? ORDER BY id ASC LIMIT ?', (user_id, limit))
    messages = c.fetchall()
    conn.close()
    return messages

def save_message(user_id, sender, message):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('INSERT INTO messages (user_id, sender, message, timestamp) VALUES (?, ?, ?, ?)',
              (user_id, sender, message, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()

def add_user(user_id, full_name, username, join_date, invite_link, photo_url=None, label=None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO users (user_id, full_name, username, join_date, invite_link, photo_url, label) VALUES (?, ?, ?, ?, ?, ?, ?)', (user_id, full_name, username, join_date, invite_link, photo_url, label))
    conn.commit()
    conn.close()

def get_active_users(minutes=60):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    since = (datetime.datetime.now() - datetime.timedelta(minutes=minutes)).strftime('%Y-%m-%d %H:%M:%S')
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
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM users WHERE join_date LIKE ?', (f'{today}%',))
    count = c.fetchone()[0]
    conn.close()
    return count

def get_user_online_status(user_id, minutes=5):
    """Check if user has been active in the last N minutes"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    since = (datetime.datetime.now() - datetime.timedelta(minutes=minutes)).strftime('%Y-%m-%d %H:%M:%S')
    c.execute('SELECT 1 FROM messages WHERE user_id = ? AND timestamp >= ? LIMIT 1', (user_id, since))
    is_online = c.fetchone() is not None
    conn.close()
    return is_online

@app.route('/user-status/<int:user_id>')
def user_status(user_id):
    """Get user online status and last activity"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Get last message timestamp
    c.execute('SELECT timestamp FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT 1', (user_id,))
    last_message = c.fetchone()
    
    # Check if online (active in last 5 minutes)
    is_online = get_user_online_status(user_id, 5)
    
    # Get user info
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

# --- Flask API Endpoints ---
@app.route('/dashboard-users')
def dashboard_users():
    # Get page and page_size from query params, default page=1, page_size=10
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

    # Add online status for each user
    users_with_status = []
    for u in users:
        is_online = get_user_online_status(u[0], 5)
        users_with_status.append({
                'user_id': u[0],
                'full_name': u[1],
                'username': u[2],
                'join_date': u[3],
            'invite_link': u[4],
            'photo_url': u[5],
            'is_online': is_online,
            'label': u[6]
        })

    return jsonify({
        'users': users_with_status,
        'total': total,
        'page': page,
        'page_size': page_size
    })

@app.route('/dashboard-stats')
def dashboard_stats():
    # Total users in the database
    total_users = get_total_users()
    # Active users: users who sent messages in the last 60 minutes
    active_users = get_active_users()  # last 60 minutes
    # Total messages sent (all time)
    total_messages = get_total_messages()
    # New joins today
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
    # messages is a list of (sender, message, timestamp)
    return jsonify([
        [sender, message, timestamp] for sender, message, timestamp in messages
    ])

@app.route('/get_channel_invite_link', methods=['GET'])
def get_channel_invite_link():
    try:
        # Use static URL from config instead of generating dynamic link
        return jsonify({'invite_link': CHANNEL_URL})
    except Exception as e:
        print(f"Error getting invite link: {e}")
        return jsonify({'error': str(e)}), 500

# --- Telegram Bot Handlers ---
async def user_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        return
    full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
    username = user.username or ''
    join_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # Fetch profile photo URL
    photo_url = None
    try:
        photos = await context.bot.get_user_profile_photos(user.id, limit=1)
        if photos.total_count > 0:
            file = await context.bot.get_file(photos.photos[0][0].file_id)
            photo_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
    except Exception as e:
        print(f"Could not fetch profile photo for user {user.id}: {e}")
    add_user(user.id, full_name, username, join_date, None, photo_url)

    # Handle bulk media: For each message in a media group, this handler is called separately
    if update.message.photo:
        file = await context.bot.get_file(update.message.photo[-1].file_id)
        # Check if file_path already contains the full URL
        if file.file_path.startswith('http'):
            file_url = file.file_path
        else:
            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
        
        # Get original file information - try multiple ways
        original_filename = None
        mime_type = None
        
        # Try to get file_name from the photo object
        try:
            original_filename = getattr(update.message.photo[-1], 'file_name', None)
        except:
            pass
            
        # Try to get mime_type from the photo object
        try:
            mime_type = getattr(update.message.photo[-1], 'mime_type', None)
        except:
            pass
            
        # If we don't have the original info, try to get it from the file object
        if not original_filename:
            try:
                original_filename = getattr(file, 'file_name', None)
            except:
                pass
                
        if not mime_type:
            try:
                mime_type = getattr(file, 'mime_type', None)
            except:
                pass
        
        # Check message caption for GIF hints
        caption = getattr(update.message, 'caption', '')
        if caption and 'gif' in caption.lower():
            print(f"Debug - Found GIF hint in caption: {caption}")
        
        # Check if message has any GIF-specific attributes
        message_type = getattr(update.message, 'content_type', None)
        print(f"Debug - Message content type: {message_type}")
        
        # Check if this is a GIF file using original information
        is_gif = is_gif_file(file.file_path, mimetype=mime_type, original_filename=original_filename)
        
        # If we couldn't detect it by filename/mimetype, try checking the actual file content
        if not is_gif and file_url:
            print(f"Debug - Trying to check file content for GIF...")
            is_gif = is_gif_by_url(file_url)
            print(f"Debug - File content check result: {is_gif}")
        
        # Additional check: if the file path contains 'gif' anywhere, it might be a GIF
        if not is_gif and 'gif' in file.file_path.lower():
            print(f"Debug - Found 'gif' in file path, treating as GIF")
            is_gif = True
        
        print(f"Debug - user image file.file_path: {file.file_path}")
        print(f"Debug - user image constructed URL: {file_url}")
        print(f"Debug - original filename: {original_filename}")
        print(f"Debug - mime type: {mime_type}")
        print(f"Debug - caption: {caption}")
        print(f"Debug - message content type: {message_type}")
        print(f"Debug - is GIF: {is_gif}")
        print(f"Debug - photo object attributes: {dir(update.message.photo[-1])}")
        print(f"Debug - file object attributes: {dir(file)}")
        print(f"Debug - message object attributes: {dir(update.message)}")
        
        # Save with appropriate prefix for GIFs
        if is_gif:
            save_message(user.id, 'user', f"[gif]{file_url}")
            print(f"Debug - Saved as GIF: [gif]{file_url}")
        else:
            save_message(user.id, 'user', f"[image]{file_url}")
            print(f"Debug - Saved as image: [image]{file_url}")
        
        # Real-time notify admin dashboard
        socketio.emit('new_message', {'user_id': user.id, 'full_name': full_name, 'username': username})
    elif update.message.video:
        file = await context.bot.get_file(update.message.video.file_id)
        # Check if file_path already contains the full URL
        if file.file_path.startswith('http'):
            file_url = file.file_path
        else:
            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
        save_message(user.id, 'user', f"[video]{file_url}")
        # Real-time notify admin dashboard
        socketio.emit('new_message', {'user_id': user.id, 'full_name': full_name, 'username': username})
    elif update.message.voice:
        file = await context.bot.get_file(update.message.voice.file_id)
        # Check if file_path already contains the full URL
        if file.file_path.startswith('http'):
            file_url = file.file_path
        else:
            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
        save_message(user.id, 'user', f"[voice]{file_url}")
        # Real-time notify admin dashboard
        socketio.emit('new_message', {'user_id': user.id, 'full_name': full_name, 'username': username})
    elif update.message.audio:
        file = await context.bot.get_file(update.message.audio.file_id)
        # Check if file_path already contains the full URL
        if file.file_path.startswith('http'):
            file_url = file.file_path
        else:
            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
        save_message(user.id, 'user', f"[audio]{file_url}")
        # Real-time notify admin dashboard
        socketio.emit('new_message', {'user_id': user.id, 'full_name': full_name, 'username': username})
    elif update.message.text:
        save_message(user.id, 'user', update.message.text)

        # Real-time notify admin dashboard
        socketio.emit('new_message', {'user_id': user.id, 'full_name': full_name, 'username': username})

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user is None:
        return
    # Check if user is new or old
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT 1 FROM users WHERE user_id = ?', (user.id,))
    exists = c.fetchone()
    conn.close()
    if exists:
        # Old user: just private message
        await update.message.reply_text("👋 Welcome back! You can chat with me here anytime.")
    else:
        # New user: save and send channel join prompt
        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        username = user.username or ''
        join_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # Generate unique invite link for this user
        invite_link = None
        try:
            chat = await context.bot.create_chat_invite_link(chat_id=CHANNEL_ID, member_limit=1, name=f"{full_name} ({user.id})")
            invite_link = chat.invite_link
        except Exception as e:
            print(f"Failed to create unique invite link: {e}")
        if not invite_link:
            await update.message.reply_text("❌ Sorry, could not generate your invite link. Please contact admin.")
            return
        add_user(user.id, full_name, username, join_date, invite_link)
        keyboard = [
            [InlineKeyboardButton('Join Channel', url=invite_link)],
            [InlineKeyboardButton('I have joined', callback_data='joined_channel')]
        ]
        text = (
            "👋 Welcome!\n\n"
            "To access all features, please join our channel first.\n"
            f"{invite_link}\n\n"
            "After joining, click the button below."
        )
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def channel_joined_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()
    # Send professional welcome message
    welcome = (
        "🎉 Thank you for joining our channel!\n\n"
        "You are now a full member. You can chat with me here anytime."
    )
    await context.bot.send_message(chat_id=user.id, text=welcome)
    # Optionally, notify admin (bot owner)
    try:
        # ADMIN_USER_ID is not defined in the original file, so this line is commented out
        # await context.bot.send_message(chat_id=ADMIN_USER_ID, text=f"User {user.full_name} (@{user.username}) [{user.id}] has joined the channel and can now chat.")
        pass # Placeholder for ADMIN_USER_ID
    except Exception:
        pass

async def approve_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.chat_join_request.approve()
        user = update.chat_join_request.from_user
        # Store user info in DB
        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        username = user.username or ''
        join_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        invite_link = update.chat_join_request.invite_link.invite_link if update.chat_join_request.invite_link else None
        add_user(user.id, full_name, username, join_date, invite_link)
        try:
            await context.bot.send_message(user.id, "🎉 Welcome! You are now a member. Feel free to chat with me.")
        except Exception as e:
            print(f"Failed to send welcome message: {e}")
    except Exception as e:
        if "User_already_participant" in str(e):
            print(f"User is already a participant, skipping approval")
        else:
            print(f"Error approving join request: {e}")

# Register handlers for Telegram bot
application = ApplicationBuilder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler('start', start))
application.add_handler(CallbackQueryHandler(channel_joined_callback, pattern='^joined_channel$'))
application.add_handler(MessageHandler(tg_filters.TEXT & ~tg_filters.COMMAND, user_message_handler))
application.add_handler(MessageHandler(tg_filters.PHOTO, user_message_handler))
application.add_handler(MessageHandler(tg_filters.VIDEO, user_message_handler))
application.add_handler(MessageHandler(tg_filters.VOICE, user_message_handler))
application.add_handler(MessageHandler(tg_filters.AUDIO, user_message_handler))
application.add_handler(ChatJoinRequestHandler(approve_join))

# Pyrogram Bot Setup
pyro_app = Client(
    "AutoApproveBot",
    bot_token=config.BOT_TOKEN,
    api_id=config.API_ID,
    api_hash=config.API_HASH
)

CHAT_ID = config.CHAT_ID
WELCOME_TEXT = getattr(config, "WELCOME_TEXT", "🎉 Hi {mention}, you are now a member of {title}!")

@pyro_app.on_chat_join_request(pyro_filters.chat(CHAT_ID))
async def approve_and_dm(client: Client, join_request: ChatJoinRequest):
    user = join_request.from_user
    chat = join_request.chat

    print(f"🔔 Join request received from {user.first_name} ({user.id}) for {chat.title}")
    print(f"🔧 CHAT_ID: {CHAT_ID}, chat.id: {chat.id}")

    try:
        # Approve the join request
        await client.approve_chat_join_request(chat.id, user.id)
        print(f"✅ Approved: {user.first_name} ({user.id}) in {chat.title}")

        # Add user to DB
        from datetime import datetime
        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        username = user.username or ''
        join_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        invite_link = None  # Pyrogram does not provide invite_link in join request
        add_user(user.id, full_name, username, join_date, invite_link)
        print(f"💾 User {user.first_name} ({user.id}) added to database")

        # Send welcome message
        try:
            welcome_message = WELCOME_TEXT.format(mention=user.mention, title=chat.title)
            print(f"📝 Sending welcome message to {user.first_name} ({user.id}): {welcome_message}")
            
            await client.send_message(
                user.id,
                welcome_message
            )
            print(f"✅ DM sent successfully to {user.first_name} ({user.id})")
        except Exception as e:
            print(f"❌ Failed to send DM to {user.first_name} ({user.id}): {e}")
            print(f"🔍 Error type: {type(e).__name__}")
            print(f"🔍 Error details: {str(e)}")
            
            # Try to get more specific error information
            if "Forbidden" in str(e):
                print(f"⚠️ User {user.first_name} ({user.id}) has blocked the bot or doesn't allow DMs")
            elif "User not found" in str(e):
                print(f"⚠️ User {user.first_name} ({user.id}) not found - may have deleted account")
            elif "Chat not found" in str(e):
                print(f"⚠️ Chat not found for user {user.first_name} ({user.id})")
                
    except Exception as e:
        if "User_already_participant" in str(e) or "USER_ALREADY_PARTICIPANT" in str(e):
            print(f"ℹ️ User {user.first_name} ({user.id}) is already a participant in {chat.title}")
        else:
            print(f"❌ Error approving join request for {user.first_name} ({user.id}): {e}")
            print(f"🔍 Error type: {type(e).__name__}")
            print(f"🔍 Full error: {str(e)}")


@app.route('/chat/<int:user_id>', methods=['POST'])
def chat_send(user_id):
    message = request.form.get('message')
    files = request.files.getlist('files')
    sent = False
    response = {'status': 'error', 'message': 'No message or files sent'}

    # Handle text message
    if message:
        save_message(user_id, 'admin', message)
        try:
            # Use direct HTTP request instead of asyncio
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            data = {
                'chat_id': int(user_id),
                'text': message
            }
            response = requests.post(url, data=data)
            if response.status_code == 200:
                sent = True
                response_data = {'status': 'success', 'message': 'Message sent'}
            else:
                print(f"Telegram API error: {response.text}")
                response_data = {'status': 'error', 'message': f'Telegram API error: {response.text}'}
                return jsonify(response_data), 500
        except Exception as e:
            print(f"Telegram send error: {e}")
            response_data = {'status': 'error', 'message': str(e)}
            return jsonify(response_data), 500

    # Handle files
    if files and len(files) > 0:
        media_group = []  # Unified media group for all types
        temp_paths = []
        
        # File size validation (Telegram limits: 50MB for files, 20MB for photos)
        MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
        MAX_PHOTO_SIZE = 20 * 1024 * 1024  # 20MB
        
        for file in files:
            filename = file.filename
            mimetype = file.mimetype
            print('File received:', filename, mimetype)
            
            # Check file size
            file.seek(0, 2)  # Seek to end
            file_size = file.tell()
            file.seek(0)  # Reset to beginning
            
            if mimetype.startswith('image/') and file_size > MAX_PHOTO_SIZE:
                return jsonify({'status': 'error', 'message': f'Image {filename} is too large. Maximum size is 20MB.'}), 400
            elif file_size > MAX_FILE_SIZE:
                return jsonify({'status': 'error', 'message': f'File {filename} is too large. Maximum size is 50MB.'}), 400
            
            temp_path = f'temp_{filename}'
            file.save(temp_path)
            temp_paths.append(temp_path)
            
            # Check if this is a GIF file before processing
            is_gif = is_gif_file(temp_path, mimetype=mimetype, original_filename=filename)
            print(f"Debug - admin upload: filename={filename}, mimetype={mimetype}, is_gif={is_gif}")
            
            # Add to unified media group
            if mimetype.startswith('image/'):
                media_group.append(InputMediaPhoto(open(temp_path, 'rb')))
            elif mimetype.startswith('video/'):
                media_group.append(InputMediaVideo(open(temp_path, 'rb')))
            elif mimetype.startswith('audio/'):
                media_group.append(InputMediaAudio(open(temp_path, 'rb')))
        
        try:
            if len(media_group) > 1:
                print(f'Sending unified media group ({len(media_group)} files)...')
                # For now, just save the message without trying to get file URLs
                for i, media in enumerate(media_group):
                    if isinstance(media, InputMediaPhoto):
                        save_message(user_id, 'admin', f'[image]sent')
                    elif isinstance(media, InputMediaVideo):
                        save_message(user_id, 'admin', f'[video]sent')
                    elif isinstance(media, InputMediaAudio):
                        save_message(user_id, 'admin', f'[audio]sent')
                
                sent = True
            elif len(media_group) == 1:
                # Single file - just save the message
                media = media_group[0]
                if isinstance(media, InputMediaPhoto):
                    save_message(user_id, 'admin', f'[image]sent')
                elif isinstance(media, InputMediaVideo):
                    save_message(user_id, 'admin', f'[video]sent')
                elif isinstance(media, InputMediaAudio):
                    save_message(user_id, 'admin', f'[audio]sent')
                
                sent = True
        except Exception as e:
            print(f"Telegram file send error: {e}")
            traceback.print_exc()
            return jsonify({'status': 'error', 'message': f'Failed to send media: {str(e)}'}), 500
        finally:
            for temp_path in temp_paths:
                try:
                    os.remove(temp_path)
                except Exception as e:
                    print('Error removing temp file:', temp_path, e)

    # Emit socket event and return response
    socketio.emit('new_message', {'user_id': user_id}, room='chat_' + str(user_id))
    socketio.emit('admin_message_sent', {'user_id': user_id}, room='chat_' + str(user_id))
    
    if sent:
        return jsonify({'status': 'success', 'message': 'Message sent successfully'}), 200
    else:
        return jsonify(response), 500

@app.route('/send_one', methods=['POST'])
def send_one():
    user_id = request.form.get('user_id')
    message = request.form.get('message')
    if not user_id or not message:
        return {'status': 'error', 'msg': 'Missing user_id or message'}, 400
    save_message(int(user_id), 'admin', message)
    try:
        # Use direct HTTP request instead of asyncio
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': int(user_id),
            'text': message
        }
        response = requests.post(url, data=data)
        if response.status_code != 200:
            print(f"Telegram API error: {response.text}")
    except Exception as e:
        print(f"Telegram send error: {e}")
    socketio.emit('new_message', {'user_id': int(user_id)}, room='chat_' + str(user_id))
    socketio.emit('admin_message_sent', {'user_id': int(user_id)}, room='chat_' + str(user_id))
    return {'status': 'ok'}

@app.route('/send_all', methods=['POST'])
def send_all():
    message = request.form.get('message')
    if not message:
        return {'status': 'error', 'msg': 'Missing message'}, 400
    users = get_all_users()
    for u in users:
        save_message(u[0], 'admin', message)
        try:
            # Use direct HTTP request instead of asyncio
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            data = {
                'chat_id': int(u[0]),
                'text': message
            }
            response = requests.post(url, data=data)
            if response.status_code != 200:
                print(f"Telegram API error for user {u[0]}: {response.text}")
        except Exception as e:
            print(f"Telegram send error for user {u[0]}: {e}")
        socketio.emit('new_message', {'user_id': u[0]}, room='chat_' + str(u[0]))
        socketio.emit('admin_message_sent', {'user_id': u[0]}, room='chat_' + str(u[0]))
    return {'status': 'ok', 'count': len(users)}

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

if __name__ == '__main__':
    import multiprocessing
    import time
    import os
    
    print("🚀 Starting AutoJOIN Bot Application...")
    print(f"🔧 CHAT_ID: {CHAT_ID}")
    print(f"🔧 BOT_TOKEN: {BOT_TOKEN[:10]}...")
    print(f"🔧 API_ID: {config.API_ID}")
    print(f"🔧 API_HASH: {config.API_HASH[:10]}...")
    
    def run_telegram_bot():
        """Run Telegram bot in a separate process"""
        print("🤖 Telegram bot starting in separate process...")
        import asyncio
        import signal
        
        # Disable signal handlers for this process
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(application.run_polling(drop_pending_updates=True))
        except Exception as e:
            print(f"❌ Telegram bot error: {e}")
    
    def run_pyrogram_bot():
        """Run Pyrogram bot in a separate process"""
        print("🔥 Pyrogram bot starting in separate process...")
        import asyncio
        import signal
        
        # Disable signal handlers for this process
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(pyro_app.run())
        except Exception as e:
            print(f"❌ Pyrogram bot error: {e}")
    
    # Start bots in separate processes
    telegram_process = multiprocessing.Process(target=run_telegram_bot, daemon=True)
    pyrogram_process = multiprocessing.Process(target=run_pyrogram_bot, daemon=True)
    
    telegram_process.start()
    pyrogram_process.start()
    
    # Give the bots time to start
    print("⏳ Waiting for bots to initialize...")
    time.sleep(3)
    
    print("🌐 Starting Flask app...")
    
    # Get port from environment variable (Render sets PORT)
    port = int(os.environ.get('PORT', 8080))
    host = '0.0.0.0'  # Bind to all interfaces for Render
    
    print(f"🚀 Server starting on {host}:{port}")
    
    # Run Flask in the main process
    socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True) 
