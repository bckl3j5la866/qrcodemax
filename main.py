# max_main.py
import asyncio
import logging
import signal
import sys
from typing import Dict, List, Tuple

from maxapi import Bot, Dispatcher
from maxapi.types import (
    BotStarted,
    MessageCreated,
    MessageCallback,
    Attachment,
    InputMediaBuffer,
)
from maxapi.types.attachments.attachment import ButtonsPayload
from maxapi.types.attachments.buttons import CallbackButton

from settings import settings
from config import setup_logging
from database import conn, close_connection
from qr_utils import generate_qr_code_data

# Настройка логирования
setup_logging()
logger = logging.getLogger(__name__)

# Проверка токена
if not settings.BOT_TOKEN:
    logger.error("BOT_TOKEN не задан! Проверьте .env файл.")
    sys.exit(1)

# Проверка соединения с БД
if conn is None:
    logger.error("Не удалось подключиться к БД")
    sys.exit(1)

bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()

# Хранилище состояний пользователей
user_states: Dict[int, Dict] = {}

# Сопоставление payload кнопок с полными названиями
PAYLOAD_TO_PURPOSE = {
    "payment_hotmeal": "Оплата горячего питания",
    "payment_org": "Организационный взнос за участие в конференции и выставке",
    "payment_print": "Оплата полиграфических и иных услуг",
    "payment_donate": "Добровольное пожертвование",
}

# Клавиатура главного меню (одно место — нет дублирования)
MAIN_MENU_BUTTONS = [
    [("Горячее питание", "payment_hotmeal")],
    [("Организационный взнос", "payment_org")],
    [("Полиграфические услуги", "payment_print")],
    [("Добровольное пожертвование", "payment_donate")],
]


# ---------------------------------------------------------------------------
# 🧩 ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ---------------------------------------------------------------------------

def create_keyboard_attachments(
    buttons_rows: List[List[Tuple[str, str]]],
) -> List[Attachment]:
    """Создаёт inline-клавиатуру из списка строк кнопок."""
    buttons = []
    for row in buttons_rows:
        row_buttons = []
        for text, payload in row:
            row_buttons.append(CallbackButton(text=text, payload=payload))
        buttons.append(row_buttons)

    buttons_payload = ButtonsPayload(buttons=buttons)
    attachment = Attachment(type="inline_keyboard", payload=buttons_payload)
    return [attachment]


def get_main_keyboard() -> List[Attachment]:
    """Возвращает клавиатуру главного меню."""
    return create_keyboard_attachments(MAIN_MENU_BUTTONS)


# ---------------------------------------------------------------------------
# 🤖 ХЭНДЛЕРЫ БОТА
# ---------------------------------------------------------------------------

@dp.bot_started()
async def handle_bot_started(event: BotStarted):
    """Приветственное сообщение при первом запуске бота."""
    await event.bot.send_message(
        chat_id=event.chat.chat_id,
        text="Добро пожаловать! Выберите назначение платежа:",
        attachments=get_main_keyboard(),
    )


@dp.message_callback()
async def handle_callback(event: MessageCallback):
    """Обработка нажатий на inline-кнопки."""
    user_id = event.from_user.user_id
    chat_id = event.chat.chat_id
    payload = event.callback.payload

    if payload.startswith("payment_"):
        user_states[user_id] = {"payment_type": payload}
        cancel_keyboard = create_keyboard_attachments([[("Отмена", "cancel")]])
        await event.bot.send_message(
            chat_id=chat_id,
            text="Введите сумму:",
            attachments=cancel_keyboard,
        )

    elif payload == "cancel":
        user_states.pop(user_id, None)
        await event.bot.send_message(
            chat_id=chat_id,
            text="Действие отменено. Выберите назначение платежа:",
            attachments=get_main_keyboard(),
        )


