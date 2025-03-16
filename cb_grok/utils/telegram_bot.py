import telegram
import logging
from telegram.request import HTTPXRequest  # Используем правильный класс

class TelegramBot:
    def __init__(self, token, chat_id, timeout=20):
        # Используем HTTPXRequest для настройки тайм-аута
        self.bot = telegram.Bot(token=token, request=HTTPXRequest(read_timeout=timeout))
        self.chat_id = chat_id
        self.logger = logging.getLogger(__name__)

    async def send_message(self, message):
        """Отправка сообщения в Telegram с обработкой исключений."""
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=message)
        except telegram.error.TimedOut:
            self.logger.error("Тайм-аут при отправке сообщения в Telegram")
        except telegram.error.TelegramError as e:
            self.logger.error(f"Ошибка Telegram: {e}")