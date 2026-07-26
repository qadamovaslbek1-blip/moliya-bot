# -*- coding: utf-8 -*-
"""
Moliya Nazorati Bot — shaxsiy xarajatlarni kuzatish uchun Telegram bot.
"""

import os
import sqlite3
import logging
from datetime import datetime, date
from calendar import monthrange

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "SIZNING_BOT_TOKENINGIZ_BU_YERGA")
DB_PATH = os.path.join(os.path.dirname(__file__), "moliya.db")

KATEGORIYALAR = [
    "🍔 Ovqat",
    "🚕 Transport",
    "🏠 Uy-joy",
    "🛍 Kiyim",
    "💊 Sog'liq",
    "🎮 O'yin-kulgi",
    "📚 Ta'lim",
    "📦 Boshqa",
]

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def db_connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS xarajatlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            summa REAL NOT NULL,
            kategoriya TEXT NOT NULL,
            izoh TEXT,
            sana TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS foydalanuvchilar (
            user_id INTEGER PRIMARY KEY,
            ism TEXT,
            oylik_limit REAL DEFAULT 0
        )
        """
    )
    conn.commit()
    conn.close()


def foydalanuvchini_saqlash(user_id: int, ism: str):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO foydalanuvchilar (user_id, ism) VALUES (?, ?)",
        (user_id, ism),
    )
    conn.commit()
    conn.close()


def xarajat_qoshish(user_id: int, summa: float, kategoriya: str, izoh: str = ""):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO xarajatlar (user_id, summa, kategoriya, izoh, sana) VALUES (?, ?, ?, ?, ?)",
        (user_id, summa, kategoriya, izoh, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def oylik_xarajatlar(user_id: int, yil: int, oy: int):
    conn = db_connect()
    cur = conn.cursor()
    boshlanish = f"{yil:04d}-{oy:02d}-01"
    oxirgi_kun = monthrange(yil, oy)[1]
    tugash = f"{yil:04d}-{oy:02d}-{oxirgi_kun:02d}T23:59:59"
    cur.execute(
        """
        SELECT kategoriya, SUM(summa) as jami
        FROM xarajatlar
        WHERE user_id = ? AND sana BETWEEN ? AND ?
        GROUP BY kategoriya
        ORDER BY jami DESC
        """,
        (user_id, boshlanish, tugash),
    )
    natija = cur.fetchall()
    conn.close()
    return natija


def kunlik_xarajatlar(user_id: int, kun: str):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT summa, kategoriya, izoh, sana FROM xarajatlar
        WHERE user_id = ? AND sana LIKE ?
        ORDER BY sana DESC
        """,
        (user_id, f"{kun}%"),
    )
    natija = cur.fetchall()
    conn.close()
    return natija


def limit_ornatish(user_id: int, limit: float):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        "UPDATE foydalanuvchilar SET oylik_limit = ? WHERE user_id = ?",
        (limit, user_id),
    )
    conn.commit()
    conn.close()


def limitni_olish(user_id: int):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT oylik_limit FROM foydalanuvchilar WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else 0


def asosiy_klaviatura():
    tugmalar = [KeyboardButton(k) for k in KATEGORIYALAR]
    qatorlar = [tugmalar[i : i + 2] for i in range(0, len(tugmalar), 2)]
    return ReplyKeyboardMarkup(qatorlar, resize_keyboard=True)


def summani_formatlash(summa: float) -> str:
    return f"{summa:,.0f}".replace(",", " ")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    foydalanuvchini_saqlash(user.id, user.first_name or "")
    matn = (
        f"Assalomu alaykum, {user.first_name}! 👋\n\n"
        "Men — shaxsiy moliya nazorati botiman. Xarajatlaringizni yozib boring, "
        "men esa qayerga qancha pul ketayotganini hisoblab beraman.\n\n"
        "*Qanday foydalanish:*\n"
        "Shunchaki xabar yozing: `50000 taksi`\n"
        "yoki: `taksi 50000`\n\n"
        "*Buyruqlar:*\n"
        "/kunlik — bugungi xarajatlar\n"
        "/oylik — shu oylik hisobot\n"
        "/limit 2000000 — oylik xarajat limitini belgilash\n"
        "/yordam — qo'llanma\n\n"
        "Pastdagi tugmalardan kategoriya tanlab, keyin summani yozishingiz ham mumkin."
    )
    await update.message.reply_text(matn, parse_mode="Markdown", reply_markup=asosiy_klaviatura())


async def yordam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    matn = (
        "*Qo'llanma*\n\n"
        "1️⃣ Xarajat qo'shish uchun shunday yozing:\n"
        "   `50000 taksi` yoki `taksi ish uchun 50000`\n\n"
        "2️⃣ Yoki avval kategoriya tugmasini bosing, keyin faqat summani yuboring.\n\n"
        "3️⃣ /kunlik — bugungi barcha xarajatlaringiz ro'yxati\n"
        "4️⃣ /oylik — shu oy bo'yicha kategoriyalar kesimida hisobot\n"
        "5️⃣ /limit 1500000 — oylik xarajat chegarasini belgilaysiz, limitdan oshsangiz ogohlantiraman"
    )
    await update.message.reply_text(matn, parse_mode="Markdown")


