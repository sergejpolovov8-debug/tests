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
        # Потоковая загрузка для экономии памяти
        response = requests.get(dropbox_url, stream=True, timeout=120)
        response.raise_for_status()
        
        # Собираем данные частями
        chunks = []
        total_size = 0
        
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                chunks.append(chunk)
                total_size += len(chunk)
                if total_size > 300 * 1024 * 1024:  # 300MB лимит
                    print("❌ Файл слишком большой для Free тарифа")
                    return
        
        print(f"📦 Загружено: {total_size / (1024*1024):.1f} MB")
        
        # Объединяем чанки и распаковываем
        file_data = b''.join(chunks)
        compressed_data = io.BytesIO(file_data)
        
        with gzip.open(compressed_data, 'rt', encoding='utf-8') as file:
            PHONE_INDEX = json.load(file)
        
        # Очищаем память
        del chunks, file_data, compressed_data
        
        LOAD_TIME = time.time() - start_time
        print(f"✅ База загружена! Записей: {len(PHONE_INDEX):,}")
        
    except Exception as error:
        print(f"❌ Ошибка: {error}")
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
    if not PHONE_INDEX:
        return jsonify({"error": "База не загружена"}), 503
        
    if not request.json:
        return jsonify({"error": "Требуется JSON"}), 400
    
    data = request.json
    phone_input = data.get('phone')
    token_input = data.get('token')
    
    if not phone_input or not token_input:
        return jsonify({"error": "Нужны phone и token"}), 400
    
    if token_input != API_TOKEN:
        return jsonify({"error": "Неверный токен"}), 401
    
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
