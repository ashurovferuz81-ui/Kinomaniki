import asyncio
import sqlite3
import logging
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Loglarni sozlash (Xatoni ko'rish uchun)
logging.basicConfig(level=logging.INFO)

# --- SOZLAMALAR ---
TELEGRAM_TOKEN = "8509571152:AAFw5GXdZRyuiqTOzm3znlQCa_S4JQXcnvU"
GEMINI_API_KEY = "AIzaSyD3eNOVqi838s25_sU0ErfZTUGG9FAhCek"
ADMIN_ID = 5775388579
ADMIN_USERNAME = "@Sardorbeko008"

# Gemini sozlamalari
genai.configure(api_key=GEMINI_API_KEY)
# Bu yerda xavfsizlik sozlamalarini o'chiramiz (javob qaytishi aniq bo'lishi uchun)
generation_config = {
  "temperature": 0.9,
  "top_p": 1,
  "top_k": 1,
  "max_output_tokens": 2048,
}
model = genai.GenerativeModel(model_name="gemini-1.5-flash", generation_config=generation_config)

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- BAZA ---
def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, limit_count INTEGER DEFAULT 10)")
    cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('card', '8600000000000000')")
    conn.commit()
    conn.close()

def db_action(query, params=()):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute(query, params)
    res = cursor.fetchone() if "SELECT" in query else None
    conn.commit()
    conn.close()
    return res

# --- KLAVIATURA ---
def main_menu(uid):
    kb = [
        [KeyboardButton(text="💬 AI bilan suhbat")],
        [KeyboardButton(text="📊 Limitim"), KeyboardButton(text="💳 To'lov")]
    ]
    if uid == ADMIN_ID:
        kb.append([KeyboardButton(text="⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    init_db()
    db_action("INSERT OR IGNORE INTO users (id) VALUES (?)", (message.from_user.id,))
    await message.answer("Salom! Men yangilangan Gemini AI botman. Savol bering!", reply_markup=main_menu(message.from_user.id))

@dp.message(F.text == "📊 Limitim")
async def check_limit(message: types.Message):
    user = db_action("SELECT limit_count FROM users WHERE id=?", (message.from_user.id,))
    await message.answer(f"Sizda {user[0]} ta limit bor.")

@dp.message(F.text == "💳 To'lov")
async def pay(message: types.Message):
    card = db_action("SELECT value FROM settings WHERE key='card'")[0]
    await message.answer(f"Karta: `{card}`\nAdmin: {ADMIN_USERNAME}", parse_mode="Markdown")

@dp.message(Command("add"))
async def add_limit(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    try:
        _, uid, amt = message.text.split()
        db_action("UPDATE users SET limit_count = limit_count + ? WHERE id = ?", (amt, uid))
        await message.answer(f"ID {uid} ga {amt} limit qo'shildi.")
    except:
        await message.answer("Xato! /add ID LIMIT")

# --- ASOSIY CHAT QISMI ---
@dp.message(F.text)
async def ai_chat(message: types.Message):
    # Menyudagi tugmalarni chetlab o'tish
    if message.text in ["💬 AI bilan suhbat", "📊 Limitim", "💳 To'lov", "⚙️ Admin Panel"]:
        return

    # Limitni tekshirish
    user = db_action("SELECT limit_count FROM users WHERE id=?", (message.from_user.id,))
    if not user or user[0] <= 0:
        await message.answer("Limitingiz tugadi. ❌")
        return

    await bot.send_chat_action(message.chat.id, "typing")

    try:
        # Gemini-dan javob olishning eng xavfsiz usuli
        response = model.generate_content(message.text)
        
        # Javobni tekshirish va yuborish
        if response and response.text:
            await message.reply(response.text, parse_mode="Markdown")
            db_action("UPDATE users SET limit_count = limit_count - 1 WHERE id=?", (message.from_user.id,))
        else:
            await message.answer("AI hozircha bu savolga javob bera olmadi.")
            
    except Exception as e:
        logging.error(f"Xatolik yuz berdi: {e}")
        await message.answer("⚠️ Tizimda xatolik. API kalit yoki internet aloqasini tekshiring.")

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
