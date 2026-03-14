import io
import json
import logging
import uuid
from datetime import datetime
import qrcode
from config import load_payment_data, payment_logger
from database import conn, insert_payment
from settings import settings

logger = logging.getLogger(__name__)


def format_amount(amount: float) -> str:
    """Форматирует сумму в рубли и копейки."""
    rubles = int(amount)
    kopecks = round((amount - rubles) * 100)
    if kopecks >= 100:
        rubles += 1
        kopecks -= 100
    return f"{rubles} руб. {kopecks:02d} коп."


def generate_payment_string(amount: float, payment_data: dict) -> str:
    """
    Генерирует строку для QR-кода по ГОСТ 56042-2014.
    """
    required_keys = [
        'payee_name', 'checking_account', 'bik', 'correspondent_account',
        'kpp', 'inn', 'personal_account', 'payment_purpose', 'cbc', 'oktmo'
    ]
    for key in required_keys:
        if key not in payment_data:
            raise ValueError(f"Отсутствует обязательное поле: {key}")
    
    amount_in_kopecks = int(round(amount * 100))

    # Формируем строку БЕЗ пробелов вокруг разделителей |
    payment_string = (
        f"ST00012|"
        f"Name={payment_data['payee_name']}|"
        f"PersonalAcc={payment_data['checking_account']}|"
        f"BankName=УФК по Республике Саха (Якутия)|"
        f"BIC={payment_data['bik']}|"
        f"CorrespAcc={payment_data['correspondent_account']}|"
        f"KPP={payment_data['kpp']}|"
        f"PayeeINN={payment_data['inn']}|"
        f"PersAcc={payment_data['personal_account']}|"
        f"Sum={amount_in_kopecks}|"
        f"Purpose={payment_data['payment_purpose']}|"
        f"CBC={payment_data['cbc']}|"
        f"OKTMO={payment_data['oktmo']}"
    )

    # --- Статус плательщика ---
    # .strip() гарантирует удаление любых пробелов из YAML
    status_value = str(payment_data.get('status', '24')).strip()
    
    # Имя поля: приоритет YAML -> .env -> стандарт PayerStatus
    status_field = (
        str(payment_data.get('status_field_name', '')).strip() or
        settings.STATUS_FIELD_NAME or
        "PayerStatus"
    )
    
    payment_string += f"|{status_field}={status_value}"

    # --- UIN (опционально) ---
    uin = str(payment_data.get('uin', '0')).strip()
    if uin and uin != '0':
        payment_string += f"|UIN={uin}"

    return payment_string


def generate_qr_code_data(amount: float, payment_purpose: str, user_id: int) -> dict:
    """Генерирует QR-код, сохраняет запись в БД и возвращает словарь с данными."""
    logger.info(f"Генерация QR: сумма={amount}, назначение={payment_purpose}, user={user_id}")
    
    # 1. Загружаем данные платежей
    payment_data = load_payment_data()
    if payment_purpose not in payment_data:
        raise ValueError(f"Назначение платежа '{payment_purpose}' не найдено в payment_data.yaml")

    details = payment_data[payment_purpose]

    # 2. Формируем уникальный ID
    user_id_str = str(user_id)
    masked_user_id = f"{user_id_str[:3]}***{user_id_str[-3:]}"
    qr_code_id = f"{masked_user_id}_{uuid.uuid4()}"

    # 3. Генерируем платежную строку
    payment_string = generate_payment_string(amount, details)

    # 4. Создаём QR-код
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4
    )
    qr.add_data(payment_string)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer)
    buffer.seek(0)

    # 5. Сохраняем в БД
    current_timestamp = datetime.now().isoformat()
    success = insert_payment(conn, current_timestamp, qr_code_id, amount,
                             payment_purpose, user_id)
    if success is None:
        logger.error(f"Не удалось записать платеж {qr_code_id} в БД")

    # 6. Логируем платёж
    log_data = {
        "timestamp": current_timestamp,
        "qr_code_id": qr_code_id,
        "amount": amount,
        "payment_purpose": payment_purpose,
        "user_id": user_id,
    }
    payment_logger.info(json.dumps(log_data))

    # 7. Формируем подпись
    formatted_amount = format_amount(amount)
    caption = f"QR-код для {payment_purpose} на сумму {formatted_amount}.\nID QR-кода: {qr_code_id}"

    return {
        "buffer": buffer,
        "caption": caption,
        "qr_code_id": qr_code_id
    }