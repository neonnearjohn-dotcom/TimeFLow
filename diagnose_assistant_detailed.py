"""
Детальная диагностика проблемы с модулем ассистента
"""

import os
import sys
import importlib.util


def check_file_exists(filepath):
    """Проверяет существование файла"""
    return os.path.exists(filepath)


def check_import(module_path):
    """Проверяет возможность импорта модуля"""
    try:
        spec = importlib.util.spec_from_file_location("test_module", module_path)
        if spec is None:
            return False, "Не удалось загрузить спецификацию модуля"

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return True, "OK"
    except Exception as e:
        return False, str(e)


print("=== ДИАГНОСТИКА МОДУЛЯ АССИСТЕНТА ===\n")

# 1. Проверка файлов
print("1. Проверка наличия файлов:")
files_to_check = [
    ("handlers/assistant.py", "Обработчики ассистента"),
    ("keyboards/assistant.py", "Клавиатуры ассистента"),
    ("states/assistant.py", "Состояния FSM"),
    ("utils/openai_api.py", "API для OpenAI"),
    ("database/assistant_db.py", "База данных ассистента"),
]

missing_files = []
for filepath, description in files_to_check:
    exists = check_file_exists(filepath)
    status = "✅" if exists else "❌"
    print(f"{status} {filepath} - {description}")
    if not exists:
        missing_files.append(filepath)

# 2. Проверка импортов
print("\n2. Проверка импортов:")
if check_file_exists("handlers/assistant.py"):
    success, error = check_import("handlers/assistant.py")
    if success:
        print("✅ handlers/assistant.py импортируется успешно")
    else:
        print(f"❌ Ошибка импорта handlers/assistant.py: {error}")

# 3. Проверка содержимого handlers/menu.py
print("\n3. Проверка обработчика в handlers/menu.py:")
if check_file_exists("handlers/menu.py"):
    with open("handlers/menu.py", "r", encoding="utf-8") as f:
        content = f.read()

    # Проверяем наличие обработчика для кнопки ассистента
    if '"🤖 ИИ-ассистент"' in content or "'🤖 ИИ-ассистент'" in content:
        print("✅ Кнопка '🤖 ИИ-ассистент' найдена в menu.py")

        # Проверяем, есть ли обработчик
        if "handle_assistant" in content:
            print("✅ Функция handle_assistant найдена")
        else:
            print("❌ Функция handle_assistant НЕ найдена")
    else:
        print("❌ Кнопка '🤖 ИИ-ассистент' НЕ найдена в menu.py")

# 4. Проверка регистрации роутера в main.py
print("\n4. Проверка регистрации в main.py:")
if check_file_exists("main.py"):
    with open("main.py", "r", encoding="utf-8") as f:
        content = f.read()

    # Проверяем импорт
    if "from handlers import" in content and "assistant" in content:
        print("✅ Модуль assistant импортируется в main.py")
    else:
        print("❌ Модуль assistant НЕ импортируется в main.py")

    # Проверяем регистрацию роутера
    if "assistant.router" in content:
        print("✅ Роутер assistant.router регистрируется")
    else:
        print("❌ Роутер assistant.router НЕ регистрируется")

# 5. Проверка структуры handlers/assistant.py
print("\n5. Анализ handlers/assistant.py:")
if check_file_exists("handlers/assistant.py"):
    with open("handlers/assistant.py", "r", encoding="utf-8") as f:
        content = f.read()

    # Проверяем наличие роутера
    if "router = Router()" in content:
        print("✅ Роутер создан")
    else:
        print("❌ Роутер НЕ создан")

    # Проверяем наличие обработчиков
    handlers = []
    if '@router.message(F.text == "🤖 ИИ-ассистент")' in content:
        handlers.append("Обработчик кнопки из главного меню")
    if "handle_assistant_menu" in content:
        handlers.append("Функция handle_assistant_menu")
    if "@router.callback_query" in content:
        handlers.append("Callback обработчики")

    if handlers:
        print("✅ Найдены обработчики:")
        for h in handlers:
            print(f"   - {h}")
    else:
        print("❌ Обработчики НЕ найдены")

# 6. Рекомендации
print("\n=== РЕКОМЕНДАЦИИ ===")
if missing_files:
    print("\n❌ Отсутствуют файлы:")
    for f in missing_files:
        print(f"   - {f}")
    print("\nСоздайте эти файлы из предыдущих диалогов.")

print("\n💡 Для исправления проблемы:")
print("1. Убедитесь, что все файлы созданы")
print("2. Проверьте, что в handlers/menu.py есть обработчик для кнопки")
print("3. Проверьте, что в main.py подключен роутер ассистента")
print("4. Перезапустите бота")

# Проверка версии aiogram
print("\n=== ВЕРСИИ БИБЛИОТЕК ===")
try:
    import aiogram

    print(f"aiogram: {aiogram.__version__}")
except:
    print("aiogram: не установлен")

try:
    import openai

    print(f"openai: {openai.__version__}")
except:
    print("openai: не установлен (это нормально)")
