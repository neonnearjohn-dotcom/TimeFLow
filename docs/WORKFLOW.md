# Рабочий процесс

## Инварианты
- Python 3.12; aiogram 3.4.x; Firestore; async only.
- Без time.sleep/блокирующих вызовов.
- Транзакции Firestore и атомарные инкременты для счётчиков.
- Анти‑абьюз: идемпотентность/дедупликация/rate‑limit.
- CI: ruff, black --check, pytest; CD: SSH + systemd; post‑deploy `/health`.

## Шаги задачи
1) GPT‑5 пишет Issue (см. шаблон) и ТЗ.
2) Claude реализует минимальный патч по ТЗ.
3) Codex делает ревью и дописывает тесты.
4) Автор правит замечания → merge.
5) Автодеплой на main → проверка smoke и метрик.
6) GPT‑5 обновляет Snapshot и Decision log.

## Коммиты
- Conventional Commits: feat:/fix:/refactor:/chore:/test:/docs:.
- Ruff+Black обязательны; типы (type hints) везде; pytest.