@dp.message_created()
async def handle_message(event: MessageCreated):
    """Обработка текстовых сообщений."""
    user_id = event.from_user.user_id
    chat_id = event.chat.chat_id
    text = event.message.body.text

    if not text:
        return

    # Команда /start
    if text == "/start":
        user_states.pop(user_id, None)
        await event.message.answer(
            text="Выберите назначение платежа:",
            attachments=get_main_keyboard(),
        )
        return

    # Если пользователь ввёл сумму после выбора платежа
    if user_id in user_states and "payment_type" in user_states[user_id]:
        # Валидация суммы
        try:
            amount = float(text.replace(",", "."))
            if amount <= 0:
                raise ValueError
            if amount > 500_000:
                await event.message.answer(
                    "Сумма не может превышать 500 000 руб. Введите другую сумму:"
                )
                return
        except ValueError:
            await event.message.answer(
                "Некорректная сумма. Введите число больше 0:"
            )
            return

        payment_type = user_states[user_id]["payment_type"]
        full_purpose = PAYLOAD_TO_PURPOSE.get(payment_type)

        if not full_purpose:
            await event.message.answer(
                text="Ошибка: неизвестный тип платежа. Выберите назначение платежа:",
                attachments=get_main_keyboard(),
            )
            user_states.pop(user_id, None)
            return

        try:
            # Генерация QR и запись в БД
            qr_data = generate_qr_code_data(
                amount=amount,
                payment_purpose=full_purpose,
                user_id=user_id,
            )

            # Отправка QR-кода через встроенный механизм maxapi
            image_bytes = qr_data["buffer"].getvalue()

            media = InputMediaBuffer(
                buffer=image_bytes,
                filename="qrcode.png",
            )

            await event.bot.send_message(
                chat_id=chat_id,
                text=qr_data["caption"],
                attachments=[media],
            )

            # Очищаем состояние пользователя
            del user_states[user_id]

            # Показываем меню снова
            await event.bot.send_message(
                chat_id=chat_id,
                text="Выберите назначение платежа:",
                attachments=get_main_keyboard(),
            )

        except Exception:
            logger.exception("Ошибка при генерации или отправке QR")
            user_states.pop(user_id, None)
            await event.message.answer(
                text="Произошла ошибка. Попробуйте снова. Выберите назначение платежа:",
                attachments=get_main_keyboard(),
            )
    else:
        # Непонятное сообщение — показываем меню
        await event.message.answer(
            text="Выберите назначение платежа:",
            attachments=get_main_keyboard(),
        )


# ---------------------------------------------------------------------------
# 🚀 ЗАПУСК И ЗАВЕРШЕНИЕ
# ---------------------------------------------------------------------------

async def wait_for_shutdown_signal():
    """Ожидает сигналы SIGINT или SIGTERM."""
    loop = asyncio.get_running_loop()
    shutdown_event = asyncio.Event()

    def signal_handler():
        logger.info("Получен сигнал завершения")
        shutdown_event.set()

    try:
        loop.add_signal_handler(signal.SIGINT, signal_handler)
        loop.add_signal_handler(signal.SIGTERM, signal_handler)
    except NotImplementedError:
        logger.warning(
            "Обработка сигналов не поддерживается. Используйте Ctrl+C."
        )
        # Windows: ждём бесконечно — KeyboardInterrupt прервёт
        await asyncio.Event().wait()

    await shutdown_event.wait()


async def main():
    logger.info("Запуск MAX бота в режиме polling...")

    try:
        polling_task = asyncio.create_task(dp.start_polling(bot))
        signal_task = asyncio.create_task(wait_for_shutdown_signal())

        done, pending = await asyncio.wait(
            [polling_task, signal_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    finally:
        logger.info("Закрытие ресурсов...")
        if hasattr(bot, "session") and bot.session and not bot.session.closed:
            await bot.session.close()
        close_connection(conn)
        await asyncio.sleep(0.25)
        logger.info("Бот остановлен.")


if __name__ == "__main__":
    # Фикс для Windows — предотвращает SSL ошибки при закрытии
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Принудительная остановка по Ctrl+C")
        close_connection(conn)
