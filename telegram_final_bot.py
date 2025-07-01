import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import asyncio
import logging
from datetime import datetime, timedelta

# Bot token and channel ID - using environment variables for security
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Will be set in Railway/Render dashboard
CHANNEL_ID = os.getenv("CHANNEL_ID", "-1002864117186")  # Your channel ID with fallback

# Validate required environment variables
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")

# Define starting message IDs and chapter counts
BOOK_START_IDS = {
    1: 208,   # Replace with actual ID for Philosopher's Stone
    2: 226,  # Replace with actual ID for Chamber of Secrets
    3: 245,  # Adjust accordingly
    4: 268,
    5: 306,
    6: 345,
    7: 376,
}

BOOK_NUM_CHAPTERS = {
    1: 17,
    2: 18,
    3: 22,
    4: 37,
    5: 38,
    6: 30,
    7: 37,
}

# Book titles
BOOK_TITLES = [
    "Harry Potter and the Philosopher's Stone",
    "Harry Potter and the Chamber of Secrets",
    "Harry Potter and the Prisoner of Azkaban",
    "Harry Potter and the Goblet of Fire",
    "Harry Potter and the Order of the Phoenix",
    "Harry Potter and the Half-Blood Prince",
    "Harry Potter and the Deathly Hallows"
]

# Global variable to store deletion tasks
deletion_tasks = {}

# Set up logging with better formatting for production
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command with welcome message."""
    welcome_message = (
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

    await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode="Markdown")

async def books_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /books command."""
    await show_book_selection(update.message.chat_id, context.bot, None)

