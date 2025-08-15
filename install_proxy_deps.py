"""
Установка дополнительных зависимостей для работы с прокси
"""
import subprocess
import sys

print("=== УСТАНОВКА ЗАВИСИМОСТЕЙ ДЛЯ ПРОКСИ ===\n")

packages = [
    ("httpx[socks]", "Для поддержки SOCKS5 прокси"),
    ("python-socks", "Дополнительная поддержка SOCKS"),
]

for package, description in packages:
    print(f"📦 Устанавливаю {package} - {description}")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ {package} установлен\n")
    except subprocess.CalledProcessError:
        print(f"❌ Ошибка установки {package}\n")

print("\n✅ Установка завершена!")
print("\n📝 Теперь добавьте в .env файл:")
print("PROXY_URL=http://proxy-server:port")
print("# или для SOCKS5:")
print("PROXY_URL=socks5://proxy-server:port")