import json
import os
import subprocess
import sys
import asyncio
from telethon import TelegramClient, events
import time

# Список необходимых пакетов
required_packages = [
    'telethon',  # Библиотека для работы с Telegram API
    'requests'   # Если используете запросы для обновлений или других целей
]

# Функция для проверки и установки недостающих пакетов
def check_install(package):
    try:
        __import__(package)
    except ImportError:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
        print(f"Пакет {package} успешно установлен.")
    else:
        print(f"Пакет {package} уже установлен.")

# Устанавливаем все необходимые пакеты
for package in required_packages:
    check_install(package)

# Функция для автоматического обновления из GitHub
def update_from_git():
    try:
        print("Проверка наличия обновлений...")
        # Если репозиторий является git-репозиторием, выполняем pull
        result = subprocess.run(["git", "pull"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            print("Обновления успешно загружены!")
        else:
            print(f"Ошибка при загрузке обновлений: {result.stderr.decode('utf-8')}")
    except Exception as e:
        print(f"Не удалось выполнить обновление: {e}")

# Выполнение обновлений перед запуском
update_from_git()

# Файл для хранения данных
CONFIG_FILE = 'config.json'

# Проверяем, существует ли файл конфигурации и загружаем его
if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        API_ID = config['api_id']
        API_HASH = config['api_hash']
        PHONE_NUMBER = config['phone_number']
        print(f"Данные загружены из конфигурации: API_ID={API_ID}, API_HASH={API_HASH}, PHONE_NUMBER={PHONE_NUMBER}")
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Ошибка в файле конфигурации: {e}")
        sys.exit(1)  # Останавливаем выполнение, если файл поврежден
else:
    # Запрашиваем у пользователя данные (если файла конфигурации нет)
    print("Файл конфигурации не найден, необходимо ввести данные вручную.")
    
    while True:
        try:
            API_ID = int(input("Введите ваш API ID: "))
            break
        except ValueError:
            print("API ID должен быть числом. Попробуйте снова.")

    API_HASH = input("Введите ваш API Hash: ").strip()
    while True:
        PHONE_NUMBER = input("Введите ваш номер телефона (в формате +375XXXXXXXXX, +7XXXXXXXXXX): ").strip()
        if PHONE_NUMBER.startswith('+') and len(PHONE_NUMBER) > 10:
            break
        else:
            print("Неверный формат номера телефона. Попробуйте снова.")

    with open(CONFIG_FILE, 'w') as f:
        json.dump({'api_id': API_ID, 'api_hash': API_HASH, 'phone_number': PHONE_NUMBER}, f)
    print(f"Данные сохранены в конфигурации: API_ID={API_ID}, API_HASH={API_HASH}, PHONE_NUMBER={PHONE_NUMBER}")

# Инициализация клиента
client = TelegramClient('sessions', API_ID, API_HASH)

# Устанавливаем стандартную скорость печатания 0.4
typing_speed = 0.4

# Доступные анимации (оставлены только анимации 1 и 2)
animations = {
    1: "Засветка",
    2: "Секретный код",
}

# Реализация анимаций
async def animate_brightness(event, text):
    for i in range(len(text) + 1):
        await event.edit("░" * (len(text) - i) + text[:i])
        await asyncio.sleep(typing_speed)

async def animate_secret_code(event, text):
    import random
    for i in range(len(text) + 1):
        fake_text = ''.join(random.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(len(text)))
        await event.edit(fake_text[:i] + text[i:])
        await asyncio.sleep(typing_speed)
    await event.edit(text)

animation_functions = {
    1: animate_brightness,
    2: animate_secret_code,
}

# Переменная для текущей анимации
current_animation = 1
# Флаг для отображения выбора анимации
awaiting_animation_choice = False
start_time = time.time()

# Обработчик команд
@client.on(events.NewMessage(outgoing=True))
async def handler(event):
    global current_animation, awaiting_animation_choice, start_time

    # Проверка на таймаут при ожидании выбора анимации
    timeout = 30  # Таймаут в секундах
    if awaiting_animation_choice and time.time() - start_time > timeout:
        awaiting_animation_choice = False  # Сбросим, если пользователь не ответил за 30 секунд
        await event.respond("Время выбора анимации вышло. Повторите попытку.")

    # Обработка команды "001" для вывода доступных анимаций
    if event.raw_text == "001":
        animations_list = "\n".join([f"{key}) {value}" for key, value in animations.items()])
        message = await event.respond(f"Доступные анимации:\n{animations_list}\nВыберите номер анимации:")
        # Запоминаем сообщение, чтобы удалить его после выбора анимации
        awaiting_animation_choice = True
        start_time = time.time()
        return

    # Обработка выбора анимации
    elif awaiting_animation_choice:
        if event.raw_text.isdigit():
            choice = int(event.raw_text)
            if choice in animations:
                current_animation = choice
                awaiting_animation_choice = False
                start_time = time.time()  # сбросим таймер
                # После выбора анимации удалим сообщение с выбором анимации
                await event.delete()  # Удаляем сообщение с разделом анимаций
                # Отправляем сообщение о выбранной анимации
                await event.respond(f"Вы выбрали анимацию: {animations[choice]}\n"
                                    "Чтобы анимировать текст, отправьте команду /p <ваш текст>")
            else:
                await event.respond("Неверный номер анимации. Попробуйте снова.")
        else:
            await event.respond("Пожалуйста, введите числовое значение для выбора анимации.")

    # Обработка команды смены анимации
    elif event.raw_text.isdigit():
        choice = int(event.raw_text)
        if choice in animations:
            current_animation = choice
            await event.respond(f"Анимация изменена на: {animations[choice]}")
        else:
            await event.respond("Неверный номер анимации. Пожалуйста, выберите существующую анимацию.")

    elif event.raw_text.startswith('/p '):
        text_to_animate = event.raw_text[3:].strip()  # Убираем лишние пробелы
        if not text_to_animate:
            await event.edit("Ошибка: Текст для анимации не может быть пустым.")
            return
        if len(text_to_animate) > 200:
            await event.edit("Ошибка: текст слишком длинный. Используйте текст до 200 символов.")
            return

        try:
            await animation_functions[current_animation](event, text_to_animate)
        except Exception as e:
            print(f"Ошибка при выполнении анимации: {e}")
            await event.edit(f"Произошла ошибка при выполнении анимации: {e}")

# Главная асинхронная функция
async def main():
    print("Запуск main()")
    await client.start(phone=PHONE_NUMBER)
    print("Скрипт успешно запущен! Отправьте команду '001' для выбора анимации.")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
