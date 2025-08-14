import sqlite3
import asyncio
import os
import requests
import logging
from flask import Flask, jsonify, request, session, redirect, url_for, flash
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from threading import Thread
from config import BOT_TOKEN, DASHBOARD_PASSWORD, CHANNEL_ID, GROUP_INVITE_LINK, CHANNEL_URL, RECEPTIONIST_ID, ADMIN_USER_ID
import datetime
import traceback
import signal
import functools

from db import init_db

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
from telegram.ext import ChatJoinRequestHandler

from pyrogram import Client, filters
from pyrogram.types import ChatJoinRequest
import config  # config.py should have BOT_TOKEN, API_ID, API_HASH, CHAT_ID, WELCOME_MESSAGE

from telegram.ext import filters as tg_filters
from pyrogram import filters as pyro_filters
from telegram import InputMediaPhoto, InputMediaVideo, InputMediaAudio
from telegram.request import HTTPXRequest as Request
import json

# Set up logging
logging.basicConfig(level=logging.INFO, filename='app.log', format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def timeout_handler(signum, frame):
    raise TimeoutError("Operation timed out")

def timeout(seconds):
    """Decorator to add timeout to functions"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Set up signal handler for timeout
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
        return wrapper
    return decorator

app = Flask(__name__)
app.secret_key = 'change_this_secret_key'

# Flask timeout configuration
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['PERMANENT_SESSION_LIFETIME'] = 300  # 5 minutes
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

# Render CORS configuration
CORS(app, origins=[
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://192.168.1.3:3000",  # Local network IP
    "http://192.168.0.1:3000",  # Common local network
    "http://192.168.1.1:3000",  # Common local network
    "http://192.168.0.3:3000",  # Common local network
    "http://192.168.1.2:3000",  # Common local network
    "http://10.0.0.1:3000",     # Common local network
    "http://10.0.0.2:3000",     # Common local network
    "https://admin-o7ei.onrender.com",
    "https://admin-o7ei.onrender.com/",
    "https://admin-aa3r.onrender.com",  # Previous Render frontend
    "https://admin-aa3r.onrender.com/", # Previous Render frontend
    "https://admin-8f9s.onrender.com",  # Current Render frontend
    "https://admin-8f9s.onrender.com/", # Current Render frontend
    "https://apiserverjoin.onrender.com",
    "https://apiserverjoin.onrender.com",
    "https://apiserverjoin.onrender.com",
    "*"  # Allow all origins as fallback
], supports_credentials=True)

# Use threading for better compatibility with Gunicorn
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins=[
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://192.168.1.3:3000",  # Local network IP
    "http://192.168.0.1:3000",  # Common local network
    "http://192.168.1.1:3000",  # Common local network
    "http://192.168.0.3:3000",  # Common local network
    "http://192.168.1.2:3000",  # Common local network
    "http://10.0.0.1:3000",     # Common local network
    "http://10.0.0.2:3000",     # Common local network
    "https://admin-o7ei.onrender.com",
    "https://admin-o7ei.onrender.com/",
    "https://admin-aa3r.onrender.com",  # Previous Render frontend
    "https://admin-aa3r.onrender.com/", # Previous Render frontend
    "https://admin-8f9s.onrender.com",  # Current Render frontend
    "https://admin-8f9s.onrender.com/", # Current Render frontend
    "https://apiserverjoin.onrender.com",
    "https://apiserverjoin.onrender.com",
    "https://apiserverjoin.onrender.com",
    "*"  # Allow all origins as fallback
])

DB_NAME = 'users.db'

# Ensure DB tables exist
init_db()

# Database migration function
def migrate_database():
    """Migrate existing database to include new tracking columns"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    try:
        # Check if referred_by column exists
        c.execute('SELECT referred_by FROM users LIMIT 1')
        print("✅ referred_by column exists")
    except sqlite3.OperationalError:
        print("🔄 Adding referred_by column...")
        c.execute('ALTER TABLE users ADD COLUMN referred_by INTEGER')
        print("✅ referred_by column added")
    
    try:
        # Check if referral_count column exists
        c.execute('SELECT referral_count FROM users LIMIT 1')
        print("✅ referral_count column exists")
    except sqlite3.OperationalError:
        print("🔄 Adding referral_count column...")
        c.execute('ALTER TABLE users ADD COLUMN referral_count INTEGER DEFAULT 0')
        print("✅ referral_count column added")
    
    try:
        # Check if created_at column exists
        c.execute('SELECT created_at FROM users LIMIT 1')
        print("✅ created_at column exists")
    except sqlite3.OperationalError:
        print("🔄 Adding created_at column...")
        # Use a simple approach without default value to avoid SQLite limitation
        c.execute('ALTER TABLE users ADD COLUMN created_at TEXT')
        # Update existing rows with current timestamp
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute('UPDATE users SET created_at = ? WHERE created_at IS NULL', (current_time,))
        print("✅ created_at column added")
    
    conn.commit()
    conn.close()
    print("✅ Database migration completed")

# Run migration
migrate_database()

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

def generate_unique_channel_link(user_id, user_name=None):
    """Generate a unique channel link for each user with tracking parameters"""
    base_url = CHANNEL_URL.rstrip('/')
    
    # Create unique parameters for each user
    timestamp = int(datetime.datetime.now().timestamp())
    user_hash = hash(f"{user_id}_{timestamp}") % 1000000  # Create a hash for uniqueness
    
    # Generate unique tracking parameters
    tracking_params = {
        'ref': user_id,  # Referrer ID
        'uid': user_hash,  # Unique user hash
        't': timestamp,  # Timestamp
        'src': 'bot'  # Source
    }
    
    # Build the URL with parameters
    param_strings = []
    for key, value in tracking_params.items():
        param_strings.append(f"{key}={value}")
    
    unique_link = f"{base_url}?{'&'.join(param_strings)}"
    
    print(f"🔗 Generated unique link for user {user_id}: {unique_link}")
    return unique_link

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

def add_user(user_id, full_name, username, join_date, invite_link=None, photo_url=None, label=None, referred_by=None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Create table with tracking support if it doesn't exist
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER PRIMARY KEY, 
                  full_name TEXT, 
                  username TEXT, 
                  join_date TEXT, 
                  invite_link TEXT, 
                  photo_url TEXT, 
                  label TEXT,
                  referred_by INTEGER,
                  referral_count INTEGER DEFAULT 0,
                  created_at TEXT)''')
    
    # Check if referred_by column exists, if not add it
    try:
        c.execute('SELECT referred_by FROM users LIMIT 1')
    except sqlite3.OperationalError:
        # Column doesn't exist, add it
        print("Adding referred_by column to users table...")
        c.execute('ALTER TABLE users ADD COLUMN referred_by INTEGER')
    
    # Check if referral_count column exists, if not add it
    try:
        c.execute('SELECT referral_count FROM users LIMIT 1')
    except sqlite3.OperationalError:
        # Column doesn't exist, add it
        print("Adding referral_count column to users table...")
        c.execute('ALTER TABLE users ADD COLUMN referral_count INTEGER DEFAULT 0')
    
    # Check if created_at column exists, if not add it
    try:
        c.execute('SELECT created_at FROM users LIMIT 1')
    except sqlite3.OperationalError:
        # Column doesn't exist, add it
        print("Adding created_at column to users table...")
        c.execute('ALTER TABLE users ADD COLUMN created_at TEXT')
    
    # Set current timestamp for new users
    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    c.execute('INSERT OR IGNORE INTO users (user_id, full_name, username, join_date, invite_link, photo_url, label, referred_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
              (user_id, full_name, username, join_date, invite_link, photo_url, label, referred_by, current_time))
    
    # If this user was referred by someone, update the referrer's count
    if referred_by:
        c.execute('UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?', (referred_by,))
    
    conn.commit()
    conn.close()

def track_referral(user_id, referrer_id):
    """Track when a user joins through a referral link"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Update the user's referred_by field
    c.execute('UPDATE users SET referred_by = ? WHERE user_id = ?', (referrer_id, user_id))
    
    # Increment referrer's referral count
    c.execute('UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?', (referrer_id,))
    
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
    c.execute('SELECT user_id, full_name, username, join_date, invite_link, photo_url, label, referral_count, referred_by FROM users ORDER BY join_date DESC LIMIT ? OFFSET ?', (page_size, offset))
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
                'label': u[6],
                'referral_count': u[7] or 0,
                'referred_by': u[8]
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
        # Generate a personal bot link for the admin
        personal_link = generate_personal_bot_link(ADMIN_USER_ID, "Admin")
        return jsonify({'invite_link': personal_link})
    except Exception as e:
        print(f"Error getting invite link: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/get_user_link/<int:user_id>', methods=['GET'])
def get_user_unique_link(user_id):
    """Get unique channel link for a specific user"""
    try:
        # Check if user exists in database
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('SELECT invite_link FROM users WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        conn.close()
        
        if result and result[0]:
            # Return existing link from database
            return jsonify({
                'user_id': user_id,
                'invite_link': result[0],
                'source': 'database'
            })
        else:
            # Generate new unique link for user
            unique_link = generate_unique_channel_link(user_id)
            return jsonify({
                'user_id': user_id,
                'invite_link': unique_link,
                'source': 'generated'
            })
            
    except Exception as e:
        print(f"Error getting user link: {e}")
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

    # Handle media groups (multiple images/videos sent together)
    if update.message.media_group_id:
        # This is part of a media group
        media_group_id = update.message.media_group_id
        
        # Store media group info for processing
        if not hasattr(context, 'media_groups'):
            context.media_groups = {}
        
        if media_group_id not in context.media_groups:
            context.media_groups[media_group_id] = {
                'items': [],
                'processed': False
            }
        
        # Add this item to the media group
        if update.message.photo:
            file = await context.bot.get_file(update.message.photo[-1].file_id)
            if file.file_path.startswith('http'):
                file_url = file.file_path
            else:
                file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
            
            # Check if it's a GIF
            is_gif = is_gif_file(file.file_path)
            
            context.media_groups[media_group_id]['items'].append({
                'type': 'gif' if is_gif else 'image',
                'file_url': file_url,
                'caption': update.message.caption
            })
            
        elif update.message.video:
            file = await context.bot.get_file(update.message.video.file_id)
            if file.file_path.startswith('http'):
                file_url = file.file_path
            else:
                file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
            
            context.media_groups[media_group_id]['items'].append({
                'type': 'video',
                'file_url': file_url,
                'caption': update.message.caption
            })
        
        # Process the media group after a short delay to collect all items
        await asyncio.sleep(0.5)
        
        if not context.media_groups[media_group_id]['processed']:
            context.media_groups[media_group_id]['processed'] = True
            
            # Create a group media message with all items
            group_items = context.media_groups[media_group_id]['items']
            if len(group_items) > 1:
                # Save as group media message
                group_media_data = {
                    'type': 'group_media',
                    'items': group_items,
                    'count': len(group_items)
                }
                save_message(user.id, 'user', f"[group_media]{json.dumps(group_media_data)}")
            else:
                # Save as single media message
                item = group_items[0]
                save_message(user.id, 'user', f"[{item['type']}]{item['file_url']}")
            
            # Real-time notify admin dashboard
            socketio.emit('new_message', {'user_id': user.id, 'full_name': full_name, 'username': username})
        
        return

    # Handle bulk media: For each message in a media group, this handler is called separately
    if update.message.photo:
        file = await context.bot.get_file(update.message.photo[-1].file_id)
        # Check if file_path already contains the full URL
        if file.file_path.startswith('http'):
            file_url = file.file_path
        else:
            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
        
        # File size validation for user uploads
        try:
            file_info = await context.bot.get_file(file.file_id)
            if hasattr(file_info, 'file_size'):
                file_size = file_info.file_size
                MAX_PHOTO_SIZE = 20 * 1024 * 1024  # 20MB
                if file_size > MAX_PHOTO_SIZE:
                    await update.message.reply_text("❌ Image is too large. Maximum size is 20MB.")
                    return
        except Exception as e:
            print(f"Could not check file size: {e}")
        
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
        
        # File size validation for user uploads
        try:
            file_info = await context.bot.get_file(file.file_id)
            if hasattr(file_info, 'file_size'):
                file_size = file_info.file_size
                MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
                if file_size > MAX_FILE_SIZE:
                    await update.message.reply_text("❌ Video is too large. Maximum size is 50MB.")
                    return
        except Exception as e:
            print(f"Could not check file size: {e}")
        
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
    elif update.message.document:
        file = await context.bot.get_file(update.message.document.file_id)
        # Check if file_path already contains the full URL
        if file.file_path.startswith('http'):
            file_url = file.file_path
        else:
            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
        
        # File size validation for user uploads
        try:
            file_info = await context.bot.get_file(file.file_id)
            if hasattr(file_info, 'file_size'):
                file_size = file_info.file_size
                MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
                if file_size > MAX_FILE_SIZE:
                    await update.message.reply_text("❌ File is too large. Maximum size is 50MB.")
                    return
        except Exception as e:
            print(f"Could not check file size: {e}")
        
        save_message(user.id, 'user', f"[document]{file_url}")
        # Real-time notify admin dashboard
        socketio.emit('new_message', {'user_id': user.id, 'full_name': full_name, 'username': username})
    elif update.message.text:
        save_message(user.id, 'user', update.message.text)

        # Real-time notify admin dashboard
        socketio.emit('new_message', {'user_id': user.id, 'full_name': full_name, 'username': username})

def generate_personal_bot_link(user_id, user_name=None):
    """Generate a personal bot chat link that goes directly to the receptionist"""
    bot_username = None
    
    try:
        # Get bot info to get username
        response = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe", timeout=10)
        if response.status_code == 200:
            bot_data = response.json()
            if bot_data.get('ok'):
                bot_username = bot_data['result'].get('username')
    except Exception as e:
        print(f"❌ Could not get bot username: {e}")
    
    if bot_username:
        # Create personal bot chat link with start parameter
        personal_link = f"https://t.me/{bot_username}?start=chat_{user_id}"
        print(f"🔗 Generated personal bot link for user {user_id}: {personal_link}")
        return personal_link
    else:
        # Fallback: create a deep link to the bot
        personal_link = f"https://t.me/{BOT_TOKEN.split(':')[0]}?start=chat_{user_id}"
        print(f"🔗 Generated fallback personal bot link for user {user_id}: {personal_link}")
        return personal_link

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        if user is None:
            print("❌ No user found in update")
            return
        
        print(f"🔔 /start command received from {user.first_name} ({user.id})")
        
        # Check if this is a personal chat start
        if context.args and context.args[0].startswith('chat_'):
            # This is someone coming through a personal bot link
            referrer_id = context.args[0].replace('chat_', '')
            try:
                referrer_id = int(referrer_id)
                print(f"🎯 User {user.id} came through personal bot link from user {referrer_id}")
                
                # Send welcome message for personal chat
                welcome_text = (
                    f"👋 Welcome to MEXQuick Community!\n\n"
                    "You're now connected to our personal support chat.\n\n"
                    "💡 <b>How we can help you:</b>\n"
                    "• Get personalized support\n"
                    "• Learn about earning opportunities\n"
                    "• Join our community\n"
                    "• Get your personal tracking link\n\n"
                    "🚀 <b>Start by telling us:</b>\n"
                    "• What brings you here?\n"
                    "• Are you interested in earning?\n"
                    "• Do you have any questions?\n\n"
                    "I'm here to help you succeed! 💰"
                )
                
                await update.message.reply_text(welcome_text, parse_mode='HTML')
                
                # Notify the referrer (you) that someone joined
                try:
                    notification_text = (
                        f"🎉 New customer joined through your personal bot link!\n\n"
                        f"👤 <b>Customer:</b> {user.first_name} {user.last_name or ''}\n"
                        f"🆔 <b>User ID:</b> {user.id}\n"
                        f"👤 <b>Username:</b> @{user.username or 'No username'}\n\n"
                        f"💬 <b>Start chatting with them!</b>\n"
                        f"They're waiting for your response."
                    )
                    
                    await context.bot.send_message(
                        chat_id=RECEPTIONIST_ID,
                        text=notification_text,
                        parse_mode='HTML'
                    )
                    print(f"✅ Notified receptionist {RECEPTIONIST_ID} about new customer {user.id}")
                    
                except Exception as e:
                    print(f"❌ Could not notify receptionist: {e}")
                
                # Save user for tracking
                full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
                username = user.username or ''
                join_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                personal_link = generate_personal_bot_link(referrer_id, full_name)
                
                add_user(user.id, full_name, username, join_date, personal_link, referred_by=referrer_id)
                print(f"💾 Personal chat user {user.id} saved to database")
                
                return
                
            except ValueError:
                print(f"⚠️ Invalid referrer ID in personal chat start: {context.args[0]}")
        
        # Regular /start command (existing logic)
        # Check if user is new or old
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('SELECT 1 FROM users WHERE user_id = ?', (user.id,))
        exists = c.fetchone()
        
        if exists:
            # Old user: send their existing tracking link
            c.execute('SELECT invite_link FROM users WHERE user_id = ?', (user.id,))
            existing_link = c.fetchone()
            if existing_link and existing_link[0]:
                # Generate personal bot link instead of channel link
                personal_link = generate_personal_bot_link(user.id, user.first_name)
                welcome_text = config.WELCOME_MESSAGE.replace('{TRACKING_LINK}', personal_link)
                print(f"📝 Sending personal bot link to user {user.id}")
                await update.message.reply_text(welcome_text, parse_mode='HTML')
            else:
                welcome_text = config.WELCOME_MESSAGE.replace('{TRACKING_LINK}', 'No tracking link available')
                await update.message.reply_text(welcome_text, parse_mode='HTML')
        else:
            # New user: generate personal bot link and save
            full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
            username = user.username or ''
            join_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"🆕 New user {user.id}: {full_name} (@{username})")
            
            # Generate personal bot link instead of channel link
            personal_link = generate_personal_bot_link(user.id, full_name)
            print(f"🔗 Generated personal bot link: {personal_link}")
            
            # Save user with personal bot link
            add_user(user.id, full_name, username, join_date, personal_link)
            print(f"💾 User {user.id} saved to database")
            
            # Send welcome message with personal bot link
            welcome_text = config.WELCOME_MESSAGE.replace('{TRACKING_LINK}', personal_link)
            
            # Send ONE message without any buttons
            print(f"📝 Sending welcome message to user {user.id}")
            await update.message.reply_text(
                welcome_text,
                parse_mode='HTML'
            )
            print(f"✅ Welcome message sent to user {user.id}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error in /start command: {e}")
        print(f"🔍 Error type: {type(e).__name__}")
        print(f"🔍 Full error: {str(e)}")
        
        # Send error message to user
        try:
            await update.message.reply_text(
                "❌ Sorry, there was an error processing your request. Please try again later."
            )
        except:
            pass

async def approve_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.chat_join_request.from_user
        chat = update.chat_join_request.chat
        
        print(f"🔔 Telegram bot: Join request received from {user.first_name} ({user.id}) for {chat.title}")
        print(f"🔧 CHAT_ID: {CHAT_ID}, chat.id: {chat.id}")
        print(f"🔧 User details: {user.first_name} {user.last_name}, @{user.username}")
        
        await update.chat_join_request.approve()
        logger.info(f"✅ Telegram bot: Approved join request for user {user.id}")

        # Store user info
        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        username = user.username or ''
        join_date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Get the invite link that was used for joining
        invite_link = None
        referred_by = None
        
        # Check if this user came through a tracking link
        if update.chat_join_request.invite_link:
            invite_link = update.chat_join_request.invite_link.invite_link
            print(f"🔗 Telegram bot: Invite link used: {invite_link}")
            # Check if the invite link contains tracking parameter
            if invite_link and 'ref=' in invite_link:
                try:
                    # Extract referrer ID from the link
                    ref_param = invite_link.split('ref=')[1].split('&')[0]
                    referred_by = int(ref_param)
                    print(f"🎯 Telegram bot: User {user.id} was referred by user {referred_by}")
                except (ValueError, IndexError):
                    print(f"⚠️ Telegram bot: Could not parse referral ID from link: {invite_link}")
        else:
            # Generate a unique channel link for this user
            invite_link = generate_unique_channel_link(user.id, full_name)
            print(f"🔗 Telegram bot: Generated unique channel link: {invite_link}")
        
        photo_url = None
        try:
            photos = await context.bot.get_user_profile_photos(user.id, limit=1)
            if photos.total_count > 0:
                file = await context.bot.get_file(photos.photos[0][0].file_id)
                photo_url = f"https://api.telegram.org/file/bot{context.bot.token}/{file.file_path}"
        except Exception as e:
            logger.error(f"Could not fetch profile photo for user {user.id}: {e}")

        # Add user with the actual invite link they used
        add_user(user.id, full_name, username, join_date, invite_link, photo_url, referred_by=referred_by)
        print(f"💾 Telegram bot: User {user.first_name} ({user.id}) added to database with invite link: {invite_link}")

        # Send real-time notification to frontend about new user
        socketio.emit('new_user_joined', {
            'user_id': user.id,
            'full_name': full_name,
            'username': username,
            'join_date': join_date,
            'invite_link': invite_link,
            'photo_url': photo_url,
            'referred_by': referred_by,
            'is_online': True
        })
        print(f"📡 Telegram bot: Sent real-time notification for new user {user.id}")

        # Send welcome DM
        if referred_by:
            # Custom welcome for referred users
            welcome_message = config.WELCOME_MESSAGE
        else:
            welcome_message = config.WELCOME_MESSAGE
        
        try:
            print(f"📝 Telegram bot: Sending welcome message to {user.first_name} ({user.id})")
            print(f"📝 Message: {welcome_message}")
            
            await context.bot.send_message(chat_id=user.id, text=welcome_message)
            logger.info(f"✅ Telegram bot: Sent welcome DM to user {user.id}")
            
            # If this was a referral, notify the referrer
            if referred_by:
                try:
                    referrer_message = (
                        f"🎉 Great news!\n\n"
                        f"Someone joined through your tracking link!\n"
                        f"👤 **New Member:** {full_name}\n"
                        f"🆔 **User ID:** {user.id}\n\n"
                        f"Keep sharing your link to grow your network! 🚀"
                    )
                    await context.bot.send_message(chat_id=referred_by, text=referrer_message)
                    print(f"✅ Telegram bot: Notified referrer {referred_by} about new referral {user.id}")
                except Exception as e:
                    print(f"❌ Telegram bot: Could not notify referrer {referred_by}: {e}")
                    
        except Exception as e:
            print(f"❌ Telegram bot: Failed to send DM to {user.first_name} ({user.id}): {e}")
            print(f"🔍 Error type: {type(e).__name__}")
            print(f"🔍 Error details: {str(e)}")
            
            if "Forbidden" in str(e) or "chat not found" in str(e):
                logger.warning(f"Telegram bot: Cannot send DM to user {user.id}: User may have blocked the bot or restricted DMs")
                socketio.emit('dm_failed', {'user_id': user.id, 'error': 'User may have blocked the bot or restricted DMs'})
                
                # Try to send a message in the channel instead
                try:
                    channel_message = config.WELCOME_MESSAGE
                    await context.bot.send_message(chat_id=CHAT_ID, text=channel_message)
                    print(f"✅ Sent welcome message to channel for user {user.id}")
                except Exception as channel_error:
                    print(f"❌ Could not send channel message: {channel_error}")
                    
            elif "USER_DEACTIVATED" in str(e):
                print(f"⚠️ Telegram bot: User {user.first_name} ({user.id}) has deactivated their account")
            elif "USER_IS_BLOCKED" in str(e):
                print(f"⚠️ Telegram bot: User {user.first_name} ({user.id}) has blocked the bot")
            else:
                logger.error(f"Telegram bot: Error sending welcome DM to user {user.id}: {e}")
                
    except Exception as e:
        if "User_already_participant" in str(e):
            logger.info(f"Telegram bot: User {user.id} is already a participant")
        elif "CHAT_NOT_FOUND" in str(e):
            print(f"❌ Telegram bot: Chat not found: {chat.title} (ID: {chat.id})")
        elif "BOT_NOT_MEMBER" in str(e):
            print(f"❌ Telegram bot: Bot is not a member of {chat.title} (ID: {chat.id})")
        elif "NOT_MEMBER" in str(e):
            print(f"❌ Telegram bot: Bot is not a member of {chat.title} (ID: {chat.id})")
        else:
            logger.error(f"Telegram bot: Error approving join request for user {user.id}: {e}")

# Register handlers for Telegram bot
application = ApplicationBuilder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler('start', start))
application.add_handler(MessageHandler(tg_filters.TEXT & ~tg_filters.COMMAND, user_message_handler))
application.add_handler(MessageHandler(tg_filters.PHOTO, user_message_handler))
application.add_handler(MessageHandler(tg_filters.VIDEO, user_message_handler))
application.add_handler(MessageHandler(tg_filters.VOICE, user_message_handler))
application.add_handler(MessageHandler(tg_filters.AUDIO, user_message_handler))
application.add_handler(MessageHandler(tg_filters.Document.ALL, user_message_handler))
application.add_handler(ChatJoinRequestHandler(approve_join))

# Pyrogram Bot Setup
pyro_app = Client(
    "AutoApproveBot",
    bot_token=config.BOT_TOKEN,
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    in_memory=True  # Add this to prevent session file issues
)

CHAT_ID = config.CHAT_ID
WELCOME_TEXT = config.WELCOME_MESSAGE

# Test Pyrogram connection
async def test_pyrogram_connection():
    try:
        await pyro_app.start()
        me = await pyro_app.get_me()
        print(f"✅ Pyrogram bot connected: @{me.username}")
        await pyro_app.stop()
        return True
    except Exception as e:
        print(f"❌ Pyrogram connection failed: {e}")
        return False

@pyro_app.on_chat_join_request(pyro_filters.chat(CHAT_ID))
async def approve_and_dm(client: Client, join_request: ChatJoinRequest):
    user = join_request.from_user
    chat = join_request.chat

    print(f"🔔 Join request received from {user.first_name} ({user.id}) for {chat.title}")
    print(f"🔧 CHAT_ID: {CHAT_ID}, chat.id: {chat.id}")
    print(f"🔧 User details: {user.first_name} {user.last_name}, @{user.username}")

    try:
        # Approve the join request
        await client.approve_chat_join_request(chat.id, user.id)
        print(f"✅ Approved: {user.first_name} ({user.id}) in {chat.title}")

        # Add user to DB
        from datetime import datetime
        full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        username = user.username or ''
        join_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Get the invite link that was used for joining
        invite_link = None
        referred_by = None
        
        # Check if this user came through a tracking link
        if join_request.invite_link:
            invite_link = join_request.invite_link.invite_link
            print(f"🔗 Invite link used: {invite_link}")
            # Check if the invite link contains tracking parameter
            if invite_link and 'ref=' in invite_link:
                try:
                    # Extract referrer ID from the link
                    ref_param = invite_link.split('ref=')[1].split('&')[0]
                    referred_by = int(ref_param)
                    print(f"🎯 User {user.id} was referred by user {referred_by}")
                except (ValueError, IndexError):
                    print(f"⚠️ Could not parse referral ID from link: {invite_link}")
        else:
            # Generate a unique channel link for this user
            invite_link = generate_unique_channel_link(user.id, full_name)
            print(f"🔗 Generated unique channel link: {invite_link}")
        
        add_user(user.id, full_name, username, join_date, invite_link, referred_by=referred_by)
        print(f"💾 User {user.first_name} ({user.id}) added to database with invite link: {invite_link}")

        # Send real-time notification to frontend about new user
        socketio.emit('new_user_joined', {
            'user_id': user.id,
            'full_name': full_name,
            'username': username,
            'join_date': join_date,
            'invite_link': invite_link,
            'photo_url': None,  # Pyrogram doesn't fetch photo by default
            'referred_by': referred_by,
            'is_online': True
        })
        print(f"📡 Pyrogram bot: Sent real-time notification for new user {user.id}")

        # Send welcome message
        try:
            if referred_by:
                # Custom welcome for referred users
                welcome_message = config.WELCOME_MESSAGE
            else:
                welcome_message = config.WELCOME_MESSAGE
            
            print(f"📝 Sending welcome message to {user.first_name} ({user.id})")
            print(f"📝 Message: {welcome_message}")
            
            await client.send_message(
                user.id,
                welcome_message
            )
            print(f"✅ DM sent successfully to {user.first_name} ({user.id})")
            
            # If this was a referral, notify the referrer
            if referred_by:
                try:
                    referrer_message = (
                        f"🎉 Great news!\n\n"
                        f"Someone joined through your tracking link!\n"
                        f"👤 **New Member:** {full_name}\n"
                        f"🆔 **User ID:** {user.id}\n\n"
                        f"Keep sharing your link to grow your network! 🚀"
                    )
                    await client.send_message(chat_id=referred_by, text=referrer_message)
                    print(f"✅ Notified referrer {referred_by} about new referral {user.id}")
                except Exception as e:
                    print(f"❌ Could not notify referrer {referred_by}: {e}")
                    
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
            elif "USER_DEACTIVATED" in str(e):
                print(f"⚠️ User {user.first_name} ({user.id}) has deactivated their account")
            elif "USER_IS_BLOCKED" in str(e):
                print(f"⚠️ User {user.first_name} ({user.id}) has blocked the bot")
                
            # Try to send a message in the channel instead
            try:
                channel_message = config.WELCOME_MESSAGE
                await client.send_message(chat_id=CHAT_ID, text=channel_message)
                print(f"✅ Sent welcome message to channel for user {user.id}")
            except Exception as channel_error:
                print(f"❌ Could not send channel message: {channel_error}")
                
    except Exception as e:
        if "User_already_participant" in str(e) or "USER_ALREADY_PARTICIPANT" in str(e):
            print(f"ℹ️ User {user.first_name} ({user.id}) is already a participant in {chat.title}")
        elif "CHAT_NOT_FOUND" in str(e):
            print(f"❌ Chat not found: {chat.title} (ID: {chat.id})")
        elif "BOT_NOT_MEMBER" in str(e):
            print(f"❌ Bot is not a member of {chat.title} (ID: {chat.id})")
        elif "NOT_MEMBER" in str(e):
            print(f"❌ Bot is not a member of {chat.title} (ID: {chat.id})")
        else:
            print(f"❌ Error approving join request for {user.first_name} ({user.id}): {e}")
            print(f"🔍 Error type: {type(e).__name__}")
            print(f"🔍 Full error: {str(e)}")

@app.route('/chat/<int:user_id>', methods=['POST'])
def chat_send(user_id):
    message = request.form.get('message')
    files = request.files.getlist('files')
    
    if not message and not files:
        return {'status': 'error', 'msg': 'Missing message or files'}, 400
    
    try:
        # Handle text message
        if message:
            save_message(user_id, 'admin', message)
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            data = {
                'chat_id': user_id,
                'text': message
            }
            response = requests.post(url, data=data, timeout=10)  # Added timeout
            if response.status_code != 200:
                return {'status': 'error', 'msg': f'Telegram API error: {response.text}'}, 500
        
        # Handle files
        if files and len(files) > 0:
            temp_paths = []
            
            # File size validation
            MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
            MAX_PHOTO_SIZE = 20 * 1024 * 1024  # 20MB
            
            for file in files:
                filename = file.filename
                mimetype = file.mimetype
                
                # Check file size
                file.seek(0, 2)
                file_size = file.tell()
                file.seek(0)
                
                if mimetype.startswith('image/') and file_size > MAX_PHOTO_SIZE:
                    continue  # Skip this file
                elif file_size > MAX_FILE_SIZE:
                    continue  # Skip this file
                
                temp_path = f'temp_{filename}_{user_id}'
                file.save(temp_path)
                temp_paths.append(temp_path)
            
            try:
                for temp_path in temp_paths:
                    filename = os.path.basename(temp_path).split('_')[1]  # Get original filename
                    mimetype = None
                    
                    # Determine mimetype from file extension
                    if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                        mimetype = 'image'
                    elif filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                        mimetype = 'video'
                    elif filename.lower().endswith(('.mp3', '.wav', '.ogg', '.m4a')):
                        mimetype = 'audio'
                    else:
                        mimetype = 'document'
                    
                    # Send file to Telegram
                    with open(temp_path, 'rb') as f:
                        files_data = {'document': f}
                        data = {'chat_id': user_id}
                        
                        if message and temp_path == temp_paths[0]:  # Add caption to first file only
                            data['caption'] = message
                        
                        if mimetype == 'image':
                            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
                            files_data = {'photo': f}
                        elif mimetype == 'video':
                            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
                            files_data = {'video': f}
                        elif mimetype == 'audio':
                            # Check if it's a voice message (m4a format)
                            if filename.lower().endswith('.m4a') or 'voice' in filename.lower():
                                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice"
                                files_data = {'voice': f}
                            else:
                                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendAudio"
                                files_data = {'audio': f}
                        else:
                            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
                            files_data = {'document': f}
                        
                        f.seek(0)  # Reset file pointer
                        response = requests.post(url, data=data, files=files_data, timeout=30)  # Increased timeout for file uploads
                        
                        if response.status_code != 200:
                            return {'status': 'error', 'msg': f'Telegram API error: {response.text}'}, 500
                        
                        # Get the file_id from the response to construct proper URL
                        response_data = response.json()
                        file_id = None
                        
                        if response_data.get('ok'):
                            result = response_data.get('result', {})
                            
                            # Extract file_id based on message type
                            if mimetype == 'image':
                                file_id = result.get('photo', [{}])[-1].get('file_id') if result.get('photo') else None
                            elif mimetype == 'video':
                                file_id = result.get('video', {}).get('file_id')
                            elif mimetype == 'audio':
                                if filename.lower().endswith('.m4a') or 'voice' in filename.lower():
                                    file_id = result.get('voice', {}).get('file_id')
                                else:
                                    file_id = result.get('audio', {}).get('file_id')
                            else:
                                file_id = result.get('document', {}).get('file_id')
                        
                        # Save message with proper URL if we got file_id, otherwise use placeholder
                        if file_id:
                            # Get file path from Telegram
                            file_info_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}"
                            file_info_response = requests.get(file_info_url, timeout=10)
                            
                            if file_info_response.status_code == 200:
                                file_info = file_info_response.json()
                                if file_info.get('ok'):
                                    file_path = file_info['result'].get('file_path')
                                    if file_path:
                                        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
                                        
                                        # Save with proper URL
                                        if mimetype == 'image':
                                            is_gif = filename.lower().endswith('.gif')
                                            save_message(user_id, 'admin', f'[{"gif" if is_gif else "image"}]{file_url}')
                                        elif mimetype == 'video':
                                            save_message(user_id, 'admin', f'[video]{file_url}')
                                        elif mimetype == 'audio':
                                            if filename.lower().endswith('.m4a') or 'voice' in filename.lower():
                                                save_message(user_id, 'admin', f'[voice]{file_url}')
                                            else:
                                                save_message(user_id, 'admin', f'[audio]{file_url}')
                                        else:
                                            save_message(user_id, 'admin', f'[document]{file_url}')
                                    else:
                                        # Fallback to placeholder
                                        save_message(user_id, 'admin', f'[{mimetype}]admin-sent-{filename}')
                                else:
                                    # Fallback to placeholder
                                    save_message(user_id, 'admin', f'[{mimetype}]admin-sent-{filename}')
                            else:
                                # Fallback to placeholder
                                save_message(user_id, 'admin', f'[{mimetype}]admin-sent-{filename}')
                        else:
                            # Fallback to placeholder
                            save_message(user_id, 'admin', f'[{mimetype}]admin-sent-{filename}')
                        
                        # Real-time notify admin dashboard
                        socketio.emit('admin_message_sent', {'user_id': user_id})
                    
            except Exception as e:
                return {'status': 'error', 'msg': f'File send error: {str(e)}'}, 500
            finally:
                for temp_path in temp_paths:
                    try:
                        os.remove(temp_path)
                    except Exception as e:
                        print('Error removing temp file:', temp_path, e)
        
        socketio.emit('new_message', {'user_id': user_id}, room='chat_' + str(user_id))
        socketio.emit('admin_message_sent', {'user_id': user_id}, room='chat_' + str(user_id))
        
        return {'status': 'ok'}
        
    except Exception as e:
        return {'status': 'error', 'msg': str(e)}, 500

@app.route('/send_one', methods=['POST'])
def send_one():
    user_id = request.form.get('user_id')
    message = request.form.get('message')
    files = request.files.getlist('files')
    
    if not user_id or not (message or files):
        return {'status': 'error', 'msg': 'Missing user_id or message/files'}, 400
    
    sent = False
    
    # Handle text message
    if message:
        save_message(int(user_id), 'admin', message)
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            data = {
                'chat_id': int(user_id),
                'text': message
            }
            response = requests.post(url, data=data)
            if response.status_code == 200:
                sent = True
            else:
                print(f"Telegram API error: {response.text}")
        except Exception as e:
            print(f"Telegram send error: {e}")
    
    # Handle files
    if files and len(files) > 0:
        temp_paths = []
        
        # File size validation
        MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
        MAX_PHOTO_SIZE = 20 * 1024 * 1024  # 20MB
        
        for file in files:
            filename = file.filename
            mimetype = file.mimetype
            
            # Check file size
            file.seek(0, 2)
            file_size = file.tell()
            file.seek(0)
            
            if mimetype.startswith('image/') and file_size > MAX_PHOTO_SIZE:
                return jsonify({'status': 'error', 'message': f'Image {filename} is too large. Maximum size is 20MB.'}), 400
            elif file_size > MAX_FILE_SIZE:
                return jsonify({'status': 'error', 'message': f'File {filename} is too large. Maximum size is 50MB.'}), 400
            
            temp_path = f'temp_{filename}'
            file.save(temp_path)
            temp_paths.append(temp_path)
        
        try:
            for temp_path in temp_paths:
                filename = os.path.basename(temp_path)
                mimetype = None
                
                # Determine mimetype from file extension
                if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                    mimetype = 'image'
                elif filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                    mimetype = 'video'
                elif filename.lower().endswith(('.mp3', '.wav', '.ogg', '.m4a')):
                    mimetype = 'audio'
                else:
                    mimetype = 'document'
                
                # Send file to Telegram
                with open(temp_path, 'rb') as f:
                    files_data = {'document': f}
                    data = {'chat_id': int(user_id)}
                    
                    if message and temp_path == temp_paths[0]:  # Add caption to first file only
                        data['caption'] = message
                    
                    
                    if mimetype == 'image':
                        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
                        files_data = {'photo': f}
                    elif mimetype == 'video':
                        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
                        files_data = {'video': f}
                    elif mimetype == 'audio':
                        # Check if it's a voice message (m4a format)
                        if filename.lower().endswith('.m4a') or 'voice' in filename.lower():
                            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice"
                            files_data = {'voice': f}
                        else:
                            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendAudio"
                            files_data = {'audio': f}
                    else:
                        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
                        files_data = {'document': f}
                    
                    f.seek(0)  # Reset file pointer
                    response = requests.post(url, data=data, files=files_data)
                    
                    if response.status_code == 200:
                        # Save message based on type
                        if mimetype == 'image':
                            is_gif = filename.lower().endswith('.gif')
                            # For admin-sent files, we'll use a placeholder URL that indicates it was sent
                            save_message(int(user_id), 'admin', f'[{"gif" if is_gif else "image"}]admin-sent-{filename}')
                        elif mimetype == 'video':
                            save_message(int(user_id), 'admin', f'[video]admin-sent-{filename}')
                        elif mimetype == 'audio':
                            if filename.lower().endswith('.m4a') or 'voice' in filename.lower():
                                save_message(int(user_id), 'admin', f'[voice]admin-sent-{filename}')
                            else:
                                save_message(int(user_id), 'admin', f'[audio]admin-sent-{filename}')
                        else:
                            save_message(int(user_id), 'admin', f'[document]admin-sent-{filename}')
                        
                        sent = True
                    else:
                        print(f"Telegram API error sending file: {response.text}")
            
        except Exception as e:
            print(f"Telegram file send error: {e}")
            return jsonify({'status': 'error', 'message': f'Failed to send media: {str(e)}'}), 500
        finally:
            for temp_path in temp_paths:
                try:
                    os.remove(temp_path)
                except Exception as e:
                    print('Error removing temp file:', temp_path, e)
    
    socketio.emit('new_message', {'user_id': int(user_id)}, room='chat_' + str(user_id))
    socketio.emit('admin_message_sent', {'user_id': int(user_id)}, room='chat_' + str(user_id))
    
    if sent:
        return {'status': 'ok'}
    else:
        return {'status': 'error', 'msg': 'Failed to send message'}, 500

@app.route('/send_all', methods=['POST'])
def send_all():
    message = request.form.get('message')
    files = request.files.getlist('files')
    
    if not message and not files:
        return {'status': 'error', 'msg': 'Missing message or files'}, 400
    
    users = get_all_users()
    success_count = 0
    
    for u in users:
        try:
            # Handle text message
            if message:
                save_message(u[0], 'admin', message)
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                data = {
                    'chat_id': int(u[0]),
                    'text': message
                }
                response = requests.post(url, data=data, timeout=10)  # Added timeout
                if response.status_code == 200:
                    success_count += 1
                else:
                    print(f"Telegram API error for user {u[0]}: {response.text}")
            
            # Handle files
            if files and len(files) > 0:
                temp_paths = []
                
                # File size validation
                MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
                MAX_PHOTO_SIZE = 20 * 1024 * 1024  # 20MB
                
                for file in files:
                    filename = file.filename
                    mimetype = file.mimetype
                    
                    # Check file size
                    file.seek(0, 2)
                    file_size = file.tell()
                    file.seek(0)
                    
                    if mimetype.startswith('image/') and file_size > MAX_PHOTO_SIZE:
                        continue  # Skip this file for this user
                    elif file_size > MAX_FILE_SIZE:
                        continue  # Skip this file for this user
                    
                    temp_path = f'temp_{filename}_{u[0]}'  # Unique temp file per user
                    file.save(temp_path)
                    temp_paths.append(temp_path)
                
                try:
                    for temp_path in temp_paths:
                        filename = os.path.basename(temp_path).split('_')[1]  # Get original filename
                        mimetype = None
                        
                        # Determine mimetype from file extension
                        if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                            mimetype = 'image'
                        elif filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                            mimetype = 'video'
                        elif filename.lower().endswith(('.mp3', '.wav', '.ogg', '.m4a')):
                            mimetype = 'audio'
                        else:
                            mimetype = 'document'
                        
                        # Send file to Telegram
                        with open(temp_path, 'rb') as f:
                            files_data = {'document': f}
                            data = {'chat_id': int(u[0])}
                            
                            if message and temp_path == temp_paths[0]:  # Add caption to first file only
                                data['caption'] = message
                            
                            if mimetype == 'image':
                                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
                                files_data = {'photo': f}
                            elif mimetype == 'video':
                                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo"
                                files_data = {'video': f}
                            elif mimetype == 'audio':
                                # Check if it's a voice message (m4a format)
                                if filename.lower().endswith('.m4a') or 'voice' in filename.lower():
                                    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendVoice"
                                    files_data = {'voice': f}
                                else:
                                    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendAudio"
                                    files_data = {'audio': f}
                            else:
                                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
                                files_data = {'document': f}
                            
                            f.seek(0)  # Reset file pointer
                            response = requests.post(url, data=data, files=files_data, timeout=30)  # Increased timeout for file uploads
                            
                            if response.status_code == 200:
                                # Save message based on type
                                if mimetype == 'image':
                                    is_gif = filename.lower().endswith('.gif')
                                    # For admin-sent files, we'll use a placeholder URL that indicates it was sent
                                    save_message(u[0], 'admin', f'[{"gif" if is_gif else "image"}]admin-sent-{filename}')
                                elif mimetype == 'video':
                                    save_message(u[0], 'admin', f'[video]admin-sent-{filename}')
                                elif mimetype == 'audio':
                                    if filename.lower().endswith('.m4a') or 'voice' in filename.lower():
                                        save_message(u[0], 'admin', f'[voice]admin-sent-{filename}')
                                    else:
                                        save_message(u[0], 'admin', f'[audio]admin-sent-{filename}')
                                else:
                                    save_message(u[0], 'admin', f'[document]admin-sent-{filename}')
                                
                                success_count += 1
                            else:
                                print(f"Telegram API error sending file to user {u[0]}: {response.text}")
                        
                except Exception as e:
                    print(f"Telegram file send error for user {u[0]}: {e}")
                finally:
                    for temp_path in temp_paths:
                        try:
                            os.remove(temp_path)
                        except Exception as e:
                            print('Error removing temp file:', temp_path, e)
            
            socketio.emit('new_message', {'user_id': u[0]}, room='chat_' + str(u[0]))
            socketio.emit('admin_message_sent', {'user_id': u[0]}, room='chat_' + str(u[0]))
            
        except Exception as e:
            print(f"Telegram send error for user {u[0]}: {e}")
    
    return {'status': 'ok', 'count': success_count, 'total': len(users)}

@app.route('/user/<int:user_id>/label', methods=['POST'])
def set_user_label(user_id):
    label = request.json.get('label')
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('UPDATE users SET label = ? WHERE user_id = ?', (label, user_id))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok', 'user_id': user_id, 'label': label})

@app.route('/tracking-stats')
def get_tracking_stats():
    """Get tracking statistics for admin dashboard"""
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        # Get total referrals
        c.execute('SELECT COUNT(*) FROM users WHERE referred_by IS NOT NULL')
        total_referrals = c.fetchone()[0]
        
        # Get top referrers
        c.execute('''
            SELECT u1.full_name, u1.username, u1.referral_count, u1.user_id
            FROM users u1 
            WHERE u1.referral_count > 0 
            ORDER BY u1.referral_count DESC 
            LIMIT 10
        ''')
        top_referrers = c.fetchall()
        
        # Get recent referrals
        c.execute('''
            SELECT u1.full_name, u1.username, u1.user_id, u1.join_date, u2.full_name as referrer_name
            FROM users u1 
            LEFT JOIN users u2 ON u1.referred_by = u2.user_id
            WHERE u1.referred_by IS NOT NULL 
            ORDER BY u1.join_date DESC 
            LIMIT 20
        ''')
        recent_referrals = c.fetchall()
        
        # Get conversion rate (users who got their own tracking link)
        c.execute('SELECT COUNT(*) FROM users WHERE invite_link LIKE "%ref=%"')
        users_with_tracking = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM users')
        total_users = c.fetchone()[0]
        
        conversion_rate = (users_with_tracking / total_users * 100) if total_users > 0 else 0
        
        conn.close()
        
        return jsonify({
            'total_referrals': total_referrals,
            'top_referrers': [
                {
                    'name': row[0] or 'Unknown',
                    'username': row[1] or '',
                    'referral_count': row[2],
                    'user_id': row[3]
                } for row in top_referrers
            ],
            'recent_referrals': [
                {
                    'name': row[0] or 'Unknown',
                    'username': row[1] or '',
                    'user_id': row[2],
                    'join_date': row[3],
                    'referrer_name': row[4] or 'Unknown'
                } for row in recent_referrals
            ],
            'conversion_rate': round(conversion_rate, 2),
            'users_with_tracking': users_with_tracking,
            'total_users': total_users
        })
        
    except Exception as e:
        logger.error(f"Error getting tracking stats: {e}")
        return jsonify({'error': 'Failed to get tracking stats'}), 500

@app.route('/user-tracking/<int:user_id>')
def get_user_tracking(user_id):
    """Get tracking information for a specific user"""
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        # Get user's tracking info
        c.execute('''
            SELECT full_name, username, referral_count, invite_link, join_date
            FROM users WHERE user_id = ?
        ''', (user_id,))
        user_info = c.fetchone()
        
        if not user_info:
            return jsonify({'error': 'User not found'}), 404
        
        # Get user's referrals
        c.execute('''
            SELECT full_name, username, user_id, join_date
            FROM users 
            WHERE referred_by = ? 
            ORDER BY join_date DESC
        ''', (user_id,))
        referrals = c.fetchall()
        
        # Get who referred this user
        c.execute('''
            SELECT full_name, username, user_id
            FROM users 
            WHERE user_id = (SELECT referred_by FROM users WHERE user_id = ?)
        ''', (user_id,))
        referrer = c.fetchone()
        
        conn.close()
        
        return jsonify({
            'user_info': {
                'full_name': user_info[0] or 'Unknown',
                'username': user_info[1] or '',
                'referral_count': user_info[2] or 0,
                'invite_link': user_info[3] or '',
                'join_date': user_info[4]
            },
            'referrals': [
                {
                    'name': row[0] or 'Unknown',
                    'username': row[1] or '',
                    'user_id': row[2],
                    'join_date': row[3]
                } for row in referrals
            ],
            'referrer': {
                'name': referrer[0] or 'Unknown',
                'username': referrer[1] or '',
                'user_id': referrer[2]
            } if referrer else None
        })
        
    except Exception as e:
        logger.error(f"Error getting user tracking info: {e}")
        return jsonify({'error': 'Failed to get user tracking info'}), 500

@socketio.on('join')
def on_join(data):
    room = data.get('room')
    join_room(room)

# ========================================
# 🤖 BOT PROCESS FUNCTIONS
# ========================================

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
        print("🔧 Setting up Telegram bot handlers...")
        print(f"🔧 Bot token: {BOT_TOKEN[:10]}...")
        print(f"🔧 Chat ID: {CHAT_ID}")
        
        # Add error handling for bot conflicts
        loop.run_until_complete(application.run_polling(
            drop_pending_updates=True,
            allowed_updates=['message', 'callback_query', 'chat_join_request'],
            close_loop=False
        ))
        print("✅ Telegram bot started successfully")
    except Exception as e:
        print(f"❌ Telegram bot error: {e}")
        print(f"🔍 Error type: {type(e).__name__}")
        if "Conflict" in str(e):
            print("⚠️ Bot conflict detected. Another instance might be running.")
        elif "terminated by other getUpdates request" in str(e):
            print("⚠️ Multiple bot instances detected. Stopping this instance.")
        elif "Unauthorized" in str(e):
            print("❌ Bot token is invalid or bot is not authorized.")
        elif "Forbidden" in str(e):
            print("❌ Bot is forbidden from accessing the chat.")
        else:
            print(f"🔍 Full error: {str(e)}")
    finally:
        print("🛑 Telegram bot process stopped")

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
        if "Conflict" in str(e):
            print("⚠️ Pyrogram bot conflict detected.")

@app.route('/bot-status')
def bot_status():
    """Check if bots are working properly"""
    try:
        # Test Telegram bot
        response = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe", timeout=5)
        telegram_status = "✅ Working" if response.status_code == 200 else "❌ Not working"
        
        # Test Pyrogram bot connection
        import asyncio
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            pyrogram_status = "✅ Working" if loop.run_until_complete(test_pyrogram_connection()) else "❌ Not working"
        except Exception as e:
            pyrogram_status = f"❌ Error: {str(e)}"
        
        return jsonify({
            "telegram_bot": telegram_status,
            "pyrogram_bot": pyrogram_status,
            "chat_id": CHAT_ID,
            "channel_url": CHANNEL_URL,
            "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

@app.route('/health')
def health_check():
    """Simple health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'bot_token': BOT_TOKEN[:10] + '...' if BOT_TOKEN else 'Not configured'
    })

@app.route('/')
def index():
    return "Hello, world!"

@app.route('/media/<path:file_path>')
def serve_media(file_path):
    """Serve Telegram media files with proper CORS headers"""
    try:
        # Construct the full Telegram file URL
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        
        # Fetch the file from Telegram
        response = requests.get(file_url, stream=True, timeout=30)
        
        if response.status_code == 200:
            # Set CORS headers
            headers = {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Range',
                'Content-Type': response.headers.get('Content-Type', 'application/octet-stream'),
                'Content-Length': response.headers.get('Content-Length', ''),
                'Cache-Control': 'public, max-age=3600',  # Cache for 1 hour
                'Accept-Ranges': 'bytes'
            }
            
            # Return the file with proper headers
            return response.content, 200, headers
        else:
            print(f"Telegram API error for {file_path}: {response.status_code}")
            return jsonify({'error': 'File not found'}), 404
            
    except Exception as e:
        print(f"Error serving media file {file_path}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/media/<path:file_path>', methods=['OPTIONS'])
def serve_media_options(file_path):
    """Handle CORS preflight requests for media files"""
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Range',
        'Access-Control-Max-Age': '86400'
    }
    return '', 204, headers

@app.route('/media-proxy')
def media_proxy():
    """Proxy media files from Telegram with CORS support"""
    file_path = request.args.get('path')
    if not file_path:
        return jsonify({'error': 'No file path provided'}), 400
    
    try:
        # Construct the full Telegram file URL
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        
        # Fetch the file from Telegram
        response = requests.get(file_url, stream=True, timeout=30)
        
        if response.status_code == 200:
            # Set CORS headers
            headers = {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Range',
                'Content-Type': response.headers.get('Content-Type', 'application/octet-stream'),
                'Content-Length': response.headers.get('Content-Length', ''),
                'Cache-Control': 'public, max-age=3600',  # Cache for 1 hour
                'Accept-Ranges': 'bytes'
            }
            
            # Return the file with proper headers
            return response.content, 200, headers
        else:
            print(f"Telegram API error for {file_path}: {response.status_code}")
            return jsonify({'error': 'File not found'}), 404
            
    except Exception as e:
        print(f"Error proxying media file {file_path}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/media-proxy', methods=['OPTIONS'])
def media_proxy_options():
    """Handle CORS preflight requests for media proxy"""
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Range',
        'Access-Control-Max-Age': '86400'
    }
    return '', 204, headers

if __name__ == '__main__':
    import multiprocessing
    import time
    import os
    import requests
    
    print("🚀 Starting AutoJOIN Bot Application...")
    print(f"🔧 CHAT_ID: {CHAT_ID}")
    print(f"🔧 BOT_TOKEN: {BOT_TOKEN[:10]}...")
    print(f"🔧 API_ID: {config.API_ID}")
    print(f"🔧 API_HASH: {config.API_HASH[:10]}...")
    
    # Check if bot is already running
    try:
        response = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe", timeout=5)
        if response.status_code == 200:
            print("✅ Bot is accessible")
        else:
            print("❌ Bot is not accessible")
    except Exception as e:
        print(f"⚠️ Could not check bot status: {e}")
    
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
    port = int(os.environ.get('PORT', 5001))  # Changed from 8080 to 5001
    host = '0.0.0.0'  # Bind to all interfaces for Render
    
    print(f"🚀 Server starting on {host}:{port}")
    
    # Run Flask in the main process
    socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True)
