# database.py
import sqlite3
import logging
import os
from paths import get_qrcbot_path

# Настройка логирования
logger = logging.getLogger(__name__)

def create_connection():
    """
    Создает соединение с базой данных SQLite.
    Возвращает объект соединения или None в случае ошибки.
    """
    try:
        # ИСПРАВЛЕННАЯ СТРОКА: используем os.path.join для создания пути
        db_path = get_qrcbot_path(os.path.join("db", "bot_data.db"))
        conn = sqlite3.connect(db_path, check_same_thread=False)
        logger.info("Подключение к SQLite DB успешно. База данных: %s", db_path)
        return conn
    except sqlite3.Error as e:
        logger.error(f"Ошибка подключения к SQLite DB: {e}")
        return None

def create_tables(conn):
    """
    Создает таблицы в базе данных, если они не существуют.
    """
    sql_create_payments_table = """
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        qr_code_id TEXT NOT NULL UNIQUE,
        amount REAL NOT NULL,
        payment_purpose TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        status TEXT DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    try:
        c = conn.cursor()
        c.execute(sql_create_payments_table)
        conn.commit()
        logger.info("Таблицы успешно созданы.")
    except sqlite3.Error as e:
        logger.error(f"Ошибка при создании таблиц: {e}")
        raise

def insert_payment(conn, timestamp, qr_code_id, amount, payment_purpose, user_id):
    """
    Вставляет запись о новом платеже в базу данных.
    Возвращает ID вставленной записи или None в случае ошибки.
    """
    sql = '''INSERT INTO payments(timestamp, qr_code_id, amount, payment_purpose, user_id)
             VALUES(?,?,?,?,?)'''
    cur = conn.cursor()
    try:
        cur.execute(sql, (timestamp, qr_code_id, amount, payment_purpose, user_id))
        conn.commit()
        logger.info(f"Платеж {qr_code_id} добавлен в БД.")
        return cur.lastrowid
    except sqlite3.IntegrityError:
        logger.error(f"QR-код {qr_code_id} уже существует в БД.")
        return None
    except sqlite3.Error as e:
        logger.error(f"Ошибка при добавлении платежа в БД: {e}")
        conn.rollback()
        return None

def close_connection(conn):
    """
    Закрывает соединение с базой данных.
    """
    if conn:
        conn.close()
        logger.info("Соединение с SQLite DB закрыто.")

# Инициализация базы данных при импорте модуля
conn = create_connection()
if conn is not None:
    create_tables(conn)
else:
    logger.error("Не удалось создать соединение с базой данных.")