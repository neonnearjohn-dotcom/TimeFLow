# fix_assistant.py
import fileinput
import sys

# Читаем файл utils/openai_api.py
with open("utils/openai_api.py", "r", encoding="utf-8") as f:
    content = f.read()

# Находим класс OpenAIAssistant и добавляем метод
if "def has_api_key" not in content:
    # Находим место после __init__ метода
    lines = content.split("\n")
    new_lines = []
    for i, line in enumerate(lines):
        new_lines.append(line)
        # Если нашли конец __init__ метода
        if "self.is_configured" in line and i < len(lines) - 1:
            # Добавляем метод has_api_key
            new_lines.extend(
                [
                    "",
                    "    def has_api_key(self) -> bool:",
                    '        """Проверяет наличие API ключа"""',
                    "        return self.is_configured",
                ]
            )

    # Записываем обратно
    with open("utils/openai_api.py", "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines))

    print("✅ Метод has_api_key добавлен в OpenAIAssistant")
else:
    print("✅ Метод has_api_key уже существует")
