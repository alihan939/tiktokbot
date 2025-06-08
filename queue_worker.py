# queue_worker.py

import os
import asyncio
import logging
import re
from telegram import InputFile
from config import OUTPUT_PATH, TIKTOK_URL_PATTERN
from db import increment_user_downloads, get_user_language
from translations import translations

async def process_video(update, context):
    user_id = update.message.from_user.id
    lang = get_user_language(user_id)
    url = update.message.text.strip()

    if not re.match(TIKTOK_URL_PATTERN, url):
        await update.message.reply_text(translations[lang]['invalid_link'])
        return

    await update.message.reply_text(translations[lang]['downloading'])

    try:
        if os.path.exists(OUTPUT_PATH):
            os.remove(OUTPUT_PATH)

        process = await asyncio.create_subprocess_exec(
            'yt-dlp', '-f', 'mp4', '-o', OUTPUT_PATH, url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logging.error(f"yt-dlp error: {stderr.decode()}")
            await update.message.reply_text(translations[lang]['error'])
            return

        increment_user_downloads(user_id)

        with open(OUTPUT_PATH, 'rb') as f:
            await update.message.reply_video(video=InputFile(f), caption="🎬")

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await update.message.reply_text(translations[lang]['error'])
    finally:
        if os.path.exists(OUTPUT_PATH):
            os.remove(OUTPUT_PATH)

async def task_worker(app, task_queue):
    while True:
        update, context = await task_queue.get()
        await process_video(update, context)
        task_queue.task_done()
