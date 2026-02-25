import asyncio
import sqlite3
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# --- ASOSIY SOZLAMALAR ---
TELEGRAM_TOKEN = "8509571152:AAFw5GXdZRyuiqTOzm3znlQCa_S4JQXcnvU"
GEMINI_API_KEY = "AIzaSyD3eNOVqi838s25_sU0ErfZTUGG9FAhCek"
ADMIN_ID = 5775388579
ADMIN_USERNAME = "@Sardorbeko008"

# Gemini AI ni sozlash
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# --- MA'LUMOTLAR BAZASI ---
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

# --- MENYU ---
def main_menu(uid):
    buttons = [
        [KeyboardButton(text="💬 AI bilan suhbat")],
        [KeyboardButton(text="📊 Limitim"), KeyboardButton(text="💳 To'lov")]
    ]
    if uid == ADMIN_ID:
        buttons.append([KeyboardButton(text="⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# --- START ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    init_db()
    db_action("INSERT OR IGNORE INTO users (id) VALUES (?)", (message.from_user.id,))
    await message.answer(
        f"Xush kelibsiz! Men Gemini AI botman. 🤖\nSavollaringizga aqlli javoblar beraman.",
        reply_markup=main_menu(message.from_user.id)
    )

# --- LIMITNI TEKSHIRISH ---
@dp.message(F.text == "📊 Limitim")
async def check_limit(message: types.Message):
    user = db_action("SELECT limit_count FROM users WHERE id=?", (message.from_user.id,))
    await message.answer(f"Sizda {user[0]} ta bepul savol berish imkoniyati qoldi.")

# --- TO'LOV MA'LUMOTI ---
@dp.message(F.text == "💳 To'lov")
async def payment_info(message: types.Message):
    card = db_action("SELECT value FROM settings WHERE key='card'")[0]
    await message.answer(f"💎 Premium (Cheksiz) olish uchun:\n\n💳 Karta: `{card}`\n👤 Adminga skrinshot yuboring: {ADMIN_USERNAME}", parse_mode="Markdown")

# --- ADMIN PANEL ---
@dp.message(F.text == "⚙️ Admin Panel")
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    count = db_action("SELECT COUNT(*) FROM users")[0]
    await message.answer(f"Siz adminsiz.\nJami foydalanuvchilar: {count}\n\nLimit qo'shish uchun: `/add ID LIMIT` deb yozing.")

@dp.message(Command("add"))
async def add_limit(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    try:
        _, user_id, amount = message.text.split()
        db_action("UPDATE users SET limit_count = limit_count + ? WHERE id = ?", (amount, user_id))
        await message.answer(f"ID {user_id} ga {amount} ta limit qo'shildi! ✅")
        await bot.send_message(user_id, f"Tabriklaymiz! Sizga {amount} ta qo'shimcha limit berildi. ✨")
    except:
        await message.answer("Xato! Format: `/add ID LIMIT` (Masalan: /add 123456 50)")

# --- GEMINI CHAT ---
@dp.message(F.text)
async def chat_handler(message: types.Message):
    if message.text in ["💬 AI bilan suhbat", "📊 Limitim", "💳 To'lov", "⚙️ Admin Panel"]: return
    
    user = db_action("SELECT limit_count FROM users WHERE id=?", (message.from_user.id,))
    if not user or user[0] <= 0:
        await message.answer("Limitingiz tugadi. ❌\nIltimos, limit sotib oling yoki adminga murojaat qiling.")
        return

    await bot.send_chat_action(message.chat.id, "typing")
    
    try:
        response = model.generate_content(message.text)
        await message.answer(response.text, parse_mode="Markdown")
        # Har bir javobdan keyin limitni 1 taga kamaytirish
        db_action("UPDATE users SET limit_count = limit_count - 1 WHERE id=?", (message.from_user.id,))
    except Exception as e:
        await message.answer("⚠️ Hozirda tizim band. Birozdan so'ng urinib ko'ring.")

async def main():
    init_db()
    print("Gemini Bot Admin Panel bilan ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
