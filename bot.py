# bot.py

import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from config import BOT_TOKEN, MAX_QUEUE_SIZE, NUM_WORKERS, CHANNEL_USERNAME, SUPPORT_URL, ADMIN_ID
from db import init_db, set_user_language, get_user_language, get_user_downloads, add_channel, remove_channel, get_channels
from translations import translations
from utils import check_subscription
from queue_worker import task_worker

logging.basicConfig(level=logging.INFO)

task_queue = asyncio.Queue()

# === Команды ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🇷🇺 Русский", callback_data='lang_ru')],
        [InlineKeyboardButton("🇬🇧 English", callback_data='lang_en')],
        [InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data='lang_uz')],
        [InlineKeyboardButton("🇹🇲 Türkmençe", callback_data='lang_tm')]
    ]
    await update.message.reply_text(translations['ru']['start'], reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("Укажите username канала.")
        return

    username = context.args[0].lstrip('@')
    add_channel(username)
    await update.message.reply_text(f"✅ Канал @{username} добавлен.")

async def admin_remove_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("Укажите username канала.")
        return

    username = context.args[0].lstrip('@')
    remove_channel(username)
    await update.message.reply_text(f"❌ Канал @{username} удалён.")

async def admin_list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    channels = get_channels()
    if not channels:
        await update.message.reply_text("📭 Список каналов пуст.")
    else:
        await update.message.reply_text("📢 Список каналов:\n" + "\n".join([f"@{c}" for c in channels]))

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.split('_')[1]
    set_user_language(query.from_user.id, lang)
    text = translations[lang]['lang_selected'] + "\n\n" + translations[lang]['send_link']
    keyboard = [
        [translations[lang]['send_link']],
        [translations[lang]['change_language']],
        [translations[lang]['my_stats_button']],
        [translations[lang]['support']]
    ]
    await query.message.reply_text(text, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    lang = get_user_language(user_id)
    keyboard = [
        [InlineKeyboardButton("🇷🇺 Русский", callback_data='lang_ru')],
        [InlineKeyboardButton("🇬🇧 English", callback_data='lang_en')],
        [InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data='lang_uz')],
        [InlineKeyboardButton("🇹🇲 Türkmençe", callback_data='lang_tm')]
    ]
    await update.message.reply_text(translations[lang]['lang_command'], reply_markup=InlineKeyboardMarkup(keyboard))

async def my_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    lang = get_user_language(user_id)
    count = get_user_downloads(user_id)
    await update.message.reply_text(translations[lang]['download_count'].format(count=count))

# === Обработка ссылок и кнопок ===
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    lang = get_user_language(user_id)
    text = update.message.text.strip()

    if text == translations[lang]['send_link']:
        await update.message.reply_text(translations[lang]['send_link'], reply_markup=InlineKeyboardMarkup(keyboard))
        return


    if text == translations[lang]['change_language']:
        await change_language(update, context)
        return


    if text == translations[lang]['my_stats_button']:
        await my_stats(update, context)
        return
    
    
    
    if text == translations[lang]['support']:
        keyboard = [
            [InlineKeyboardButton(translations[lang]['support'], url=f'https://t.me/{SUPPORT_URL}')]
        ]
        await update.message.reply_text(translations[lang]['info_for_support'], reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return


    if not await check_subscription(context.bot, user_id):
        channels = get_channels()
        keyboard = [
            [InlineKeyboardButton(f"🔗 @{ch}", url=f"https://t.me/{ch}")] for ch in channels
        ]
        keyboard.append([InlineKeyboardButton(translations[lang]['check_subscription'], callback_data='check_subscription')])
        await update.message.reply_text(translations[lang]['not_subscribed'], reply_markup=InlineKeyboardMarkup(keyboard))

        await update.message.reply_text(translations[lang]['not_subscribed'], reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if task_queue.qsize() >= MAX_QUEUE_SIZE:
        await update.message.reply_text(translations[lang]['too_many_requests'])
        return

    await update.message.reply_text(translations[lang]['queue'])
    await task_queue.put((update, context))

async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    lang = get_user_language(user_id)

    if await check_subscription(context.bot, user_id):
        await query.answer(translations[lang]['check_sub_success'], show_alert=True)
        keyboard = [
            [translations[lang]['send_link']],
            [translations[lang]['change_language']],
            [translations[lang]['my_stats_button']],
            [translations[lang]['support']]
        ]
        await query.message.reply_text(translations[lang]['check_sub_success'] + "\n\n" + translations[lang]['send_link'],
                                       reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    else:
        await query.answer(translations[lang]['check_sub_fail'], show_alert=True)

# === Запуск ===
def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("my", my_stats))
    app.add_handler(CommandHandler("language", change_language))
    app.add_handler(CommandHandler("addchannel", admin_add_channel))
    app.add_handler(CommandHandler("removechannel", admin_remove_channel))
    app.add_handler(CommandHandler("listchannels", admin_list_channels))

    app.add_handler(CallbackQueryHandler(set_language, pattern='lang_'))
    app.add_handler(CallbackQueryHandler(check_subscription_callback, pattern='check_subscription'))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_video))

    async def post_init(app):
        for _ in range(NUM_WORKERS):
            asyncio.create_task(task_worker(app, task_queue))

    app.post_init = post_init
    app.run_polling()

if __name__ == "__main__":
    main()
