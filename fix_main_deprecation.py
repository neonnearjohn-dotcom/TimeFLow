"""
Исправление предупреждения о deprecated параметрах в main.py
"""

import os
import re

print("=== ИСПРАВЛЕНИЕ ПРЕДУПРЕЖДЕНИЯ AIOGRAM ===\n")

if not os.path.exists("main.py"):
    print("❌ Файл main.py не найден!")
    exit(1)

# Читаем текущий main.py
with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

# Создаем резервную копию
from datetime import datetime

backup_name = f"main_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
with open(backup_name, "w", encoding="utf-8") as f:
    f.write(content)
print(f"✅ Создана резервная копия: {backup_name}")

# Находим строку с Bot(
bot_pattern = r"bot = Bot\(\s*token=BOT_TOKEN,\s*parse_mode=ParseMode\.HTML\s*\)"
bot_match = re.search(bot_pattern, content, re.MULTILINE | re.DOTALL)

if bot_match:
    # Заменяем на новый формат
    old_code = bot_match.group(0)
    new_code = """bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML
        )
    )"""

    content = content.replace(old_code, new_code)
    print("✅ Обновлен код инициализации Bot")

    # Проверяем импорт DefaultBotProperties
    if "DefaultBotProperties" not in content:
        # Добавляем импорт
        import_line = "from aiogram.enums import ParseMode"
        new_import = "from aiogram.enums import ParseMode\nfrom aiogram.client.default import DefaultBotProperties"
        content = content.replace(import_line, new_import)
        print("✅ Добавлен импорт DefaultBotProperties")
else:
    print("⚠️ Не найден старый формат Bot(). Возможно, уже исправлено.")

# Сохраняем исправленный файл
with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("\n✅ Файл main.py обновлен!")
print("Предупреждение должно исчезнуть при следующем запуске.")
