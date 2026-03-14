# config.py
"""
Модуль конфигурации проекта QRC Bot:
- централизованное логирование;
- загрузка YAML с данными оплат;
- безопасная обработка путей и ошибок;
- интеграция с settings.py и paths.py.
"""

import os
import sys
import yaml
import logging
from logging.handlers import RotatingFileHandler
from settings import settings
from paths import get_qrcbot_path


# ---------------------------------------------------------------------------
# 🧩 НАСТРОЙКА ЛОГИРОВАНИЯ
# ---------------------------------------------------------------------------

def setup_logging(log_name: str = "qrc_bot.log"):
    """Настраивает единое логирование для всех модулей."""
    log_dir = get_qrcbot_path("logs")
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, log_name)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # предотвращаем дублирование хэндлеров при повторных вызовах
    if not root_logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler = RotatingFileHandler(
            log_file, maxBytes=5_000_000, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)

        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

    logging.info("Логирование успешно настроено")


# ---------------------------------------------------------------------------
# 🧾 ЛОГГЕР ДЛЯ ПЛАТЕЖЕЙ
# ---------------------------------------------------------------------------

def setup_payment_logger():
    """Настраивает отдельный логгер для платежей."""
    payment_log_dir = get_qrcbot_path("logs")
    os.makedirs(payment_log_dir, exist_ok=True)
    
    payment_log_file = os.path.join(payment_log_dir, "payments.log")
    
    # Создаем отдельный логгер для платежей
    payment_logger = logging.getLogger('payment')
    payment_logger.setLevel(logging.INFO)
    
    # Предотвращаем дублирование хэндлеров
    if not payment_logger.handlers:
        payment_handler = RotatingFileHandler(
            payment_log_file, 
            maxBytes=5_000_000, 
            backupCount=5, 
            encoding="utf-8"
        )
        payment_handler.setFormatter(logging.Formatter('%(message)s'))
        payment_logger.addHandler(payment_handler)
        payment_logger.propagate = False

    return payment_logger

# Инициализируем логгер платежей при импорте модуля
payment_logger = setup_payment_logger()


# ---------------------------------------------------------------------------
# ⚙️  ЗАГРУЗКА YAML (payment_data.yaml)
# ---------------------------------------------------------------------------

def load_payment_data() -> dict:
    """
    Загружает файл payment_data.yaml.
    Путь берётся через paths.get_qrcbot_path().
    """
    logger = logging.getLogger()

    # 1. Определяем путь - используем только get_qrcbot_path
    yaml_file = get_qrcbot_path("payment_data.yaml")

    logger.info(f"Загрузка payment_data из: {yaml_file}")

    # 2. Проверяем существование
    if not os.path.exists(yaml_file):
        # Дополнительная проверка: ищем файл в текущей рабочей директории
        current_dir = os.getcwd()
        current_dir_file = os.path.join(current_dir, "payment_data.yaml")
        
        if os.path.exists(current_dir_file):
            logger.info(f"Файл найден в рабочей директории: {current_dir_file}")
            yaml_file = current_dir_file
        else:
            logger.error(f"Файл {yaml_file} не найден. Текущая рабочая директория: {current_dir}")
            try:
                logger.error(f"Файлы в директории: {os.listdir(current_dir)}")
            except Exception:
                pass
            raise ValueError(
                f"Файл {yaml_file} не найден. Проверь расположение файла."
            )

    # 3. Читаем YAML
    try:
        with open(yaml_file, "r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
            if not isinstance(data, dict):
                raise ValueError("Формат payment_data.yaml некорректен — ожидается словарь.")
            
            # Извлекаем payment_types из структуры
            if 'payment_types' in data:
                payment_types = data['payment_types']
                logger.info(f"Файл payment_data.yaml успешно загружен ({len(payment_types)} записей)")
                return payment_types
            else:
                # Если структура старого формата (без payment_types), возвращаем как есть
                logger.info(f"Файл payment_data.yaml успешно загружен ({len(data)} записей)")
                return data
                
    except yaml.YAMLError as e:
        logger.error(f"Ошибка чтения YAML {yaml_file}: {e}")
        raise


# ---------------------------------------------------------------------------
# 🧠 ДОПОЛНИТЕЛЬНЫЕ УТИЛИТЫ
# ---------------------------------------------------------------------------

def ensure_directories():
    """Создаёт служебные директории (logs, temp, db)"""
    dirs = [
        get_qrcbot_path("logs"),
        get_qrcbot_path("temp"),
        get_qrcbot_path("db"),
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
    logging.info("Все служебные директории проверены и созданы.")


# ---------------------------------------------------------------------------
# 🧾  ИНИЦИАЛИЗАЦИЯ ПРИ ИМПОРТЕ
# ---------------------------------------------------------------------------

setup_logging()
ensure_directories()

# Явный экспорт для импорта в других модулях
__all__ = ['load_payment_data', 'payment_logger', 'setup_logging', 'setup_payment_logger', 'ensure_directories']