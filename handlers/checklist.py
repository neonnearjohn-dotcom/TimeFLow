"""
Обработчики для модуля чек-листа
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from datetime import datetime, timedelta
import logging
import random
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.firestore_db import FirestoreDB
from database.checklist_db import ChecklistDB
from database.gamification_db import GamificationDB
from keyboards.checklist import (
    get_checklist_menu_keyboard,
    get_priority_keyboard,
    get_tasks_list_keyboard,
    get_task_actions_keyboard,
    get_deadline_keyboard,
    get_skip_keyboard,
    get_confirmation_keyboard,
    get_priority_emoji,
    get_priority_name,
    get_edit_field_keyboard,
    get_cancel_edit_keyboard,
)
from keyboards.main_menu import get_main_menu_keyboard
from states.checklist import TaskCreationStates, TaskEditStates
from utils.messages import ERROR_MESSAGES
from utils.achievements import POINTS_TABLE
from handlers.profile import show_new_achievements

# Создаем роутер
router = Router()
logger = logging.getLogger(__name__)

# Инициализируем базу данных
db = FirestoreDB()
checklist_db = ChecklistDB(db.db)
gamification_db = GamificationDB(db.db)

# Мотивационные сообщения
COMPLETION_MESSAGES = [
    "Задача выполнена.",
    "Отличная работа.",
    "Задача завершена успешно.",
    "Прогресс достигнут.",
    "Еще одна задача выполнена.",
    "Хорошая работа.",
    "Задача закрыта.",
    "Результат достигнут.",
]

# Шаблоны задач
TASK_TEMPLATES = {
    "morning": {
        "name": "Утренние дела",
        "tasks": [
            {"title": "Зарядка", "priority": "not_urgent_important"},
            {"title": "Завтрак", "priority": "not_urgent_important"},
            {"title": "Планирование дня", "priority": "urgent_important"},
            {"title": "Проверка почты", "priority": "urgent_not_important"},
        ],
    },
    "work": {
        "name": "Рабочие задачи",
        "tasks": [
            {"title": "Приоритетная задача дня", "priority": "urgent_important"},
            {"title": "Ответить на письма", "priority": "urgent_not_important"},
            {"title": "Совещание", "priority": "urgent_important"},
            {"title": "Планирование на завтра", "priority": "not_urgent_important"},
        ],
    },
    "evening": {
        "name": "Вечерняя рутина",
        "tasks": [
            {"title": "Ужин", "priority": "not_urgent_important"},
            {"title": "Чтение", "priority": "not_urgent_important"},
            {"title": "Подготовка одежды на завтра", "priority": "not_urgent_not_important"},
            {"title": "Отход ко сну до 23:00", "priority": "not_urgent_important"},
        ],
    },
    "home": {
        "name": "Домашние дела",
        "tasks": [
            {"title": "Уборка", "priority": "not_urgent_important"},
            {"title": "Покупка продуктов", "priority": "urgent_important"},
            {"title": "Оплата счетов", "priority": "urgent_important"},
            {"title": "Полив растений", "priority": "not_urgent_not_important"},
        ],
    },
    "health": {
        "name": "Здоровье и спорт",
        "tasks": [
            {"title": "Тренировка", "priority": "not_urgent_important"},
            {"title": "Прием витаминов", "priority": "not_urgent_important"},
            {"title": "Запись к врачу", "priority": "urgent_important"},
            {"title": "Прогулка на свежем воздухе", "priority": "not_urgent_important"},
        ],
    },
    "education": {
        "name": "Обучение",
        "tasks": [
            {"title": "Изучение нового материала", "priority": "not_urgent_important"},
            {"title": "Выполнение домашнего задания", "priority": "urgent_important"},
            {"title": "Практика навыков", "priority": "not_urgent_important"},
            {"title": "Чтение профессиональной литературы", "priority": "not_urgent_important"},
        ],
    },
}


# === ГЛАВНОЕ МЕНЮ ЧЕК-ЛИСТА ===


@router.message(F.text == "✓ Чек-лист", StateFilter(default_state))
async def handle_checklist_menu(message: Message):
    """Обработчик кнопки Чек-лист из главного меню"""
    await message.answer(
        "<b>✓ Чек-лист задач</b>\n\n"
        "Организуйте задачи по матрице Эйзенхауэра для эффективной приоритизации.\n\n"
        "Матрица приоритетов:\n"
        "• Важно и срочно — выполнить немедленно\n"
        "• Важно, не срочно — запланировать\n"
        "• Срочно, не важно — делегировать\n"
        "• Не важно, не срочно — исключить\n\n"
        "Выберите действие:",
        reply_markup=get_checklist_menu_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "checklist_menu")
async def show_checklist_menu(callback: CallbackQuery):
    """Показывает главное меню чек-листа"""
    await callback.message.edit_text(
        "<b>✓ Чек-лист задач</b>\n\n"
        "Организуйте задачи по матрице Эйзенхауэра для эффективной приоритизации.\n\n"
        "Выберите действие:",
        reply_markup=get_checklist_menu_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()


# === СОЗДАНИЕ ЗАДАЧИ ===


@router.callback_query(F.data == "add_task")
async def start_task_creation(callback: CallbackQuery, state: FSMContext):
    """Начинает процесс создания задачи"""
    await callback.message.answer(
        "<b>Создание новой задачи</b>\n\n" "Введите название задачи:",
        reply_markup=get_skip_keyboard(),
        parse_mode="HTML",
    )
    await callback.message.delete()
    await state.set_state(TaskCreationStates.waiting_for_title)
    await callback.answer()


@router.message(TaskCreationStates.waiting_for_title)
async def process_task_title(message: Message, state: FSMContext):
    """Обрабатывает название задачи"""
    if message.text == "Отмена":
        await cancel_task_creation(message, state)
        return

    await state.update_data(title=message.text)

    await message.answer(
        "<b>Описание задачи</b>\n\n"
        "Добавьте описание или детали.\n"
        "Отправьте точку (.) чтобы пропустить.",
        reply_markup=get_skip_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(TaskCreationStates.waiting_for_description)


@router.message(TaskCreationStates.waiting_for_description)
async def process_task_description(message: Message, state: FSMContext):
    """Обрабатывает описание задачи"""
    if message.text == "Отмена":
        await cancel_task_creation(message, state)
        return

    description = message.text if message.text not in [".", "Пропустить"] else ""
    await state.update_data(description=description)

    await message.answer(
        "<b>Приоритет задачи</b>\n\n" "Выберите приоритет по матрице Эйзенхауэра:",
        reply_markup=get_priority_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(TaskCreationStates.waiting_for_priority)


@router.callback_query(F.data.startswith("priority:"), TaskCreationStates.waiting_for_priority)
async def process_task_priority(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор приоритета"""
    priority = callback.data.split(":")[1]
    await state.update_data(priority=priority)

    await callback.message.edit_text(
        "<b>Дедлайн задачи</b>\n\n" "Установите срок выполнения:",
        reply_markup=get_deadline_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(TaskCreationStates.waiting_for_deadline)
    await callback.answer()


@router.callback_query(F.data.startswith("deadline:"), TaskCreationStates.waiting_for_deadline)
async def process_task_deadline(callback: CallbackQuery, state: FSMContext):
    """Завершает создание задачи"""
    deadline_type = callback.data.split(":")[1]

    # Вычисляем дедлайн
    deadline = None
    if deadline_type == "today":
        deadline = datetime.utcnow().replace(hour=23, minute=59, second=59)
    elif deadline_type == "tomorrow":
        deadline = datetime.utcnow() + timedelta(days=1)
    elif deadline_type == "3days":
        deadline = datetime.utcnow() + timedelta(days=3)
    elif deadline_type == "week":
        deadline = datetime.utcnow() + timedelta(weeks=1)
    elif deadline_type == "month":
        deadline = datetime.utcnow() + timedelta(days=30)

    # Получаем все данные
    data = await state.get_data()
    user_id = callback.from_user.id

    try:
        # Создаем задачу
        task_data = {
            "title": data.get("title"),
            "description": data.get("description", ""),
            "priority": data.get("priority"),
            "deadline": deadline,
        }

        task_id = await checklist_db.create_task(user_id, task_data)

        if task_id:
            priority_name = get_priority_name(data.get("priority"))

            await callback.message.edit_text(
                f"<b>✓ Задача создана</b>\n\n"
                f"{data.get('title')}\n"
                f"Приоритет: {priority_name}\n"
                f"{'Дедлайн: ' + deadline.strftime('%d.%m.%Y') if deadline else 'Без дедлайна'}\n\n"
                f"Задача добавлена в ваш список.",
                reply_markup=get_checklist_menu_keyboard(),
                parse_mode="HTML",
            )
        else:
            await callback.message.answer(ERROR_MESSAGES["database_error"])

        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при создании задачи: {e}")
        await callback.message.answer(ERROR_MESSAGES["unknown_error"])
        await state.clear()

    await callback.answer()


# === ПРОСМОТР ЗАДАЧ ===


@router.callback_query(F.data == "active_tasks")
async def show_active_tasks(callback: CallbackQuery):
    """Показывает активные задачи пользователя"""
    user_id = callback.from_user.id

    try:
        # Получаем только активные задачи
        tasks = await checklist_db.get_all_tasks(user_id, status="active")

        text = "<b>📋 Активные задачи</b>\n\n"

        if not tasks:
            text += "У вас пока нет активных задач.\n\n"
            text += "Создайте новую задачу, чтобы начать работу!"
        else:
            # Группируем задачи по приоритетам
            by_priority = {}
            for task in tasks:
                priority = task.get("priority", "not_urgent_not_important")
                if priority not in by_priority:
                    by_priority[priority] = []
                by_priority[priority].append(task)

            # Порядок приоритетов
            priority_order = [
                "urgent_important",
                "not_urgent_important",
                "urgent_not_important",
                "not_urgent_not_important",
            ]

            for priority in priority_order:
                if priority in by_priority and by_priority[priority]:
                    priority_name = get_priority_name(priority)
                    priority_emoji = get_priority_emoji(priority)
                    text += f"\n<b>{priority_emoji} {priority_name}:</b>\n"

                    for task in by_priority[priority]:
                        text += f"• {task.get('title', 'Без названия')}"
                        if task.get("deadline"):
                            deadline = task["deadline"]
                            text += f" (до {deadline.strftime('%d.%m')})"
                        text += "\n"

        await callback.message.edit_text(
            text, reply_markup=get_tasks_list_keyboard(tasks, "active"), parse_mode="HTML"
        )
        logger.info(f"Показано {len(tasks)} активных задач для пользователя {user_id}")

    except Exception as e:
        logger.error(f"Ошибка при показе активных задач для пользователя {user_id}: {e}")
        await callback.answer(
            "Произошла ошибка при загрузке задач. Попробуйте позже.", show_alert=True
        )

    await callback.answer()


@router.callback_query(F.data == "completed_tasks")
async def show_completed_tasks(callback: CallbackQuery):
    """Показывает выполненные задачи пользователя"""
    user_id = callback.from_user.id

    try:
        # Получаем историю выполненных задач
        tasks = await checklist_db.get_completed_tasks_history(user_id, limit=50)

        text = "<b>✓ Выполненные задачи</b>\n\n"

        if not tasks:
            text += "У вас пока нет выполненных задач.\n\n"
            text += "Начните выполнять задачи, чтобы увидеть свой прогресс!"
        else:
            # Показываем последние 20 задач
            text += f"Последние {min(20, len(tasks))} выполненных задач:\n\n"

            for i, task in enumerate(tasks[:20], 1):
                text += f"{i}. {task.get('title', 'Без названия')}"
                if task.get("completed_at"):
                    completed_at = task["completed_at"]
                    text += f" ({completed_at.strftime('%d.%m.%Y')})"
                text += "\n"

            if len(tasks) > 20:
                text += f"\n... и ещё {len(tasks) - 20} задач"

        # Создаем клавиатуру только с кнопкой назад
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="◀ Назад", callback_data="checklist_menu"))

        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
        logger.info(f"Показано {len(tasks)} выполненных задач для пользователя {user_id}")

    except Exception as e:
        logger.error(f"Ошибка при показе выполненных задач для пользователя {user_id}: {e}")
        await callback.answer(
            "Произошла ошибка при загрузке задач. Попробуйте позже.", show_alert=True
        )

    await callback.answer()


