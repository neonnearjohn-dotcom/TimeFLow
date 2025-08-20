"""
Тестирование работы OpenAI API через прокси
"""

import os
import asyncio
import httpx
from dotenv import load_dotenv

load_dotenv()


async def test_proxy():
    """Тест прокси-сервера"""
    proxy_url = os.getenv("PROXY_URL")

    if not proxy_url:
        print("❌ PROXY_URL не найден в .env файле")
        print("Добавьте в .env файл:")
        print("PROXY_URL=http://your-proxy:port")
        print("или")
        print("PROXY_URL=socks5://your-proxy:port")
        return False

    print(f"🔍 Тестирую прокси: {proxy_url}")

    try:
        async with httpx.AsyncClient(proxies=proxy_url, timeout=10.0) as client:
            response = await client.get("http://httpbin.org/ip")
            data = response.json()
            print(f"✅ Прокси работает! Ваш IP через прокси: {data['origin']}")
            return True
    except Exception as e:
        print(f"❌ Ошибка прокси: {e}")
        return False


async def test_openai():
    """Тест OpenAI API"""
    api_key = os.getenv("OPENAI_API_KEY")
    proxy_url = os.getenv("PROXY_URL")

    if not api_key or api_key == "ваш_ключ_api_от_openai":
        print("❌ OPENAI_API_KEY не найден или не настроен в .env файле")
        print("Добавьте в .env файл:")
        print("OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx")
        return

    print("\n🤖 Тестирую OpenAI API...")

    try:
        import openai

        # Создаем клиента с прокси
        if proxy_url:
            http_client = httpx.AsyncClient(proxies=proxy_url, timeout=30.0)
            client = openai.AsyncOpenAI(api_key=api_key, http_client=http_client)
            print(f"📡 Используется прокси: {proxy_url}")
        else:
            client = openai.AsyncOpenAI(api_key=api_key)
            print("📡 Прямое подключение (без прокси)")

        # Делаем тестовый запрос
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Ты помощник. Отвечай кратко."},
                {"role": "user", "content": "Скажи 'Привет, я работаю!' на русском"},
            ],
            max_tokens=50,
        )

        answer = response.choices[0].message.content
        print(f"✅ OpenAI API работает!")
        print(f"📝 Ответ: {answer}")
        print(f"💰 Использовано токенов: {response.usage.total_tokens}")

    except Exception as e:
        print(f"❌ Ошибка OpenAI API: {e}")

        if "Connection error" in str(e):
            print("\n💡 Возможные решения:")
            print("1. Проверьте интернет-соединение")
            print("2. Проверьте правильность прокси")
            print("3. Попробуйте другой прокси-сервер")
        elif "Incorrect API key" in str(e):
            print("\n💡 Проверьте API ключ в .env файле")
        elif "Rate limit" in str(e):
            print("\n💡 Превышен лимит запросов. Подождите немного.")


async def main():
    print("=== ТЕСТИРОВАНИЕ OPENAI С ПРОКСИ ===\n")

    # Показываем текущие настройки
    print("📋 Текущие настройки:")
    print(
        f"OPENAI_API_KEY: {'✅ Установлен' if os.getenv('OPENAI_API_KEY') else '❌ Не установлен'}"
    )
    print(f"PROXY_URL: {os.getenv('PROXY_URL') or '❌ Не установлен'}")

    # Тестируем прокси
    if os.getenv("PROXY_URL"):
        proxy_works = await test_proxy()
        if not proxy_works:
            print("\n⚠️ Прокси не работает. OpenAI API может быть недоступен.")

    # Тестируем OpenAI
    await test_openai()

    print("\n=== ТЕСТ ЗАВЕРШЕН ===")


if __name__ == "__main__":
    asyncio.run(main())
