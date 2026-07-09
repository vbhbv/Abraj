from fastapi import FastAPI, HTTPException
import os
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from models import BirthDataInput, ChartResult, ProfileScores
from chart import CoreAstrologyEngine
from time_service import BirthDataService
from facts_engine import FactsEngine
from scoring import RulesEngine

# 1. إعدادات الـ Logs لقراءة الأحداث من لوحة تحكم Railway
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Astrology Engine Mapped Bot", version="1.0.0")

engine = CoreAstrologyEngine()
time_service = BirthDataService()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# --- أكواد معالجة البوت داخل نفس الملف ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔮 مرحباً بك في المحرك الفلكي المدمج!\n\n"
        "أرسل بيانات المولد بالصيغة التالية مباشرة:\n"
        "السنة, الشهر, اليوم, الساعة, الدقيقة, خط الطول, خط العرض\n\n"
        "مثال:\n1995, 5, 15, 14, 30, 35.2, 45.1"
    )

async def handle_bot_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    try:
        parts = [float(x.strip()) for x in text.split(',')]
        if len(parts) < 7:
            await update.message.reply_text("⚠️ يرجى إدخال العناصر الـ 7 كاملة.")
            return

        # الحساب الفلكي المباشر دون الحاجة لطلبات HTTP خارجية
        birth_data = BirthDataInput(
            year=int(parts[0]), month=int(parts[1]), day=int(parts[2]),
            hour=int(parts[3]), minute=int(parts[4]),
            latitude=parts[5], longitude=parts[6]
        )
        
        await update.message.reply_text("🔄 جاري معالجة البيانات الفلكية وتوليد الخريطة...")
        
        dt_utc = time_service.process_and_convert_to_utc(birth_data)
        chart_data = engine.compute_natal_chart(dt_utc, birth_data.latitude, birth_data.longitude)
        facts = FactsEngine.extract_facts(chart_data)
        score_data = RulesEngine.evaluate(facts)

        # بناء رسالة الرد المنسقة
        response_text = f"✨ **النتائج الفلكية المستخرجة:**\n\n"
        response_text += f"🌅 الطالع: {chart_data.ascendant}\n"
        response_text += f"🌌 وتد السماء: {chart_data.midheaven}\n\n"
        response_text += f"🪐 **موقع الأجرام:**\n"
        
        for p_name, p_info in chart_data.planets.items():
            retro = " (تراجع)" if p_info.retrograde else ""
            response_text += f"• {p_name}: {p_info.sign} {p_info.degree}° في البيت {p_info.house}{retro}\n"

        response_text += f"\n📊 **التقييم الحسابي:** {score_data.total_score}\n"
        await update.message.reply_text(response_text, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"❌ حدث خطأ أثناء الحساب: {str(e)}")

# --- تشغيل البوت كمهام خلفية (Background Task) مع إقلاع السيرفر ---
@app.on_event("startup")
async def startup_event():
    if TOKEN:
        global bot_app
        bot_app = Application.builder().token(TOKEN).build()
        bot_app.add_handler(CommandHandler("start", start))
        bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bot_message))
        
        # تهيئة البوت وبدء الاستماع دورياً في الخلفية
        await bot_app.initialize()
        await bot_app.updater.start_polling()
        await bot_app.start()
        logger.info("✅ Telegram Bot Polling started successfully in background!")
    else:
        logger.error("❌ TELEGRAM_BOT_TOKEN is missing from environment variables!")

@app.on_event("shutdown")
async def shutdown_event():
    if TOKEN and bot_app:
        await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()

@app.get("/")
def health_check():
    return {"status": "online", "bot_running": True if TOKEN else False}
