"""
Обработчики для онбординга ИИ-ассистента с полной логикой
"""
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timezone
import logging
import asyncio

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from utils.plan_generator import generate_plan
from handlers.assistant_plan import show_plan_preview
from aiogram.fsm.state import State, StatesGroup

from handlers.assistant_plan import PlanPreviewStates, show_plan_preview

# Импорт базы данных и состояний
from database.firestore_db import FirestoreDB
from database.assistant_profile_db import AssistantProfileDB
from states.assistant_onboarding import AssistantOnboardingStates
from keyboards.main_menu import get_main_menu_keyboard

# Создаем роутер
router = Router()
logger = logging.getLogger(__name__)

_db: Optional[FirestoreDB] = None
_profile_db: Optional[AssistantProfileDB] = None

def get_db():
    """Получить или создать экземпляр БД (ленивая инициализация)"""
    global _db, _profile_db
    if _db is None:
        try:
            _db = FirestoreDB()
            # Проверяем, что у БД есть клиент
            if _db.db is not None:
                _profile_db = AssistantProfileDB(_db.db)
            else:
                logger.error("Не удалось получить клиент Firestore")
                _profile_db = None
        except Exception as e:
            logger.error(f"Ошибка инициализации БД: {e}")
            _db = None
            _profile_db = None
    return _db, _profile_db

# Загружаем вопросы из JSON
def load_questions() -> Dict[str, Any]:
    """Загружает вопросы онбординга из JSON файла"""
    try:
        json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'onboarding_questions.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки вопросов: {e}")
        return {"categories": {}, "constraints_questions": {"general": []}}

# Загружаем вопросы при старте
QUESTIONS_DATA = load_questions()                                                   

logger.info(f"Загружено категорий: {len(QUESTIONS_DATA.get('categories', {}))}")
logger.info(f"Категории: {list(QUESTIONS_DATA.get('categories', {}).keys())}")

@router.message(Command("onboarding"))
async def start_onboarding_command(message: Message, state: FSMContext):
    """Обработчик команды /onboarding"""
    # Получаем БД
    _, profile_db = get_db()
    if not profile_db:
        await message.answer("⚠️ База данных временно недоступна")
        return
    
    await state.clear()
    
    # Проверяем существующий профиль
    profile = await profile_db.get_profile(message.from_user.id)
    
    if profile and profile.onboarding.completed:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Настроить заново", callback_data="onb_restart_confirmed")],
            [InlineKeyboardButton(text="📊 Мой план", callback_data="ai_show_plan")],
            [InlineKeyboardButton(text="◀️ В меню", callback_data="assistant_menu")]
        ])
        
        await message.answer(
            "✅ <b>У вас уже есть настроенный профиль!</b>\n\n"
            f"Категория: {QUESTIONS_DATA['categories'].get(profile.active_category, {}).get('emoji', '')} "
            f"{QUESTIONS_DATA['categories'].get(profile.active_category, {}).get('title', '')}\n\n"
            "Что вы хотите сделать?",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "🎯 <b>Добро пожаловать в ИИ-планировщик!</b>\n\n"
            "Я помогу создать персональный план достижения вашей цели.\n"
            "Процесс займет 3-5 минут.\n\n"
            "Для начала выберите категорию:",
            reply_markup=get_category_keyboard(),
            parse_mode="HTML"
        )
        
        await state.set_state(AssistantOnboardingStates.choosing_category)

# Инициализируем базы данных
db = FirestoreDB()
profile_db = AssistantProfileDB(db.db)

# Загружаем вопросы из JSON
def load_questions() -> Dict[str, Any]:
    """Загружает вопросы онбординга из JSON файла"""
    try:
        json_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'onboarding_questions.json')
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки вопросов: {e}")
        return {"categories": {}, "constraints_questions": {"general": []}}

# Загружаем вопросы при старте
QUESTIONS_DATA = load_questions()


# === НАВИГАЦИОННЫЕ КЛАВИАТУРЫ ===



