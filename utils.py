# utils.py

import logging
from telegram import Bot
from db import get_channels

async def check_subscription(bot: Bot, user_id):
    try:
        for username in get_channels():
            member = await bot.get_chat_member(f"@{username}", user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        return True
    except Exception as e:
        logging.error(f"Ошибка при проверке подписки: {e}")
        return False
