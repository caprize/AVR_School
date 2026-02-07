import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import json
import os
import hashlib
from datetime import datetime
from database import DatabaseManager

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load configuration
with open('config.json', 'r') as f:
    config = json.load(f)

# Initialize Database Manager
db = DatabaseManager(
    host=config['redis']['host'],
    port=config['redis']['port'],
    db=config['redis']['db']
)

ADMIN_IDS = config['admin_ids']
BOT_TOKEN = config['bot_token']
LECTURES_DIR = config['lectures_storage']

# Create lectures directory if it doesn't exist
if not os.path.exists(LECTURES_DIR):
    os.makedirs(LECTURES_DIR)

# Global dictionary to store category hash mappings
category_mappings = {}

# Helper functions for category hash management
def get_category_hash(category: str) -> str:
    """Get short hash for category name to use in callback_data"""
    return hashlib.md5(category.encode()).hexdigest()[:8]

def store_category_mapping(category: str) -> None:
    """Store mapping between category hash and name"""
    hash_val = get_category_hash(category)
    category_mappings[hash_val] = category

def get_category_from_hash(hash_val: str) -> str:
    """Get category name from hash"""
    return category_mappings.get(hash_val, "Без категории")

def get_student_id(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get the actual student ID, considering admin viewing mode"""
    if user_id in ADMIN_IDS and 'viewing_student_id' in context.user_data:
        return context.user_data['viewing_student_id']
    return user_id

# Bot commands
ADMIN_COMMANDS = [
    BotCommand("start", "Главное меню"),
    BotCommand("help", "Справка"),
]

STUDENT_COMMANDS = [
    BotCommand("start", "Главное меню"),
    BotCommand("help", "Справка"),
]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command handler"""
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    # Set bot commands based on user role
    if user_id in ADMIN_IDS:
        await context.bot.set_my_commands(ADMIN_COMMANDS, scope=None)
        await show_admin_menu(update, context)
    else:
        # Check if user is a student
        student_data = db.get_student(user_id)
        if student_data:
            await context.bot.set_my_commands(STUDENT_COMMANDS, scope=None)
            await show_student_menu(update, context)
        else:
            await update.message.reply_text(
                "👋 Привет! Тебе нужно получить доступ у администратора.\n"
                f"Твой username: @{username}\n"
                f"Твой ID: {user_id}"
            )


async def show_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show admin menu"""
    keyboard = [
        [InlineKeyboardButton("👥 Ученики", callback_data="admin_students_menu")],
        [InlineKeyboardButton("📚 Лекции", callback_data="admin_lectures_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text("🔧 Меню администратора:", reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text("🔧 Меню администратора:", reply_markup=reply_markup)


async def show_student_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show student menu"""
    keyboard = [
        [InlineKeyboardButton("📅 Моё расписание", callback_data="student_schedule")],
        [InlineKeyboardButton("📚 Доступные лекции", callback_data="student_lectures")],
        [InlineKeyboardButton("📓 Домашнее задание", callback_data="student_homework")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text("🔧 Меню ученика:", reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text("🔧 Меню ученика:", reply_markup=reply_markup)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show help information"""
    user_id = update.effective_user.id
    is_admin = user_id in ADMIN_IDS
    
    if is_admin:
        help_text = """
🤖 <b>Chemistry Bot - Справка администратора</b>

<b>Основные команды:</b>
/start - Главное меню
/help - Эта справка

<b>Функции в меню:</b>
👥 <b>Ученики</b>
  ➕ Добавить ученика
  📋 Информация об ученике
  ✏️ Редактировать ученика (добавить/удалить лекции, изменить расписание)
  🗑️ Удалить ученика

📚 <b>Лекции</b>
  ➕ Добавить лекцию (загрузить файл)
  📖 Просмотр всех лекций
  🗑️ Удалить лекцию
"""
    else:
        help_text = """
🤖 <b>Chemistry Bot - Справка ученика</b>

<b>Основные команды:</b>
/start - Главное меню
/help - Эта справка

<b>Функции в меню:</b>
📅 <b>Моё расписание</b> - Просмотр времени занятий

📚 <b>Доступные лекции</b> - Скачивание и управление материалами

⚙️ <b>Мои настройки</b>
  📝 Редактировать расписание
  📚 Управлять лекциями (удалить из списка)
"""
    
    await update.message.reply_text(help_text, parse_mode='HTML')


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menu command handler"""
    user_id = update.effective_user.id
    
    # Set bot commands based on user role
    if user_id in ADMIN_IDS:
        await show_admin_menu(update, context)
    else:
        # Check if user is a student
        student_data = db.get_student(user_id)
        if student_data:
            await show_student_menu(update, context)
        else:
            await update.message.reply_text(
                "👋 Привет! Тебе нужно получить доступ у администратора."
            )




async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button presses"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    is_admin = user_id in ADMIN_IDS
    is_viewing_student = 'viewing_student_id' in context.user_data
    
    # Handle noop button (for dividers)
    if query.data == "noop":
        return
    
    # Handle exit student view (only for admins in viewing mode)
    if query.data == "exit_student_view":
        if is_admin and is_viewing_student:
            # Clear student viewing mode and return to admin menu
            if 'admin_id' in context.user_data:
                del context.user_data['admin_id']
            if 'viewing_student_id' in context.user_data:
                del context.user_data['viewing_student_id']
            await show_admin_menu(update, context)
        return
    
    # Handle "back" buttons
    if query.data == "back_to_admin":
        if is_admin and is_viewing_student:
            # Clear student viewing mode when going back
            if 'admin_id' in context.user_data:
                del context.user_data['admin_id']
            if 'viewing_student_id' in context.user_data:
                del context.user_data['viewing_student_id']
        await show_admin_menu(update, context)
        return
    
    if query.data == "back_to_menu":
        if is_viewing_student:
            # If admin is viewing student, show student menu with exit button
            student_id = context.user_data['viewing_student_id']
            student = db.get_student(student_id)
            if student:
                keyboard = [
                    [InlineKeyboardButton("📅 Моё расписание", callback_data="student_schedule")],
                    [InlineKeyboardButton("📚 Доступные лекции", callback_data="student_lectures")],
                    [InlineKeyboardButton("� Домашнее задание", callback_data="student_homework")],
                    [InlineKeyboardButton("�🔙 Вернуться в админ-панель", callback_data="exit_student_view")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(f"🔍 Просмотр как ученик: <b>{student['username']}</b>\n\n🔧 Меню ученика:", reply_markup=reply_markup, parse_mode='HTML')
            else:
                await show_admin_menu(update, context)
        elif is_admin:
            await show_admin_menu(update, context)
        else:
            await show_student_menu(update, context)
        return
    
    # Admin callbacks
    if is_admin:
        # Handle student callbacks when admin is viewing student
        if is_viewing_student:
            if query.data == "student_schedule":
                student_id = get_student_id(user_id, context)
                student_data = db.get_student(student_id)
                schedule = student_data.get('schedule', 'Расписание не установлено') if student_data else 'Ошибка'
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(f"📅 Ваше расписание:\n{schedule}", reply_markup=reply_markup)
                return
            
            elif query.data == "student_homework":
                student_id = get_student_id(user_id, context)
                student_data = db.get_student(student_id)
                homework = student_data.get('homework', 'Домашнее задание не установлено') if student_data else 'Ошибка'
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(f"📓 Домашнее задание:\n{homework}", reply_markup=reply_markup)
                return
            
            elif query.data == "student_lectures":
                await show_student_lectures(update, context)
                return
            
            elif query.data.startswith("student_lectures_cat_"):
                cat_hash = query.data.replace("student_lectures_cat_", "")
                category = get_category_from_hash(cat_hash)
                # Show lectures in this category
                student_id = get_student_id(user_id, context)
                student_data = db.get_student(student_id)
                
                if student_data:
                    available_lectures = student_data.get('lectures', [])
                    
                    # Filter lectures by category
                    category_lectures = {}
                    for lecture_id in available_lectures:
                        lecture = db.get_lecture(lecture_id)
                        if lecture and lecture.get('category', 'Без категории') == category:
                            category_lectures[lecture_id] = lecture['name']
                    
                    if not category_lectures:
                        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="student_lectures")]]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        await query.edit_message_text(f"📭 В папке '{category}' нет лекций", reply_markup=reply_markup)
                        return
                    
                    keyboard = []
                    for lecture_id, lecture_name in category_lectures.items():
                        keyboard.append([InlineKeyboardButton(f"📚 {lecture_name}", callback_data=f"download_lecture_{lecture_id}")])
                    
                    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="student_lectures")])
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text(f"📚 Лекции в папке '{category}':", reply_markup=reply_markup)
                return
            
            elif query.data == "student_settings":
                await show_student_settings(update, context)
                return
            
            elif query.data == "student_manage_lectures":
                await show_student_manage_lectures(update, context)
                return
            
            elif query.data.startswith("student_manage_cat_"):
                cat_hash = query.data.replace("student_manage_cat_", "")
                category = get_category_from_hash(cat_hash)
                # Show lectures in this category for removal
                student_id = get_student_id(user_id, context)
                student_data = db.get_student(student_id)
                
                if student_data:
                    available_lectures = student_data.get('lectures', [])
                    
                    # Filter lectures by category
                    category_lectures = {}
                    for lecture_id in available_lectures:
                        lecture = db.get_lecture(lecture_id)
                        if lecture and lecture.get('category', 'Без категории') == category:
                            category_lectures[lecture_id] = lecture['name']
                    
                    if not category_lectures:
                        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="student_manage_lectures")]]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        await query.edit_message_text(f"📭 В папке '{category}' нет ваших лекций", reply_markup=reply_markup)
                        return
                    
                    keyboard = []
                    for lecture_id, lecture_name in category_lectures.items():
                        keyboard.append([InlineKeyboardButton(f"🗑️ {lecture_name}", callback_data=f"remove_lecture_{lecture_id}")])
                    
                    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="student_manage_lectures")])
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text(
                        f"📚 Лекции в папке '{category}':\n\n"
                        "Нажмите на лекцию чтобы удалить:",
                        reply_markup=reply_markup
                    )
                return
            
            elif query.data == "student_edit_schedule":
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="student_settings")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "📝 Введите новое расписание:\n\n"
                    "Примеры:\n"
                    "  пн,ср,пт 15:00-16:00\n"
                    "  вт,чт 17:00\n"
                    "  пн-пт 10:00-11:00",
                    reply_markup=reply_markup
                )
                context.user_data['action'] = 'edit_schedule'
                return
            
            elif query.data.startswith("remove_lecture_"):
                lecture_id = query.data.replace("remove_lecture_", "")
                student_id = get_student_id(user_id, context)
                student_data = db.get_student(student_id)
                if student_data and lecture_id in student_data.get('lectures', []):
                    db.remove_lecture_from_student(student_id, lecture_id)
                    lectures_dict = db.get_all_lectures()
                    lecture_name = lectures_dict.get(lecture_id, "Неизвестная лекция")
                    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="student_manage_lectures")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(
                        f"✅ Лекция '{lecture_name}' удалена из вашего списка",
                        reply_markup=reply_markup
                    )
                else:
                    await query.answer("❌ Лекция не найдена", show_alert=True)
                return
            
            elif query.data.startswith("download_lecture_"):
                lecture_id = query.data.replace("download_lecture_", "")
                lecture = db.get_lecture(lecture_id)
                if lecture and lecture['file']:
                    file_path = lecture['file'].get('filepath')
                    if file_path and os.path.exists(file_path):
                        with open(file_path, 'rb') as f:
                            await update.effective_user.send_document(f, filename=lecture['file'].get('filename'))
                        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="student_lectures")]]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        await query.edit_message_text("✅ Файл загружен", reply_markup=reply_markup)
                    else:
                        await query.answer("❌ Файл не найден", show_alert=True)
                else:
                    await query.answer("❌ Лекция не найдена", show_alert=True)
                return
        
        # Admin panel callbacks
        if query.data == "admin_students_menu":
            await show_admin_students_menu(update, context)
        
        elif query.data == "admin_add_student":
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_students_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "📝 Отправьте информацию об ученике в формате:\n\n"
                "`user_id username расписание`\n\n"
                "Пример: `123456789 vasya пн,ср,пт 15:00`\n\n"
                "⚠️ user_id - это числовой ID ученика в Telegram\n"
                "Его можно получить через @userinfobot",
                reply_markup=reply_markup
            )
            context.user_data['action'] = 'add_student'
        
        elif query.data == "admin_student_info":
            await show_students_list(update, context, "info")
        
        elif query.data == "admin_edit_student":
            await show_students_list(update, context, "edit")
        
        elif query.data == "admin_become_student":
            await show_students_list(update, context, "become")
        
        elif query.data == "admin_delete_student":
            await show_students_list(update, context, "delete")
        
        elif query.data == "admin_lectures_menu":
            await show_admin_lectures_menu(update, context)
        
        elif query.data == "admin_add_lecture":
            keyboard = [
                [InlineKeyboardButton("📄 Новая лекция", callback_data="admin_add_lecture_new")],
                [InlineKeyboardButton("📚 Существующая лекция", callback_data="admin_add_lecture_existing")],
                [InlineKeyboardButton("🔙 Назад", callback_data="admin_lectures_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text("Что вы хотите сделать?", reply_markup=reply_markup)
        
        elif query.data == "admin_view_all_lectures":
            await show_all_lectures_info(update, context)
        
        elif query.data == "admin_delete_lecture":
            await show_categories_for_delete(update, context)
        
        elif query.data == "admin_manage_categories":
            await show_manage_categories_menu(update, context)
        
        elif query.data == "admin_add_lecture_new":
            await show_add_lecture_new(update, context)
        
        elif query.data == "admin_add_lecture_existing":
            await show_categories_for_existing_lecture(update, context)
        
        elif query.data.startswith("view_category_"):
            cat_hash = query.data.replace("view_category_", "")
            category = get_category_from_hash(cat_hash)
            await show_category_details(update, context, category)
        
        elif query.data.startswith("select_cat_new_"):
            cat_hash = query.data.replace("select_cat_new_", "")
            category = get_category_from_hash(cat_hash)
            context.user_data['lecture_category'] = category
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_add_lecture_new")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"📚 Название лекции для папки '{category}':\n\n"
                "Отправьте название лекции",
                reply_markup=reply_markup
            )
            context.user_data['action'] = 'add_lecture_new'
        
        elif query.data == "add_category_for_new_lecture":
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_add_lecture_new")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "Введите название новой папки:",
                reply_markup=reply_markup
            )
            context.user_data['action'] = 'add_category_new_lecture'
        
        elif query.data.startswith("select_cat_existing_"):
            cat_hash = query.data.replace("select_cat_existing_", "")
            category = get_category_from_hash(cat_hash)
            await show_lectures_in_category(update, context, category, "existing")
        
        elif query.data.startswith("select_existing_lec_"):
            lecture_id = query.data.replace("select_existing_lec_", "")
            context.user_data['selected_lecture_id'] = lecture_id
            
            # Show categories to move lecture to
            categories = db.get_all_categories()
            keyboard = []
            
            for category in categories:
                # Store the category mapping and use hash in callback_data
                store_category_mapping(category)
                cat_hash = get_category_hash(category)
                keyboard.append([InlineKeyboardButton(f"📁 {category}", callback_data=f"move_lec_to_cat_{lecture_id}_{cat_hash}")])
            
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_add_lecture_existing")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            lecture = db.get_lecture(lecture_id)
            if lecture:
                await query.edit_message_text(f"Выберите папку для лекции '{lecture['name']}':", reply_markup=reply_markup)
            else:
                await query.edit_message_text("❌ Лекция не найдена")
                return
        
        elif query.data.startswith("move_lec_to_cat_"):
            # Extract from the end since cat_hash is always 8 chars
            data = query.data.replace("move_lec_to_cat_", "")
            cat_hash = data[-8:]  # Last 8 characters are the hash
            lecture_id = data[:-9]  # Everything except the last 9 chars (hash + underscore)
            category = get_category_from_hash(cat_hash)
            
            lecture = db.get_lecture(lecture_id)
            if lecture:
                # Get all students with this lecture
                students = db.get_all_students()
                students_with_lecture = [s for s in students if lecture_id in s.get('lectures', [])]
                
                # Move lecture to category
                db.move_lecture_to_category(lecture_id, category)
                
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_lectures_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    f"✅ Лекция '{lecture['name']}' перемещена в папку '{category}'!\n\n"
                    f"👥 Лекция назначена {len(students_with_lecture)} ученик(ам)",
                    reply_markup=reply_markup
                )
            else:
                await query.edit_message_text("❌ Лекция не найдена")
        
        elif query.data.startswith("select_cat_delete_"):
            cat_hash = query.data.replace("select_cat_delete_", "")
            category = get_category_from_hash(cat_hash)
            await show_lectures_in_category(update, context, category, "delete")
        
        elif query.data.startswith("delete_category_"):
            cat_hash = query.data.replace("delete_category_", "")
            category = get_category_from_hash(cat_hash)
            if db.delete_category(category):
                keyboard = [[InlineKeyboardButton("Назад", callback_data="admin_manage_categories")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    f"✅ Папка '{category}' удалена!\n\n"
                    f"ℹ️ Лекции перемещены в 'Без категории'",
                    reply_markup=reply_markup
                )
            else:
                keyboard = [[InlineKeyboardButton("Назад", callback_data="admin_manage_categories")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text("❌ Ошибка при удалении папки", reply_markup=reply_markup)
        
        elif query.data == "add_category":
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_manage_categories")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "Введите название новой папки:",
                reply_markup=reply_markup
            )
            context.user_data['action'] = 'add_category'
        
        elif query.data.startswith("delete_lecture_"):
            lecture_id = query.data.replace("delete_lecture_", "")
            lecture = db.get_lecture(lecture_id)
            if lecture:
                # Count how many students have this lecture
                students = db.get_all_students()
                students_count = sum(1 for s in students if lecture_id in s.get('lectures', []))
                
                # Delete lecture
                db.delete_lecture(lecture_id)
                
                keyboard = [[InlineKeyboardButton("Назад", callback_data="admin_delete_lecture")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                if students_count > 0:
                    await query.edit_message_text(
                        f"✅ Лекция '{lecture['name']}' удалена!\n\n"
                        f"ℹ️ Удалена у {students_count} ученика(ов)",
                        reply_markup=reply_markup
                    )
                else:
                    await query.edit_message_text(
                        f"✅ Лекция '{lecture['name']}' удалена!",
                        reply_markup=reply_markup
                    )
            else:
                keyboard = [[InlineKeyboardButton("Назад", callback_data="admin_delete_lecture")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text("❌ Лекция не найдена", reply_markup=reply_markup)
        
        elif query.data.startswith("view_student_info_"):
            student_id = int(query.data.replace("view_student_info_", ""))
            student = db.get_student(student_id)
            if student:
                lectures_list = ""
                lectures_dict = db.get_all_lectures()
                categories_dict = {}
                
                # Organize lectures by categories
                for lecture_id in student.get('lectures', []):
                    lecture = db.get_lecture(lecture_id)
                    if lecture:
                        category = lecture.get('category', 'Без категории')
                        lecture_name = lecture['name']
                        if category not in categories_dict:
                            categories_dict[category] = []
                        categories_dict[category].append(lecture_name)
                
                # Format lectures by category
                if categories_dict:
                    for category in sorted(categories_dict.keys()):
                        lectures_list += f"📁 <b>{category}</b>\n"
                        for lecture_name in sorted(categories_dict[category]):
                            lectures_list += f"  • {lecture_name}\n"
                else:
                    lectures_list = "  Нет лекций"
                
                homework = student.get('homework', '')
                homework_text = f"\n📓 <b>Домашнее задание:</b>\n{homework}" if homework else ""
                
                info_text = (
                    f"👤 <b>{student['username']}</b>\n"
                    f"📅 Расписание: {student['schedule']}\n"
                    f"📚 Доступные лекции:\n{lectures_list}"
                    f"{homework_text}"
                )
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_students_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(info_text, reply_markup=reply_markup, parse_mode='HTML')
            else:
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_students_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text("❌ Ученик не найден", reply_markup=reply_markup)
        
        elif query.data.startswith("edit_student_add_lec_cat_"):
            parts = query.data.replace("edit_student_add_lec_cat_", "").split("_", 1)
            student_id = int(parts[0])
            cat_hash = parts[1]
            category = get_category_from_hash(cat_hash)
            
            student = db.get_student(student_id)
            if student:
                student_lectures = student.get('lectures', [])
                lectures_in_cat = db.get_lectures_by_category(category)
                
                # Filter lectures not yet added to student
                available_lectures = {lid: lname for lid, lname in lectures_in_cat.items() if lid not in student_lectures}
                
                if not available_lectures:
                    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f"edit_student_add_lec_{student_id}")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(f"� Все лекции в папке '{category}' уже добавлены", reply_markup=reply_markup)
                    return
                
                keyboard = []
                for lecture_id, lecture_name in available_lectures.items():
                    keyboard.append([InlineKeyboardButton(f"➕ {lecture_name}", callback_data=f"add_lec_to_student_{student_id}_{lecture_id}")])
                
                keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"edit_student_add_lec_{student_id}")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(f"📚 Лекции в папке '{category}':", reply_markup=reply_markup)
        
        elif query.data.startswith("edit_student_add_lec_"):
            student_id = int(query.data.replace("edit_student_add_lec_", ""))
            student = db.get_student(student_id)
            if student:
                # Show categories first
                categories = db.get_all_categories()
                student_lectures = student.get('lectures', [])
                
                # Filter categories that have lectures not yet added to student
                available_categories = {}
                for category in categories:
                    lectures_in_cat = db.get_lectures_by_category(category)
                    available_lectures_in_cat = {lid: lname for lid, lname in lectures_in_cat.items() if lid not in student_lectures}
                    if available_lectures_in_cat:
                        available_categories[category] = available_lectures_in_cat
                
                if not available_categories:
                    keyboard = [[InlineKeyboardButton("📭 Все лекции добавлены", callback_data="noop")]]
                    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"edit_student_{student_id}")])
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(f"� Добавить лекцию ученику {student['username']}:", reply_markup=reply_markup)
                    return
                
                keyboard = []
                for category in sorted(available_categories.keys()):
                    store_category_mapping(category)
                    cat_hash = get_category_hash(category)
                    count = len(available_categories[category])
                    keyboard.append([InlineKeyboardButton(f"🔧 {category} ({count})", callback_data=f"edit_student_add_lec_cat_{student_id}_{cat_hash}")])
                
                keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"edit_student_{student_id}")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(f"📚 Добавить лекцию ученику {student['username']}:", reply_markup=reply_markup)
            else:
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_students_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text("❌ Ученик не найден", reply_markup=reply_markup)
        
        elif query.data.startswith("edit_student_remove_lec_cat_"):
            parts = query.data.replace("edit_student_remove_lec_cat_", "").split("_", 1)
            student_id = int(parts[0])
            cat_hash = parts[1]
            category = get_category_from_hash(cat_hash)
            
            student = db.get_student(student_id)
            if student:
                student_lectures = student.get('lectures', [])
                
                # Filter lectures in this category
                category_lectures = {}
                for lecture_id in student_lectures:
                    lecture = db.get_lecture(lecture_id)
                    if lecture and lecture.get('category', 'Без категории') == category:
                        category_lectures[lecture_id] = lecture['name']
                
                if not category_lectures:
                    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f"edit_student_remove_lec_{student_id}")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(f"📭 В папке '{category}' нет лекций ученика", reply_markup=reply_markup)
                    return
                
                keyboard = []
                for lecture_id, lecture_name in category_lectures.items():
                    keyboard.append([InlineKeyboardButton(f"🗑️ {lecture_name}", callback_data=f"remove_lec_from_student_{student_id}_{lecture_id}")])
                
                keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"edit_student_remove_lec_{student_id}")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(f"📚 Лекции в папке '{category}':", reply_markup=reply_markup)
        
        elif query.data.startswith("edit_student_remove_lec_"):
            student_id = int(query.data.replace("edit_student_remove_lec_", ""))
            student = db.get_student(student_id)
            if student:
                student_lectures = student.get('lectures', [])
                
                if not student_lectures:
                    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f"edit_student_{student_id}")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text("📭 У ученика нет лекций", reply_markup=reply_markup)
                    return
                
                # Group lectures by category
                categories_with_lectures = {}
                for lecture_id in student_lectures:
                    lecture = db.get_lecture(lecture_id)
                    if lecture:
                        category = lecture.get('category', 'Без категории')
                        if category not in categories_with_lectures:
                            categories_with_lectures[category] = []
                        categories_with_lectures[category].append(lecture_id)
                
                keyboard = []
                for category in sorted(categories_with_lectures.keys()):
                    store_category_mapping(category)
                    cat_hash = get_category_hash(category)
                    count = len(categories_with_lectures[category])
                    keyboard.append([InlineKeyboardButton(f"🔧 {category} ({count})", callback_data=f"edit_student_remove_lec_cat_{student_id}_{cat_hash}")])
                
                keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"edit_student_{student_id}")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(f"🗑️ Удалить лекцию ученика {student['username']}:", reply_markup=reply_markup)
            else:
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_students_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text("❌ Ученик не найден", reply_markup=reply_markup)
        
        elif query.data.startswith("edit_student_schedule_"):
            student_id = int(query.data.replace("edit_student_schedule_", ""))
            student = db.get_student(student_id)
            if student:
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f"edit_student_{student_id}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    f"📝 Редактирование расписания ученика {student['username']}\n\n"
                    f"Текущее расписание: {student['schedule']}\n\n"
                    "Отправьте новое расписание:",
                    reply_markup=reply_markup
                )
                context.user_data['action'] = 'edit_student_schedule'
                context.user_data['edit_student_id'] = student_id
            else:
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_students_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text("❌ Ученик не найден", reply_markup=reply_markup)
        
        elif query.data.startswith("edit_student_add_homework_"):
            student_id = int(query.data.replace("edit_student_add_homework_", ""))
            student = db.get_student(student_id)
            if student:
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f"edit_student_{student_id}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    f"📝 Добавление ДЗ для ученика {student['username']}\n\n"
                    f"Текущее ДЗ: {student.get('homework', 'Не установлено')}\n\n"
                    "Отправьте текст с ДЗ:",
                    reply_markup=reply_markup
                )
                context.user_data['action'] = 'edit_student_homework'
                context.user_data['edit_student_id'] = student_id
            else:
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_students_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text("❌ Ученик не найден", reply_markup=reply_markup)
        
        elif query.data.startswith("edit_student_"):
            student_id = int(query.data.replace("edit_student_", ""))
            student = db.get_student(student_id)
            if student:
                keyboard = [
                    [InlineKeyboardButton("➕ Добавить лекцию", callback_data=f"edit_student_add_lec_{student_id}")],
                    [InlineKeyboardButton("🗑️ Удалить лекцию", callback_data=f"edit_student_remove_lec_{student_id}")],
                    [InlineKeyboardButton("📝 Редактировать расписание", callback_data=f"edit_student_schedule_{student_id}")],
                    [InlineKeyboardButton("� Добавить ДЗ", callback_data=f"edit_student_add_homework_{student_id}")],
                    [InlineKeyboardButton("�🔙 Назад", callback_data="admin_students_menu")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(f"✏️ Редактирование {student['username']}:", reply_markup=reply_markup)
            else:
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_students_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text("❌ Ученик не найден", reply_markup=reply_markup)
        
        elif query.data.startswith("become_student_"):
            student_id = int(query.data.replace("become_student_", ""))
            student = db.get_student(student_id)
            if student:
                # Store admin_id and viewing_student_id in context
                context.user_data['admin_id'] = user_id
                context.user_data['viewing_student_id'] = student_id
                # Show student menu
                keyboard = [
                    [InlineKeyboardButton("📅 Моё расписание", callback_data="student_schedule")],
                    [InlineKeyboardButton("📚 Доступные лекции", callback_data="student_lectures")],
                    [InlineKeyboardButton("🔙 Вернуться в админ-панель", callback_data="exit_student_view")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(f"🔍 Просмотр как ученик: <b>{student['username']}</b>\n\n🔧 Меню ученика:", reply_markup=reply_markup, parse_mode='HTML')
            else:
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_students_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text("❌ Ученик не найден", reply_markup=reply_markup)
        
        elif query.data.startswith("delete_student_"):
            student_id = int(query.data.replace("delete_student_", ""))
            student = db.get_student(student_id)
            if student:
                # Delete the student
                db.delete_student(student_id)
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_students_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    f"✅ Ученик '{student['username']}' удален из базы данных!",
                    reply_markup=reply_markup
                )
            else:
                await query.edit_message_text("❌ Ученик не найден")
        
        elif query.data.startswith("add_lec_to_student_"):
            # Extract data after prefix
            data = query.data.replace("add_lec_to_student_", "")
            # Find where digits end (student_id is all digits)
            i = 0
            while i < len(data) and data[i].isdigit():
                i += 1
            # Skip the underscore separator
            if i < len(data) and data[i] == "_":
                student_id = int(data[:i])
                lecture_id = data[i+1:]
            else:
                await query.answer("❌ Ошибка обработки", show_alert=True)
                return
            
            student = db.get_student(student_id)
            lecture = db.get_lecture(lecture_id)
            
            if not student:
                await query.answer("❌ Ученик не найден", show_alert=True)
            elif not lecture:
                await query.answer("❌ Лекция не найдена", show_alert=True)
            elif lecture_id in student.get('lectures', []):
                await query.answer(f"⚠️ Лекция '{lecture['name']}' уже у ученика {student['username']}", show_alert=True)
            elif db.add_lecture_to_student(student_id, lecture_id):
                await query.answer(f"✅ Лекция '{lecture['name']}' добавлена ученику {student['username']}", show_alert=True)
                # Return to categories menu (to select another lecture)
                categories = db.get_all_categories()
                updated_student = db.get_student(student_id)
                if updated_student:
                    student_lectures = updated_student.get('lectures', [])
                    
                    # Filter categories that have lectures not yet added to student
                    available_categories = {}
                    for category in categories:
                        lectures_in_cat = db.get_lectures_by_category(category)
                        available_lectures_in_cat = {lid: lname for lid, lname in lectures_in_cat.items() if lid not in student_lectures}
                        if available_lectures_in_cat:
                            available_categories[category] = available_lectures_in_cat
                    
                    if not available_categories:
                        keyboard = [[InlineKeyboardButton("📭 Все лекции добавлены", callback_data="noop")]]
                        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"edit_student_{student_id}")])
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        await query.edit_message_text(f"📚 Добавить лекцию ученику {updated_student['username']}:", reply_markup=reply_markup)
                    else:
                        keyboard = []
                        for category in sorted(available_categories.keys()):
                            store_category_mapping(category)
                            cat_hash = get_category_hash(category)
                            count = len(available_categories[category])
                            keyboard.append([InlineKeyboardButton(f"🔧 {category} ({count})", callback_data=f"edit_student_add_lec_cat_{student_id}_{cat_hash}")])
                        
                        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"edit_student_{student_id}")])
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        await query.edit_message_text(f"📚 Добавить лекцию ученику {updated_student['username']}:", reply_markup=reply_markup)
            else:
                await query.answer("❌ Ошибка при добавлении лекции", show_alert=True)
        
        elif query.data.startswith("remove_lec_from_student_"):
            # Extract data after prefix
            data = query.data.replace("remove_lec_from_student_", "")
            # Find where digits end (student_id is all digits)
            i = 0
            while i < len(data) and data[i].isdigit():
                i += 1
            # Skip the underscore separator
            if i < len(data) and data[i] == "_":
                student_id = int(data[:i])
                lecture_id = data[i+1:]
            else:
                await query.answer("❌ Ошибка обработки", show_alert=True)
                return
            
            student = db.get_student(student_id)
            if student and lecture_id in student.get('lectures', []):
                lectures_dict = db.get_all_lectures()
                lecture_name = lectures_dict.get(lecture_id, "Неизвестная лекция")
                db.remove_lecture_from_student(student_id, lecture_id)
                await query.answer(f"✅ Лекция '{lecture_name}' удалена у ученика {student['username']}", show_alert=True)
                
                # Return to remove lecture menu
                updated_student = db.get_student(student_id)
                if updated_student:
                    lectures_dict = db.get_all_lectures()
                    student_lectures = updated_student.get('lectures', [])
                    
                    if not student_lectures:
                        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f"edit_student_{student_id}")]]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        await query.edit_message_text("📭 У ученика больше нет лекций", reply_markup=reply_markup)
                        return
                    
                    keyboard = []
                    # Show lectures that student has with remove button
                    for lec_id in student_lectures:
                        lec_name = lectures_dict.get(lec_id, f"Лекция {lec_id}")
                        keyboard.append([InlineKeyboardButton(f"🗑️ {lec_name}", callback_data=f"remove_lec_from_student_{student_id}_{lec_id}")])
                    
                    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data=f"edit_student_{student_id}")])
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(f"🗑️ Удалить лекцию ученика {updated_student['username']}:", reply_markup=reply_markup)
            else:
                await query.answer("❌ Лекция не найдена", show_alert=True)
    
    # Student callbacks
    else:
        if query.data == "student_schedule":
            student_id = get_student_id(user_id, context)
            student_data = db.get_student(student_id)
            schedule = student_data.get('schedule', 'Расписание не установлено') if student_data else 'Ошибка'
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"📅 Ваше расписание:\n{schedule}", reply_markup=reply_markup)
        
        elif query.data == "student_homework":
            student_id = get_student_id(user_id, context)
            student_data = db.get_student(student_id)
            homework = student_data.get('homework', 'Домашнее задание не установлено') if student_data else 'Ошибка'
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"📓 Домашнее задание:\n{homework}", reply_markup=reply_markup)
        
        elif query.data == "student_lectures":
            await show_student_lectures(update, context)
        
        elif query.data.startswith("student_lectures_cat_"):
            cat_hash = query.data.replace("student_lectures_cat_", "")
            category = get_category_from_hash(cat_hash)
            # Show lectures in this category
            student_id = get_student_id(user_id, context)
            student_data = db.get_student(student_id)
            
            if student_data:
                available_lectures = student_data.get('lectures', [])
                
                # Filter lectures by category
                category_lectures = {}
                for lecture_id in available_lectures:
                    lecture = db.get_lecture(lecture_id)
                    if lecture and lecture.get('category', 'Без категории') == category:
                        category_lectures[lecture_id] = lecture['name']
                
                if not category_lectures:
                    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="student_lectures")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(f"📭 В папке '{category}' нет лекций", reply_markup=reply_markup)
                    return
                
                keyboard = []
                for lecture_id, lecture_name in category_lectures.items():
                    keyboard.append([InlineKeyboardButton(f"📚 {lecture_name}", callback_data=f"download_lecture_{lecture_id}")])
                
                keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="student_lectures")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(f"📚 Лекции в папке '{category}':", reply_markup=reply_markup)
        
        elif query.data == "student_settings":
            await show_student_settings(update, context)
        
        elif query.data == "student_manage_lectures":
            await show_student_manage_lectures(update, context)
        
        elif query.data.startswith("student_manage_cat_"):
            cat_hash = query.data.replace("student_manage_cat_", "")
            category = get_category_from_hash(cat_hash)
            # Show lectures in this category for removal
            student_id = get_student_id(user_id, context)
            student_data = db.get_student(student_id)
            
            if student_data:
                available_lectures = student_data.get('lectures', [])
                
                # Filter lectures by category
                category_lectures = {}
                for lecture_id in available_lectures:
                    lecture = db.get_lecture(lecture_id)
                    if lecture and lecture.get('category', 'Без категории') == category:
                        category_lectures[lecture_id] = lecture['name']
                
                if not category_lectures:
                    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="student_manage_lectures")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text(f"📭 В папке '{category}' нет ваших лекций", reply_markup=reply_markup)
                    return
                
                keyboard = []
                for lecture_id, lecture_name in category_lectures.items():
                    keyboard.append([InlineKeyboardButton(f"🗑️ {lecture_name}", callback_data=f"remove_lecture_{lecture_id}")])
                
                keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="student_manage_lectures")])
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"📚 Лекции в папке '{category}':\n\n"
                    "Нажмите на лекцию чтобы удалить:",
                    reply_markup=reply_markup
                )
        
        elif query.data == "student_edit_schedule":
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="student_settings")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "📝 Введите новое расписание:\n\n"
                "Примеры:\n"
                "  пн,ср,пт 15:00-16:00\n"
                "  вт,чт 17:00\n"
                "  пн-пт 10:00-11:00",
                reply_markup=reply_markup
            )
            context.user_data['action'] = 'edit_schedule'
        
        elif query.data.startswith("remove_lecture_"):
            lecture_id = query.data.replace("remove_lecture_", "")
            student_id = get_student_id(user_id, context)
            student_data = db.get_student(student_id)
            if student_data and lecture_id in student_data.get('lectures', []):
                db.remove_lecture_from_student(student_id, lecture_id)
                lectures_dict = db.get_all_lectures()
                lecture_name = lectures_dict.get(lecture_id, "Неизвестная лекция")
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="student_manage_lectures")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    f"✅ Лекция '{lecture_name}' удалена из вашего списка",
                    reply_markup=reply_markup
                )
            else:
                await query.answer("❌ Лекция не найдена", show_alert=True)
        
        elif query.data.startswith("download_lecture_"):
            lecture_id = query.data.replace("download_lecture_", "")
            lecture = db.get_lecture(lecture_id)
            if lecture and lecture['file']:
                file_path = lecture['file'].get('filepath')
                if file_path and os.path.exists(file_path):
                    with open(file_path, 'rb') as f:
                        await update.effective_user.send_document(f, filename=lecture['file'].get('filename'))
                    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="student_lectures")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await query.edit_message_text("✅ Файл загружен", reply_markup=reply_markup)
                else:
                    await query.answer("❌ Файл не найден", show_alert=True)
            else:
                await query.answer("❌ Лекция не найдена", show_alert=True)


