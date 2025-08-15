"""
Диагностика проблем с обработчиками ассистента
"""
import os

def check_main_py():
    """Проверяет main.py"""
    print("📄 Проверка main.py...\n")
    
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Проверяем импорт
    if 'from handlers import' in content and 'assistant' in content:
        if '# , assistant' in content or '#, assistant' in content:
            print("❌ Модуль assistant закомментирован в импорте!")
            return False
        else:
            print("✅ Импорт assistant найден")
    else:
        print("❌ Импорт assistant не найден!")
        return False
    
    # Проверяем регистрацию роутера
    if 'dp.include_router(assistant.router)' in content:
        if '# dp.include_router(assistant.router)' in content:
            print("❌ Роутер assistant закомментирован!")
            return False
        else:
            print("✅ Роутер assistant зарегистрирован")
    else:
        print("❌ Регистрация роутера assistant не найдена!")
        return False
    
    return True


def check_menu_handler():
    """Проверяет обработчик в menu.py"""
    print("\n📄 Проверка handlers/menu.py...\n")
    
    if not os.path.exists('handlers/menu.py'):
        print("❌ Файл handlers/menu.py не найден!")
        return False
    
    with open('handlers/menu.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Проверяем обработчик
    if '🤖 ИИ-ассистент' in content:
        print("✅ Обработчик для '🤖 ИИ-ассистент' найден")
        
        # Проверяем, вызывается ли assistant.handle_assistant_menu
        if 'assistant.handle_assistant_menu' in content:
            print("✅ Вызов assistant.handle_assistant_menu найден")
        else:
            print("❌ Вызов assistant.handle_assistant_menu НЕ найден!")
            return False
    else:
        print("❌ Обработчик для '🤖 ИИ-ассистент' НЕ найден!")
        return False
    
    return True


def check_keyboard():
    """Проверяет клавиатуру"""
    print("\n📄 Проверка keyboards/main_menu.py...\n")
    
    with open('keyboards/main_menu.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    if '🤖 ИИ-ассистент' in content:
        print("✅ Кнопка '🤖 ИИ-ассистент' найдена в клавиатуре")
    else:
        print("❌ Кнопка '🤖 ИИ-ассистент' НЕ найдена в клавиатуре!")
        return False
    
    return True


def fix_menu_handler():
    """Исправляет обработчик меню"""
    print("\n🔧 Исправление handlers/menu.py...")
    
    correct_content = '''"""
Обработчики для кнопок главного меню
"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import StateFilter
from aiogram.fsm.state import default_state
from aiogram.fsm.context import FSMContext

# Создаем роутер для обработчиков меню
router = Router()


@router.message(F.text == "📊 Трекеры", StateFilter(default_state))
async def handle_trackers(message: Message):
    """Обработчик кнопки Трекеры"""
    from handlers import trackers
    await trackers.handle_trackers_menu(message)


@router.message(F.text == "✅ Чек-лист", StateFilter(default_state))
async def handle_checklist(message: Message):
    """Обработчик кнопки Чек-лист"""
    from handlers import checklist
    await checklist.handle_checklist_menu(message)


@router.message(F.text == "🎯 Фокус", StateFilter(default_state))
async def handle_focus(message: Message):
    """Обработчик кнопки Фокус"""
    from handlers import focus
    await focus.handle_focus_menu(message)


@router.message(F.text == "🤖 ИИ-ассистент", StateFilter(default_state))
async def handle_assistant(message: Message, state: FSMContext):
    """Обработчик кнопки ИИ-ассистент"""
    from handlers import assistant
    await assistant.handle_assistant_menu(message, state)


@router.message(F.text == "👤 Профиль", StateFilter(default_state))
async def handle_profile(message: Message):
    """Обработчик кнопки Профиль"""
    from handlers import profile
    await profile.handle_profile_menu(message)


@router.message(F.text == "⚙️ Настройки", StateFilter(default_state))
async def handle_settings(message: Message):
    """Обработчик кнопки Настройки"""
    await message.answer(
        "⚙️ <b>Настройки</b>\\n\\n"
        "🚧 Этот раздел находится в разработке.\\n\\n"
        "Скоро здесь появятся:\\n"
        "• 🔔 Настройка уведомлений\\n"
        "• 🎨 Выбор темы оформления\\n"
        "• 🌐 Смена языка\\n"
        "• 📊 Экспорт данных\\n"
        "• 🔐 Приватность\\n\\n"
        "А пока используй другие разделы бота! 😊",
        parse_mode="HTML"
    )
'''
    
    with open('handlers/menu.py', 'w', encoding='utf-8') as f:
        f.write(correct_content)
    
    print("✅ Файл handlers/menu.py исправлен")


def fix_main_py():
    """Исправляет main.py"""
    print("\n🔧 Исправление main.py...")
    
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Раскомментируем assistant
    content = content.replace('# , assistant', ', assistant')
    content = content.replace('#, assistant', ', assistant')
    content = content.replace('# dp.include_router(assistant.router)', 'dp.include_router(assistant.router)')
    
    with open('main.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ main.py исправлен")


def main():
    """Главная функция диагностики"""
    print("🔍 Диагностика модуля ассистента\n")
    
    issues = []
    
    # Проверяем main.py
    if not check_main_py():
        issues.append("main.py")
    
    # Проверяем menu.py
    if not check_menu_handler():
        issues.append("menu.py")
    
    # Проверяем клавиатуру
    if not check_keyboard():
        issues.append("keyboard")
    
    if issues:
        print(f"\n❌ Найдены проблемы в: {', '.join(issues)}")
        
        response = input("\nИсправить автоматически? (y/n): ")
        if response.lower() == 'y':
            if "main.py" in issues:
                fix_main_py()
            if "menu.py" in issues:
                fix_menu_handler()
            
            print("\n✅ Все исправлено! Перезапустите бота.")
    else:
        print("\n✅ Все обработчики настроены правильно!")
        print("\nЕсли ассистент все еще не работает, проверьте:")
        print("1. Перезапустили ли вы бота после изменений")
        print("2. Нет ли ошибок в консоли при запуске")


if __name__ == "__main__":
    main()