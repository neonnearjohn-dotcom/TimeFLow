"""
Обработчик генерации и просмотра планов ИИ-ассистента
"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.firestore_db import FirestoreDB
from database.assistant_profile_db import AssistantProfileDB
from utils.plan_generator import generate_plan
from keyboards.assistant_plan import (
    get_plan_preview_keyboard,
    get_plan_saved_keyboard,
    get_plan_generate_keyboard,
    get_plan_management_keyboard
)

# Настройка логирования
logger = logging.getLogger(__name__)

# Создаем роутер
router = Router()

# Инициализация БД
db = FirestoreDB()
profile_db = AssistantProfileDB(db.db)


class PlanPreviewStates(StatesGroup):
    """Состояния для превью плана"""
    viewing = State()


@router.message(F.text == "/plan")
async def cmd_plan(message: Message):
    """Обработчик команды /plan для просмотра текущего плана"""
    telegram_id = message.from_user.id
    
    try:
        profile = await profile_db.get_profile(telegram_id)
        
        if not profile or not profile.plan:
            await message.answer(
                "<b>📅 У вас пока нет плана</b>\n\n"
                "Создайте персональный план с помощью ИИ-ассистента.\n"
                "Используйте команду /plan_generate или перейдите в меню ассистента.",
                parse_mode="HTML"
            )
            return
        
        # Показываем первые дни плана
        plan = profile.plan
        await show_plan_preview(message, plan, 1, is_view_mode=True)
        
    except Exception as e:
        logger.error(f"Ошибка при показе плана: {e}", exc_info=True)
        await message.answer(
            "<b>❌ Ошибка</b>\n\n"
            "Не удалось загрузить план. Попробуйте позже.",
            parse_mode="HTML"
        )


@router.callback_query(F.data == "plan:generate")
async def callback_plan_generate(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки генерации плана"""
    await callback.answer()
    await generate_plan_handler(callback.message, callback.from_user.id, state)


async def generate_plan_handler(message: Message, telegram_id: int, state: FSMContext):
    """Основная логика генерации плана"""
    try:
        # Получаем профиль
        profile = await profile_db.get_profile(telegram_id)
        
        if not profile:
            await message.answer(
                "<b>❌ Профиль не найден</b>\n\n"
                "Сначала пройдите онбординг с помощью команды /onboarding",
                parse_mode="HTML"
            )
            return
        
        # Проверяем завершенность онбординга
        if not profile.onboarding or not profile.onboarding.completed:
            await message.answer(
                "<b>⚠️ Онбординг не завершен</b>\n\n"
                "Сначала завершите настройку профиля с помощью команды /onboarding",
                parse_mode="HTML"
            )
            return
        
        # Показываем сообщение о генерации
        status_msg = await message.answer(
            "<b>⏳ Генерирую персональный план...</b>",
            parse_mode="HTML"
        )
        
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
        await show_plan_preview(status_msg, plan, 1)
        
    except Exception as e:
        logger.error(f"Ошибка при генерации плана: {e}", exc_info=True)
        await message.answer(
            "<b>❌ Ошибка генерации плана</b>\n\n"
            "Произошла ошибка. Попробуйте позже.",
            parse_mode="HTML"
        )

# Добавьте этот обработчик в handlers/assistant.py после других обработчиков

@router.callback_query(F.data == "ai_plan_menu")
async def show_plan_menu(callback: CallbackQuery, state: FSMContext):
    """Показывает меню управления планом"""
    
    # Получаем БД через функцию из assistant_onboarding
    from handlers import assistant_onboarding
    _, profile_db = assistant_onboarding.get_db()
    
    if not profile_db:
        await callback.answer("⚠️ База данных временно недоступна", show_alert=True)
        return
    
    # Проверяем наличие плана у пользователя
    profile = await profile_db.get_profile(callback.from_user.id)
    has_plan = profile and profile.plan is not None
    
    if has_plan:
        # Если план есть - показываем меню управления
        from keyboards.assistant_plan import get_plan_management_keyboard
        
        await callback.message.edit_text(
            "<b>📅 Управление планом</b>\n\n"
            "У вас уже есть активный план.\n"
            "Выберите действие:",
            reply_markup=get_plan_management_keyboard(),
            parse_mode="HTML"
        )
    else:
        # Если плана нет - предлагаем создать
        from keyboards.assistant_plan import get_plan_generate_keyboard
        
        await callback.message.edit_text(
            "<b>📅 Создание плана</b>\n\n"
            "У вас пока нет персонального плана.\n"
            "Хотите создать план для достижения вашей цели?",
            reply_markup=get_plan_generate_keyboard(),
            parse_mode="HTML"
        )
    
    await callback.answer()

