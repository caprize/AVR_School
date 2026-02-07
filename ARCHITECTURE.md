# Архитектура Chemistry Bot

## 📁 Структура проекта

```
avr_bot/
├── bot.py                    # Основной Telegram бот
├── database.py               # Менеджер базы данных Redis
├── admin_cli.py              # CLI для администраторов
├── config.json               # Конфигурация (токен, ID админа)
├── requirements.txt          # Python зависимости
├── setup.sh                  # Скрипт установки
├── lectures/                 # Папка хранения файлов лекций
├── readme.md                 # Исходное ТЗ
├── PROJECT_README.md         # Основная документация
├── QUICKSTART.md             # Быстрый старт
├── EXAMPLES.md               # Примеры использования
├── ARCHITECTURE.md           # Этот файл
├── test_database.py          # Тесты базы данных
├── test_integration.py       # Интеграционные тесты
└── .gitignore               # Git ignore список
```

## 🏗️ Архитектура системы

```
┌─────────────────────────────────────────────────────────┐
│                   Telegram Clients                       │
│        (Admin Users & Student Users)                    │
└────────────────┬────────────────────────────────────────┘
                 │
                 │ Telegram Bot API
                 │
         ┌───────▼──────────┐
         │    bot.py        │  ← Основной бот
         │  (Handler Layer) │     обработчик команд
         └───────┬──────────┘
                 │
         ┌───────▼────────────┐
         │  database.py       │  ← DatabaseManager
         │ (Abstraction Layer)│     CRUD операции
         └───────┬────────────┘
                 │
         ┌───────▼────────────┐
         │    Redis DB        │  ← Хранилище данных
         │  (Data Layer)      │     Ключ-значение БД
         └────────────────────┘

┌─────────────────────────────────────────────────────────┐
│              admin_cli.py                                │
│      (Administrative Interface)                          │
└────────────────┬────────────────────────────────────────┘
                 │
         ┌───────▼────────────┐
         │  database.py       │
         │ (Abstraction Layer)│
         └───────┬────────────┘
                 │
         ┌───────▼────────────┐
         │    Redis DB        │
         └────────────────────┘
```

## 📊 Компоненты системы

### 1. **bot.py** - Основной Telegram бот
- Роль: Взаимодействие с пользователями через Telegram
- Функции:
  - Обработка команды `/start`
  - Отправка меню администратора и студентов
  - Обработка нажатий кнопок (InlineKeyboardButton)
  - Загрузка файлов лекций
  - Авторизация по user_id

```python
async def start()           # Инициализация бота
async def show_admin_menu() # Меню администратора
async def show_student_menu() # Меню студента
async def button_callback()   # Обработка кнопок
async def handle_message()    # Обработка текста
async def handle_document()   # Загрузка файлов
```

### 2. **database.py** - Менеджер базы данных
- Роль: Абстракция для работы с Redis
- Функции:
  - CRUD операции для учеников
  - CRUD операции для лекций
  - Связь между учениками и лекциями
  - Проверка подключения
  - Получение статистики

```python
class DatabaseManager:
    # Student operations
    def add_student()
    def get_student()
    def get_all_students()
    def update_student()
    def delete_student()
    def add_lecture_to_student()
    def remove_lecture_from_student()
    
    # Lecture operations
    def add_lecture()
    def get_lecture()
    def get_all_lectures()
    def delete_lecture()
    def update_lecture()
    
    # Utility
    def is_redis_connected()
    def get_stats()
    def clear_all_data()
```

### 3. **admin_cli.py** - Администраторский интерфейс
- Роль: CLI для управления системой
- Функции:
  - Добавление/удаление учеников
  - Добавление/удаление лекций
  - Назначение лекций ученикам
  - Управление расписанием
  - Просмотр статистики

```
Меню:
1 - Добавить ученика
2 - Просмотреть ученика
3 - Список учеников
4 - Обновить расписание
...и т.д.
```

## 🗄️ Структура данных Redis

### Хранилище учеников
```
student:{user_id} → JSON
{
  "user_id": 123456789,
  "username": "vasya",
  "schedule": "пн,ср,пт 15:00-16:00",
  "lectures": ["lecture_1707314400", "lecture_1707314401"],
  "created_at": "2026-02-07T12:00:00.123456"
}
```

### Хранилище лекций (Hash)
```
lectures → {lecture_id: lecture_name}
{
  "lecture_1707314400": "Периодическая таблица",
  "lecture_1707314401": "Химические связи"
}
```

