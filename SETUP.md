# 🚀 Настройка и запуск улучшенного бэкенда

## 📋 **Что было улучшено**

### ✅ **Безопасность**
- Убраны все захардкоженные токены и ID
- Добавлена валидация входящих данных
- Централизованная конфигурация через переменные окружения

### 🏗️ **Архитектура**
- Модульная структура с разделением ответственности
- Отдельные файлы для моделей, схем, бизнес-логики
- Чистые API эндпоинты с валидацией

### 🛡️ **Надежность**
- Централизованная обработка ошибок
- Структурированное логирование
- Graceful handling исключений

### 🧪 **Тестирование**
- Готовая структура для unit и integration тестов
- Pytest конфигурация
- Тестовые фикстуры

### 📱 **WebApp интеграция**
- **Исправлены CORS проблемы** - WebApp теперь работает у всех пользователей
- **SQLite БД** - данные сохраняются локально
- **Новый эндпоинт** `/api/webapp/init/{tg_id}` для инициализации
- **Персистентность данных** - пользователи не теряются при перезагрузке

## 🚀 **Быстрый старт**

### 1. **Установка зависимостей**
```bash
# Установка всех зависимостей
make install

# Или вручную
pip install -r requirements.txt
```

### 2. **Настройка переменных окружения**
```bash
# Копирование примера конфигурации
cp env.example .env

# Редактирование .env файла
nano .env
```

**Обязательные настройки в .env:**
```env
# Telegram Bot Token (получить у @BotFather)
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# ID администраторов (через запятую)
ADMIN_IDS=123456789,987654321

# URL вашего backend'а (автоопределяется для GitHub Codespaces)
BACKEND_URL=http://localhost:8000

# URL фронтенда
WEBAPP_URL=https://frontend-delta-sandy-58.vercel.app
```

### 3. **Запуск приложения**

#### **Вариант 1: Ручной запуск**
```bash
# Терминал 1: FastAPI сервер
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Терминал 2: Telegram бот
python bot_handler.py
```

#### **Вариант 2: Через Makefile**
```bash
# Запуск FastAPI сервера
make run

# Запуск бота
make run-bot

# Или запуск в режиме разработки
make dev
```

#### **Вариант 3: Docker**
```bash
# Сборка и запуск
make docker-compose-up

# Остановка
make docker-compose-down
```

## 🔍 **Проверка работоспособности**

### **API Endpoints**
- **Health Check**: http://localhost:8000/health
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **WebApp Init**: `GET /api/webapp/init/{tg_id}`

### **Telegram Bot**
- Отправьте `/start` боту
- Должна появиться кнопка WebApp
- Проверьте команды `/help` и `/status`

### **WebApp тестирование**
- WebApp должен открываться у всех пользователей
- Данные должны сохраняться в SQLite БД
- Регистрация не должна повторяться

## 🧪 **Тестирование**

### **Запуск тестов**
```bash
# Базовые тесты
make test

# Тесты с покрытием
make test-cov

# Тесты в режиме наблюдения
make test-watch
```

### **Проверка кода**
```bash
# Линтинг
make lint

# Форматирование
make format
```

## 🗄️ **База данных**

### **SQLite - мини БД**
- ✅ **Автоматическое создание** при запуске
- ✅ **Локальное хранение** - не нужен облачный сервер
- ✅ **Производительность** - быстро для небольших данных
- ✅ **Простота** - один файл, легко бэкапить

### **Автоматическое создание**
База данных создается автоматически при первом запуске.

### **Сброс БД**
```bash
make db-reset
```

### **Проверка БД**
```bash
# Установить SQLite клиент
sqlite3 db.sqlite3

# Проверить таблицы
.tables

# Проверить пользователей
SELECT * FROM users;

# Проверить слоты
SELECT * FROM stocks;
```

## 🔧 **Отладка**

### **Логи**
- Все операции логируются в консоль
- Уровни: INFO, WARNING, ERROR
- Структурированный формат

### **Переменные окружения**
```bash
# Проверка текущих настроек
python -c "from config import settings; print(settings.dict())"
```

### **Проверка конфигурации**
```bash
# Проверка .env файла
cat .env

# Проверка переменных окружения
env | grep -E "(BOT_TOKEN|ADMIN_IDS|BACKEND_URL)"
```

## 🚨 **Частые проблемы**

### **1. "Bot token not configured"**
```bash
# Проверьте .env файл
cat .env | grep BOT_TOKEN

# Убедитесь, что файл загружается
python -c "from config import settings; print(settings.BOT_TOKEN)"
```

### **2. "Database error occurred"**
```bash
# Проверьте права на файл БД
ls -la db.sqlite3

# Сбросьте БД
make db-reset
```

### **3. "Admin system not configured"**
```bash
# Проверьте ADMIN_IDS в .env
cat .env | grep ADMIN_IDS

# Формат: ADMIN_IDS=123456789,987654321
```

### **4. WebApp не открывается у других пользователей**
```bash
# Проверьте CORS настройки в main.py
# Должно быть: allow_origins=["*"]

# Проверьте логи бэкенда на CORS ошибки
```

### **5. Пользователи не сохраняются**
```bash
# Проверьте права на запись в директорию
ls -la

# Проверьте логи бэкенда
# Убедитесь, что БД создана
```

## 📱 **Интеграция с фронтендом**

### **CORS настройки**
```python
# В main.py уже настроено правильно
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешаем все домены для WebApp
    allow_credentials=True,  # Разрешаем credentials для WebApp
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### **WebApp URL**
```env
# URL вашего фронтенда
WEBAPP_URL=https://frontend-delta-sandy-58.vercel.app
```

### **Новый эндпоинт для WebApp**
```bash
# Инициализация WebApp
GET /api/webapp/init/{tg_id}

# Регистрация пользователя
POST /api/register

# Получение профиля
GET /api/main/{tg_id}
```

## 🚀 **Deployment**

### **GitHub Codespaces**
```env
# .env для Codespaces
BOT_TOKEN=your_bot_token
ADMIN_IDS=your_telegram_id
BACKEND_URL=https://your-codespace-url
WEBAPP_URL=https://frontend-delta-sandy-58.vercel.app
```

### **Production настройки**
```env
# .env.production
DATABASE_URL=sqlite+aiosqlite:///db.sqlite3
ALLOWED_ORIGINS=https://yourdomain.com
BOT_TOKEN=your_production_bot_token
ADMIN_IDS=123456789,987654321
```

### **Docker Production**
```bash
# Сборка production образа
docker build -t hookah-api:prod .

# Запуск с production .env
docker run -p 8000:8000 --env-file .env.production hookah-api:prod
```

## 📝 **Changelog**

### **v2.1.0** - WebApp Fixes
- 🔒 **Исправлены CORS проблемы** - WebApp работает у всех пользователей
- 💾 **SQLite БД** - локальное хранение данных
- 📱 **Новый эндпоинт** `/api/webapp/init/{tg_id}`
- 🔄 **Персистентность данных** - пользователи не теряются

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

### **Полезные команды**
```bash
# Показать справку по командам
make help

# Настройка проекта
make setup

# Очистка временных файлов
make clean

# Проверка БД
sqlite3 db.sqlite3
```

### **Логи и отладка**
- Проверьте консоль на наличие ошибок
- Убедитесь, что все переменные окружения настроены
- Проверьте права доступа к файлам
- Проверьте CORS настройки для WebApp

---

**🎉 Поздравляем! Ваш бэкенд теперь современный, безопасный и надежный!**

**📱 WebApp будет работать у всех пользователей!**
