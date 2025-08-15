# 🚀 Hookah Stock Manager API

Современный FastAPI бэкенд для управления слотами кальянов с интеграцией Telegram и Google Sheets.

## ✨ **Основные улучшения v2.0**

- 🔒 **Безопасность**: Убраны захардкоженные токены и ID
- 🏗️ **Архитектура**: Модульная структура с разделением ответственности
- ✅ **Валидация**: Строгая валидация данных через Pydantic схемы
- 🛡️ **Обработка ошибок**: Централизованная обработка исключений
- 📝 **Логирование**: Структурированное логирование всех операций
- ⚙️ **Конфигурация**: Централизованная конфигурация через переменные окружения
- 🧪 **Тестирование**: Готовая структура для unit и integration тестов

## 🏗️ **Архитектура**

```
AppBack/
├── main.py              # FastAPI приложение и эндпоинты
├── models.py            # Модели базы данных SQLAlchemy
├── schemas.py           # Pydantic схемы для валидации
├── rq.py               # Бизнес-логика и операции с БД
├── bot_handler.py      # Telegram бот
├── config.py           # Конфигурация приложения
├── requirements.txt    # Python зависимости
└── env.example        # Пример переменных окружения
```

## 🚀 **Быстрый старт**

### 1. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 2. Настройка переменных окружения
Скопируйте `env.example` в `.env` и заполните:
```bash
cp env.example .env
```

Отредактируйте `.env`:
```env
BOT_TOKEN=your_telegram_bot_token
ADMIN_IDS=123456789,987654321
BACKEND_URL=https://your-backend-domain.com
```

### 3. Запуск приложения
```bash
# Запуск FastAPI сервера
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Запуск Telegram бота (в отдельном терминале)
python bot_handler.py
```

## 📚 **API Документация**

После запуска сервера доступна автоматическая документация:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔌 **API Эндпоинты**

### **Stocks (Слоты)**
- `POST /api/stocks/{tg_id}` - Обновление слотов
- `GET /api/stocks/{tg_id}` - Получение слотов пользователя

### **Profile (Профиль)**
- `GET /api/main/{tg_id}` - Профиль пользователя
- `POST /api/register` - Регистрация/обновление пользователя

### **Admin (Админ)**
- `GET /redeem/{guest_tg_id}` - Добавление бесплатного слота (только админы)

### **Telegram Integration**
- `POST /send_webapp_button/{chat_id}` - Отправка WebApp кнопки

### **System**
- `GET /health` - Проверка состояния системы

## 🗄️ **База данных**

### **Модели**
- **User**: Пользователи с Telegram ID
- **Stock**: Слоты кальянов (платные/бесплатные)

### **Особенности**
- Автоматическое создание таблиц при запуске
- Индексы для оптимизации запросов
- Каскадное удаление связанных записей
- Timestamps для аудита

## 🤖 **Telegram Bot**

### **Команды**
- `/start` - Открыть WebApp
- `/help` - Справка
- `/status` - Статус системы

### **Функции**
- Автоматическая отправка WebApp кнопок
- Обработка ошибок и логирование
- Проверка состояния backend'а

## ⚙️ **Конфигурация**

### **Основные настройки**
```python
# config.py
class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///db.sqlite3"
    BOT_TOKEN: str = ""
    WEBAPP_URL: str = "https://frontend-delta-sandy-58.vercel.app"
    MAX_STOCKS_PER_USER: int = 5
    ADMIN_IDS: List[int] = []
```

### **Переменные окружения**
- `BOT_TOKEN` - Токен Telegram бота
- `ADMIN_IDS` - ID админов (через запятую)
- `DATABASE_URL` - URL базы данных
- `WEBAPP_URL` - URL фронтенда
- `GOOGLE_APPS_SCRIPT_URL` - URL Google Apps Script

## 🔒 **Безопасность**

- ✅ Валидация всех входящих данных
- ✅ Проверка прав доступа для админских функций
- ✅ Безопасная обработка ошибок (без утечки информации)
- ✅ Логирование всех важных операций
- ✅ CORS настройки через конфигурацию

## 🧪 **Тестирование**

### **Структура тестов**
```
tests/
├── test_api.py         # Тесты API эндпоинтов
├── test_models.py      # Тесты моделей БД
├── test_business.py    # Тесты бизнес-логики
└── conftest.py         # Конфигурация pytest
```

### **Запуск тестов**
```bash
pytest tests/ -v
pytest tests/ --cov=. --cov-report=html
```

## 📊 **Мониторинг и логирование**

### **Логирование**
- Структурированные логи в формате JSON
- Разные уровни логирования (INFO, WARNING, ERROR)
- Логирование всех API запросов и ошибок

### **Health Check**
- Эндпоинт `/health` для мониторинга
- Проверка состояния базы данных
- Время последнего обновления

## 🚀 **Deployment**

### **Production настройки**
```env
# .env.production
DATABASE_URL=postgresql+asyncpg://user:pass@host/db
ALLOWED_ORIGINS=https://yourdomain.com
BOT_TOKEN=your_production_bot_token
```

### **Docker**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 🔄 **Миграции**

При изменении моделей БД:
1. Обновите модели в `models.py`
2. Удалите старую БД: `rm db.sqlite3`
3. Перезапустите приложение (БД создастся автоматически)

## 📝 **Changelog**

### **v2.0.0** - Major Refactoring
- 🔒 Убраны захардкоженные токены
- 🏗️ Модульная архитектура
- ✅ Строгая валидация данных
- 🛡️ Централизованная обработка ошибок
- 📝 Структурированное логирование
- ⚙️ Конфигурация через переменные окружения

### **v1.0.0** - Initial Release
- Базовый функционал управления слотами
- Интеграция с Telegram
- Google Sheets интеграция

## 🤝 **Contributing**

1. Fork репозитория
2. Создайте feature branch
3. Добавьте тесты для новой функциональности
4. Убедитесь, что все тесты проходят
5. Создайте Pull Request

## 📄 **License**

MIT License - см. файл LICENSE для деталей.

## 🆘 **Поддержка**

При возникновении проблем:
1. Проверьте логи приложения
2. Убедитесь, что все переменные окружения настроены
3. Проверьте документацию API
4. Создайте Issue в репозитории

---

**Сделано с ❤️ для управления кальянными слотами**
