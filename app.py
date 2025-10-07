from flask import Flask, request, jsonify
import requests
import json
import gzip
import io
import os
import time

app = Flask(__name__)

API_TOKEN = "YXNwZWN0"
PHONE_INDEX = None
LOAD_TIME = None

def load_index():
    global PHONE_INDEX, LOAD_TIME
    
    print("📥 Загружаю базу с Dropbox...")
    start_time = time.time()
    
    dropbox_url = "https://www.dropbox.com/scl/fi/kxj0wuh6z3yqplb8qc42n/phone_index.json.gz?rlkey=y5gsvr81wel9vty1jodaqtc1b&st=y1zwvbme&dl=1"
    
    try:
        response = requests.get(dropbox_url, timeout=60)
        response.raise_for_status()
        
        print(f"📦 Размер файла: {len(response.content) / (1024*1024):.1f} MB")
        
        # РАСПАКОВЫВАЕМ ВСЮ БАЗУ В ПАМЯТЬ
        compressed_data = io.BytesIO(response.content)
        with gzip.open(compressed_data, 'rt', encoding='utf-8') as file:
            PHONE_INDEX = json.load(file)
        
        LOAD_TIME = time.time() - start_time
        print(f"✅ База загружена за {LOAD_TIME:.1f} сек! Записей: {len(PHONE_INDEX):,}")
        
    except Exception as error:
        print(f"❌ Ошибка загрузки: {error}")
        PHONE_INDEX = {}

def clean_phone(phone_str):
    digits = ''.join(filter(str.isdigit, phone_str))
    if len(digits) == 10:
        return '7' + digits
    elif len(digits) > 11:
        return digits[:11]
    return digits

@app.route('/')
def home():
    return "Phone Search API"

@app.route('/search', methods=['POST'])
def search_phone():
    if not request.json:
        return jsonify({"error": "Требуется JSON"}), 400
    
    data = request.json
    phone_input = data.get('phone')
    token_input = data.get('token')
    
    if not phone_input or not token_input:
        return jsonify({"error": "Нужны phone и token"}), 400
    
    if token_input != API_TOKEN:
        return jsonify({"error": "Неверный токен"}), 401
    
    if not PHONE_INDEX:
        return jsonify({"error": "База не загружена"}), 503
    
    clean_number = clean_phone(phone_input)
    
    if len(clean_number) != 11:
        return jsonify({"error": "Неверный формат номера"}), 400
    
    # БЫСТРЫЙ ПОИСК В ПАМЯТИ
    start_time = time.time()
    record = PHONE_INDEX.get(clean_number)
    search_time = time.time() - start_time
    
    if record:
        return jsonify({
            "phone": clean_number,
            "name": record.get('n', ''),
            "email": record.get('e', ''),
            "search_time_ms": round(search_time * 1000, 3)
        })
    else:
        return jsonify({
            "phone": clean_number,
            "status": "not_found",
            "search_time_ms": round(search_time * 1000, 3)
        })

@app.route('/status')
def status():
    return jsonify({
        "status": "online" if PHONE_INDEX else "loading",
        "records": len(PHONE_INDEX) if PHONE_INDEX else 0,
        "load_time_sec": round(LOAD_TIME, 2) if LOAD_TIME else 0
    })

# Загружаем базу при старте
load_index()

# Убери блок if __name__ если используешь gunicorn
