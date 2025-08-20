#!/usr/bin/env python3
"""
Скрипт для автоматического исправления handlers/assistant_onboarding.py
Добавляет ленивую инициализацию БД
"""

import re
import os
import shutil
from datetime import datetime


def fix_assistant_onboarding():
    file_path = "handlers/assistant_onboarding.py"

    # Создаем резервную копию
    backup_path = f"{file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(file_path, backup_path)
    print(f"✅ Создана резервная копия: {backup_path}")

    # Читаем файл
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Заменяем глобальную инициализацию БД
    old_db_init = """# Инициализация базы данных
db = FirestoreDB()
profile_db = AssistantProfileDB(db.db)"""

    new_db_init = """# Глобальные переменные для БД (будут инициализированы при первом использовании)
_db: Optional[FirestoreDB] = None
_profile_db: Optional[AssistantProfileDB] = None

def get_db():
    \"\"\"Получить или создать экземпляр БД (ленивая инициализация)\"\"\"
    global _db, _profile_db
    if _db is None:
        _db = FirestoreDB()
        if _db.is_connected():
            _profile_db = AssistantProfileDB(_db.get_client())
        else:
            logger.error("Не удалось подключиться к БД")
            _profile_db = None
    return _db, _profile_db"""

    # Выполняем замену
    content = content.replace(old_db_init, new_db_init)

    # 2. Добавляем проверку БД в функции
    functions_to_update = [
        "start_onboarding_command",
        "start_ai_onboarding",
        "restart_onboarding_confirmed",
        "process_category_choice",
        "process_select_answer",
        "process_text_input",
        "process_number_input",
        "process_date_input",
        "process_list_input",
        "process_quick_date",
        "process_quick_number",
        "show_plan_settings",
        "show_current_plan",
        "finalize_onboarding",
    ]

    # Код для вставки в начало функций
    db_check_code = """    # Получаем БД
    _, profile_db = get_db()
    if not profile_db:
        await callback.answer("⚠️ База данных временно недоступна", show_alert=True)
        return
    """

    db_check_code_message = """    # Получаем БД
    _, profile_db = get_db()
    if not profile_db:
        await message.answer("⚠️ База данных временно недоступна")
        return
    """

    for func_name in functions_to_update:
        # Находим функцию
        func_pattern = rf'(async def {func_name}\([^)]+\):\s*\n\s*"""[^"]*""")\n'

        def replacer(match):
            func_def = match.group(1)
            # Определяем тип функции по параметрам
            if "message:" in func_def:
                return func_def + "\n" + db_check_code_message + "\n"
            else:
                return func_def + "\n" + db_check_code + "\n"

        content = re.sub(func_pattern, replacer, content)

    # 3. Добавляем импорт Optional если его нет
    if "from typing import" in content and "Optional" not in content:
        content = content.replace(
            "from typing import Dict, Any, List", "from typing import Dict, Any, List, Optional"
        )

    # 4. Сохраняем исправленный файл
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    print("✅ Файл успешно исправлен!")
    print("\nЧто было сделано:")
    print("1. Заменена глобальная инициализация БД на ленивую")
    print("2. Добавлена функция get_db()")
    print("3. В каждую функцию добавлена проверка БД")
    print("\n⚠️ Рекомендуется проверить файл вручную!")


if __name__ == "__main__":
    print("🔧 Исправление handlers/assistant_onboarding.py\n")

    if not os.path.exists("handlers/assistant_onboarding.py"):
        print("❌ Файл handlers/assistant_onboarding.py не найден!")
        print("Запустите скрипт из корневой папки проекта")
        exit(1)

    response = input("Начать исправление? (y/n): ")
    if response.lower() == "y":
        fix_assistant_onboarding()
    else:
        print("Отменено")
