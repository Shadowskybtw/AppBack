from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import requests
import logging
from config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BotError(Exception):
    """Custom exception for bot operations"""
    pass


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    logger.info(f"Start command from user {user.id} in chat {chat_id}")
    
    if not settings.BOT_TOKEN:
        logger.error("Bot token not configured")
        await update.message.reply_text("Бот не настроен. Обратитесь к администратору.")
        return
    
    if not settings.WEBAPP_URL:
        logger.error("WebApp URL not configured")
        await update.message.reply_text("WebApp URL не настроен. Обратитесь к администратору.")
        return
    
    try:
        # Call FastAPI endpoint to send WebApp button
        response = requests.post(
            f"{settings.BACKEND_URL}/send_webapp_button/{chat_id}",
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info(f"WebApp button sent successfully to chat {chat_id}")
            await update.message.reply_text("✅ Кнопка WebApp отправлена!")
        else:
            logger.error(f"Failed to send WebApp button: {response.status_code} - {response.text}")
            await update.message.reply_text("❌ Ошибка при отправке кнопки WebApp. Попробуйте позже.")
            
    except requests.RequestException as e:
        logger.error(f"Request error while sending WebApp button: {e}")
        await update.message.reply_text("❌ Ошибка связи с сервером. Попробуйте позже.")
    except Exception as e:
        logger.error(f"Unexpected error in start command: {e}")
        await update.message.reply_text("❌ Произошла неожиданная ошибка. Попробуйте позже.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
🤖 **Доступные команды:**

/start - Открыть приложение WebApp
/help - Показать эту справку
/status - Проверить статус бота

📱 **WebApp** - это веб-приложение для управления слотами кальянов.

❓ **Нужна помощь?** Обратитесь к администратору.
    """
    
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command"""
    try:
        # Check backend health
        response = requests.get(f"{settings.BACKEND_URL}/health", timeout=5)
        
        if response.status_code == 200:
            status_data = response.json()
            status_text = f"""
✅ **Статус системы:**

🖥️ **Backend**: Работает
⏰ **Время**: {status_data.get('timestamp', 'N/A')}
🤖 **Бот**: Работает
            """
        else:
            status_text = """
❌ **Статус системы:**

🖥️ **Backend**: Ошибка
🤖 **Бот**: Работает
            """
            
    except Exception as e:
        logger.error(f"Error checking status: {e}")
        status_text = """
❌ **Статус системы:**

🖥️ **Backend**: Недоступен
🤖 **Бот**: Работает
        """
    
    await update.message.reply_text(status_text, parse_mode='Markdown')


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors in bot updates"""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Произошла ошибка при обработке команды. Попробуйте позже."
        )


def run_bot():
    """Initialize and run the bot"""
    if not settings.BOT_TOKEN:
        logger.error("Bot token not configured. Cannot start bot.")
        return
    
    try:
        # Build bot application
        app = ApplicationBuilder().token(settings.BOT_TOKEN).build()
        
        # Add command handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("status", status_command))
        
        # Add error handler
        app.add_error_handler(error_handler)
        
        logger.info("Bot started successfully")
        logger.info(f"Bot username: @{app.bot.username}")
        
        # Start polling
        app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise BotError(f"Bot startup failed: {e}")


if __name__ == "__main__":
    try:
        run_bot()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        exit(1)