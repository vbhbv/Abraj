from fastapi import FastAPI, HTTPException, Request
import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from models import BirthDataInput, ChartResult, ProfileScores
from chart import CoreAstrologyEngine
from time_service import BirthDataService
from facts_engine import FactsEngine
from scoring import RulesEngine

# إعداد الـ Logs لمراقبة أداء السيرفر والبوت من لوحة التحكم
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Astrology Webhook Bot Engine", version="1.0.0")

engine = CoreAstrologyEngine()
time_service = BirthDataService()

# جلب المتغيرات الأساسية من لوحة تحكم Railway
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BASE_URL = os.getenv("RAILWAY_PUBLIC_URL", "https://Abraj-production.up.railway.app")

# تهيئة تطبيق تليجرام للعمل بنظام الاستقبال الفوري (Webhook)
bot_app = Application.builder().token(TOKEN).build()

# --- منطق ردود البوت الداخلي ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔮 مرحباً بك في بوت المحرك الفلكي الاحترافي!\n\n"
        "أرسل بيانات المولد بالصيغة التالية مباشرة في رسالة واحدة:\n"
        "السنة, الشهر, اليوم, الساعة, الدقيقة, خط الطول, خط العرض\n\n"
        "مثال:\n`1995, 5, 15, 14, 30, 35.2, 45.1`",
        parse_mode="Markdown"
    )

async def handle_bot_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    try:
        # تفكيك النص المرسل عبر الفواصل
        parts = [float(x.strip()) for x in text.split(',')]
        if len(parts) < 7:
            await update.message.reply_text("⚠️ يرجى إدخال العناصر الـ 7 كاملة ومفصولة بفواصل.")
            return

        birth_data = BirthDataInput(
            year=int(parts[0]), month=int(parts[1]), day=int(parts[2]),
            hour=int(parts[3]), minute=int(parts[4]),
            latitude=parts[5], longitude=parts[6]
        )
        
        await update.message.reply_text("🔄 جاري معالجة البيانات الفلكية وتوليد الخريطة والحقائق...")
        
        # الحساب الفلكي المباشر عبر المحرك
        dt_utc = time_service.process_and_convert_to_utc(birth_data)
        chart_data = engine.compute_natal_chart(dt_utc, birth_data.latitude, birth_data.longitude)
        facts = FactsEngine.extract_facts(chart_data)
        score_data = RulesEngine.evaluate(facts)

        # بناء رسالة الرد المنسقة للمستخدم تليجرام
        response_text = f"✨ **النتائج الفلكية المستخرجة:**\n\n"
        response_text += f"🌅 الطالع (Ascendant): {chart_data.ascendant}\n"
        response_text += f"🌌 وتد السماء (Midheaven): {chart_data.midheaven}\n\n"
        response_text += f"🪐 **مواقع الأجرام والبيوت:**\n"
        
        for p_name, p_info in chart_data.planets.items():
            retro = " (تراجع)" if p_info.retrograde else ""
            response_text += f"• {p_name}: {p_info.sign} {p_info.degree}° في البيت {p_info.house}{retro}\n"

        response_text += f"\n📊 **التقييم الحسابي الإجمالي:** {score_data.total_score}\n"
        await update.message.reply_text(response_text, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"❌ حدث خطأ أثناء الحساب: {str(e)}")

# إضافة معالجات الأحداث للبوت المدمج
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bot_message))

# --- مسار استقبال حزم الـ Webhook من سيرفرات تليجرام ---
@app.post("/webhook")
async def telegram_webhook(request: Request):
    """تلقي البيانات المدفوعة وتمريرها للمعالجة الفورية"""
    json_data = await request.json()
    update = Update.de_json(json_data, bot_app.bot)
    await bot_app.process_update(update)
    return {"status": "ok"}

# --- إعداد وتحديث تفعيل الـ Webhook تلقائياً عند إقلاع السيرفر ---
@app.on_event("startup")
async def startup_event():
    await bot_app.initialize()
    webhook_url = f"{BASE_URL}/webhook"
    # إخطار سيرفرات تليجرام بالرابط العام لإرسال الرسائل إليه مباشرة
    await bot_app.bot.set_webhook(url=webhook_url)
    logger.info(f"✅ Webhook successfully set to: {webhook_url}")

@app.on_event("shutdown")
async def shutdown_event():
    await bot_app.bot.delete_webhook()
    await bot_app.shutdown()

@app.get("/")
def health_check():
    return {"status": "online", "mode": "webhook", "public_url": BASE_URL}
