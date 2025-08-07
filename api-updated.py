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
from config import BOT_TOKEN, DASHBOARD_PASSWORD, CHANNEL_ID, CHANNEL_URL
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

# Import our new configuration system
from api_config import api_config

app = Flask(__name__)
app.secret_key = 'change_this_secret_key'

# Use configuration from api_config
CORS(app, origins=api_config.CORS_ORIGINS, supports_credentials=True)
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins=api_config.CORS_ORIGINS)

DB_NAME = api_config.DATABASE_PATH

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
    count = c.fetchone()[0]
    conn.close()
    return count

def get_messages_for_user(user_id, limit=100):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM messages WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?', (user_id, limit))
    messages = c.fetchall()
    conn.close()
    return messages

def save_message(user_id, sender, message):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('INSERT INTO messages (user_id, sender, message, timestamp) VALUES (?, ?, ?, ?)', 
              (user_id, sender, message, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()

def add_user(user_id, full_name, username, join_date, invite_link, photo_url=None, label=None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO users (user_id, full_name, username, join_date, invite_link, photo_url, label) VALUES (?, ?, ?, ?, ?, ?, ?)', 
              (user_id, full_name, username, join_date, invite_link, photo_url, label))
    conn.commit()
    conn.close()

def get_active_users(minutes=60):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    cutoff_time = (datetime.datetime.now() - datetime.timedelta(minutes=minutes)).isoformat()
    c.execute('SELECT COUNT(DISTINCT user_id) FROM messages WHERE timestamp > ?', (cutoff_time,))
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
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    today = datetime.datetime.now().date().isoformat()
    c.execute('SELECT COUNT(*) FROM users WHERE DATE(join_date) = ?', (today,))
    count = c.fetchone()[0]
    conn.close()
    return count

def get_user_online_status(user_id, minutes=5):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    cutoff_time = (datetime.datetime.now() - datetime.timedelta(minutes=minutes)).isoformat()
    c.execute('SELECT COUNT(*) FROM messages WHERE user_id = ? AND timestamp > ?', (user_id, cutoff_time))
    count = c.fetchone()[0]
    conn.close()
    return count > 0

@app.route('/user-status/<int:user_id>')
def user_status(user_id):
    is_online = get_user_online_status(user_id)
    return jsonify({'is_online': is_online})

@app.route('/dashboard-users')
def dashboard_users():
    # Get page and page_size from query params, default page=1, page_size=10
    page = int(request.args.get('page', 1))
    page_size = int(request.args.get('page_size', 10))
    
    # Get all users
    users = get_all_users()
    
    # Calculate pagination
    total_users = len(users)
    total_pages = (total_users + page_size - 1) // page_size
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    
    # Get users for current page
    page_users = users[start_idx:end_idx]
    
    # Convert to list of dictionaries
    users_list = []
    for user in page_users:
        user_id, full_name, username, join_date, invite_link, photo_url, label = user
        users_list.append({
            'user_id': user_id,
            'full_name': full_name,
            'username': username,
            'join_date': join_date,
            'invite_link': invite_link,
            'photo_url': photo_url,
            'label': label,
            'is_online': get_user_online_status(user_id)
        })
    
    return jsonify({
        'users': users_list,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total_users': total_users,
            'total_pages': total_pages
        }
    })

@app.route('/dashboard-stats')
def dashboard_stats():
    # Total users in the database
    total_users = get_total_users()
    
    # Active users (users who sent messages in last 60 minutes)
    active_users = get_active_users(60)
    
    # Total messages
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
    messages = get_messages_for_user(user_id, 100)
    return jsonify(messages)

@app.route('/get_channel_invite_link', methods=['GET'])
def get_channel_invite_link():
    return jsonify({'invite_link': CHANNEL_URL})

# ... (rest of your existing code remains the same)

# ========================================
# 🚀 SERVER STARTUP
# ========================================

if __name__ == '__main__':
    # Print current configuration
    api_config.print_config()
    
    print(f"🚀 Starting API server on {api_config.HOST}:{api_config.PORT}")
    print(f"🌐 Frontend URL: {api_config.FRONTEND_URL}")
    print(f"🔧 Environment: {api_config.environment}")
    print(f"🐛 Debug mode: {api_config.DEBUG}")
    
    # Start the server with configuration
    socketio.run(
        app, 
        host=api_config.HOST, 
        port=api_config.PORT, 
        debug=api_config.DEBUG
    ) 