def get_navigation_keyboard(question_index: int, total_questions: int, required: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура навигации по вопросам (без прогресс-бара)"""
    builder = InlineKeyboardBuilder()
    
    # Кнопки навигации
    buttons = []
    
    # Кнопка "Назад" (если не первый вопрос)
    if question_index > 0:
        buttons.append(
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data="onb_previous_question"
            )
        )
    
    # Кнопка "Пропустить" (если вопрос не обязательный)
    if not required:
        buttons.append(
            InlineKeyboardButton(
                text="➡️ Пропустить",
                callback_data="onb_skip_current"
            )
        )
    
    if buttons:
        builder.row(*buttons)
    
    # Кнопка отмены
    builder.row(
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="onb_cancel"
        )
    )
    
    return builder.as_markup()


# === ОБНОВЛЕННЫЕ ФУНКЦИИ ПОКАЗА ВОПРОСОВ ===

async def show_next_question(obj: Any, state: FSMContext):
    """Универсальная функция показа следующего вопроса"""
    data = await state.get_data()
    
    # Получаем все вопросы (категории + ограничения)
    category_questions = data.get("category_questions", [])
    constraint_questions = data.get("constraint_questions", [])
    all_questions = category_questions + constraint_questions
    
    current_index = data.get("current_question_index", 0)
    
    # Проверяем, закончились ли вопросы
    if current_index >= len(all_questions):
        await show_summary(obj, state)
        return
    
    # Получаем текущий вопрос
    question = all_questions[current_index]
    question_type = question["type"]
    required = question.get("required", True)
    
    # Формируем текст вопроса
    text = f"<b>Вопрос {current_index + 1} из {len(all_questions)}</b>\n\n"
    text += question["text"]
    
    if question.get("placeholder"):
        text += f"\n\n<i>Например: {question['placeholder']}</i>"
    
    # Сохраняем информацию о текущем вопросе
    await state.update_data(
        all_questions=all_questions,
        current_question=question,
        current_question_id=question["id"],
        current_question_required=required
    )
    
    # Показываем вопрос в зависимости от типа
    if question_type == "select":
        await show_select_question(obj, question, current_index, len(all_questions), text)
        
    elif question_type == "multiselect":
        await show_multiselect_question(obj, state, question, current_index, len(all_questions), text)
        
    elif question_type in ["text", "number", "date", "time", "list"]:
        await show_input_question(obj, state, question, question_type, current_index, len(all_questions), text, required)


async def show_select_question(obj, question, current_index, total_questions, text):
    """Показывает вопрос с выбором"""
    builder = InlineKeyboardBuilder()
    
    # Добавляем опции выбора
    for option in question["options"]:
        builder.row(
            InlineKeyboardButton(
                text=option['label'],
                callback_data=f"onb_answer_{question['id']}_{option['value']}"
            )
        )
    
    # Добавляем навигацию
    nav_keyboard = get_navigation_keyboard(current_index, total_questions, question.get("required", True))
    for row in nav_keyboard.inline_keyboard:
        builder.row(*row)
    
    # Отправляем сообщение
    if hasattr(obj, 'message'):  # CallbackQuery
        await obj.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    else:  # Message
        await obj.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")


async def show_multiselect_question(obj, state, question, current_index, total_questions, text):
    """Показывает вопрос с множественным выбором"""
    data = await state.get_data()
    selected = data.get("multiselect_temp", [])
    
    builder = InlineKeyboardBuilder()
    
    # Опции с чекбоксами
    for option in question["options"]:
        is_selected = option['value'] in selected
        checkbox = "✅" if is_selected else "⬜"
        builder.row(
            InlineKeyboardButton(
                text=f"{checkbox} {option['label']}",
                callback_data=f"onb_multi_{question['id']}_{option['value']}"
            )
        )
    
    # Кнопка "Далее" (активна только если выбран хотя бы один элемент или вопрос необязательный)
    if selected or not question.get("required", True):
        builder.row(
            InlineKeyboardButton(
                text="✅ Далее",
                callback_data=f"onb_multi_done_{question['id']}"
            )
        )
    
    # Навигация
    nav_keyboard = get_navigation_keyboard(current_index, total_questions, question.get("required", True))
    for row in nav_keyboard.inline_keyboard:
        builder.row(*row)
    
    if hasattr(obj, 'message'):
        await obj.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    else:
        await obj.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")


async def show_input_question(obj, state, question, question_type, current_index, total_questions, text, required):
    """Показывает вопрос с вводом текста/числа/даты"""
    # Добавляем инструкцию по вводу
    input_instructions = {
        "text": "📝 Введите текст:",
        "number": "🔢 Введите число:",
        "date": "📅 Введите дату (ДД.ММ.ГГГГ):",
        "time": "🕐 Введите время (ЧЧ:ММ):",
        "list": "📋 Введите элементы через запятую:"
    }
    
    text += f"\n\n{input_instructions.get(question_type, '📝 Введите ответ:')}"
    
    # Показываем быстрые кнопки для некоторых типов
    if question_type == "date" and question.get("validation") == "future_date":
        keyboard = get_date_quick_select_keyboard()
    elif question_type == "number" and "min" in question and "max" in question:
        keyboard = get_number_quick_select_keyboard(
            question["min"], 
            question["max"], 
            unit=question.get("unit", "")
        )
    else:
        keyboard = get_navigation_keyboard(current_index, total_questions, required)
    
    # Отправляем сообщение
    if hasattr(obj, 'message'):
        await obj.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        await obj.answer(text, reply_markup=keyboard, parse_mode="HTML")
    
    # Устанавливаем состояние ожидания
    state_map = {
        "text": AssistantOnboardingStates.waiting_for_text,
        "number": AssistantOnboardingStates.waiting_for_number,
        "date": AssistantOnboardingStates.waiting_for_date,
        "time": AssistantOnboardingStates.waiting_for_time,
        "list": AssistantOnboardingStates.waiting_for_list
    }
    await state.set_state(state_map[question_type])


# === ОБРАБОТЧИКИ НАВИГАЦИИ ===

@router.callback_query(F.data == "onb_previous")
async def go_to_previous_question(callback: CallbackQuery, state: FSMContext):
    """Возврат к предыдущему вопросу"""
    data = await state.get_data()
    current_index = data.get("current_question_index", 0)
    
    if current_index > 0:
        # Возвращаемся к предыдущему вопросу
        await state.update_data(current_question_index=current_index - 1)
        await show_next_question(callback, state)
    
    await callback.answer()


@router.callback_query(F.data == "onb_skip_current")
async def skip_current_question(callback: CallbackQuery, state: FSMContext):
    """Пропуск текущего вопроса"""
    data = await state.get_data()
    question_id = data.get("current_question_id")
    current_index = data.get("current_question_index", 0)
    
    # Сохраняем null для пропущенного вопроса
    answers = data.get("answers", {})
    answers[question_id] = None
    
    await state.update_data(
        answers=answers,
        current_question_index=current_index + 1
    )
    
    await show_next_question(callback, state)
    await callback.answer("Вопрос пропущен")


# === ОСНОВНЫЕ ОБРАБОТЧИКИ (обновленные) ===

@router.callback_query(F.data == "ai_assistant_start")
async def start_ai_onboarding(callback: CallbackQuery, state: FSMContext):
    """Начало онбординга ИИ-ассистента - всегда начинаем с чистого листа для первого плана"""
    # Получаем БД
    _, profile_db = get_db()
    if not profile_db:
        await callback.answer("⚠️ База данных временно недоступна", show_alert=True)
        return
    
    await state.clear()
    
    # Проверяем существующий профиль
    profile = await profile_db.get_profile(callback.from_user.id)
    
    # Если профиль и план уже есть - это не должно происходить через эту кнопку
    # (для создания нового плана есть отдельная кнопка)
    if profile and profile.plan:
        # Перенаправляем на меню ассистента
        from handlers import assistant
        await assistant.show_assistant_menu(callback)
        return
    
    # Если профиль есть, но плана нет - предлагаем варианты
    if profile and profile.onboarding.completed and not profile.plan:
        await callback.message.edit_text(
            "✅ <b>Профиль настроен, но план еще не создан</b>\n\n"
            "Хотите создать план на основе ваших настроек?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Создать план", callback_data="onb_generate_plan_from_profile")],
                [InlineKeyboardButton(text="🔄 Изменить настройки", callback_data="onb_restart_confirmed")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="assistant_menu")]
            ]),
            parse_mode="HTML"
        )
        return
    
    # В остальных случаях начинаем новый онбординг
    await callback.message.edit_text(
        "🎯 <b>Добро пожаловать в ИИ-планировщик!</b>\n\n"
        "Я помогу создать персональный план достижения вашей цели.\n\n"
        "Для начала выберите категорию:",
        reply_markup=get_category_keyboard(),
        parse_mode="HTML"
    )
    
    await state.set_state(AssistantOnboardingStates.choosing_category)
    await callback.answer()


@router.callback_query(F.data == "onb_restart_with_delete")
async def restart_onboarding_with_delete(callback: CallbackQuery, state: FSMContext):
    """Перезапуск онбординга с удалением старого плана"""
    # Получаем БД
    _, profile_db = get_db()
    if not profile_db:
        await callback.answer("⚠️ База данных временно недоступна", show_alert=True)
        return
    
    # Удаляем старый план
    success = await profile_db.delete_plan(callback.from_user.id)
    
    if success:
        await callback.message.edit_text(
            "<b>✅ Старый план удалён</b>\n\n"
            "Начинаем создание нового плана...",
            parse_mode="HTML"
        )
        
        # Небольшая задержка для UX
        import asyncio
        await asyncio.sleep(1)
        
        # Запускаем онбординг заново
        await restart_onboarding_confirmed(callback, state)
    else:
        await callback.answer("Ошибка при удалении плана", show_alert=True)


@router.callback_query(F.data == "onb_generate_plan_from_profile")
async def generate_plan_from_existing_profile(callback: CallbackQuery, state: FSMContext):
    """Генерация плана на основе существующего профиля"""
    # Получаем БД
    _, profile_db = get_db()
    if not profile_db:
        await callback.answer("⚠️ База данных временно недоступна", show_alert=True)
        return
    
    # Получаем профиль
    profile = await profile_db.get_profile(callback.from_user.id)
    
    if not profile or not profile.onboarding.completed:
        await callback.answer("Профиль не найден или не завершен", show_alert=True)
        return
    
    await callback.message.edit_text(
        "<b>⏳ Генерирую план на основе ваших настроек...</b>",
        parse_mode="HTML"
    )
    
    try:
        # Генерируем план
        plan = await generate_plan(
            category=profile.active_category,
            answers=profile.onboarding.answers,
            constraints=profile.constraints.dict() if profile.constraints else {},
            horizon_days=15
        )
        
        # Сохраняем план в состоянии для превью
        await state.update_data(
            generated_plan=plan.dict(),
            current_start_day=1
        )
        await state.set_state(PlanPreviewStates.viewing)
        
        # Показываем превью
        await show_plan_preview(callback.message, plan, 1)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при генерации плана: {e}", exc_info=True)
        await callback.message.edit_text(
            "<b>❌ Ошибка при генерации плана</b>\n\n"
            "Попробуйте позже или пройдите настройку заново.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Настроить заново", callback_data="onb_restart_confirmed")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="assistant_menu")]
            ]),
            parse_mode="HTML"
        )


@router.callback_query(F.data == "onb_restart_confirmed")
async def restart_onboarding_confirmed(callback: CallbackQuery, state: FSMContext):
    """Подтвержденный перезапуск онбординга"""
    # Получаем БД
    _, profile_db = get_db()
    if not profile_db:
        await callback.answer("⚠️ База данных временно недоступна", show_alert=True)
        return
    
    await state.clear()
    
    # Показываем выбор категории
    await callback.message.edit_text(
        "🎯 <b>Настройка нового плана</b>\n\n"
        "Выберите категорию для вашей цели:",
        reply_markup=get_category_keyboard(),
        parse_mode="HTML"
    )
    
    await state.set_state(AssistantOnboardingStates.choosing_category)
    await callback.answer()


@router.callback_query(F.data.startswith("onb_category_"), StateFilter(AssistantOnboardingStates.choosing_category))
async def process_category_choice(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора категории"""
    # Получаем БД
    _, profile_db = get_db()
    if not profile_db:
        await callback.answer("⚠️ База данных временно недоступна", show_alert=True)
        return
    
    category = callback.data.split("_")[2]
    
    # Подготавливаем вопросы
    category_questions = QUESTIONS_DATA["categories"][category]["questions"]
    constraint_questions = QUESTIONS_DATA.get("constraints_questions", {}).get("general", [])
    
    # Сохраняем в state
    await state.update_data(
        category=category,
        answers={},
        current_question_index=0,
        category_questions=category_questions,
        constraint_questions=constraint_questions,
        multiselect_temp=[]
    )
    
    # Создаем профиль если его нет
    if not await profile_db.get_profile(callback.from_user.id):
        await profile_db.create_profile(callback.from_user.id)
    
    # Сохраняем выбор категории
    await profile_db.save_onboarding_answer(callback.from_user.id, "category", category)
    
    # Переходим к первому вопросу
    await state.set_state(AssistantOnboardingStates.answering_questions)
    await show_next_question(callback, state)
    await callback.answer()


@router.callback_query(F.data.startswith("onb_answer_"))
async def process_select_answer(callback: CallbackQuery, state: FSMContext):
    """Обработка ответа на вопрос с выбором"""
    # Получаем БД
    _, profile_db = get_db()
    if not profile_db:
        await callback.answer("⚠️ База данных временно недоступна", show_alert=True)
        return
    
    parts = callback.data.split("_", 3)  # Ограничиваем split для сохранения подчеркиваний в значении
    question_id = parts[2]
    answer = parts[3] if len(parts) > 3 else ""
    
    # Преобразуем значение если это число
    try:
        answer = int(answer)
    except ValueError:
        pass  # Оставляем как строку
    
    # Сохраняем ответ
    data = await state.get_data()
    answers = data.get("answers", {})
    answers[question_id] = answer
    
    # Сохраняем в БД
    await profile_db.save_onboarding_answer(callback.from_user.id, question_id, answer)
    
    # Переходим к следующему вопросу
    current_index = data.get("current_question_index", 0)
    await state.update_data(
        answers=answers,
        current_question_index=current_index + 1
    )
    
    await show_next_question(callback, state)
    await callback.answer()


# === ОБРАБОТЧИКИ ТЕКСТОВОГО ВВОДА С ВАЛИДАЦИЕЙ ===

@router.message(StateFilter(AssistantOnboardingStates.waiting_for_text))
async def process_text_input(message: Message, state: FSMContext):
    """Обработка текстового ответа с валидацией"""
    # Получаем БД
    _, profile_db = get_db()
    if not profile_db:
        await message.answer("⚠️ База данных временно недоступна")
        return
    
    data = await state.get_data()
    question = data.get("current_question", {})
    question_id = data.get("current_question_id")
    
    # Валидация длины
    if "min_length" in question and len(message.text) < question["min_length"]:
        await message.answer(f"❌ Минимум {question['min_length']} символов")
        await message.delete()
        return
    
    if "max_length" in question and len(message.text) > question["max_length"]:
        await message.answer(f"❌ Максимум {question['max_length']} символов")
        await message.delete()
        return
    
    # Сохраняем ответ
    answers = data.get("answers", {})
    answers[question_id] = message.text
    
    await profile_db.save_onboarding_answer(message.from_user.id, question_id, message.text)
    
    # Переходим дальше
    current_index = data.get("current_question_index", 0)
    await state.update_data(
        answers=answers,
        current_question_index=current_index + 1
    )
    
    await message.delete()
    
    # Показываем следующий вопрос
    new_msg = await message.answer("✅ Сохранено!")
    await asyncio.sleep(0.5)
    await new_msg.delete()
    
    await state.set_state(AssistantOnboardingStates.answering_questions)
    bot_msg = await message.answer("Загружаю следующий вопрос...")
    await show_next_question(bot_msg, state)


@router.message(StateFilter(AssistantOnboardingStates.waiting_for_date))
async def process_date_input(message: Message, state: FSMContext):
    """Обработка ввода даты"""
    # Получаем БД
    _, profile_db = get_db()
    if not profile_db:
        await message.answer("⚠️ База данных временно недоступна")
        return
    
    try:
        # Пробуем разные форматы даты
        date_formats = ["%d.%m.%Y", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"]
        date_value = None
        
        for fmt in date_formats:
            try:
                date_value = datetime.strptime(message.text, fmt).date()
                break
            except ValueError:
                continue
        
        if not date_value:
            await message.answer("❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ")
            await message.delete()
            return
        
        data = await state.get_data()
        question = data.get("current_question", {})
        question_id = data.get("current_question_id")
        
        # Валидация будущей даты
        if question.get("validation") == "future_date" and date_value <= date.today():
            await message.answer("❌ Дата должна быть в будущем")
            await message.delete()
            return
        
        # Сохраняем ответ
        answers = data.get("answers", {})
        answers[question_id] = date_value.isoformat()
        
        await profile_db.save_onboarding_answer(message.from_user.id, question_id, date_value.isoformat())
        
        # Переходим дальше
        current_index = data.get("current_question_index", 0)
        await state.update_data(
            answers=answers,
            current_question_index=current_index + 1
        )
        
        await message.delete()
        
        new_msg = await message.answer("✅ Сохранено!")
        await asyncio.sleep(0.5)
        await new_msg.delete()
        
        await state.set_state(AssistantOnboardingStates.answering_questions)
        bot_msg = await message.answer("Загружаю следующий вопрос...")
        await show_next_question(bot_msg, state)
        
    except Exception as e:
        logger.error(f"Ошибка обработки даты: {e}")
        await message.answer("❌ Ошибка обработки даты")
        await message.delete()


@router.message(StateFilter(AssistantOnboardingStates.waiting_for_list))
async def process_list_input(message: Message, state: FSMContext):
    """Обработка ввода списка через запятую"""
    # Получаем БД
    _, profile_db = get_db()
    if not profile_db:
        await message.answer("⚠️ База данных временно недоступна")
        return
    
    data = await state.get_data()
    question = data.get("current_question", {})
    question_id = data.get("current_question_id")
    
    # Разбираем список
    items = [item.strip() for item in message.text.split(",") if item.strip()]
    
    if not items:
        await message.answer("❌ Пожалуйста, введите хотя бы один элемент")
        await message.delete()
        return
    
    # Сохраняем ответ
    answers = data.get("answers", {})
    answers[question_id] = items
    
    await profile_db.save_onboarding_answer(message.from_user.id, question_id, items)
    
    # Переходим дальше
    current_index = data.get("current_question_index", 0)
    await state.update_data(
        answers=answers,
        current_question_index=current_index + 1
    )
    
    await message.delete()
    
    # Показываем следующий вопрос
    new_msg = await message.answer("✅ Сохранено!")
    await asyncio.sleep(0.5)
    await new_msg.delete()
    
    await state.set_state(AssistantOnboardingStates.answering_questions)
    bot_msg = await message.answer("Загружаю следующий вопрос...")
    await show_next_question(bot_msg, state)


# === ПОКАЗ СВОДКИ ===

async def show_summary(obj: Any, state: FSMContext):
    """Показывает итоговую сводку перед завершением"""
    data = await state.get_data()
    category = data.get("category")
    answers = data.get("answers", {})
    
    category_info = QUESTIONS_DATA["categories"][category]
    
    # Формируем текст сводки
    text = f"📊 <b>Проверьте ваши данные:</b>\n\n"
    text += f"<b>Категория:</b> {category_info['emoji']} {category_info['title']}\n\n"
    
    # Разделяем ответы на категории и ограничения
    text += "<b>Основные параметры:</b>\n"
    
    # Показываем ответы на вопросы категории
    category_questions = data.get("category_questions", [])
    for q in category_questions:
        if q["id"] in answers and answers[q["id"]] is not None:
            value = answers[q["id"]]
            if isinstance(value, list):
                value_str = ", ".join(str(v) for v in value)
            else:
                value_str = str(value)
            
            # Сокращаем длинные значения
            if len(value_str) > 50:
                value_str = value_str[:50] + "..."
            
            text += f"• {q['text'][:40]}...: <code>{value_str}</code>\n"
    
    text += "\n<b>Ограничения:</b>\n"
    
    # Показываем ограничения
    constraint_questions = data.get("constraint_questions", [])
    for q in constraint_questions:
        if q["id"] in answers and answers[q["id"]] is not None:
            value = answers[q["id"]]
            if q["id"] == "working_days":
                days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
                value_str = ", ".join(days[d-1] for d in value if 1 <= d <= 7)
            elif q["id"] == "daily_time_minutes":
                hours = value // 60
                minutes = value % 60
                value_str = f"{hours}ч {minutes}мин" if hours > 0 else f"{minutes} минут"
            else:
                value_str = str(value)
            
            text += f"• {q['text'][:40]}...: <code>{value_str}</code>\n"
    
    text += "\n<b>Все верно?</b>"
    
    # Отправляем сводку
    keyboard = get_confirmation_keyboard()
    
    if hasattr(obj, 'message'):  # CallbackQuery
        await obj.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    else:  # Message
        await obj.answer(text, reply_markup=keyboard, parse_mode="HTML")
    
    await state.set_state(AssistantOnboardingStates.confirming_data)


@router.callback_query(F.data == "onb_confirm_final", StateFilter(AssistantOnboardingStates.confirming_data))
async def finalize_onboarding(callback: CallbackQuery, state: FSMContext):
    """Завершение онбординга и создание плана"""
    # Получаем БД
    _, profile_db = get_db()
    if not profile_db:
        await callback.answer("⚠️ База данных временно недоступна", show_alert=True)
        return
    
    data = await state.get_data()
    category = data.get("category")
    answers = data.get("answers", {})
    
    # Разделяем ответы на основные и ограничения
    constraints = {
        "daily_minutes": answers.get("daily_time_minutes", 60),
        "daily_time_minutes": answers.get("daily_time_minutes", 60),
        "working_days": answers.get("working_days", [1, 2, 3, 4, 5])
    }
    
    # Добавляем специфичные ограничения категории
    category_specific = {}
    category_questions = data.get("category_questions", [])
    
    for q in category_questions:
        if q["id"] in answers and answers[q["id"]] is not None:
            category_specific[q["id"]] = answers[q["id"]]
    
    # Финализируем онбординг
    success = await profile_db.finalize_onboarding(
        callback.from_user.id,
        category,
        answers,
        constraints
    )
    
    if success:
        await callback.message.edit_text(
            "✅ <b>Отлично! Данные сохранены.</b>\n\n"
            "🤖 Сейчас ИИ создаст для вас персональный план.\n"
            "Это может занять несколько секунд...",
            parse_mode="HTML"
        )
        
        try:
            # Генерируем план
            plan = await generate_plan(
                category=category,
                answers=answers,
                constraints=constraints,
                horizon_days=15
            )
            
            # Сохраняем план в состоянии для превью
            await state.update_data(
                generated_plan=plan.dict(),
                current_start_day=1
            )
            
            # Меняем состояние на просмотр плана
            await state.set_state(AssistantOnboardingStates.viewing_generated_plan)
            
            # Показываем превью плана
            await show_plan_preview(callback.message, plan, 1)
            
        except Exception as e:
            logger.error(f"Ошибка при генерации плана: {e}", exc_info=True)
            await callback.message.edit_text(
                "❌ <b>Ошибка при создании плана</b>\n\n"
                "Произошла ошибка. Попробуйте позже.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ В меню", callback_data="assistant_menu")]
                ]),
                parse_mode="HTML"
            )
    else:
        await callback.answer("Ошибка сохранения данных", show_alert=True)