@router.callback_query(F.data == "all_tasks")
async def show_all_tasks(callback: CallbackQuery):
    """Показывает все задачи пользователя (активные и выполненные)"""
    user_id = callback.from_user.id

    try:
        # Получаем активные задачи
        active_tasks = await checklist_db.get_all_tasks(user_id, status="active")
        # Получаем последние выполненные задачи
        completed_tasks = await checklist_db.get_completed_tasks_history(user_id, limit=10)

        text = "<b>📋 Все задачи</b>\n\n"

        if not active_tasks and not completed_tasks:
            text += "У вас пока нет задач.\n\n"
            text += "Создайте новую задачу, чтобы начать!"
        else:
            if active_tasks:
                text += f"<b>Активные ({len(active_tasks)}):</b>\n"
                for task in active_tasks[:10]:  # Показываем до 10 активных
                    priority_emoji = get_priority_emoji(task.get("priority"))
                    text += f"○ {priority_emoji} {task.get('title', 'Без названия')}"
                    if task.get("deadline"):
                        deadline = task["deadline"]
                        text += f" (до {deadline.strftime('%d.%m')})"
                    text += "\n"

                if len(active_tasks) > 10:
                    text += f"... и ещё {len(active_tasks) - 10} активных задач\n"

                text += "\n"

            if completed_tasks:
                text += f"<b>Недавно выполненные ({len(completed_tasks)}):</b>\n"
                for task in completed_tasks[:5]:  # Показываем до 5 выполненных
                    text += f"✓ {task.get('title', 'Без названия')}"
                    if task.get("completed_at"):
                        completed_at = task["completed_at"]
                        text += f" ({completed_at.strftime('%d.%m')})"
                    text += "\n"

                if len(completed_tasks) > 5:
                    text += f"... и ещё {len(completed_tasks) - 5} выполненных задач\n"

        # Используем активные задачи для клавиатуры
        await callback.message.edit_text(
            text, reply_markup=get_tasks_list_keyboard(active_tasks, "all"), parse_mode="HTML"
        )

        total_tasks = len(active_tasks) + len(completed_tasks)
        logger.info(
            f"Показано {total_tasks} задач для пользователя {user_id} (активных: {len(active_tasks)}, выполненных: {len(completed_tasks)})"
        )

    except Exception as e:
        logger.error(f"Ошибка при показе всех задач для пользователя {user_id}: {e}")
        await callback.answer(
            "Произошла ошибка при загрузке задач. Попробуйте позже.", show_alert=True
        )

    await callback.answer()