# Добавьте эти обработчики в handlers/assistant_plan.py

@router.callback_query(F.data == "plan:open_preview")
async def handle_plan_open_preview(callback: CallbackQuery, state: FSMContext):
    """Обработчик открытия просмотра плана"""
    telegram_id = callback.from_user.id
    
    try:
        profile = await profile_db.get_profile(telegram_id)
        
        if not profile or not profile.plan:
            await callback.answer("План не найден", show_alert=True)
            return
        
        # Сохраняем план в состоянии для навигации
        await state.update_data(
            viewing_plan=profile.plan.dict(),
            current_start_day=1,
            is_view_mode=True
        )
        await state.set_state(PlanPreviewStates.viewing)
        
        # Показываем план
        await show_plan_preview(callback.message, profile.plan, 1, is_view_mode=True)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при открытии плана: {e}", exc_info=True)
        await callback.answer("Ошибка при загрузке плана", show_alert=True)


@router.callback_query(F.data == "plan:back")
async def handle_plan_back(callback: CallbackQuery):
    """Возврат в меню ассистента"""
    from handlers import assistant
    await assistant.show_assistant_menu(callback)


@router.callback_query(F.data == "plan:generate")
async def handle_plan_generate_start(callback: CallbackQuery, state: FSMContext):
    """Начало генерации плана - проверка существующего плана и перенаправление"""
    telegram_id = callback.from_user.id
    
    try:
        # Проверяем наличие существующего плана
        profile = await profile_db.get_profile(telegram_id)
        
        if profile and profile.plan:
            # Если план уже есть, спрашиваем о замене
            await callback.message.edit_text(
                "<b>⚠️ У вас уже есть активный план</b>\n\n"
                "Хотите создать новый план?\n"
                "Текущий план будет удалён.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✅ Да, создать новый",
                            callback_data="plan:generate_confirm_new"
                        ),
                        InlineKeyboardButton(
                            text="❌ Нет, оставить текущий",
                            callback_data="plan:view"
                        )
                    ]
                ]),
                parse_mode="HTML"
            )
        else:
            # Если плана нет, сразу начинаем онбординг
            from handlers import assistant_onboarding
            await assistant_onboarding.start_ai_onboarding(callback, state)
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при проверке плана: {e}", exc_info=True)
        await callback.answer("Произошла ошибка", show_alert=True)

