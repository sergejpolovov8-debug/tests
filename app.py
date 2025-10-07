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
    
    print("📥 Загружаю базу...")
    start_time = time.time()
    
    # ИСПРАВЛЕНИЕ 1: Добавляем параметр confirm
    file_id = "1QqkEINOehMyzei27M3m_gGHWc_IJ3gVM"
    google_drive_url = f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t"
    
    try:
        # ИСПРАВЛЕНИЕ 2: Добавляем заголовки
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        session = requests.Session()
        response = session.get(google_drive_url, headers=headers, timeout=60)
        response.raise_for_status()
        
        # ИСПРАВЛЕНИЕ 3: Проверяем что это не HTML
        if response.text.strip().startswith('<!DOCTYPE') or response.text.strip().startswith('<html'):
            print("❌ Google Drive вернул HTML страницу вместо файла")
            print("🔧 Решение: Используй другой хостинг для файла")
            return
        
        # Пробуем распаковать
        compressed_data = io.BytesIO(response.content)
        
        try:
            with gzip.open(compressed_data, 'rt', encoding='utf-8') as file:
                PHONE_INDEX = json.load(file)
        except gzip.BadGzipFile:
            print("❌ Файл не является gzip архивом")
            # Пробуем как обычный JSON
            try:
                PHONE_INDEX = json.loads(response.text)
                print("✅ Файл загружен как обычный JSON")
            except:
                print("❌ Файл не является JSON")
                return
        
        LOAD_TIME = time.time() - start_time
        print(f"✅ База загружена! Записей: {len(PHONE_INDEX):,}")
        
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
    return "detail not found", 404

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
    
    if clean_number in PHONE_INDEX:
        record = PHONE_INDEX[clean_number]
        return jsonify({
            "📱 Телефон": clean_number,
            "👤 ФИО": record.get('n', ''),
            "📧 Email": record.get('e', '')
        })
    else:
        return jsonify({
            "📱 Телефон": clean_number,
            "💬 Статус": "Не найден"
        })

@app.route('/status')
def status():
    return jsonify({
        "status": "online" if PHONE_INDEX else "loading",
        "records": len(PHONE_INDEX) if PHONE_INDEX else 0
    })

# Загружаем базу при старте
load_index()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)