# TimeFlow Bot on TimeWeb Ubuntu 24.04

## 1. Создание инстанса
1. В панели TimeWeb создайте VPS с Ubuntu 24.04.
2. В поле *cloud-init* вставьте содержимое файла `cloud-init.yaml` из этого репозитория (раздел **Deploy**).
3. Укажите свой SSH‑ключ в секции `ssh_authorized_keys`.

## 2. Где лежит код
Cloud‑init клонирует репозиторий в `/opt/TimeFLow` и создаёт виртуальное окружение в `/opt/TimeFLow/venv`.
Сервис `timeflow.service` запускает файл `main.py` через systemd и перезапускается автоматически.

## 3. Настройка секретов
1. Скопируйте файл сервисного аккаунта Firestore в `/opt/TimeFLow/service-account.json` и установите права `600`.
2. Создайте `/opt/TimeFLow/.env` на основе `.env.example`:
   ```
   BOT_TOKEN=...
   OPENAI_API_KEY=...
   OPENAI_MODEL=gpt-4o-mini
   OPENAI_PROXY=http://user:pass@host:port  # опционально
   GOOGLE_APPLICATION_CREDENTIALS=/opt/TimeFLow/service-account.json
   FIREBASE_PROJECT_ID=...
   ```
3. Убедитесь, что в файле нет BOM и строк с CRLF.
4. Перезапустите сервис: `sudo systemctl restart timeflow`.

## 4. Управление сервисом
- Проверить статус: `sudo systemctl status timeflow`
- Просмотреть логи: `journalctl -u timeflow -f`
- Перезапустить: `sudo systemctl restart timeflow`

## 5. Диагностика
- Проверка Telegram‑токена:
  `curl https://api.telegram.org/bot$BOT_TOKEN/getMe`
- Проверка OpenAI через прокси:
  ```bash
  curl --proxy $OPENAI_PROXY https://api.openai.com/v1/models \
       -H "Authorization: Bearer $OPENAI_API_KEY"
  ```
- Скрипт самопроверки:
  ```bash
  cd /opt/TimeFLow
  MOCK_MODE=1 venv/bin/python scripts/self_check.py
  ```

### Частые ошибки
- BOM или CRLF в `.env` — используйте UTF‑8 без BOM и переводы строк `\n`.
- Неверный путь к `service-account.json` — должен совпадать с переменной `GOOGLE_APPLICATION_CREDENTIALS`.
- Глобальные прокси мешают Telegram/Firestore — задавайте прокси только через `OPENAI_PROXY`.
- Неверный формат `OPENAI_PROXY` — используйте `http://user:pass@host:port`.
