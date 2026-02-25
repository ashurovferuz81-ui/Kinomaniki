import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# --- SOZLAMALAR ---
TOKEN = "8509571152:AAFw5GXdZRyuiqTOzm3znlQCa_S4JQXcnvU"
ADMIN_ID = 5775388579
ADMIN_USERNAME = "@Sardorbeko008"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- BAZA ---
def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, limit_count INTEGER DEFAULT 2)")
    cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('card', '8600123456789012')")
    conn.commit()
    conn.close()

def update_db(query, params=()):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    conn.close()

def get_db(query, params=()):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute(query, params)
    res = cursor.fetchone()
    conn.close()
    return res

# --- KLAVIATURALAR ---
def main_menu(uid):
    kb = [[KeyboardButton(text="🎨 Rasm chizish")]]
    kb.append([KeyboardButton(text="📊 Limitim")])
    if uid == ADMIN_ID:
        kb.append([KeyboardButton(text="⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# --- HANDLERLAR ---
@dp.message(Command("start"))
async def start(message: types.Message):
    init_db()
    update_db("INSERT OR IGNORE INTO users (id) VALUES (?)", (message.from_user.id,))
    await message.answer("Xush kelibsiz! Men AI rasm chizuvchi botman.", reply_markup=main_menu(message.from_user.id))

@dp.message(F.text == "📊 Limitim")
async def my_limit(message: types.Message):
    user = get_db("SELECT limit_count FROM users WHERE id=?", (message.from_user.id,))
    await message.answer(f"Sizda {user[0]} ta bepul limit bor.")

@dp.message(F.text == "🎨 Rasm chizish")
async def draw_start(message: types.Message):
    user = get_db("SELECT limit_count FROM users WHERE id=?", (message.from_user.id,))
    if user[0] <= 0:
        card = get_db("SELECT value FROM settings WHERE key='card'")[0]
        btn = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💎 Premium olish", callback_data="buy")]])
        return await message.answer(f"Limitingiz tugadi.\nKarta: `{card}`\nSkrinshotni {ADMIN_USERNAME} ga tashlang.", reply_markup=btn, parse_mode="Markdown")
    
    await message.answer("Rasm uchun Inglizcha so'z yuboring:")

@dp.message()
async def generate(message: types.Message):
    if message.text in ["📊 Limitim", "🎨 Rasm chizish", "⚙️ Admin Panel"]: return
    
    user = get_db("SELECT limit_count FROM users WHERE id=?", (message.from_user.id,))
    if user[0] > 0:
        wait = await message.answer("Chizyapman... 🎨")
        # Tekin rasm generator linki
        img_url = f"https://pollinations.ai/p/{message.text.replace(' ', '%20')}?width=1024&height=1024"
        
        try:
            await message.answer_photo(photo=img_url, caption=f"Tayyor! ✅\nLimit -1")
            update_db("UPDATE users SET limit_count = limit_count - 1 WHERE id=?", (message.from_user.id,))
            await wait.delete()
        except:
            await wait.edit_text("Xatolik bo'ldi.")
    else:
        await message.answer("Limit tugagan!")

# Admin panel sodda qilib
@dp.callback_query(F.data == "buy")
async def buy_info(call: types.CallbackQuery):
    await call.answer("Admin bilan bog'laning!", show_alert=True)

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