@router.callback_query(F.data.startswith("plan:"), StateFilter(AssistantOnboardingStates.viewing_generated_plan))
async def handle_plan_actions_in_onboarding(callback: CallbackQuery, state: FSMContext):
    """Обработчик действий с планом в процессе онбординга"""
    
    if callback.data == "plan:save":
        # Сохраняем план
        data = await state.get_data()
        plan_dict = data.get("generated_plan")
        
        if not plan_dict:
            await callback.answer("Ошибка: план не найден")
            return
        
        # Получаем БД
        _, profile_db = get_db()
        if not profile_db:
            await callback.answer("⚠️ База данных временно недоступна", show_alert=True)
            return
        
        success = await profile_db.save_plan(callback.from_user.id, plan_dict)
        
        if success:
            await callback.message.edit_text(
                "🎉 <b>План успешно создан и сохранён!</b>\n\n"
                "Теперь вы можете начать работу над своей целью.\n"
                "Используйте меню ассистента для отслеживания прогресса.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📊 Мой прогресс", callback_data="ai_show_plan")],
                    [InlineKeyboardButton(text="◀️ В меню ассистента", callback_data="assistant_menu")]
                ]),
                parse_mode="HTML"
            )
            
            await state.clear()
        else:
            await callback.answer("Ошибка при сохранении плана", show_alert=True)
    
    elif callback.data == "plan:cancel":
        await state.clear()
        await callback.message.edit_text(
            "❌ Создание плана отменено.\n\n"
            "Вы можете вернуться к генерации плана позже.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ В меню ассистента", callback_data="assistant_menu")]
            ]),
            parse_mode="HTML"
        )
    
    elif callback.data.startswith("plan:prev:") or callback.data.startswith("plan:next:"):
        # Передаём управление обработчику из assistant_plan
        from handlers.assistant_plan import handle_plan_prev, handle_plan_next
        
        if callback.data.startswith("plan:prev:"):
            await handle_plan_prev(callback, state)
        else:
            await handle_plan_next(callback, state)
    
    await callback.answer()


# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===

def get_category_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора категории"""
    builder = InlineKeyboardBuilder()
    
    for category_id, category_data in QUESTIONS_DATA["categories"].items():
        builder.row(
            InlineKeyboardButton(
                text=f"{category_data['emoji']} {category_data['title']}",
                callback_data=f"onb_category_{category_id}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="assistant_menu"
        )
    )
    
    return builder.as_markup()


def get_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="✅ Все верно, продолжить",
            callback_data="onb_confirm_final"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="✏️ Изменить ответы",
            callback_data="onb_restart_confirmed"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="onb_cancel"
        )
    )
    
    return builder.as_markup()




def get_date_quick_select_keyboard() -> InlineKeyboardMarkup:
    """Быстрый выбор даты"""
    from datetime import timedelta
    
    builder = InlineKeyboardBuilder()
    today = date.today()
    
    options = [
        ("Через неделю", 7),
        ("Через 2 недели", 14),
        ("Через месяц", 30),
        ("Через 2 месяца", 60),
        ("Через 3 месяца", 90)
    ]
    
    for label, days in options:
        target_date = today + timedelta(days=days)
        builder.row(
            InlineKeyboardButton(
                text=f"{label} ({target_date.strftime('%d.%m.%Y')})",
                callback_data=f"onb_date_{target_date.isoformat()}"
            )
        )
    
    return builder.as_markup()


def get_number_quick_select_keyboard(min_val: int, max_val: int, unit: str = "") -> InlineKeyboardMarkup:
    """Быстрый выбор числа"""
    builder = InlineKeyboardBuilder()
    
    # Генерируем разумные опции
    if max_val - min_val <= 10:
        options = list(range(min_val, max_val + 1))
    else:
        step = (max_val - min_val) // 5
        options = [min_val + i * step for i in range(6)]
        if max_val not in options:
            options[-1] = max_val
    
    # Кнопки в 2 ряда
    for i in range(0, len(options), 3):
        row_options = options[i:i+3]
        builder.row(*[
            InlineKeyboardButton(
                text=f"{opt}{unit}",
                callback_data=f"onb_number_{opt}"
            )
            for opt in row_options
        ])
    
    return builder.as_markup()


# === ОБРАБОТЧИКИ БЫСТРОГО ВЫБОРА ===

@router.callback_query(F.data.startswith("onb_date_"))
async def process_quick_date(callback: CallbackQuery, state: FSMContext):
    """Обработка быстрого выбора даты"""
    # Получаем БД
    _, profile_db = get_db()
    if not profile_db:
        await callback.answer("⚠️ База данных временно недоступна", show_alert=True)
        return
    
    date_str = callback.data.split("_")[2]
    
    data = await state.get_data()
    question_id = data.get("current_question_id")
    answers = data.get("answers", {})
    answers[question_id] = date_str
    
    await profile_db.save_onboarding_answer(callback.from_user.id, question_id, date_str)
    
    current_index = data.get("current_question_index", 0)
    await state.update_data(
        answers=answers,
        current_question_index=current_index + 1
    )
    
    await state.set_state(AssistantOnboardingStates.answering_questions)
    await show_next_question(callback, state)
    await callback.answer()


@router.callback_query(F.data.startswith("onb_number_"))
async def process_quick_number(callback: CallbackQuery, state: FSMContext):
    """Обработка быстрого выбора числа"""
    # Получаем БД
    _, profile_db = get_db()
    if not profile_db:
        await callback.answer("⚠️ База данных временно недоступна", show_alert=True)
        return
    
    number = int(callback.data.split("_")[2])
    
    data = await state.get_data()
    question_id = data.get("current_question_id")
    answers = data.get("answers", {})
    answers[question_id] = number
    
    await profile_db.save_onboarding_answer(callback.from_user.id, question_id, number)
    
    current_index = data.get("current_question_index", 0)
    await state.update_data(
        answers=answers,
        current_question_index=current_index + 1
    )
    
    await state.set_state(AssistantOnboardingStates.answering_questions)
    await show_next_question(callback, state)
    await callback.answer()


@router.callback_query(F.data == "onb_cancel")
async def cancel_onboarding(callback: CallbackQuery, state: FSMContext):
    """Отмена онбординга"""
    await state.clear()
    
    await callback.message.edit_text(
        "❌ Настройка отменена.\n\n"
        "Вы можете вернуться к ней в любое время!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ В меню ассистента", callback_data="assistant_menu")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
    )
    await callback.answer()

@router.callback_query(F.data.startswith("onb_multi_"))
async def process_multiselect(callback: CallbackQuery, state: FSMContext):
    """Обработка множественного выбора"""
    if callback.data.startswith("onb_multi_done_"):
        # Завершение множественного выбора
        question_id = callback.data.split("_")[3]
        data = await state.get_data()
        selected = data.get("multiselect_temp", [])
        
        # Сохраняем ответ
        answers = data.get("answers", {})
        answers[question_id] = selected
        
        await profile_db.save_onboarding_answer(callback.from_user.id, question_id, selected)
        
        # Очищаем временный выбор и переходим дальше
        current_index = data.get("current_question_index", 0)
        await state.update_data(
            answers=answers,
            current_question_index=current_index + 1,
            multiselect_temp=[]
        )
        
        await show_next_question(callback, state)
        await callback.answer()
    else:
        # Переключение выбора опции
        parts = callback.data.split("_")
        question_id = parts[2]
        value = int(parts[3]) if parts[3].isdigit() else parts[3]
        
        data = await state.get_data()
        selected = data.get("multiselect_temp", [])
        
        if value in selected:
            selected.remove(value)
            await callback.answer("Убрано из выбора")
        else:
            selected.append(value)
            await callback.answer("Добавлено в выбор")
        
        await state.update_data(multiselect_temp=selected)
        
        # Обновляем отображение
        await show_next_question(callback, state)

@router.callback_query(F.data == "ai_show_plan")
async def show_current_plan(callback: CallbackQuery, state: FSMContext):
    """Показывает текущий план пользователя для просмотра"""
    # Получаем БД
    _, profile_db = get_db()
    if not profile_db:
        await callback.answer("⚠️ База данных временно недоступна", show_alert=True)
        return
    
    # Получаем профиль
    profile = await profile_db.get_profile(callback.from_user.id)
    
    if not profile or not profile.plan:
        await callback.message.edit_text(
            "❌ <b>План еще не создан</b>\n\n"
            "Сначала пройдите настройку для создания персонального плана.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎯 Создать план", callback_data="ai_assistant_start")],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="assistant_menu")]
            ]),
            parse_mode="HTML"
        )
        return
    
    # Сохраняем план в состоянии для навигации
    await state.update_data(
        viewing_plan=profile.plan.dict(),
        current_start_day=1,
        is_view_mode=True
    )
    await state.set_state(PlanPreviewStates.viewing)
    
    # Показываем план через функцию из assistant_plan
    await show_plan_preview(callback.message, profile.plan, 1, is_view_mode=True)
    await callback.answer()



