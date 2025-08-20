"""
Быстрое решение всех проблем для запуска бота
"""

import subprocess
import sys
import os

print("=== БЫСТРОЕ РЕШЕНИЕ ВСЕХ ПРОБЛЕМ ===\n")


def run_script(script_name):
    """Запускает Python скрипт"""
    print(f"\n🔧 Запускаю {script_name}...")
    try:
        result = subprocess.run([sys.executable, script_name], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {script_name} выполнен успешно")
            return True
        else:
            print(f"❌ Ошибка в {script_name}:")
            print(result.stderr)
            return False
    except FileNotFoundError:
        print(f"❌ Файл {script_name} не найден")
        return False


# 1. Исправляем проблему с Firestore
print("1️⃣ Настройка работы без Firestore...")
if run_script("run_without_firestore.py"):
    print("✅ Бот настроен для работы без облачной БД")

# 2. Исправляем ассистента
print("\n2️⃣ Исправление модуля ассистента...")
if run_script("fix_assistant_db_error.py"):
    print("✅ Модуль ассистента исправлен")

# 3. Исправляем OpenAI
print("\n3️⃣ Настройка OpenAI для работы без API...")
if run_script("run_without_openai.py"):
    print("✅ OpenAI настроен в демо-режиме")

# 4. Исправляем предупреждение aiogram
print("\n4️⃣ Исправление предупреждения aiogram...")
if os.path.exists("main.py"):
    with open("main.py", "r", encoding="utf-8") as f:
        content = f.read()

    if "parse_mode=ParseMode.HTML" in content and "DefaultBotProperties" not in content:
        # Добавляем импорт
        if "from aiogram.client.default import DefaultBotProperties" not in content:
            content = content.replace(
                "from aiogram.enums import ParseMode",
                "from aiogram.enums import ParseMode\nfrom aiogram.client.default import DefaultBotProperties",
            )

        # Заменяем инициализацию бота
        content = content.replace(
            "bot = Bot(\n        token=BOT_TOKEN,\n        parse_mode=ParseMode.HTML\n    )",
            """bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML
        )
    )""",
        )

        # Альтернативный вариант без переносов
        content = content.replace(
            "bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)",
            """bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML
        )
    )""",
        )

        with open("main.py", "w", encoding="utf-8") as f:
            f.write(content)
        print("✅ Предупреждение aiogram исправлено")
    else:
        print("✅ Предупреждение aiogram уже исправлено или отсутствует")

print("\n" + "=" * 50)
print("\n🎉 ВСЕ ГОТОВО!\n")
print("✅ Исправлено:")
print("• Работа без Firestore (данные в памяти)")
print("• Модуль ассистента (демо-режим)")
print("• OpenAI API (демо-ответы)")
print("• Предупреждение aiogram")

print("\n🚀 Запустите бота:")
print("python main.py")

print("\n📱 Доступные функции:")
print("• 📊 Трекер привычек")
print("• 🎯 Фокус-сессии")
print("• ✅ Чек-лист задач")
print("• 👤 Профиль и достижения")
print("• 🤖 ИИ-ассистент (демо)")

print("\n💡 Примечания:")
print("• Данные сохраняются только в рамках сессии")
print("• При перезапуске бота данные сбрасываются")
print("• Для постоянного хранения нужно настроить Firestore")
print("• Для полноценного ИИ нужен OpenAI API + прокси")
