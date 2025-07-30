from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import requests
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
BACKEND_URL = "https://refactored-cod-v6ww469vp657fwqpw-8000.app.github.dev/"  # Заменить на домен своего backend

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    try:
        # Обращение к уже готовому эндпоинту FastAPI
        response = requests.get(f"{BACKEND_URL}/send_webapp_button/{chat_id}")
        print("Кнопка отправлена:", response.json())
    except Exception as e:
        print("Ошибка при отправке кнопки:", e)
        await update.message.reply_text("Ошибка при отправке WebApp-кнопки.")

def run_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()

if __name__ == "__main__":
    run_bot()