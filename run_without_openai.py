"""
Скрипт для запуска бота без модуля OpenAI
"""
import os
import shutil
from datetime import datetime

print("=== НАСТРОЙКА БОТА БЕЗ OPENAI ===\n")

# 1. Создаем упрощенный utils/openai_api.py
openai_stub = '''"""
Заглушка для OpenAI API (работа без прокси)
"""
import logging

logger = logging.getLogger(__name__)

class OpenAIAssistant:
    """Заглушка ассистента для работы без OpenAI"""
    
    def __init__(self):
        self.is_configured = False
        logger.info("OpenAI Assistant работает в демо-режиме")
    
    async def send_message(self, message, context=None, scenario=None, max_tokens=500):
        """Возвращает демо-ответы"""
        demo_responses = {
            'plan_day': """📅 **План на день**
                
Утро (9:00-12:00):
• ✅ Выполнить важные задачи
• ☕ Перерыв 15 минут
• 📧 Проверить почту

День (12:00-17:00):
• 🍽 Обед
• 🎯 Фокус-сессии
• 📞 Встречи

Вечер (17:00-21:00):
• 🏃 Активность
• 📚 Обучение
• 🧘 Отдых""",
            
            'motivation': """💪 **Мотивация дня**
                
Ты способен на большее, чем думаешь!

🌟 Каждый шаг приближает к цели.
🎯 Фокусируйся на главном.
💫 Верь в себя!

Действуй! 🚀""",
            
            'default': """🤖 **Ассистент в демо-режиме**
                
Для полной функциональности нужно настроить OpenAI API.

А пока используйте другие функции бота:
• 📊 Трекер привычек
• 🎯 Фокус-сессии
• ✅ Чек-лист задач
• 👤 Профиль и достижения"""
        }
        
        response = demo_responses.get(scenario, demo_responses['default'])
        
        return {
            'success': True,
            'response': response,
            'is_demo': True
        }

# Глобальный экземпляр
assistant = OpenAIAssistant()
'''

# Сохраняем заглушку
print("1. Создаю заглушку для OpenAI...")
os.makedirs("utils", exist_ok=True)

# Делаем резервную копию если есть оригинал
if os.path.exists("utils/openai_api.py"):
    backup_name = f"utils/openai_api_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
    shutil.copy("utils/openai_api.py", backup_name)
    print(f"   ✅ Создана резервная копия: {backup_name}")

with open("utils/openai_api.py", "w", encoding="utf-8") as f:
    f.write(openai_stub)
print("   ✅ Создана заглушка utils/openai_api.py")

# 2. Информация для пользователя
print("\n✅ Готово! Теперь бот будет работать без OpenAI.")
print("\n📋 Доступные функции:")
print("• 📊 Трекер привычек - отслеживание полезных и вредных привычек")
print("• 🎯 Фокус-сессии - техника Помодоро для продуктивности")
print("• ✅ Чек-лист - управление задачами по матрице Эйзенхауэра")
print("• 👤 Профиль - очки, достижения, статистика")
print("• 🤖 ИИ-ассистент - демо-ответы без API")

print("\n🚀 Запустите бота:")
print("python main.py")

print("\n💡 Чтобы включить полноценного ИИ-ассистента позже:")
print("1. Получите OpenAI API ключ")
print("2. Настройте прокси для России")
print("3. Запустите: python fix_openai_proxy.py")