from flask import Flask, request, jsonify
import requests
import json
import gzip
import io
import os
import time

app = Flask(__name__)
# Конфигурация API
API_TOKEN = "YXNwZWN0"  # Ваш секретный токен
PHONE_INDEX = None       # Здесь будет храниться наша база номеров
LOAD_TIME = None         # Время загрузки базы

def load_index():
    """Загружает базу номеров при запуске приложения"""
    global PHONE_INDEX, LOAD_TIME
    
    print("📥 Загружаю базу номеров...")
    start_time = time.time()
    
    # ЗАМЕНИТЕ НА ВАШ REAL FILE ID С GOOGLE DRIVE
    google_drive_url = "https://drive.google.com/uc?export=download&id=1QqkEINOehMyzei27M3m_gGHWc_IJ3gVM"
    
    try:
        # Скачиваем файл с Google Drive
        response = requests.get(google_drive_url, timeout=60)
        response.raise_for_status()  # Проверяем ошибки HTTP
        
        # Распаковываем сжатый JSON
        compressed_data = io.BytesIO(response.content)
        with gzip.open(compressed_data, 'rt', encoding='utf-8') as file:
            PHONE_INDEX = json.load(file)
        
        # Записываем время загрузки
        LOAD_TIME = time.time() - start_time
        print(f"✅ База загружена за {LOAD_TIME:.1f} секунд! Записей: {len(PHONE_INDEX):,}")
        
    except Exception as error:
        print(f"❌ Ошибка загрузки базы: {error}")
        PHONE_INDEX = {}  # Создаем пустую базу при ошибке

def clean_phone_number(phone_str):
    """Очищает номер телефона от лишних символов"""
    digits = ''.join(filter(str.isdigit, phone_str))  # Оставляем только цифры
    
    if len(digits) == 10:
        return '7' + digits  # Добавляем код страны
    elif len(digits) > 11:
        return digits[:11]   # Обрезаем до 11 цифр
    
    return digits

@app.route('/')
def home_page():
    """Главная страница с инструкцией"""
    return """
    <h1>🔍 API для поиска</h1>"""

@app.route('/search', methods=['POST'])
def search_phone():
    """Основная функция поиска номера телефона"""
    request_start_time = time.time()
    
    # Проверяем что запрос именно POST
    if request.method != 'POST':
        return jsonify({
            "success": False,
            "error": "Используйте POST запрос",
            "example": {
                "phone": "71234567890",
                "token": "unknown"
            }
        }), 405  # 405 = Method Not Allowed
    
    # Проверяем что данные в формате JSON
    if not request.json:
        return jsonify({
            "success": False,
            "error": "Отправьте данные в формате JSON",
            "example": {
                "phone": "71234567890", 
                "token": "unknown"
            }
        }), 400  # 400 = Bad Request
    
    # Получаем данные из запроса
    request_data = request.json
    phone_input = request_data.get('phone')
    token_input = request_data.get('token')
    
    # Проверяем обязательные поля
    if not phone_input:
        return jsonify({
            "success": False,
            "error": "Укажите номер телефона",
            "required_fields": ["phone", "token"]
        }), 400
    
    if not token_input:
        return jsonify({
            "success": False, 
            "error": "Укажите токен доступа",
            "required_fields": ["phone", "token"]
        }), 400
    
    # Проверяем токен
    if token_input != API_TOKEN:
        return jsonify({
            "success": False,
            "error": "Неверный токен доступа"
        }), 401  # 401 = Unauthorized
    
    # Проверяем что база загружена
    if not PHONE_INDEX:
        return jsonify({
            "success": False,
            "error": "База данных еще не загружена"
        }), 503  # 503 = Service Unavailable
    
    # Очищаем номер телефона
    clean_phone = clean_phone_number(phone_input)
    
    # Проверяем формат номера
    if len(clean_phone) != 11:
        return jsonify({
            "success": False,
            "error": "Неверный формат номера",
            "provided": phone_input,
            "cleaned": clean_phone,
            "required_format": "11 цифр (79991234567)"
        }), 400
    
    # Ищем номер в базе данных
    search_start_time = time.time()
    
    if clean_phone in PHONE_INDEX:
        # Номер найден!
        record_data = PHONE_INDEX[clean_phone]
        search_duration = (time.time() - search_start_time) * 1000
        total_duration = (time.time() - request_start_time) * 1000
        
        return jsonify({
            "success": True,
            "status": "НАЙДЕНО",
            "data": {
                "phone": clean_phone,
                "name": record_data.get('n', ''),
                "email": record_data.get('e', '')
            },
            "timing": {
                "search_ms": round(search_duration, 2),
                "total_ms": round(total_duration, 2)
            }
        })
    
    else:
        # Номер не найден
        search_duration = (time.time() - search_start_time) * 1000
        total_duration = (time.time() - request_start_time) * 1000
        
        return jsonify({
            "success": True,
            "status": "НЕ_НАЙДЕНО",
            "data": {
                "phone": clean_phone
            },
            "timing": {
                "search_ms": round(search_duration, 2),
                "total_ms": round(total_duration, 2)
            }
        })

@app.route('/status', methods=['POST'])
def get_status():
    """Проверка статуса API"""
    if not request.json or request.json.get('token') != API_TOKEN:
        return jsonify({
            "success": False,
            "error": "Токен требуется для проверки статуса"
        }), 401
    
    return jsonify({
        "success": True,
        "status": "online",
        "statistics": {
            "records": len(PHONE_INDEX),
            "load_time_sec": round(LOAD_TIME, 2) if LOAD_TIME else 0,
            "memory_mb": len(str(PHONE_INDEX).encode('utf-8')) // 1024 // 1024 if PHONE_INDEX else 0
        }
    })

# Загружаем базу при запуске приложения
load_index()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)