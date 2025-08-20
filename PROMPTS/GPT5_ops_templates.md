# GPT‑5 Ops Templates

## 1) Снапшот проекта (вставляй в новый чат перед работой)
**Дата:** {{YYYY‑MM‑DD}}  
**Репозиторий/ветка:** {{repo}} / {{branch}}  
**Состояние:** кратко, 5‑10 строк.

### Текущее
- Ключевые фичи и их статус
- Открытые PR/Issue
- Риски/блокеры

### Решения (Decision log)
- {{дата}} — {{краткое решение}} — {{почему}}

### Метрики/операции
- Версия бота задеплоена: {{commit}}; health: OK/FAIL
- Ошибки OpenAI, среднее время ответа, уведомления Pomodoro

### Следующие шаги
- [ ] Шаг 1
- [ ] Шаг 2

## 2) ТЗ шаблон (для передачи Claude)
Смотри `PROMPTS/CLAUDE_architect_task_template.md`.

## 3) Чек‑лист CI/CD
- PR: ruff, black --check, pytest
- main: автодеплой, systemd restart, post‑deploy `/health`