async def show_book_selection(chat_id, bot, message_to_edit=None):
    """Display the book selection menu."""
    keyboard = [
        [InlineKeyboardButton(title, callback_data=str(i+1))]
        for i, title in enumerate(BOOK_TITLES)
    ]
    # Add back to main menu option
    keyboard.append([InlineKeyboardButton("🏠 Return to Main Hall", callback_data="main_menu")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    books_message = (
        "📖 *The Sacred Collection Awaits* 📖\n\n"
        "🪄 Choose your desired tome from the enchanted archives below. Each book contains hours of "
        "masterfully narrated adventure, ready to transport you directly into the heart of the wizarding world.\n\n"
        "✨ *Select your magical journey:*"
    )

    if message_to_edit:
        await message_to_edit.edit_text(books_message, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await bot.send_message(chat_id=chat_id, text=books_message, reply_markup=reply_markup, parse_mode="Markdown")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()

    # Handle different callback types
    if query.data == "show_books":
        await show_book_selection(query.message.chat_id, context.bot, query.message)
    elif query.data == "main_menu":
        welcome_message = (
            "🎭 *Welcome Back to the Enchanted Library* 🎭\n\n"
            "✨ The magical portal remains open for your return! ✨\n\n"
            "Your journey through the wizarding world continues. Whether you seek to revisit familiar tales "
            "or explore new magical adventures, the choice remains yours to make.\n\n"
            "🔮 *Ready to embark on another magical quest?* 🔮"
        )

        keyboard = [[InlineKeyboardButton("📚 Browse Magical Books", callback_data="show_books")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(welcome_message, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        # Handle book selection
        await handle_book_selection(query, context)

async def handle_book_selection(query, context):
    """Handle book selection and file forwarding."""
    book_number = int(query.data)
    book_title = BOOK_TITLES[book_number - 1]

    # Get the message ID range for the selected book
    start_id = BOOK_START_IDS.get(book_number)
    num_chapters = BOOK_NUM_CHAPTERS.get(book_number)
    if start_id is None or num_chapters is None:
        await query.edit_message_text(f"📜 Apologies, but the magical tome *{book_title}* appears to be temporarily unavailable in our archives.", parse_mode="Markdown")
        return

    audio_message_ids = list(range(start_id, start_id + num_chapters))

    # Inform user that files are being sent
    await query.edit_message_text(f"🪄 *Summoning the audio scrolls for {book_title}*...\n\n✨ Please wait while we gather the magical chapters from the ethereal realm.", parse_mode="Markdown")

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
            await asyncio.sleep(0.25)  # Delay to avoid rate limits
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

    # Send deletion warning with navigation
    warning = (
        "❗️ **Notice:** These files will be deleted in 10 minutes **due to copyright**.\n"
        "📌 Please **forward** and **download them now**."
    )

    if failed_forwards > 0:
        warning += f"\n\n⚠️ Note: {failed_forwards} file(s) could not be sent."

    # Add navigation button to the warning message
    keyboard = [[InlineKeyboardButton("📚 Choose Another Book", callback_data="show_books")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    warning_message = await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=warning,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    sent_message_ids.append(warning_message.message_id)

    # Log the scheduled deletion
    deletion_time = datetime.now() + timedelta(minutes=10)
    logger.info(f"Scheduling deletion of {len(sent_message_ids)} messages at {deletion_time} for chat {query.message.chat_id}")

    # Create deletion task key
    task_key = f"{query.message.chat_id}_{warning_message.message_id}"

    # Schedule deletion using both job queue and asyncio task for redundancy
    deletion_scheduled = False

    # Try job queue first
    try:
        if context.job_queue:
            context.job_queue.run_once(
                delete_messages_job,
                600,  # 10 minutes in seconds
                data={
                    "chat_id": query.message.chat_id,
                    "message_ids": sent_message_ids,
                    "book_title": book_title,
                    "task_key": task_key
                },
                name=f"delete_messages_{task_key}"
            )
            deletion_scheduled = True
            logger.info(f"Successfully scheduled deletion job using job queue for chat {query.message.chat_id}")
    except Exception as e:
        logger.error(f"Failed to schedule deletion job via job queue: {e}")

    # If job queue fails or is unavailable, use asyncio task as backup
    if not deletion_scheduled:
        try:
            # Create asyncio task for deletion
            task = asyncio.create_task(
                delete_messages_asyncio(
                    context.bot,
                    query.message.chat_id,
                    sent_message_ids,
                    book_title,
                    600  # 10 minutes in seconds
                )
            )
            deletion_tasks[task_key] = task
            deletion_scheduled = True
            logger.info(f"Successfully scheduled deletion using asyncio task for chat {query.message.chat_id}")
        except Exception as e:
            logger.error(f"Failed to schedule deletion via asyncio: {e}")

    # If both methods fail, notify user
    if not deletion_scheduled:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="⚠️ Warning: Auto-deletion could not be scheduled. Please delete the files manually after downloading."
        )

async def delete_messages_job(context: ContextTypes.DEFAULT_TYPE):
    """Delete forwarded messages and warning via job queue."""
    job = context.job
    chat_id = job.data["chat_id"]
    message_ids = job.data["message_ids"]
    book_title = job.data.get("book_title", "Unknown Book")
    task_key = job.data.get("task_key", "unknown")

    logger.info(f"Job queue deletion started for chat {chat_id} with {len(message_ids)} messages")

    # Cancel asyncio task if it exists
    if task_key in deletion_tasks:
        deletion_tasks[task_key].cancel()
        del deletion_tasks[task_key]
        logger.info(f"Cancelled redundant asyncio task for {task_key}")

    await perform_deletion(context.bot, chat_id, message_ids, book_title)

async def delete_messages_asyncio(bot, chat_id, message_ids, book_title, delay_seconds):
    """Delete forwarded messages and warning via asyncio task."""
    logger.info(f"Asyncio deletion task started for chat {chat_id}, waiting {delay_seconds} seconds")

    try:
        await asyncio.sleep(delay_seconds)
        logger.info(f"Asyncio deletion executing for chat {chat_id} with {len(message_ids)} messages")
        await perform_deletion(bot, chat_id, message_ids, book_title)
    except asyncio.CancelledError:
        logger.info(f"Asyncio deletion task cancelled for chat {chat_id}")
    except Exception as e:
        logger.error(f"Asyncio deletion task failed for chat {chat_id}: {e}")

async def perform_deletion(bot, chat_id, message_ids, book_title):
    """Perform the actual deletion of messages."""
    deleted_count = 0
    failed_count = 0

    for message_id in message_ids:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
            deleted_count += 1
            logger.debug(f"Successfully deleted message {message_id}")
            # Small delay between deletions to avoid rate limits
            await asyncio.sleep(0.1)
        except Exception as e:
            failed_count += 1
            logger.warning(f"Failed to delete message {message_id}: {e}")

    logger.info(f"Deletion completed for chat {chat_id}: {deleted_count} deleted, {failed_count} failed")

    # Send notification about deletion completion with navigation option
    try:
        if deleted_count > 0:
            notification = f"🗑️ The magical archives have reclaimed {deleted_count} audio scroll(s) for *{book_title}* as scheduled."
            if failed_count > 0:
                notification += f" ({failed_count} scrolls could not be reclaimed)"

            keyboard = [[InlineKeyboardButton("📚 Browse More Books", callback_data="show_books")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await bot.send_message(
                chat_id=chat_id,
                text=notification,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
    except Exception as e:
        logger.error(f"Failed to send deletion notification: {e}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors."""
    logger.error(f"Update {update} caused error {context.error}")

def main():
    """Run the bot."""
    try:
        # Build application with better error handling
        application = Application.builder().token(BOT_TOKEN).build()

        # Verify job queue is available
        if application.job_queue is None:
            logger.warning("Job queue is not available. Using asyncio tasks as fallback.")
        else:
            logger.info("Job queue initialized successfully")

        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("books", books_command))
        application.add_handler(CallbackQueryHandler(button_callback))
        application.add_error_handler(error_handler)

        logger.info("Starting Enchanted Library bot...")
        
        # Use polling mode for simplicity and reliability
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )

    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise

    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise

if __name__ == "__main__":
    main()