async def show_students_list(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str) -> None:
    """Show list of students"""
    students = db.get_all_students()
    
    if not students:
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_students_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text("📭 Нет учеников в базе данных", reply_markup=reply_markup)
        return
    
    keyboard = []
    for student_data in students:
        username = student_data.get('username', 'Unknown')
        user_id = student_data.get('user_id')
        
        if action == "info":
            keyboard.append([InlineKeyboardButton(f"👤 {username}", callback_data=f"view_student_info_{user_id}")])
        elif action == "edit":
            keyboard.append([InlineKeyboardButton(f"✏️ {username}", callback_data=f"edit_student_{user_id}")])
        elif action == "become":
            keyboard.append([InlineKeyboardButton(f"👁️ {username}", callback_data=f"become_student_{user_id}")])
        elif action == "delete":
            keyboard.append([InlineKeyboardButton(f"🗑️ {username}", callback_data=f"delete_student_{user_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_students_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if action == "become":
        await update.callback_query.edit_message_text("📋 Выберите ученика для просмотра:", reply_markup=reply_markup)
    else:
        await update.callback_query.edit_message_text("📋 Выберите ученика:", reply_markup=reply_markup)


async def show_admin_students_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show students management menu for admin"""
    keyboard = [
        [InlineKeyboardButton("➕ Добавить ученика", callback_data="admin_add_student")],
        [InlineKeyboardButton("📋 Информация об ученике", callback_data="admin_student_info")],
        [InlineKeyboardButton("✏️ Редактировать ученика", callback_data="admin_edit_student")],
        [InlineKeyboardButton("👁️ Стать учеником", callback_data="admin_become_student")],
        [InlineKeyboardButton("🗑️ Удалить ученика", callback_data="admin_delete_student")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text("👥 Управление учениками:", reply_markup=reply_markup)


async def show_admin_lectures_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show lectures management menu for admin"""
    keyboard = [
        [InlineKeyboardButton("➕ Добавить лекцию", callback_data="admin_add_lecture")],
        [InlineKeyboardButton("📖 Все лекции", callback_data="admin_view_all_lectures")],
        [InlineKeyboardButton("✏️ Редактировать папки", callback_data="admin_manage_categories")],
        [InlineKeyboardButton("🗑️ Удалить лекцию", callback_data="admin_delete_lecture")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text("📚 Управление лекциями:", reply_markup=reply_markup)


async def show_lectures_list(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str) -> None:
    """Show list of lectures"""
    lectures = db.get_all_lectures()
    
    if not lectures:
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_lectures_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text("📭 Нет лекций в базе данных", reply_markup=reply_markup)
        return
    
    keyboard = []
    for lecture_id, lecture_name in lectures.items():
        if action == "delete":
            keyboard.append([InlineKeyboardButton(f"🗑️ {lecture_name}", callback_data=f"delete_lecture_{lecture_id}")])
        elif action == "view":
            keyboard.append([InlineKeyboardButton(f"📚 {lecture_name}", callback_data=f"view_lecture_{lecture_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_lectures_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text("📚 Выберите лекцию:", reply_markup=reply_markup)


async def show_all_lectures_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show all lectures organized by categories"""
    lectures_by_cat = db.get_all_lectures_by_category()
    
    if not lectures_by_cat or all(not v for v in lectures_by_cat.values()):
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_lectures_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text("📭 Нет лекций в базе данных", reply_markup=reply_markup)
        return
    
    # Build detailed information about all lectures by category
    text = "📚 <b>Все загруженные лекции:</b>\n\n"
    
    lecture_count = 0
    for category, lectures in lectures_by_cat.items():
        if not lectures:
            continue
        
        text += f"<b>📁 {category}</b>\n"
        
        for lecture_id, lecture_name in lectures.items():
            lecture = db.get_lecture(lecture_id)
            if lecture:
                file_info = lecture.get('file', {})
                filename = file_info.get('filename', 'Неизвестно')
                
                # Get count of students with this lecture
                students = db.get_all_students()
                students_count = sum(1 for s in students if lecture_id in s.get('lectures', []))
                
                lecture_count += 1
                text += f"  <b>{lecture_count}. {lecture_name}</b>\n"
                text += f"     📄 {filename}\n"
                text += f"     👥 {students_count} ученик(ов)\n\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_lectures_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')


async def show_student_lectures(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show available lecture categories for student"""
    user_id = update.effective_user.id
    student_id = get_student_id(user_id, context)
    student_data = db.get_student(student_id)
    
    if not student_data:
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text("❌ Данные ученика не найдены", reply_markup=reply_markup)
        return
    
    available_lectures = student_data.get('lectures', [])
    
    if not available_lectures:
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text("📭 У вас нет доступных лекций", reply_markup=reply_markup)
        return
    
    # Group lectures by category
    categories_with_lectures = {}
    for lecture_id in available_lectures:
        lecture = db.get_lecture(lecture_id)
        if lecture:
            category = lecture.get('category', 'Без категории')
            if category not in categories_with_lectures:
                categories_with_lectures[category] = []
            categories_with_lectures[category].append(lecture_id)
    
    # Show categories
    keyboard = []
    for category in sorted(categories_with_lectures.keys()):
        store_category_mapping(category)
        cat_hash = get_category_hash(category)
        lecture_count = len(categories_with_lectures[category])
        keyboard.append([InlineKeyboardButton(f"🔧 {category} ({lecture_count})", callback_data=f"student_lectures_cat_{cat_hash}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text("📚 Папки с лекциями:", reply_markup=reply_markup)


async def show_student_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show student settings menu"""
    keyboard = [
        [InlineKeyboardButton("📝 Редактировать расписание", callback_data="student_edit_schedule")],
        [InlineKeyboardButton("📚 Управлять лекциями", callback_data="student_manage_lectures")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text("⚙️ Мои настройки:", reply_markup=reply_markup)


async def show_student_manage_lectures(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show lectures management by categories for student"""
    user_id = update.effective_user.id
    student_id = get_student_id(user_id, context)
    student_data = db.get_student(student_id)
    
    if not student_data:
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="student_settings")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text("❌ Данные ученика не найдены", reply_markup=reply_markup)
        return
    
    available_lectures = student_data.get('lectures', [])
    
    if not available_lectures:
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="student_settings")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text("📭 У вас нет лекций", reply_markup=reply_markup)
        return
    
    # Group lectures by category
    categories_with_lectures = {}
    for lecture_id in available_lectures:
        lecture = db.get_lecture(lecture_id)
        if lecture:
            category = lecture.get('category', 'Без категории')
            if category not in categories_with_lectures:
                categories_with_lectures[category] = []
            categories_with_lectures[category].append(lecture_id)
    
    # Show categories
    keyboard = []
    for category in sorted(categories_with_lectures.keys()):
        store_category_mapping(category)
        cat_hash = get_category_hash(category)
        lecture_count = len(categories_with_lectures[category])
        keyboard.append([InlineKeyboardButton(f"🔧 {category} ({lecture_count})", callback_data=f"student_manage_cat_{cat_hash}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="student_settings")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(
        "📚 Управление лекциями по папкам:\n\n"
        "Выберите папку чтобы удалить лекции:",
        reply_markup=reply_markup
    )


async def show_student_lectures_old(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show available lectures for student"""
    user_id = update.effective_user.id
    student_data = db.get_student(user_id)
    
    if not student_data:
        await update.callback_query.edit_message_text("❌ Данные ученика не найдены")
        return
    
    available_lectures = student_data.get('lectures', [])
    
    if not available_lectures:
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text("📭 У вас нет доступных лекций", reply_markup=reply_markup)
        return
    
    keyboard = []
    lectures = db.get_all_lectures()
    
    for lecture_id in available_lectures:
        lecture_name = lectures.get(lecture_id, f"Лекция {lecture_id}")
        keyboard.append([InlineKeyboardButton(f"📚 {lecture_name}", callback_data=f"download_lecture_{lecture_id}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text("📚 Доступные лекции:", reply_markup=reply_markup)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages"""
    user_id = update.effective_user.id
    is_admin = user_id in ADMIN_IDS
    
    action = context.user_data.get('action')
    text = update.message.text
    
    if is_admin:
        if action == 'add_student':
            # Parse student info: user_id username schedule
            parts = text.split(maxsplit=2)
            if len(parts) < 3:
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_students_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    "❌ Неверный формат.\n\n"
                    "Используйте: `user_id username расписание`\n\n"
                    "Пример: `123456789 vasya пн,ср,пт 15:00`",
                    reply_markup=reply_markup
                )
                return
            
            try:
                user_id_str, username, schedule = parts
                student_id = int(user_id_str)
            except ValueError:
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_students_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    "❌ user_id должен быть числом!\n\n"
                    "Пример: `123456789 vasya пн,ср,пт 15:00`",
                    reply_markup=reply_markup
                )
                return
            
            # Save student to database
            db.add_student(student_id, username, schedule)
            
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_students_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ Ученик @{username} добавлен!\n\n"
                f"📊 Данные:\n"
                f"  • User ID: {student_id}\n"
                f"  • Username: @{username}\n"
                f"  • Расписание: {schedule}",
                reply_markup=reply_markup
            )
            context.user_data['action'] = None
        
        elif action == 'add_lecture_new':
            # Store lecture name temporarily
            context.user_data['lecture_name'] = text
            await update.message.reply_text(f"📤 Отправьте файл лекции '{text}'")
        
        elif action == 'add_category_new_lecture':
            # Add new category and prepare to add lecture
            category = text.strip()
            db.add_category(category)
            context.user_data['lecture_category'] = category
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_add_lecture_new")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"✅ Папка '{category}' создана!\n\n"
                f"Введите название лекции:",
                reply_markup=reply_markup
            )
            context.user_data['action'] = 'add_lecture_new'
            return
        
        elif action == 'add_category':
            # Add new category
            category = text.strip()
            if db.add_category(category):
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_manage_categories")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    f"✅ Папка '{category}' добавлена!",
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text("❌ Ошибка при добавлении папки")
            context.user_data['action'] = None
            return
        
        elif action == 'add_lecture':
            # Store lecture name temporarily
            context.user_data['lecture_name'] = text
            await update.message.reply_text(f"📤 Отправьте файл лекции '{text}'")
        
        elif action == 'edit_student_schedule':
            # Edit student schedule
            student_id = context.user_data.get('edit_student_id')
            student = db.get_student(student_id)
            
            if student:
                new_schedule = text
                if db.update_student(student_id, schedule=new_schedule):
                    await update.message.reply_text(
                        f"✅ Расписание ученика {student['username']} обновлено!\n\n"
                        f"📅 Новое расписание: {new_schedule}"
                    )
                    # Return to edit student menu
                    keyboard = [
                        [InlineKeyboardButton("➕ Добавить лекцию", callback_data=f"edit_student_add_lec_{student_id}")],
                        [InlineKeyboardButton("🗑️ Удалить лекцию", callback_data=f"edit_student_remove_lec_{student_id}")],
                        [InlineKeyboardButton("📝 Редактировать расписание", callback_data=f"edit_student_schedule_{student_id}")],
                        [InlineKeyboardButton("� Добавить ДЗ", callback_data=f"edit_student_add_homework_{student_id}")],
                        [InlineKeyboardButton("�🔙 Назад", callback_data="back_to_admin")],
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await update.message.reply_text(f"✏️ Редактирование {student['username']}:", reply_markup=reply_markup)
                else:
                    await update.message.reply_text("❌ Ошибка при обновлении расписания")
            else:
                await update.message.reply_text("❌ Ученик не найден")
            
            context.user_data['action'] = None
            context.user_data['edit_student_id'] = None
        
        elif action == 'edit_student_homework':
            # Edit student homework
            student_id = context.user_data.get('edit_student_id')
            student = db.get_student(student_id)
            
            if student:
                new_homework = text
                if db.update_student(student_id, homework=new_homework):
                    await update.message.reply_text(
                        f"✅ ДЗ ученика {student['username']} обновлено!\n\n"
                        f"📓 Новое ДЗ: {new_homework}"
                    )
                    # Return to edit student menu
                    keyboard = [
                        [InlineKeyboardButton("➕ Добавить лекцию", callback_data=f"edit_student_add_lec_{student_id}")],
                        [InlineKeyboardButton("🗑️ Удалить лекцию", callback_data=f"edit_student_remove_lec_{student_id}")],
                        [InlineKeyboardButton("📝 Редактировать расписание", callback_data=f"edit_student_schedule_{student_id}")],
                        [InlineKeyboardButton("📓 Добавить ДЗ", callback_data=f"edit_student_add_homework_{student_id}")],
                        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_admin")],
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await update.message.reply_text(f"✏️ Редактирование {student['username']}:", reply_markup=reply_markup)
                else:
                    await update.message.reply_text("❌ Ошибка при обновлении ДЗ")
            else:
                await update.message.reply_text("❌ Ученик не найден")
            
            context.user_data['action'] = None
            context.user_data['edit_student_id'] = None
    
    else:
        # Student actions
        if action == 'edit_schedule':
            new_schedule = text
            student_id = get_student_id(user_id, context)
            if db.update_student(student_id, schedule=new_schedule):
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="student_settings")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(
                    f"✅ Расписание обновлено!\n\n"
                    f"📅 Новое расписание: {new_schedule}",
                    reply_markup=reply_markup
                )
            else:
                keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="student_settings")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text("❌ Ошибка при обновлении расписания", reply_markup=reply_markup)
            context.user_data['action'] = None


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle document uploads"""
    user_id = update.effective_user.id
    is_admin = user_id in ADMIN_IDS
    
    if not is_admin:
        return
    
    action = context.user_data.get('action')
    
    if action not in ['add_lecture', 'add_lecture_new']:
        return
    
    lecture_name = context.user_data.get('lecture_name', 'Unknown')
    category = context.user_data.get('lecture_category', 'Без категории')
    document = update.message.document
    
    # Download file
    file = await context.bot.get_file(document.file_id)
    file_path = os.path.join(LECTURES_DIR, document.file_name)
    await file.download_to_drive(file_path)
    
    # Generate unique ID for lecture
    lecture_id = f"lecture_{int(datetime.now().timestamp())}"
    
    # Store lecture info in database with category
    db.add_lecture(lecture_id, lecture_name, document.file_name, file_path, category)
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_lectures_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✅ Лекция '{lecture_name}' добавлена в папку '{category}'!",
        reply_markup=reply_markup
    )
    context.user_data['action'] = None
    context.user_data['lecture_name'] = None
    context.user_data['lecture_category'] = None


async def schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Schedule command - show student schedule"""
    user_id = update.effective_user.id
    if user_id in ADMIN_IDS:
        return
    
    student = db.get_student(user_id)
    if not student:
        await update.message.reply_text("❌ Ты не зарегистрирован в системе")
        return
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    schedule_text = f"📅 <b>Твоё расписание:</b>\n\n{student['schedule']}"
    await update.message.reply_text(schedule_text, reply_markup=reply_markup, parse_mode="HTML")


async def lectures_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lectures command - show available lectures"""
    user_id = update.effective_user.id
    
    if user_id in ADMIN_IDS:
        # Show all lectures for admin
        all_lectures = db.get_all_lectures()
        if not all_lectures:
            keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_admin")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("📚 Нет лекций в системе", reply_markup=reply_markup)
            return
        
        text = "📚 <b>Все лекции в системе:</b>\n\n"
        for lecture_id, lecture_name in all_lectures.items():
            text += f"📄 {lecture_name}\n"
        
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_admin")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")
    else:
        # Show student lectures
        student = db.get_student(user_id)
        if not student:
            await update.message.reply_text("❌ Ты не зарегистрирован в системе")
            return
        
        if not student.get('lectures'):
            keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("📚 У тебя нет доступных лекций", reply_markup=reply_markup)
            return
        
        text = f"📚 <b>Твои лекции ({len(student['lectures'])}):</b>\n\n"
        
        keyboard = []
        for lecture_id in student['lectures']:
            lecture = db.get_lecture(lecture_id)
            if lecture:
                text += f"📄 {lecture['name']}\n"
                keyboard.append([
                    InlineKeyboardButton(f"⬇️ {lecture['name']}", callback_data=f"download_{lecture_id}"),
                    InlineKeyboardButton("❌", callback_data=f"remove_lecture_{lecture_id}")
                ])
            else:
                text += f"❓ Unknown lecture\n"
        
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Settings command - show student settings"""
    user_id = update.effective_user.id
    if user_id in ADMIN_IDS:
        return
    
    student = db.get_student(user_id)
    if not student:
        await update.message.reply_text("❌ Ты не зарегистрирован в системе")
        return
    
    keyboard = [
        [InlineKeyboardButton("📅 Редактировать расписание", callback_data="student_edit_schedule")],
        [InlineKeyboardButton("📚 Управлять лекциями", callback_data="student_manage_lectures")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    settings_text = f"""
⚙️ <b>Мои настройки</b>

👤 Username: @{student['username']}
📅 Расписание: {student['schedule']}
📚 Лекции: {len(student.get('lectures', []))}
"""
    await update.message.reply_text(settings_text, reply_markup=reply_markup, parse_mode="HTML")


async def students_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Students command - show all students (admin only)"""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        return
    
    # Get all students from database
    all_students = db.get_all_students()
    if not all_students:
        await update.message.reply_text("📋 Нет учеников в системе")
        return
    
    text = f"👥 <b>Список учеников ({len(all_students)}):</b>\n\n"
    
    for student in all_students:
        lectures_count = len(student.get('lectures', []))
        text += f"👤 @{student['username']} (ID: {student['user_id']})\n"
        text += f"   📅 {student['schedule']}\n"
        text += f"   📚 Лекций: {lectures_count}\n\n"
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_admin")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")


async def add_student_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add student command (admin only)"""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        return
    
    context.user_data['action'] = 'add_student'
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_students_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "📝 Отправь данные ученика в формате:\n\n"
        "<code>user_id username расписание</code>\n\n"
        "Пример:\n"
        "<code>123456789 vasya пн,ср,пт 15:00</code>",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )


async def add_lecture_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add lecture command (admin only)"""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        return
    
    context.user_data['action'] = 'add_lecture'
    await update.message.reply_text(
        "📝 Введи название лекции:"
    )


# New category management functions
async def show_manage_categories_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show manage categories menu"""
    categories = db.get_all_categories()
    keyboard = []
    
    for category in categories:
        store_category_mapping(category)
        cat_hash = get_category_hash(category)
        keyboard.append([InlineKeyboardButton(f"📁 {category}", callback_data=f"view_category_{cat_hash}")])
    
    keyboard.append([InlineKeyboardButton("➕ Добавить папку", callback_data="add_category")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_lectures_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text("📁 Редактировать папки:", reply_markup=reply_markup)


async def show_category_details(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str) -> None:
    """Show category details with option to delete"""
    lectures = db.get_lectures_by_category(category)
    
    text = f"📁 <b>{category}</b>\n\n"
    text += f"📚 Лекций: {len(lectures)}\n\n"
    
    if lectures:
        text += "<b>Лекции:</b>\n"
        for lecture_id, lecture_name in lectures.items():
            text += f"  • {lecture_name}\n"
    
    keyboard = []
    if category != "Без категории":
        cat_hash = get_category_hash(category)
        keyboard.append([InlineKeyboardButton("🗑️ Удалить папку", callback_data=f"delete_category_{cat_hash}")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_manage_categories")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')


async def show_add_lecture_new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show select category for new lecture"""
    categories = db.get_all_categories()
    keyboard = []
    
    for category in categories:
        store_category_mapping(category)
        cat_hash = get_category_hash(category)
        keyboard.append([InlineKeyboardButton(f"📁 {category}", callback_data=f"select_cat_new_{cat_hash}")])
    
    keyboard.append([InlineKeyboardButton("➕ Новая папка", callback_data="add_category_for_new_lecture")])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_add_lecture")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text("Выберите папку для новой лекции:", reply_markup=reply_markup)


async def show_categories_for_existing_lecture(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show categories to select existing lecture from"""
    categories = db.get_all_categories()
    keyboard = []
    
    for category in categories:
        store_category_mapping(category)
        cat_hash = get_category_hash(category)
        keyboard.append([InlineKeyboardButton(f"📁 {category}", callback_data=f"select_cat_existing_{cat_hash}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_add_lecture")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text("Выберите папку:", reply_markup=reply_markup)


async def show_lectures_in_category(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str, action: str) -> None:
    """Show lectures in category"""
    lectures = db.get_lectures_by_category(category)
    
    if not lectures:
        keyboard = []
        if action == "existing":
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_add_lecture_existing")])
        elif action == "delete":
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_delete_lecture")])
        else:
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_lectures_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.callback_query.edit_message_text(f"📭 В папке '{category}' нет лекций", reply_markup=reply_markup)
        return
    
    keyboard = []
    for lecture_id, lecture_name in lectures.items():
        if action == "existing":
            keyboard.append([InlineKeyboardButton(f"📚 {lecture_name}", callback_data=f"select_existing_lec_{lecture_id}")])
        elif action == "delete":
            keyboard.append([InlineKeyboardButton(f"🗑️ {lecture_name}", callback_data=f"delete_lecture_{lecture_id}")])
    
    if action == "existing":
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_add_lecture_existing")])
    elif action == "delete":
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_delete_lecture")])
    else:
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_lectures_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text(f"📚 Лекции в папке '{category}':", reply_markup=reply_markup)


async def show_categories_for_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show categories for deleting lectures"""
    categories = db.get_all_categories()
    keyboard = []
    
    for category in categories:
        store_category_mapping(category)
        cat_hash = get_category_hash(category)
        keyboard.append([InlineKeyboardButton(f"📁 {category}", callback_data=f"select_cat_delete_{cat_hash}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_lectures_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.callback_query.edit_message_text("Выберите папку:", reply_markup=reply_markup)


def main() -> None:
    """Start the bot"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("schedule", schedule_command))
    application.add_handler(CommandHandler("lectures", lectures_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("students", students_command))
    application.add_handler(CommandHandler("add_student", add_student_command))
    application.add_handler(CommandHandler("add_lecture", add_lecture_command))
    
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start the bot
    application.run_polling()


if __name__ == '__main__':
    main()