async def show_plan_preview(message: Message, plan, start_day: int, is_view_mode: bool = False):
    """Показывает превью плана"""
    text = f"<b>📅 {'Ваш план' if is_view_mode else 'Превью вашего плана'}</b>\n"
    text += f"Горизонт: {plan.horizon_days} дней\n\n"
    
    # Показываем 3 дня
    end_day = min(start_day + 2, plan.horizon_days)
    
    for day_num in range(start_day, end_day + 1):
        # Находим задачи этого дня
        day_tasks = [task for task in plan.days if task.day_number == day_num]
        
        if day_tasks:
            text += f"<b>День {day_num}:</b>\n"
            for task in day_tasks:
                # Извлекаем время из описания
                time_info = ""
                if task.description and "Время:" in task.description:
                    time_info = task.description.replace("Время: ", "")
                
                text += f"• {time_info} - {task.title} ({task.duration_minutes} мин)\n"
            text += "\n"
    
    # Информация о чекпоинтах
    checkpoints_in_range = [
        cp for cp in plan.checkpoints 
        if start_day <= cp.day_number <= end_day
    ]
    
    if checkpoints_in_range:
        text += "<b>🎯 Контрольные точки:</b>\n"
        for cp in checkpoints_in_range:
            text += f"День {cp.day_number}: {cp.title}\n"
        text += "\n"
    
    # Добавляем навигационную информацию
    text += f"<i>Показаны дни {start_day}-{end_day} из {plan.horizon_days}</i>"
    
    if is_view_mode:
        # В режиме просмотра используем упрощенную клавиатуру
        keyboard = get_plan_preview_keyboard(start_day, plan.horizon_days)
        # Убираем кнопки сохранения в режиме просмотра
        buttons = []
        nav_row = []
        
        if start_day > 1:
            nav_row.append(
                InlineKeyboardButton(
                    text="◀️ Назад",
                    callback_data=f"plan:prev:{start_day}"
                )
            )
        
        if start_day + 2 < plan.horizon_days:
            nav_row.append(
                InlineKeyboardButton(
                    text="Дальше ▶️",
                    callback_data=f"plan:next:{start_day}"
                )
            )
        
        if nav_row:
            buttons.append(nav_row)
        
        buttons.append([
            InlineKeyboardButton(
                text="◀️ В меню ассистента",
                callback_data="assistant_menu"
            )
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    else:
        keyboard = get_plan_preview_keyboard(start_day, plan.horizon_days)
    
    if hasattr(message, 'edit_text'):
        await message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    else:
        await message.answer(
            text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("plan:prev:"), PlanPreviewStates.viewing)
async def handle_plan_prev(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Назад' в превью плана"""
    current_start = int(callback.data.split(":")[-1])
    new_start = max(1, current_start - 3)
    
    data = await state.get_data()
    is_view_mode = data.get("is_view_mode", False)
    
    # Выбираем правильный план в зависимости от режима
    if is_view_mode:
        plan_dict = data.get("viewing_plan")
    else:
        plan_dict = data.get("generated_plan")
    
    if not plan_dict:
        await callback.answer("Ошибка: план не найден")
        return
    
    # Преобразуем обратно в объект Plan
    from models.ai_profile import PlanData
    plan = PlanData(**plan_dict)
    
    await state.update_data(current_start_day=new_start)
    await show_plan_preview(callback.message, plan, new_start, is_view_mode)
    await callback.answer()


@router.callback_query(F.data.startswith("plan:next:"), PlanPreviewStates.viewing)
async def handle_plan_next(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Дальше' в превью плана"""
    current_start = int(callback.data.split(":")[-1])
    new_start = current_start + 3
    
    data = await state.get_data()
    is_view_mode = data.get("is_view_mode", False)
    
    # Выбираем правильный план в зависимости от режима
    if is_view_mode:
        plan_dict = data.get("viewing_plan")
    else:
        plan_dict = data.get("generated_plan")
    
    if not plan_dict:
        await callback.answer("Ошибка: план не найден")
        return
    
    # Преобразуем обратно в объект Plan
    from models.ai_profile import PlanData
    plan = PlanData(**plan_dict)
    
    await state.update_data(current_start_day=new_start)
    await show_plan_preview(callback.message, plan, new_start, is_view_mode)
    await callback.answer()


@router.callback_query(F.data == "plan:save", PlanPreviewStates.viewing)
async def handle_plan_save(callback: CallbackQuery, state: FSMContext):
    """Обработчик сохранения плана"""
    try:
        data = await state.get_data()
        plan_dict = data.get("generated_plan")
        
        if not plan_dict:
            await callback.answer("Ошибка: план не найден")
            return
        
        # Сохраняем план
        success = await profile_db.save_plan(callback.from_user.id, plan_dict)
        
        if success:
            # Подсчитываем статистику
            total_tasks = len(plan_dict.get("days", []))
            total_checkpoints = len(plan_dict.get("checkpoints", []))
            total_buffer_days = len(plan_dict.get("buffer_days", []))
            
            await callback.message.edit_text(
                f"<b>✅ План успешно сохранён!</b>\n\n"
                f"<b>Сводка по плану:</b>\n"
                f"• Горизонт: {plan_dict.get('horizon_days', 15)} дней\n"
                f"• Задач: {total_tasks}\n"
                f"• Контрольных точек: {total_checkpoints}\n"
                f"• Буферных дней: {total_buffer_days}\n\n"
                f"Теперь вы можете отслеживать свой прогресс!",
                reply_markup=get_plan_saved_keyboard(),
                parse_mode="HTML"
            )
            
            await state.clear()
        else:
            await callback.answer("Ошибка при сохранении плана", show_alert=True)
            
    except Exception as e:
        logger.error(f"Ошибка при сохранении плана: {e}", exc_info=True)
        await callback.answer("Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "plan:cancel", PlanPreviewStates.viewing)
async def handle_plan_cancel(callback: CallbackQuery, state: FSMContext):
    """Обработчик отмены создания плана"""
    await state.clear()
    
    await callback.message.edit_text(
        "<b>❌ Создание плана отменено</b>\n\n"
        "Вы можете вернуться к генерации плана позже.",
        reply_markup=get_plan_generate_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "plan:view")
async def handle_plan_view(callback: CallbackQuery, state: FSMContext):
    """Обработчик просмотра существующего плана"""
    telegram_id = callback.from_user.id
    
    try:
        profile = await profile_db.get_profile(telegram_id)
        
        if not profile or not profile.plan:
            await callback.answer("План не найден", show_alert=True)
            return
        
        # Сохраняем план в состоянии для навигации
        await state.update_data(
            viewing_plan=profile.plan.dict(),
            current_start_day=1,
            is_view_mode=True
        )
        await state.set_state(PlanPreviewStates.viewing)
        
        await show_plan_preview(callback.message, profile.plan, 1, is_view_mode=True)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при просмотре плана: {e}", exc_info=True)
        await callback.answer("Ошибка при загрузке плана", show_alert=True)


@router.callback_query(F.data == "plan:regenerate")
async def handle_plan_regenerate(callback: CallbackQuery, state: FSMContext):
    """Обработчик пересоздания плана"""
    await callback.answer()
    await callback.message.edit_text(
        "<b>🔄 Пересоздание плана</b>\n\n"
        "Вы уверены, что хотите создать новый план?\n"
        "Текущий план будет заменен.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Да, создать новый",
                    callback_data="plan:regenerate_confirm"
                ),
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="ai_plan_menu"
                )
            ]
        ]),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "plan:regenerate_confirm")
