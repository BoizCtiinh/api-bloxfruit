from flask import Flask, jsonify
import discord
from discord.ext import commands
import asyncio
import threading
import os
import time
from datetime import datetime

app = Flask(__name__)

# Cấu hình channels
CHANNELS = {
    'rip_indra': {
        'id': 1451756589810974882,
        'name': 'Rip Indra',
        'data': []
    },
    'doughking': {
        'id': 1451756588237979658,
        'name': 'Dough King',
        'data': []
    },
    'darkbeard': {
        'id': 1451756602196758650,
        'name': 'Dark Beard',
        'data': []
    },
    'soulreaper': {
        'id': 1451756593346777128,
        'name': 'Soul Reaper',
        'data': []
    }
}

# Tổng số message nhận được
total_messages = 0

class DiscordMonitor(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
    
    async def on_ready(self):
        print(f'✅ Đã đăng nhập: {self.user}')
        for key, channel_data in CHANNELS.items():
            print(f'📡 Đang theo dõi {channel_data["name"]}: {channel_data["id"]}')
        
        # Bắt đầu task tự động xóa
        self.loop.create_task(self.auto_cleanup())
    
    async def auto_cleanup(self):
        """Tự động xóa data cũ hơn 200s"""
        while True:
            await asyncio.sleep(10)  # Check mỗi 10s
            current_time = time.time()
            
            for channel_key, channel_data in CHANNELS.items():
                original_count = len(channel_data['data'])
                # Giữ lại data còn < 200s
                channel_data['data'] = [
                    item for item in channel_data['data']
                    if current_time - item['timestamp'] < 200
                ]
                removed = original_count - len(channel_data['data'])
                if removed > 0:
                    print(f"🗑️ Đã xóa {removed} data cũ từ {channel_data['name']}")
    
    async def on_message(self, message):
        global total_messages
        
        # Tìm channel tương ứng
        channel_key = None
        for key, channel_data in CHANNELS.items():
            if message.channel.id == channel_data['id']:
                channel_key = key
                break
        
        if not channel_key:
            return
        
        # Chỉ xử lý embed messages
        if not message.embeds:
            return
        
        embed = message.embeds[0]
        
        # Trích xuất Job ID và Server Information
        job_id = None
        server_info = None
        players = None
        
        for field in embed.fields:
            if 'Job ID' in field.name:
                job_id = field.value.strip()
            elif 'Server Information' in field.name:
                server_info = field.value.strip()
                # Trích xuất số players từ server info
                # Format thường là: "Players: 12/12" hoặc tương tự
                if 'Players:' in server_info:
                    try:
                        players_text = server_info.split('Players:')[1].strip().split()[0]
                        players = players_text  # Giữ nguyên format "12/12"
                    except:
                        players = "Unknown"
        
        if job_id and server_info:
            # Tạo data entry
            data_entry = {
                'Players': players or "Unknown",
                'jobid': job_id,
                'name': CHANNELS[channel_key]['name'],
                'age': 0,  # Sẽ được tính khi request
                'timestamp': time.time(),  # Để tính age và auto-delete
                'server_info': server_info
            }
            
            # Thêm vào danh sách
            CHANNELS[channel_key]['data'].insert(0, data_entry)
            total_messages += 1
            
            print(f"✨ [{CHANNELS[channel_key]['name']}] Job ID: {job_id} | Players: {players}")

# Khởi chạy Discord client
def run_discord_bot(token):
    client = DiscordMonitor()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(client.start(token))

# Helper function để tính age và format response
def format_response(channel_key):
    current_time = time.time()
    data = []
    
    for item in CHANNELS[channel_key]['data']:
        age = int(current_time - item['timestamp'])
        data.append({
            'Players': item['Players'],
            'jobid': item['jobid'],
            'name': item['name'],
            'age': age
        })
    
    return {
        'total': total_messages,
        'count': len(data),
        'data': data
    }

# API Endpoints
@app.route('/')
def home():
    return jsonify({
        'status': 'running',
        'message': 'Blox Fruits Boss Monitor API',
        'total_messages': total_messages,
        'endpoints': {
            '/api/rip_indra': f"Rip Indra spawns ({len(CHANNELS['rip_indra']['data'])} active)",
            '/api/doughking': f"Dough King spawns ({len(CHANNELS['doughking']['data'])} active)",
            '/api/darkbeard': f"Dark Beard spawns ({len(CHANNELS['darkbeard']['data'])} active)",
            '/api/soulreaper': f"Soul Reaper spawns ({len(CHANNELS['soulreaper']['data'])} active)",
            '/api/all': 'All boss spawns'
        }
    })

@app.route('/api/rip_indra')
def get_rip_indra():
    return jsonify(format_response('rip_indra'))

@app.route('/api/doughking')
def get_doughking():
    return jsonify(format_response('doughking'))

@app.route('/api/darkbeard')
def get_darkbeard():
    return jsonify(format_response('darkbeard'))

@app.route('/api/soulreaper')
def get_soulreaper():
    return jsonify(format_response('soulreaper'))

@app.route('/api/all')
def get_all():
    all_data = []
    for channel_key in CHANNELS.keys():
        response = format_response(channel_key)
        all_data.extend(response['data'])
    
    # Sắp xếp theo age (mới nhất trước)
    all_data.sort(key=lambda x: x['age'])
    
    return jsonify({
        'total': total_messages,
        'count': len(all_data),
        'data': all_data
    })

@app.route('/health')
def health_check():
    status = {}
    for key, channel_data in CHANNELS.items():
        status[key] = {
            'name': channel_data['name'],
            'active_spawns': len(channel_data['data'])
        }
    
    return jsonify({
        'status': 'healthy',
        'total_messages': total_messages,
        'channels': status
    })

if __name__ == '__main__':
    DISCORD_TOKEN = os.getenv('MTA4NzM4MDM5NTk3ODQwNzkzNg.GCOMfU.SnCZUhS5krYYnNpwua0gn3DNClT4NGn_lJNqro')
    PORT = int(os.getenv('PORT', 5000))
    
    if not DISCORD_TOKEN:
        print("⚠️ Cần set DISCORD_TOKEN trong environment variables")
        exit(1)
    
    print("🚀 Khởi động Discord Monitor API...")
    
    # Khởi chạy Discord bot
    discord_thread = threading.Thread(
        target=run_discord_bot,
        args=(DISCORD_TOKEN,),
        daemon=True
    )
    discord_thread.start()
    
    # Đợi bot connect
    time.sleep(3)
    
    # Chạy Flask API
    print(f"🌐 API đang chạy tại port {PORT}")
    app.run(host='0.0.0.0', port=PORT)
