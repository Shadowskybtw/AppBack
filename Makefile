.PHONY: help install run test clean lint format

help: ## Показать справку по командам
	@echo "Доступные команды:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Установить зависимости
	pip install -r requirements.txt

install-dev: ## Установить зависимости для разработки
	pip install -r requirements.txt
	pip install -e .

run: ## Запустить FastAPI сервер
	uvicorn main:app --reload --host 0.0.0.0 --port 8000

run-bot: ## Запустить Telegram бота
	python bot_handler.py

test: ## Запустить тесты
	pytest tests/ -v

test-cov: ## Запустить тесты с покрытием
	pytest tests/ --cov=. --cov-report=html --cov-report=term

test-watch: ## Запустить тесты в режиме наблюдения
	pytest tests/ -f -v

clean: ## Очистить временные файлы
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage

lint: ## Проверить код линтером
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

format: ## Форматировать код
	black . --line-length=127
	isort .

db-reset: ## Сбросить базу данных
	rm -f db.sqlite3
	@echo "База данных сброшена"

setup: ## Настройка проекта
	@echo "Настройка проекта..."
	@if [ ! -f .env ]; then \
		echo "Создание .env файла..."; \
		cp env.example .env; \
		echo "Отредактируйте .env файл с вашими настройками"; \
	else \
		echo ".env файл уже существует"; \
	fi
	@echo "Установка зависимостей..."
	$(MAKE) install
	@echo "Настройка завершена!"

dev: ## Запуск в режиме разработки
	@echo "Запуск в режиме разработки..."
	@echo "FastAPI: http://localhost:8000"
	@echo "Docs: http://localhost:8000/docs"
	@echo "Health: http://localhost:8000/health"
	$(MAKE) run

docker-build: ## Собрать Docker образ
	docker build -t hookah-api .

docker-run: ## Запустить в Docker
	docker run -p 8000:8000 --env-file .env hookah-api

docker-compose-up: ## Запустить с Docker Compose
	docker-compose up -d

docker-compose-down: ## Остановить Docker Compose
	docker-compose down
