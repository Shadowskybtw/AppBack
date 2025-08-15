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

# URL вашего backend'а
BACKEND_URL=https://your-backend-domain.com

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

### **Telegram Bot**
- Отправьте `/start` боту
- Должна появиться кнопка WebApp
- Проверьте команды `/help` и `/status`

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

### **Автоматическое создание**
База данных создается автоматически при первом запуске.

### **Сброс БД**
```bash
make db-reset
```

### **Миграции**
При изменении моделей:
1. Остановите приложение
2. Удалите `db.sqlite3`
3. Перезапустите (БД создастся заново)

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

### **4. CORS ошибки**
```bash
# Проверьте ALLOWED_ORIGINS в .env
cat .env | grep ALLOWED_ORIGINS

# Для разработки: ALLOWED_ORIGINS=*
```

## 📱 **Интеграция с фронтендом**

### **CORS настройки**
```env
# Разрешить все домены (разработка)
ALLOWED_ORIGINS=*

# Ограничить конкретными доменами (продакшн)
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

### **WebApp URL**
```env
# URL вашего фронтенда
WEBAPP_URL=https://frontend-delta-sandy-58.vercel.app
```

## 🚀 **Deployment**

### **Production настройки**
```env
# .env.production
DATABASE_URL=postgresql+asyncpg://user:pass@host/db
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

## 📞 **Поддержка**

### **Полезные команды**
```bash
# Показать справку по командам
make help

# Настройка проекта
make setup

# Очистка временных файлов
make clean
```

### **Логи и отладка**
- Проверьте консоль на наличие ошибок
- Убедитесь, что все переменные окружения настроены
- Проверьте права доступа к файлам

---

**🎉 Поздравляем! Ваш бэкенд теперь современный, безопасный и надежный!**
