from flask import Flask, request, jsonify
import requests
import json
import gzip
import io
import os
import time

app = Flask(__name__)

API_TOKEN = "YXNwZWN0"
GZIP_CONTENT = None
LOAD_TIME = None

def load_gzip_index():
    global GZIP_CONTENT, LOAD_TIME
    
    print("📥 Загружаю базу с Dropbox...")
    start_time = time.time()
    
    dropbox_url = "https://www.dropbox.com/scl/fi/kxj0wuh6z3yqplb8qc42n/phone_index.json.gz?rlkey=y5gsvr81wel9vty1jodaqtc1b&st=y1zwvbme&dl=1"
    
    try:
        response = requests.get(dropbox_url, timeout=60)
        response.raise_for_status()
        
        print(f"📦 Размер файла: {len(response.content) / (1024*1024):.1f} MB")
        
        # Сохраняем сжатые данные в памяти
        GZIP_CONTENT = response.content
        LOAD_TIME = time.time() - start_time
        print(f"✅ База загружена за {LOAD_TIME:.1f} сек!")
        
    except Exception as error:
        print(f"❌ Ошибка загрузки: {error}")
        GZIP_CONTENT = None

def search_in_gzip(phone_number):
    """
    Ищет телефон в gzip архиве без полной распаковки
    """
    if not GZIP_CONTENT:
        return None
    
    try:
        # Декомпрессия на лету
        compressed_data = io.BytesIO(GZIP_CONTENT)
        
        # Читаем файл построчно для экономии памяти
        with gzip.open(compressed_data, 'rt', encoding='utf-8') as file:
            buffer = ""
            for line in file:
                buffer += line
                
                # Ищем телефон в текущем буфере
                phone_pattern = f'"{phone_number}"'
                if phone_pattern in buffer:
                    # Нашли телефон, извлекаем полную запись
                    start_idx = buffer.find(phone_pattern)
                    
                    # Ищем начало объекта
                    obj_start = buffer.rfind('{', 0, start_idx)
                    if obj_start == -1:
                        continue
                    
                    # Ищем конец объекта
                    obj_end = buffer.find('}', start_idx)
                    if obj_end == -1:
                        # Объект продолжается в следующей строке
                        continue
                    
                    obj_end += 1  # Включаем закрывающую скобку
                    
                    try:
                        # Извлекаем и парсим JSON объект
                        record_str = buffer[obj_start:obj_end]
                        record_data = json.loads(record_str)
                        
                        if phone_number in record_data:
                            return record_data[phone_number]
                    except json.JSONDecodeError:
                        continue
                    
        return None
        
    except Exception as e:
        print(f"❌ Ошибка поиска в архиве: {e}")
        return None

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
    
    if not GZIP_CONTENT:
        return jsonify({"error": "База не загружена"}), 503
    
    clean_number = clean_phone(phone_input)
    
    if len(clean_number) != 11:
        return jsonify({"error": "Неверный формат номера"}), 400
    
    start_time = time.time()
    record = search_in_gzip(clean_number)
    search_time = time.time() - start_time
    
    if record:
        return jsonify({
            "📱 Телефон": clean_number,
            "👤 ФИО": record.get('n', ''),
            "📧 Email": record.get('e', ''),
            "⚡ Время поиска": f"{search_time:.3f} сек"
        })
    else:
        return jsonify({
            "📱 Телефон": clean_number,
            "💬 Статус": "Не найден",
            "⚡ Время поиска": f"{search_time:.3f} сек"
        })

@app.route('/status')
def status():
    return jsonify({
        "status": "online" if GZIP_CONTENT else "loading",
        "memory_usage": f"{len(GZIP_CONTENT) / (1024*1024):.1f} MB" if GZIP_CONTENT else "0 MB"
    })

# Загружаем базу
load_gzip_index()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