@router.callback_query(F.data.startswith("view_tasks:"))
async def view_tasks_by_priority(callback: CallbackQuery):
    """Показывает задачи по приоритету"""
    priority = callback.data.split(":")[1]
    user_id = callback.from_user.id

    try:
        if priority == "all":
            tasks = await checklist_db.get_all_tasks(user_id)
            text = "<b>📋 Все задачи</b>\n\n"
        else:
            tasks = await checklist_db.get_tasks_by_priority(user_id, priority)
            priority_name = get_priority_name(priority)
            text = f"<b>{get_priority_emoji(priority)} {priority_name}</b>\n\n"

        if not tasks:
            text += "Задач в этой категории пока нет."
        else:
            for task in tasks:
                status = "✓" if task.get("status") == "completed" else "○"
                text += f"{status} {task.get('title', 'Без названия')}\n"
                if task.get("deadline"):
                    deadline = task["deadline"]
                    text += f"   Дедлайн: {deadline.strftime('%d.%m.%Y')}\n"
                text += "\n"

        await callback.message.edit_text(
            text, reply_markup=get_tasks_list_keyboard(tasks, priority), parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка при просмотре задач: {e}")
        await callback.answer(ERROR_MESSAGES["unknown_error"], show_alert=True)

    await callback.answer()


@router.callback_query(F.data.startswith("tasks_page:"))
async def navigate_tasks_page(callback: CallbackQuery):
    """Навигация по страницам списка задач"""
    parts = callback.data.split(":")
    task_type = parts[1]
    page = int(parts[2])
    user_id = callback.from_user.id

    try:
        # Определяем какие задачи показывать
        if task_type == "active":
            tasks = await checklist_db.get_all_tasks(user_id, status="active")
            text = f"<b>📋 Активные задачи</b>\n"
        elif task_type == "completed":
            tasks = await checklist_db.get_completed_tasks_history(user_id, limit=100)
            text = f"<b>✓ Выполненные задачи</b>\n"
        elif task_type == "all":
            active_tasks = await checklist_db.get_all_tasks(user_id, status="active")
            completed_tasks = await checklist_db.get_completed_tasks_history(user_id, limit=50)
            tasks = active_tasks + completed_tasks
            text = f"<b>📋 Все задачи</b>\n"
        else:
            # Задачи по приоритету
            tasks = await checklist_db.get_tasks_by_priority(user_id, task_type)
            priority_name = get_priority_name(task_type)
            text = f"<b>{get_priority_emoji(task_type)} {priority_name}</b>\n"

        tasks_per_page = 10
        total_tasks = len(tasks)
        total_pages = (total_tasks + tasks_per_page - 1) // tasks_per_page

        text += f"Страница {page} из {total_pages}\n\n"

        if not tasks:
            text += "Задач в этой категории пока нет."
        else:
            start_idx = (page - 1) * tasks_per_page
            end_idx = min(start_idx + tasks_per_page, total_tasks)

            for i, task in enumerate(tasks[start_idx:end_idx], start=start_idx + 1):
                status = "✓" if task.get("status") == "completed" else "○"
                text += f"{i}. {status} {task.get('title', 'Без названия')}\n"
                if task.get("deadline"):
                    deadline = task["deadline"]
                    text += f"   Дедлайн: {deadline.strftime('%d.%m.%Y')}\n"

        await callback.message.edit_text(
            text, reply_markup=get_tasks_list_keyboard(tasks, task_type, page), parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Ошибка при навигации по страницам задач: {e}")
        await callback.answer("Произошла ошибка при загрузке страницы", show_alert=True)

    await callback.answer()


@router.callback_query(F.data == "current_page")
async def show_current_page(callback: CallbackQuery):
    """Обработчик для кнопки с номером текущей страницы"""
    await callback.answer("Текущая страница")


@router.callback_query(F.data == "no_tasks")
async def handle_no_tasks(callback: CallbackQuery):
    """Обработчик для пустого списка задач"""
    await callback.answer("Создайте новую задачу, чтобы начать работу!")


# === РАБОТА С ЗАДАЧЕЙ ===


@router.callback_query(F.data.startswith("task_detail:"))
async def view_task_from_list(callback: CallbackQuery):
    """Показывает детали задачи из списка"""
    task_id = callback.data.split(":")[1]
    user_id = callback.from_user.id

    try:
        task = await checklist_db.get_task(user_id, task_id)
        if not task:
            await callback.answer("Задача не найдена", show_alert=True)
            await callback.message.edit_text(
                "Задача не найдена. Возможно, она была удалена.",
                reply_markup=get_checklist_menu_keyboard(),
            )
            return

        priority_emoji = get_priority_emoji(task.get("priority"))
        priority_name = get_priority_name(task.get("priority"))

        text = f"<b>{task.get('title', 'Без названия')}</b>\n\n"

        if task.get("description"):
            text += f"<i>{task['description']}</i>\n\n"

        text += f"{priority_emoji} Приоритет: {priority_name}\n"

        if task.get("deadline"):
            deadline = task["deadline"]
            text += f"📅 Дедлайн: {deadline.strftime('%d.%m.%Y')}\n"

        if task.get("created_at"):
            created_at = task["created_at"]
            text += f"📝 Создано: {created_at.strftime('%d.%m.%Y %H:%M')}\n"

        if task.get("status") == "completed":
            text += f"\n✓ Выполнено"
            if task.get("completed_at"):
                text += f": {task['completed_at'].strftime('%d.%m.%Y %H:%M')}"

        # Используем правильное поле для проверки статуса
        is_completed = task.get("status") == "completed"

        await callback.message.edit_text(
            text, reply_markup=get_task_actions_keyboard(task_id, is_completed), parse_mode="HTML"
        )
        logger.info(f"Показаны детали задачи {task_id} для пользователя {user_id}")

    except Exception as e:
        logger.error(f"Ошибка при показе деталей задачи {task_id} для пользователя {user_id}: {e}")
        await callback.answer("Произошла ошибка при загрузке задачи", show_alert=True)

    await callback.answer()


@router.callback_query(F.data.startswith("task:"))
async def view_task_details(callback: CallbackQuery):
    """Показывает детали задачи"""
    task_id = callback.data.split(":")[1]
    user_id = callback.from_user.id

    try:
        task = await checklist_db.get_task(user_id, task_id)
        if not task:
            await callback.answer("Задача не найдена", show_alert=True)
            return

        priority_emoji = get_priority_emoji(task.get("priority"))
        priority_name = get_priority_name(task.get("priority"))

        text = f"<b>{task.get('title', 'Без названия')}</b>\n\n"

        if task.get("description"):
            text += f"<i>{task['description']}</i>\n\n"

        text += f"{priority_emoji} Приоритет: {priority_name}\n"

        if task.get("deadline"):
            deadline = task["deadline"]
            text += f"Дедлайн: {deadline.strftime('%d.%m.%Y')}\n"

        is_completed = task.get("status") == "completed"
        if is_completed and task.get("completed_at"):
            text += f"\n✓ Выполнено: {task['completed_at'].strftime('%d.%m.%Y %H:%M')}"

        await callback.message.edit_text(
            text, reply_markup=get_task_actions_keyboard(task_id, is_completed), parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка при показе деталей задачи: {e}")
        await callback.answer(ERROR_MESSAGES["unknown_error"], show_alert=True)

    await callback.answer()


@router.callback_query(F.data.startswith("complete_task:"))
async def complete_task(callback: CallbackQuery):
    """Отмечает задачу как выполненную"""
    user_id = callback.from_user.id
    task_id = callback.data.split(":")[1]

    try:
        success, points = await checklist_db.complete_task(user_id, task_id)

        if success:
            # Выбираем случайное мотивационное сообщение
            message = random.choice(COMPLETION_MESSAGES)

            # Проверяем достижения, связанные со временем
            time_achievements = await gamification_db.check_time_based_achievements(
                user_id, "task_completed"
            )

            # Проверяем общие достижения
            new_achievements = await gamification_db.check_and_unlock_achievements(user_id)
            all_new_achievements = time_achievements + new_achievements

            # removed: убрано отображение очков за задачи
            await callback.message.edit_text(
                f"{message}\n\n"
                # f"🏆 Заработано очков: {points}\n\n"  # bugfix: строка закомментирована
                f"Так держать! Выбери следующую задачу:",
                reply_markup=get_checklist_menu_keyboard(),
                parse_mode="HTML",
            )

            # removed: убрано уведомление об очках
            # await callback.answer(f"+{points} очков! 🎉", show_alert=True)
            await callback.answer(
                "Задача выполнена!", show_alert=True
            )  # bugfix: без упоминания очков

            # Показываем новые достижения
            if all_new_achievements:
                await show_new_achievements(callback.message, all_new_achievements)
        else:
            await callback.answer("Не удалось выполнить задачу", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка при выполнении задачи: {e}")
        await callback.answer(ERROR_MESSAGES["unknown_error"], show_alert=True)


# === УДАЛЕНИЕ ЗАДАЧИ ===


@router.callback_query(F.data.startswith("delete_task:"))
async def confirm_delete_task(callback: CallbackQuery):
    """Запрашивает подтверждение удаления"""
    task_id = callback.data.split(":")[1]

    await callback.message.edit_text(
        "<b>Подтверждение удаления</b>\n\n" "Вы уверены, что хотите удалить эту задачу?",
        reply_markup=get_confirmation_keyboard(),
        parse_mode="HTML",
    )

    # Сохраняем task_id для следующего шага
    await callback.message.edit_reply_markup(
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✓ Да", callback_data=f"confirm_delete:{task_id}"),
                    InlineKeyboardButton(text="✗ Нет", callback_data=f"task:{task_id}"),
                ]
            ]
        )
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete:"))
async def delete_task(callback: CallbackQuery):
    """Удаляет задачу"""
    user_id = callback.from_user.id
    task_id = callback.data.split(":")[1]

    try:
        success = await checklist_db.delete_task(user_id, task_id)

        if success:
            await callback.message.edit_text(
                "Задача удалена.", reply_markup=get_checklist_menu_keyboard(), parse_mode="HTML"
            )
            await callback.answer("Удалено", show_alert=True)
        else:
            await callback.answer("Не удалось удалить задачу", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка при удалении задачи: {e}")
        await callback.answer(ERROR_MESSAGES["unknown_error"], show_alert=True)


# === РЕДАКТИРОВАНИЕ ЗАДАЧИ ===


@router.callback_query(F.data.startswith("edit_task:"))
async def start_edit_task(callback: CallbackQuery, state: FSMContext):
    """Начинает процесс редактирования задачи"""
    task_id = callback.data.split(":")[1]
    user_id = callback.from_user.id

    try:
        # Получаем задачу
        task = await checklist_db.get_task(user_id, task_id)
        if not task:
            await callback.answer("Задача не найдена", show_alert=True)
            return

        # Сохраняем данные задачи в состоянии
        await state.update_data(task_id=task_id, task_data=task)

        await callback.message.edit_text(
            f"<b>Редактирование задачи</b>\n\n"
            f"Задача: {task.get('title', 'Без названия')}\n\n"
            f"Выберите, что хотите изменить:",
            reply_markup=get_edit_field_keyboard(task_id),
            parse_mode="HTML",
        )

        await state.set_state(TaskEditStates.selecting_field)

    except Exception as e:
        logger.error(f"Ошибка при начале редактирования задачи {task_id}: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)

    await callback.answer()


@router.callback_query(F.data.startswith("edit_field:"), TaskEditStates.selecting_field)
async def select_field_to_edit(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор поля для редактирования"""
    parts = callback.data.split(":")
    field = parts[1]
    task_id = parts[2]

    data = await state.get_data()
    task_data = data.get("task_data", {})

    if field == "title":
        await callback.message.answer(
            f"<b>Редактирование названия</b>\n\n"
            f"Текущее название: {task_data.get('title', 'Без названия')}\n\n"
            f"Введите новое название:",
            reply_markup=get_cancel_edit_keyboard(task_id),
            parse_mode="HTML",
        )
        await callback.message.delete()
        await state.set_state(TaskEditStates.waiting_for_new_title)

    elif field == "description":
        current_desc = task_data.get("description", "Нет описания")
        await callback.message.answer(
            f"<b>Редактирование описания</b>\n\n"
            f"Текущее описание: {current_desc}\n\n"
            f"Введите новое описание (или точку для удаления):",
            reply_markup=get_cancel_edit_keyboard(task_id),
            parse_mode="HTML",
        )
        await callback.message.delete()
        await state.set_state(TaskEditStates.waiting_for_new_description)

    elif field == "priority":
        current_priority = get_priority_name(task_data.get("priority"))
        await callback.message.edit_text(
            f"<b>Изменение приоритета</b>\n\n"
            f"Текущий приоритет: {current_priority}\n\n"
            f"Выберите новый приоритет:",
            reply_markup=get_priority_keyboard(),
            parse_mode="HTML",
        )
        await state.set_state(TaskEditStates.waiting_for_new_priority)

    elif field == "deadline":
        current_deadline = task_data.get("deadline")
        deadline_text = (
            current_deadline.strftime("%d.%m.%Y") if current_deadline else "Не установлен"
        )
        await callback.message.edit_text(
            f"<b>Изменение дедлайна</b>\n\n"
            f"Текущий дедлайн: {deadline_text}\n\n"
            f"Выберите новый дедлайн:",
            reply_markup=get_deadline_keyboard(),
            parse_mode="HTML",
        )
        await state.set_state(TaskEditStates.waiting_for_new_deadline)

    await callback.answer()


@router.message(TaskEditStates.waiting_for_new_title)
async def process_new_title(message: Message, state: FSMContext):
    """Обрабатывает новое название задачи"""
    if message.text == "Отмена":
        await cancel_edit_task(message, state)
        return

    data = await state.get_data()
    task_id = data.get("task_id")
    user_id = message.from_user.id

    try:
        # Обновляем задачу
        success = await checklist_db.update_task(user_id, task_id, {"title": message.text})

        if success:
            await message.answer(
                f"✓ Название задачи обновлено.\n\n" f"Новое название: {message.text}",
                reply_markup=get_main_menu_keyboard(),
            )
            logger.info(f"Название задачи {task_id} обновлено пользователем {user_id}")
        else:
            await message.answer("Не удалось обновить задачу")

        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка при обновлении названия задачи: {e}")
        await message.answer("Произошла ошибка при обновлении")
        await state.clear()


@router.message(TaskEditStates.waiting_for_new_description)
async def process_new_description(message: Message, state: FSMContext):
    """Обрабатывает новое описание задачи"""
    if message.text == "Отмена":
        await cancel_edit_task(message, state)
        return

    data = await state.get_data()
    task_id = data.get("task_id")
    user_id = message.from_user.id

    # Если точка - удаляем описание
    description = "" if message.text == "." else message.text

    try:
        success = await checklist_db.update_task(user_id, task_id, {"description": description})

        if success:
            desc_text = "удалено" if description == "" else f"обновлено:\n{description}"
            await message.answer(
                f"✓ Описание задачи {desc_text}", reply_markup=get_main_menu_keyboard()
            )
            logger.info(f"Описание задачи {task_id} обновлено пользователем {user_id}")
        else:
            await message.answer("Не удалось обновить задачу")

        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка при обновлении описания задачи: {e}")
        await message.answer("Произошла ошибка при обновлении")
        await state.clear()


@router.callback_query(F.data.startswith("priority:"), TaskEditStates.waiting_for_new_priority)
async def process_new_priority(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает новый приоритет задачи"""
    priority = callback.data.split(":")[1]
    data = await state.get_data()
    task_id = data.get("task_id")
    user_id = callback.from_user.id

    try:
        success = await checklist_db.update_task(user_id, task_id, {"priority": priority})

        if success:
            priority_name = get_priority_name(priority)
            await callback.message.edit_text(
                f"✓ Приоритет задачи обновлен.\n\n" f"Новый приоритет: {priority_name}",
                reply_markup=get_checklist_menu_keyboard(),
                parse_mode="HTML",
            )
            logger.info(f"Приоритет задачи {task_id} обновлен пользователем {user_id}")
        else:
            await callback.answer("Не удалось обновить задачу", show_alert=True)

        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка при обновлении приоритета задачи: {e}")
        await callback.answer("Произошла ошибка при обновлении", show_alert=True)
        await state.clear()

    await callback.answer()


@router.callback_query(F.data.startswith("deadline:"), TaskEditStates.waiting_for_new_deadline)
async def process_new_deadline(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает новый дедлайн задачи"""
    deadline_type = callback.data.split(":")[1]
    data = await state.get_data()
    task_id = data.get("task_id")
    user_id = callback.from_user.id

    # Вычисляем дедлайн
    deadline = None
    deadline_text = "не установлен"

    if deadline_type == "today":
        deadline = datetime.utcnow().replace(hour=23, minute=59, second=59)
        deadline_text = "сегодня"
    elif deadline_type == "tomorrow":
        deadline = datetime.utcnow() + timedelta(days=1)
        deadline_text = "завтра"
    elif deadline_type == "3days":
        deadline = datetime.utcnow() + timedelta(days=3)
        deadline_text = "через 3 дня"
    elif deadline_type == "week":
        deadline = datetime.utcnow() + timedelta(weeks=1)
        deadline_text = "через неделю"
    elif deadline_type == "month":
        deadline = datetime.utcnow() + timedelta(days=30)
        deadline_text = "через месяц"

    try:
        success = await checklist_db.update_task(user_id, task_id, {"deadline": deadline})

        if success:
            await callback.message.edit_text(
                f"✓ Дедлайн задачи обновлен.\n\n" f"Новый дедлайн: {deadline_text}",
                reply_markup=get_checklist_menu_keyboard(),
                parse_mode="HTML",
            )
            logger.info(f"Дедлайн задачи {task_id} обновлен пользователем {user_id}")
        else:
            await callback.answer("Не удалось обновить задачу", show_alert=True)

        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка при обновлении дедлайна задачи: {e}")
        await callback.answer("Произошла ошибка при обновлении", show_alert=True)
        await state.clear()

    await callback.answer()


async def cancel_edit_task(message: Message, state: FSMContext):
    """Отменяет редактирование задачи"""
    await state.clear()
    await message.answer("Редактирование отменено.", reply_markup=get_main_menu_keyboard())


@router.callback_query(F.data == "cancel_task_creation", StateFilter(TaskEditStates))
async def cancel_edit_task_callback(callback: CallbackQuery, state: FSMContext):
    """Отменяет редактирование задачи (callback версия)"""
    await state.clear()
    await callback.message.edit_text(
        "Редактирование отменено.", reply_markup=get_checklist_menu_keyboard()
    )
    await callback.answer()


# === СТАТИСТИКА ===


@router.callback_query(F.data == "checklist_stats")
async def show_checklist_stats(callback: CallbackQuery):
    """Показывает статистику чек-листа"""
    user_id = callback.from_user.id

    try:
        stats = await checklist_db.get_user_stats(user_id)
        history = await checklist_db.get_completed_tasks_history(user_id, limit=10)

        text = f"<b>📊 Статистика чек-листа</b>\n\n"

        # Общая статистика
        text += f"• Выполнено задач: {stats.get('total_completed', 0)}\n"
        text += f"• Заработано очков: {stats.get('total_points', 0)}\n"
        text += f"• Текущая серия: {stats.get('current_streak', 0)} дней\n"
        text += f"• Лучшая серия: {stats.get('best_streak', 0)} дней\n\n"

        # По приоритетам
        text += "<b>По приоритетам:</b>\n"
        priority_stats = stats.get("completed_by_priority", {})
        text += f"• Важно и срочно: {priority_stats.get('urgent_important', 0)}\n"
        text += f"• Важно, не срочно: {priority_stats.get('not_urgent_important', 0)}\n"
        text += f"• Срочно, не важно: {priority_stats.get('urgent_not_important', 0)}\n"
        text += f"• Не важно, не срочно: {priority_stats.get('not_urgent_not_important', 0)}\n"

        # История
        if history:
            text += "\n<b>Последние выполненные:</b>\n"
            for task in history[:5]:
                title = task.get("title", "Без названия")
                text += f"• {title}\n"

        # Сдержанное мотивационное сообщение
        total = stats.get("total_completed", 0)
        if total >= 100:
            text += "\nВыдающийся результат."
        elif total >= 50:
            text += "\nОтличный прогресс."
        elif total >= 20:
            text += "\nХороший темп работы."
        elif total >= 5:
            text += "\nНеплохое начало."

        await callback.message.edit_text(
            text, reply_markup=get_checklist_menu_keyboard(), parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Ошибка при показе статистики: {e}")
        await callback.answer(ERROR_MESSAGES["unknown_error"], show_alert=True)

    await callback.answer()


# === ПОМОЩЬ ===


@router.callback_query(F.data == "checklist_help")
async def show_checklist_help(callback: CallbackQuery):
    """Показывает справку по чек-листу"""
    text = """<b>Матрица Эйзенхауэра</b>

Инструмент для приоритизации задач по двум критериям: важность и срочность.

<b>Квадранты матрицы:</b>
• Важно и срочно — кризисные ситуации, дедлайны
• Важно, не срочно — планирование, развитие, профилактика
• Срочно, не важно — прерывания, некоторые звонки и письма
• Не важно, не срочно — развлечения, пустые разговоры

Фокусируйтесь на квадранте "Важно, не срочно" для долгосрочной эффективности."""

    await callback.message.edit_text(
        text, reply_markup=get_checklist_menu_keyboard(), parse_mode="HTML"
    )
    await callback.answer()


# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===


async def cancel_task_creation(message: Message, state: FSMContext):
    """Отменяет создание задачи"""
    await state.clear()
    await message.answer("Создание задачи отменено.", reply_markup=get_main_menu_keyboard())


@router.callback_query(F.data == "cancel_task_creation")
async def cancel_task_creation_callback(callback: CallbackQuery, state: FSMContext):
    """Отменяет создание задачи (callback версия)"""
    await state.clear()
    await callback.message.edit_text(
        "Создание задачи отменено.", reply_markup=get_checklist_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_main")
async def back_to_main_menu(callback: CallbackQuery):
    """Возврат в главное меню"""
    await callback.message.answer("Главное меню", reply_markup=get_main_menu_keyboard())
    await callback.message.delete()
    await callback.answer()
