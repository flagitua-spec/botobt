#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Телеграм-бот для фіксації емоцій
Базується на матеріалах з емоційної регуляції DBT
"""

import os
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import csv

# Токен бота - встав свій токен від BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Ініціалізація бота
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Стани для FSM
class EmotionLog(StatesGroup):
    choosing_emotion = State()
    intensity = State()
    trigger_event = State()
    motivation = State()
    communication_others = State()
    self_communication = State()

# Емоції з документа
EMOTIONS = {
    "😡 Гнів": ["гнів", "роздратування", "лють", "обурення"],
    "🤢 Огида": ["огида", "відраза", "нехіть"],
    "😒 Заздрість": ["заздрість", "ревнощі до чужого"],
    "😨 Страх": ["страх", "тривога", "паніка", "переляк"],
    "😊 Щастя": ["щастя", "радість", "задоволення"],
    "👀 Ревнощі": ["ревнощі", "підозрілість"],
    "❤️ Любов": ["любов", "прихильність", "ніжність"],
    "😢 Смуток": ["смуток", "горе", "туга"],
    "😳 Сором": ["сором", "ніяковість", "збентеження"],
    "😔 Провина": ["провина", "каяття", "жаль"],
}

# База даних
def init_db():
    conn = sqlite3.connect('emotions.db')
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS emotion_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            emotion TEXT,
            intensity INTEGER,
            trigger_event TEXT,
            motivation TEXT,
            communication_others TEXT,
            self_communication TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Клавіатури
def get_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("📝 Додати емоцію", "📊 Моя статистика")
    keyboard.add("📤 Експортувати дані", "ℹ️ Довідка")
    return keyboard

def get_emotions_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for emotion in EMOTIONS.keys():
        keyboard.insert(emotion)
    keyboard.add("🔙 Назад")
    return keyboard

def get_intensity_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=5)
    for i in range(0, 101, 10):
        keyboard.insert(str(i))
    keyboard.add("🔙 Назад")
    return keyboard

def get_skip_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("⏭ Пропустити", "🔙 Назад")
    return keyboard

# Команда /start
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.answer(
        f"Привіт, {message.from_user.first_name}! 👋\n\n"
        "Я допоможу тобі відстежувати свої емоції.\n\n"
        "Регулярна фіксація емоцій допомагає:\n"
        "• Краще розуміти себе\n"
        "• Виявляти патерни та тригери\n"
        "• Розвивати емоційний інтелект\n\n"
        "Натисни '📝 Додати емоцію', щоб почати!",
        reply_markup=get_main_keyboard()
    )

# Команда /help
@dp.message_handler(commands=['help'])
@dp.message_handler(lambda message: message.text == "ℹ️ Довідка")
async def cmd_help(message: types.Message):
    await message.answer(
        "📚 Як користуватися ботом:\n\n"
        "1️⃣ Натисни '📝 Додати емоцію'\n"
        "2️⃣ Обери емоцію зі списку\n"
        "3️⃣ Вкажи інтенсивність (0-100)\n"
        "4️⃣ Опиши ситуацію (можна пропустити)\n"
        "5️⃣ Додай деталі про мотивацію та реакції\n\n"
        "📊 Статистика - дивися свої записи\n"
        "📤 Експорт - завантажуй дані в CSV\n\n"
        "Базується на методиці DBT (Діалектична Поведінкова Терапія)",
        reply_markup=get_main_keyboard()
    )

# Початок додавання емоції
@dp.message_handler(lambda message: message.text == "📝 Додати емоцію")
async def add_emotion(message: types.Message):
    await EmotionLog.choosing_emotion.set()
    await message.answer(
        "Яку емоцію ти відчуваєш зараз або відчував(ла) нещодавно?",
        reply_markup=get_emotions_keyboard()
    )

# Вибір емоції
@dp.message_handler(state=EmotionLog.choosing_emotion)
async def process_emotion(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад":
        await state.finish()
        await message.answer("Головне меню", reply_markup=get_main_keyboard())
        return

    if message.text not in EMOTIONS:
        await message.answer("Будь ласка, обери емоцію з клавіатури")
        return

    await state.update_data(emotion=message.text)
    await EmotionLog.intensity.set()
    await message.answer(
        f"Обрано: {message.text}\n\n"
        "Яка інтенсивність цієї емоції?\n"
        "(0 = зовсім слабка, 100 = максимальна)",
        reply_markup=get_intensity_keyboard()
    )

# Інтенсивність
@dp.message_handler(state=EmotionLog.intensity)
async def process_intensity(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад":
        await EmotionLog.choosing_emotion.set()
        await message.answer("Обери емоцію", reply_markup=get_emotions_keyboard())
        return

    try:
        intensity = int(message.text)
        if not 0 <= intensity <= 100:
            raise ValueError
    except ValueError:
        await message.answer("Будь ласка, введи число від 0 до 100")
        return

    await state.update_data(intensity=intensity)
    await EmotionLog.trigger_event.set()
    await message.answer(
        "Що сталося? Опиши ситуацію, яка викликала цю емоцію\n\n"
        "(Або натисни 'Пропустити')",
        reply_markup=get_skip_keyboard()
    )

# Тригерна подія
@dp.message_handler(state=EmotionLog.trigger_event)
async def process_trigger(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад":
        await EmotionLog.intensity.set()
        await message.answer("Вкажи інтенсивність", reply_markup=get_intensity_keyboard())
        return

    trigger = "" if message.text == "⏭ Пропустити" else message.text
    await state.update_data(trigger_event=trigger)
    await EmotionLog.motivation.set()
    await message.answer(
        "Яку дію ця емоція мотивувала тебе зробити?\n"
        "Що хотілося зробити?\n\n"
        "(Або натисни 'Пропустити')",
        reply_markup=get_skip_keyboard()
    )

# Мотивація
@dp.message_handler(state=EmotionLog.motivation)
async def process_motivation(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад":
        await EmotionLog.trigger_event.set()
        await message.answer("Опиши ситуацію", reply_markup=get_skip_keyboard())
        return

    motivation = "" if message.text == "⏭ Пропустити" else message.text
    await state.update_data(motivation=motivation)
    await EmotionLog.communication_others.set()
    await message.answer(
        "Як ця емоція вплинула на інших?\n"
        "Що бачили або чули інші люди?\n\n"
        "(Або натисни 'Пропустити')",
        reply_markup=get_skip_keyboard()
    )

# Комунікація з іншими
@dp.message_handler(state=EmotionLog.communication_others)
async def process_communication_others(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад":
        await EmotionLog.motivation.set()
        await message.answer("Яку дію мотивувала емоція?", reply_markup=get_skip_keyboard())
        return

    comm_others = "" if message.text == "⏭ Пропустити" else message.text
    await state.update_data(communication_others=comm_others)
    await EmotionLog.self_communication.set()
    await message.answer(
        "Що сказала тобі ця емоція?\n"
        "Які думки виникли?\n\n"
        "(Або натисни 'Пропустити')",
        reply_markup=get_skip_keyboard()
    )

# Самокомунікація та збереження
@dp.message_handler(state=EmotionLog.self_communication)
async def process_self_communication(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад":
        await EmotionLog.communication_others.set()
        await message.answer("Як емоція вплинула на інших?", reply_markup=get_skip_keyboard())
        return

    self_comm = "" if message.text == "⏭ Пропустити" else message.text

    # Отримуємо всі дані
    data = await state.get_data()

    # Зберігаємо в БД
    conn = sqlite3.connect('emotions.db')
    c = conn.cursor()
    c.execute("""
        INSERT INTO emotion_logs 
        (user_id, username, emotion, intensity, trigger_event, motivation, 
         communication_others, self_communication, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        message.from_user.id,
        message.from_user.username or message.from_user.first_name,
        data['emotion'],
        data['intensity'],
        data['trigger_event'],
        data['motivation'],
        data['communication_others'],
        self_comm,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    conn.close()

    await state.finish()
    await message.answer(
        "✅ Запис збережено!\n\n"
        f"Емоція: {data['emotion']}\n"
        f"Інтенсивність: {data['intensity']}/100\n"
        f"Час: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        reply_markup=get_main_keyboard()
    )

# Статистика
@dp.message_handler(lambda message: message.text == "📊 Моя статистика")
async def show_stats(message: types.Message):
    conn = sqlite3.connect('emotions.db')
    c = conn.cursor()
    c.execute("""
        SELECT emotion, COUNT(*), AVG(intensity), MAX(timestamp)
        FROM emotion_logs
        WHERE user_id = ?
        GROUP BY emotion
        ORDER BY COUNT(*) DESC
    """, (message.from_user.id,))

    results = c.fetchall()

    if not results:
        await message.answer("У тебе ще немає записів. Додай першу емоцію!")
        conn.close()
        return

    stats_text = "📊 Твоя статистика емоцій:\n\n"
    for emotion, count, avg_intensity, last_time in results:
        stats_text += f"{emotion}\n"
        stats_text += f"  Записів: {count}\n"
        stats_text += f"  Середня інтенсивність: {avg_intensity:.1f}/100\n"
        stats_text += f"  Остання: {last_time}\n\n"

    # Загальна кількість
    c.execute("SELECT COUNT(*) FROM emotion_logs WHERE user_id = ?", (message.from_user.id,))
    total = c.fetchone()[0]
    stats_text += f"\n📝 Всього записів: {total}"

    conn.close()
    await message.answer(stats_text, reply_markup=get_main_keyboard())

# Експорт даних
@dp.message_handler(lambda message: message.text == "📤 Експортувати дані")
async def export_data(message: types.Message):
    conn = sqlite3.connect('emotions.db')
    c = conn.cursor()
    c.execute("""
        SELECT timestamp, emotion, intensity, trigger_event, motivation,
               communication_others, self_communication
        FROM emotion_logs
        WHERE user_id = ?
        ORDER BY timestamp DESC
    """, (message.from_user.id,))

    results = c.fetchall()
    conn.close()

    if not results:
        await message.answer("Немає даних для експорту")
        return

    # Створюємо CSV
    filename = f'emotions_{message.from_user.id}.csv'
    with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Дата та час', 'Емоція', 'Інтенсивність', 'Тригерна подія', 
                        'Мотивація', 'Вплив на інших', 'Що сказала емоція'])
        writer.writerows(results)

    # Відправляємо файл
    with open(filename, 'rb') as f:
        await message.answer_document(f, caption="📊 Твої емоційні записи")

    # Видаляємо файл
    os.remove(filename)

if __name__ == '__main__':
    print("Бот запущено...")
    executor.start_polling(dp, skip_updates=True)