### Информация о файле лекции
```
{lecture_id}:file → JSON
{
  "filename": "periodic_table.pdf",
  "filepath": "./lectures/periodic_table.pdf",
  "created_at": "2026-02-07T12:00:00.123456"
}
```

## 🔄 Потоки данных

### Сценарий 1: Добавление ученика (Админ)

```
Администратор
    ↓
Telegram Bot (button_callback)
    ↓ запрос информации
Администратор (входит username и расписание)
    ↓
Telegram Bot (handle_message)
    ↓
DatabaseManager.add_student()
    ↓
Redis.set(f"student:{user_id}", JSON)
    ↓
✅ Ученик добавлен
```

### Сценарий 2: Добавление лекции (Админ)

```
Администратор
    ↓
Telegram Bot (button_callback)
    ↓ запрос информации
Администратор (вводит название лекции)
    ↓
Telegram Bot (handle_message)
    ↓ сохраняет название во временное хранилище
Администратор (отправляет файл)
    ↓
Telegram Bot (handle_document)
    ↓ скачивает файл
DatabaseManager.add_lecture()
    ↓
Redis.hset("lectures", lecture_id, name)
Redis.set(f"{lecture_id}:file", JSON)
    ↓
✅ Лекция добавлена
```

### Сценарий 3: Просмотр расписания (Ученик)

```
Ученик
    ↓
Telegram Bot (/start)
    ↓
DatabaseManager.get_student(user_id)
    ↓
Redis.get(f"student:{user_id}")
    ↓
Возврат JSON с расписанием
    ↓
Telegram Bot (show_student_menu)
    ↓
Ученик видит меню и выбирает "Мое расписание"
    ↓
Telegram Bot (button_callback)
    ↓
DatabaseManager.get_student(user_id)
    ↓
Вывод расписания
    ↓
✅ Ученик видит расписание
```

## 🔐 Безопасность

### Авторизация
- **Администраторы**: Проверка user_id в `config.json`
- **Ученики**: Проверка наличия записи в Redis
- **Неавторизованные**: Просмотр ID и username для контакта с админом

### Защита данных
- Redis запускается локально (не в интернете)
- Config.json не отслеживается в git (.gitignore)
- Файлы лекций хранятся локально в `lectures/`

## 📈 Масштабируемость

### Текущие ограничения (локальная версия)
- Redis работает на localhost:6379
- Хранение до 50 лекций
- Хранение файлов в локальной папке

### Для масштабирования на сервер
1. Использовать Redis Cloud или Redis на сервере
2. Использовать S3/облачное хранилище для файлов лекций
3. Добавить кэширование (например, memcached)
4. Добавить логирование в централизованную систему
5. Использовать Load Balancer для нескольких экземпляров бота

## 🧪 Тестирование

### Юнит тесты
```bash
python test_database.py      # Тесты базы данных
python test_integration.py   # Интеграционные тесты
```

### Ручное тестирование
```bash
# 1. Запустить бота
python bot.py

# 2. В другом терминале запустить CLI
python admin_cli.py

# 3. Протестировать все операции
```

## 🚀 Развертывание

### Локально (разработка)
```bash
./setup.sh
python bot.py
```

### На сервере (production)
1. Установить Python 3.9+
2. Установить Redis или использовать Redis Cloud
3. Скопировать проект на сервер
4. Создать systemd service
5. Запустить с помощью supervisor или systemd
6. Настроить логирование
7. Добавить мониторинг и алерты

## 📝 Расширения (будущее)

- [ ] Веб-интерфейс для администраторов
- [ ] Система оценок учеников
- [ ] Домашние задания с дедлайнами
- [ ] Напоминания о предстоящих уроках
- [ ] Статистика просмотра лекций
- [ ] Поддержка видео-лекций
- [ ] Система обратной связи от учеников
- [ ] Интеграция с платежными системами

## 🔗 Зависимости

```
python-telegram-bot==20.7  # Telegram Bot API
redis==5.0.1              # Redis Python client
requests==2.31.0          # HTTP requests
```

## 📚 Ссылки

- [python-telegram-bot документация](https://docs.python-telegram-bot.org/)
- [Redis документация](https://redis.io/documentation)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [BotFather](https://t.me/botfather) - для создания ботов

---

**Версия**: 1.0  
**Дата**: 7 февраля 2026  
**Статус**: Готово для локального тестирования
