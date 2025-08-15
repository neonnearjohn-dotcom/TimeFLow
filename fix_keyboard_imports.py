"""
Тестирование импортов и создания клавиатур
"""

def test_keyboards():
    """Проверить, что все клавиатуры импортируются и создаются без ошибок"""
    
    print("🔍 Тестирование клавиатур...\n")
    
    errors = []
    success = []
    
    # Тест главного меню
    try:
        from keyboards.main_menu import main_menu_kb
        kb = main_menu_kb()
        success.append("✅ main_menu.py - OK")
    except ImportError as e:
        errors.append(f"❌ main_menu.py - {e}")
    except Exception as e:
        errors.append(f"❌ main_menu.py - {e}")
    
    # Тест трекера
    try:
        from keyboards.tracker import (
            tracker_menu_kb,
            habits_menu_kb,
            bad_habits_menu_kb
        )
        kb1 = tracker_menu_kb()
        kb2 = habits_menu_kb([])
        kb3 = bad_habits_menu_kb([])
        success.append("✅ tracker.py - OK")
    except ImportError as e:
        errors.append(f"❌ tracker.py - {e}")
    except Exception as e:
        errors.append(f"❌ tracker.py - {e}")
    
    # Тест фокуса
    try:
        from keyboards.focus import (
            focus_menu_kb,
            session_control_kb,
            settings_menu_kb
        )
        kb1 = focus_menu_kb()
        kb2 = session_control_kb(paused=False)
        kb3 = settings_menu_kb()
        success.append("✅ focus.py - OK")
    except ImportError as e:
        errors.append(f"❌ focus.py - {e}")
    except Exception as e:
        errors.append(f"❌ focus.py - {e}")
    
    # Тест чек-листа
    try:
        from keyboards.checklist import (
            checklist_menu_kb,
            priority_selection_kb,
            tasks_list_kb
        )
        kb1 = checklist_menu_kb()
        kb2 = priority_selection_kb()
        kb3 = tasks_list_kb([])
        success.append("✅ checklist.py - OK")
    except ImportError as e:
        errors.append(f"❌ checklist.py - {e}")
    except Exception as e:
        errors.append(f"❌ checklist.py - {e}")
    
    # Тест профиля
    try:
        from keyboards.profile import (
            profile_menu_kb,
            achievements_menu_kb,
            points_history_kb
        )
        kb1 = profile_menu_kb()
        kb2 = achievements_menu_kb()
        kb3 = points_history_kb()
        success.append("✅ profile.py - OK")
    except ImportError as e:
        errors.append(f"❌ profile.py - {e}")
    except Exception as e:
        errors.append(f"❌ profile.py - {e}")
    
    # Тест ассистента
    try:
        from keyboards.assistant import (
            assistant_menu_kb,
            assistant_chat_kb,
            continue_chat_kb
        )
        kb1 = assistant_menu_kb()
        kb2 = assistant_chat_kb()
        kb3 = continue_chat_kb()
        success.append("✅ assistant.py - OK")
    except ImportError as e:
        errors.append(f"❌ assistant.py - {e}")
    except Exception as e:
        errors.append(f"❌ assistant.py - {e}")
    
    # Вывод результатов
    print("Успешно:")
    for s in success:
        print(s)
    
    if errors:
        print("\nОшибки:")
        for e in errors:
            print(e)
        
        print("\n⚠️ Исправьте ошибки в указанных файлах")
        print("Добавьте импорты в начало файла:")
        print("from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton")
        print("from aiogram.utils.keyboard import InlineKeyboardBuilder")
    else:
        print("\n✅ Все клавиатуры работают корректно!")
    
    return len(errors) == 0


if __name__ == "__main__":
    import sys
    
    # Проверяем версию aiogram
    try:
        import aiogram
        version = aiogram.__version__
        print(f"📦 Версия aiogram: {version}")
        
        if not version.startswith('3'):
            print("⚠️ Требуется aiogram версии 3.x.x")
            print("Установите: pip install aiogram==3.4.1")
            sys.exit(1)
    except ImportError:
        print("❌ aiogram не установлен")
        print("Установите: pip install aiogram==3.4.1")
        sys.exit(1)
    
    print()
    
    # Тестируем клавиатуры
    if test_keyboards():
        sys.exit(0)
    else:
        sys.exit(1)