async def kunlik(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bugun = date.today().isoformat()
    yozuvlar = kunlik_xarajatlar(user_id, bugun)

    if not yozuvlar:
        await update.message.reply_text("Bugun hali xarajat kiritilmagan. 📭")
        return

    jami = sum(row[0] for row in yozuvlar)
    satrlar = ["📅 *Bugungi xarajatlar:*\n"]
    for summa, kategoriya, izoh, sana in yozuvlar:
        vaqt = sana.split("T")[1][:5]
        qator = f"• {vaqt} — {kategoriya}: {summani_formatlash(summa)} so'm"
        if izoh:
            qator += f" ({izoh})"
        satrlar.append(qator)

    satrlar.append(f"\n💰 *Jami: {summani_formatlash(jami)} so'm*")
    await update.message.reply_text("\n".join(satrlar), parse_mode="Markdown")


async def oylik(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    hozir = datetime.now()
    natija = oylik_xarajatlar(user_id, hozir.year, hozir.month)

    if not natija:
        await update.message.reply_text("Bu oyda hali xarajat kiritilmagan. 📭")
        return

    jami = sum(row[1] for row in natija)
    satrlar = [f"📊 *{hozir.month}-oy uchun hisobot:*\n"]
    for kategoriya, summa in natija:
        foiz = (summa / jami * 100) if jami else 0
        satrlar.append(f"• {kategoriya}: {summani_formatlash(summa)} so'm ({foiz:.0f}%)")

    satrlar.append(f"\n💰 *Jami: {summani_formatlash(jami)} so'm*")

    limit = limitni_olish(user_id)
    if limit and limit > 0:
        qolgan = limit - jami
        if qolgan >= 0:
            satrlar.append(f"✅ Limitdan {summani_formatlash(qolgan)} so'm qoldi (limit: {summani_formatlash(limit)})")
        else:
            satrlar.append(f"⚠️ Limitdan {summani_formatlash(abs(qolgan))} so'm oshib ketdingiz!")

    await update.message.reply_text("\n".join(satrlar), parse_mode="Markdown")


async def limit_belgilash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Iltimos, summani ko'rsating. Masalan: `/limit 2000000`", parse_mode="Markdown")
        return
    try:
        summa = float(context.args[0].replace(" ", "").replace(",", ""))
    except ValueError:
        await update.message.reply_text("Summani to'g'ri raqam sifatida yozing. Masalan: `/limit 2000000`", parse_mode="Markdown")
        return

    limit_ornatish(user_id, summa)
    await update.message.reply_text(f"✅ Oylik limit {summani_formatlash(summa)} so'm qilib belgilandi.")


TANLANGAN_KATEGORIYA = {}


async def matn_qabul_qilish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    matn = update.message.text.strip()

    if matn in KATEGORIYALAR:
        TANLANGAN_KATEGORIYA[user_id] = matn
        await update.message.reply_text(
            f"{matn} tanlandi. Endi summani yuboring (masalan: 50000)."
        )
        return

    if user_id in TANLANGAN_KATEGORIYA:
        tozalangan = matn.replace(" ", "").replace(",", "")
        try:
            summa = float(tozalangan)
            kategoriya = TANLANGAN_KATEGORIYA.pop(user_id)
            xarajat_qoshish(user_id, summa, kategoriya)
            await update.message.reply_text(
                f"✅ Qo'shildi: {kategoriya} — {summani_formatlash(summa)} so'm",
                reply_markup=asosiy_klaviatura(),
            )
            return
        except ValueError:
            pass

    summa, izoh = matnni_ajratish(matn)
    if summa is None:
        await update.message.reply_text(
            "Tushunmadim 🤔 Iltimos, shunday yozing: `50000 taksi`\n"
            "yoki pastdagi tugmalardan kategoriya tanlang.",
            parse_mode="Markdown",
        )
        return

    kategoriya = kategoriyani_topish(izoh)
    xarajat_qoshish(user_id, summa, kategoriya, izoh)
    await update.message.reply_text(
        f"✅ Qo'shildi: {kategoriya} — {summani_formatlash(summa)} so'm" + (f" ({izoh})" if izoh else "")
    )


def matnni_ajratish(matn: str):
    qismlar = matn.split()
    summa = None
    izoh_qismlari = []
    for qism in qismlar:
        tozalangan = qism.replace(",", "").replace(".", "")
        if tozalangan.isdigit() and summa is None:
            summa = float(tozalangan)
        else:
            izoh_qismlari.append(qism)
    return summa, " ".join(izoh_qismlari)


def kategoriyani_topish(izoh: str) -> str:
    izoh_kichik = izoh.lower()
    mapping = {
        "🍔 Ovqat": ["ovqat", "taom", "restoran", "kafe", "non", "market", "oziq"],
        "🚕 Transport": ["taksi", "avtobus", "metro", "yoqilg'i", "benzin", "transport"],
        "🏠 Uy-joy": ["ijara", "kommunal", "uy", "svet", "gaz", "suv"],
        "🛍 Kiyim": ["kiyim", "poyabzal", "shim", "koylak"],
        "💊 Sog'liq": ["dori", "shifokor", "vrach", "klinika", "sog'liq"],
        "🎮 O'yin-kulgi": ["kino", "o'yin", "concert", "bar", "klub"],
        "📚 Ta'lim": ["kurs", "kitob", "maktab", "universitet", "ta'lim"],
    }
    for kategoriya, kalitlar in mapping.items():
        if any(kalit in izoh_kichik for kalit in kalitlar):
            return kategoriya
    return "📦 Boshqa"


def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("yordam", yordam))
    app.add_handler(CommandHandler("kunlik", kunlik))
    app.add_handler(CommandHandler("oylik", oylik))
    app.add_handler(CommandHandler("limit", limit_belgilash))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, matn_qabul_qilish))

    logger.info("Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
