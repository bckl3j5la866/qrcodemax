# paths.py

import os

def get_qrcbot_path(relative_path=""):
    """Возвращает абсолютный путь к папке QRCodeMax (настраивается через QRCODE_MAX_HOME)"""
    base_dir = os.getenv("QRCODE_MAX_HOME")
    if not base_dir:
        base_dir = os.path.join(os.path.expanduser("~"), "QRCodeMax")

    # Создаём базовую директорию, если не существует
    if not os.path.exists(base_dir):
        os.makedirs(base_dir, exist_ok=True)
        print(f"Создана папка: {base_dir}")

    if not relative_path:
        return base_dir

    # Формируем полный путь
    full_path = os.path.join(base_dir, relative_path)

    # Создаём все родительские директории, если это файл
    dir_path = os.path.dirname(full_path) if os.path.splitext(relative_path)[1] else full_path
    if dir_path and not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)
        print(f"Создана директория: {dir_path}")

    return full_path