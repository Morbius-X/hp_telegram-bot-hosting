import os
import asyncio
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Bot configuration from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID", "-1002864117186")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")

# Book configuration
BOOK_START_IDS = {
    1: 208, 2: 226, 3: 245, 4: 268, 5: 306, 6: 345, 7: 376,
}

BOOK_NUM_CHAPTERS = {
    1: 17, 2: 18, 3: 22, 4: 37, 5: 38, 6: 30, 7: 37,
}

BOOK_TITLES = [
    "Harry Potter and the Philosopher's Stone",
    "Harry Potter and the Chamber of Secrets", 
    "Harry Potter and the Prisoner of Azkaban",
    "Harry Potter and the Goblet of Fire",
    "Harry Potter and the Order of the Phoenix",
    "Harry Potter and the Half-Blood Prince",
    "Harry Potter and the Deathly Hallows"
]

# Global storage for deletion tasks
deletion_tasks = {}

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message handler."""
    welcome_text = (
        "🎭 *Welcome to the Enchanted Library* 🎭\n\n"
        "✨ Greetings, fellow seeker of magical adventures! ✨\n\n"
        "You have discovered a mystical portal to the wizarding world, where ancient tales of courage, "
        "friendship, and extraordinary magic await your eager ears. Within these sacred digital halls, "
        "the complete chronicles of the Boy Who Lived whisper their secrets through the ethereal realm of sound.\n\n"
        "🔮 *Your magical journey begins with a single choice...* 🔮\n\n"
        "Shall we venture forth into the spellbinding world of Hogwarts?"
    )
    
    keyboard = [[InlineKeyboardButton("📚 Browse Magical Books", callback_data="show_books")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

async def books_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Books command handler."""
    await show_book_selection(update.message.chat_id, context.bot, None)

async def show_book_selection(chat_id, bot, message_to_edit=None):
    """Display book selection menu."""
    keyboard = [
        [InlineKeyboardButton(title, callback_data=str(i+1))]
        for i, title in enumerate(BOOK_TITLES)
    ]
    keyboard.append([InlineKeyboardButton("🏠 Return to Main Hall", callback_data="main_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    books_text = (
        "📖 *The Sacred Collection Awaits* 📖\n\n"
        "🪄 Choose your desired tome from the enchanted archives below. Each book contains hours of "
        "masterfully narrated adventure, ready to transport you directly into the heart of the wizarding world.\n\n"
        "✨ *Select your magical journey:*"
    )
    
    if message_to_edit:
        await message_to_edit.edit_text(books_text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await bot.send_message(chat_id=chat_id, text=books_text, reply_markup=reply_markup, parse_mode="Markdown")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "show_books":
        await show_book_selection(query.message.chat_id, context.bot, query.message)
    elif query.data == "main_menu":
        welcome_text = (
            "🎭 *Welcome Back to the Enchanted Library* 🎭\n\n"
            "✨ The magical portal remains open for your return! ✨\n\n"
            "Your journey through the wizarding world continues. Whether you seek to revisit familiar tales "
            "or explore new magical adventures, the choice remains yours to make.\n\n"
            "🔮 *Ready to embark on another magical quest?* 🔮"
        )
        keyboard = [[InlineKeyboardButton("📚 Browse Magical Books", callback_data="show_books")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await handle_book_selection(query, context)

async def handle_book_selection(query, context):
    """Handle book selection and file forwarding."""
    try:
        book_number = int(query.data)
        book_title = BOOK_TITLES[book_number - 1]
        
        start_id = BOOK_START_IDS.get(book_number)
        num_chapters = BOOK_NUM_CHAPTERS.get(book_number)
        
        if start_id is None or num_chapters is None:
            await query.edit_message_text(
                f"📜 Apologies, but the magical tome *{book_title}* appears to be temporarily unavailable in our archives.", 
                parse_mode="Markdown"
            )
            return
        
        # Show loading message
        await query.edit_message_text(
            f"🪄 *Summoning the audio scrolls for {book_title}*...\n\n✨ Please wait while we gather the magical chapters from the ethereal realm.", 
            parse_mode="Markdown"
        )
        
        # Forward messages
        audio_message_ids = list(range(start_id, start_id + num_chapters))
        sent_message_ids = []
        failed_forwards = 0
        
        for message_id in audio_message_ids:
            try:
                forwarded = await context.bot.forward_message(
                    chat_id=query.message.chat_id,
                    from_chat_id=CHANNEL_ID,
                    message_id=message_id
                )
                sent_message_ids.append(forwarded.message_id)
                await asyncio.sleep(0.25)  # Rate limiting
            except Exception as e:
                logger.error(f"Failed to forward message {message_id}: {e}")
                failed_forwards += 1
        
        if not sent_message_ids:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"🚫 The magical protection spells prevented us from delivering *{book_title}*. Please try again later.",
                parse_mode="Markdown"
            )
            return
        
        # Send deletion warning
        warning = (
            "❗️ **Notice:** These files will be deleted in 10 minutes **due to copyright**.\n"
            "📌 Please **forward** and **download them now**."
        )
        
        if failed_forwards > 0:
            warning += f"\n\n⚠️ Note: {failed_forwards} file(s) could not be sent."
        
        keyboard = [[InlineKeyboardButton("📚 Choose Another Book", callback_data="show_books")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        warning_message = await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=warning,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        sent_message_ids.append(warning_message.message_id)
        
        # Schedule deletion
        task_key = f"{query.message.chat_id}_{warning_message.message_id}"
        task = asyncio.create_task(
            delete_messages_after_delay(context.bot, query.message.chat_id, sent_message_ids, book_title, 600)
        )
        deletion_tasks[task_key] = task
        
        logger.info(f"Scheduled deletion of {len(sent_message_ids)} messages for chat {query.message.chat_id}")
        
    except Exception as e:
        logger.error(f"Error in handle_book_selection: {e}")
        await query.edit_message_text("❌ An error occurred. Please try again.")

async def delete_messages_after_delay(bot, chat_id, message_ids, book_title, delay_seconds):
    """Delete messages after specified delay."""
    try:
        await asyncio.sleep(delay_seconds)
        
        deleted_count = 0
        for message_id in message_ids:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
                deleted_count += 1
                await asyncio.sleep(0.1)  # Small delay between deletions
            except Exception as e:
                logger.warning(f"Failed to delete message {message_id}: {e}")
        
        # Send completion notification
        if deleted_count > 0:
            notification = f"🗑️ The magical archives have reclaimed {deleted_count} audio scroll(s) for *{book_title}* as scheduled."
            keyboard = [[InlineKeyboardButton("📚 Browse More Books", callback_data="show_books")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await bot.send_message(
                chat_id=chat_id,
                text=notification,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        
        logger.info(f"Successfully deleted {deleted_count} messages for chat {chat_id}")
        
    except asyncio.CancelledError:
        logger.info(f"Deletion task cancelled for chat {chat_id}")
    except Exception as e:
        logger.error(f"Error in deletion task for chat {chat_id}: {e}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors."""
    logger.error(f"Update {update} caused error {context.error}")

def main():
    """Start the bot."""
    try:
        logger.info("Starting Enchanted Library bot...")
        
        # Create application
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("books", books_command))
        application.add_handler(CallbackQueryHandler(button_callback))
        application.add_error_handler(error_handler)
        
        # Start polling
        logger.info("Bot is now running!")
        application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise

if __name__ == "__main__":
    main()