async def handle_plan_regenerate_confirm(callback: CallbackQuery, state: FSMContext):
    """Подтверждение пересоздания плана - удаляем старый и запускаем онбординг"""
    
    try:
        # Удаляем старый план
        success = await profile_db.delete_plan(callback.from_user.id)
        
        if success:
            await callback.message.edit_text(
                "<b>✅ Старый план удалён</b>\n\n"
                "Сейчас начнется создание нового плана...",
                parse_mode="HTML"
            )
            
            # Небольшая задержка для лучшего UX
            import asyncio
            await asyncio.sleep(1)
            
            # Очищаем состояние и запускаем онбординг заново
            await state.clear()
            from handlers import assistant_onboarding
            await assistant_onboarding.restart_onboarding_confirmed(callback, state)
        else:
            await callback.answer("Ошибка при удалении плана", show_alert=True)
            
    except Exception as e:
        logger.error(f"Ошибка при пересоздании плана: {e}", exc_info=True)
        await callback.answer("Произошла ошибка", show_alert=True)


@router.callback_query(F.data == "plan:generate_confirm_new")
async def handle_plan_generate_confirm_new(callback: CallbackQuery, state: FSMContext):
    """Подтверждение создания нового плана с удалением старого"""
    telegram_id = callback.from_user.id
    
    try:
        # Удаляем старый план
        success = await profile_db.delete_plan(telegram_id)
        
        if success:
            await callback.message.edit_text(
                "<b>✅ Старый план удалён</b>\n\n"
                "Сейчас начнется настройка нового плана...",
                parse_mode="HTML"
            )
            
            # Небольшая задержка для лучшего UX
            import asyncio
            await asyncio.sleep(1)
            
            # Запускаем онбординг для нового плана
            from handlers import assistant_onboarding
            await assistant_onboarding.start_ai_onboarding(callback, state)
        else:
            await callback.answer("Ошибка при удалении плана", show_alert=True)
            
    except Exception as e:
        logger.error(f"Ошибка при удалении плана: {e}", exc_info=True)
        await callback.answer("Произошла ошибка", show_alert=True)