import os
import logging
import httpx
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# إعداد تتبع الأخطاء (Logs) داخل السيرفر
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# جلب التوكن ورابط السيرفر محلياً من المتغيرات
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# بما أن البوت يعمل في نفس الحاوية، يمكنه مخاطبة FastAPI عبر localhost ومنافذه مباشرة
FASTAPI_URL = "http://127.0.0.1:8080" 

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """رسالة الترحيب عند تشغيل البوت"""
    reply_keyboard = [['/chart', '/status']]
    await update.message.reply_text(
        "🔮 مرحبًا بك في المحرك الفلكي الاحترافي!\n\n"
        "استخدم الأوامر التالية للتفاعل:\n"
        "🔹 /chart - لحساب الخريطة الفلكية ونقاط البروفايل.\n"
        "🔹 /status - لفحص حالة السيرفر وقاعدة البيانات.",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=True)
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """التحقق من حالة السيرفر من خلال دالة الـ health check"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{FASTAPI_URL}/")
            if response.status_code == 200:
                data = response.json()
                status_msg = (
                    "✅ السيرفر يعمل بنجاح!\n"
                    f"⚙️ المحرك: {data.get('engine')}\n"
                    f"🗄️ قاعدة البيانات: {'متصلة' if data.get('database_configured') else 'غير متصلة'}\n"
                    f"🤖 البوت: {'مربوط' if data.get('telegram_bot_configured') else 'غير مربوط'}"
                )
            else:
                status_msg = "⚠️ السيرفر متصل ولكن هناك استجابة غير متوقعة."
    except Exception as e:
        status_msg = f"❌ تعذر الاتصال بالسيرفر الداخلي. الخطأ: {str(e)}"
    
    await update.message.reply_text(status_msg)

async def chart_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """أمر طلب حساب الخريطة الفلكية"""
    await update.message.reply_text(
        "قم بإرسال بيانات المولد بالصيغة التالية (نصاً في رسالة واحدة):\n\n"
        "السنة, الشهر, اليوم, الساعة, الدقيقة, خط الطول, خط العرض\n\n"
        "مثال:\n"
        "`1995, 5, 15, 14, 30, 35.2, 45.1`",
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالجة الرسائل النصية وحساب الخريطة عبر إرسالها لـ FastAPI"""
    text = update.message.text
    try:
        # تفكيك النص المرسل من المستخدم
        parts = [float(x.strip()) for x in text.split(',')]
        if len(parts) < 7:
            await update.message.reply_text("⚠️ يرجى إدخال جميع العناصر الـ 7 المطلوبة مفصولة بفاصلة كما في المثال.")
            return

        # تجهيز البيانات لإرسالها لـ API الخاص بـ FastAPI
        payload = {
            "year": int(parts[0]), "month": int(parts[1]), "day": int(parts[2]),
            "hour": int(parts[3]), "minute": int(parts[4]),
            "latitude": parts[5], "longitude": parts[6]
        }

        await update.message.reply_text("🔄 جاري معالجة البيانات الفلكية وتوليد الخريطة...")

        async with httpx.AsyncClient() as client:
            # 1. حساب الأجرام الفلكية والبيوت
            chart_res = await client.post(f"{FASTAPI_URL}/api/v1/chart", json=payload, timeout=15.0)
            if chart_res.status_code != 200:
                await update.message.reply_text(f"❌ فشل الحساب الفلكي: {chart_res.text}")
                return
            chart_data = chart_res.json()

            # 2. جلب الحساب التقييمي (Scoring) بناءً على الخريطة الناتجة
            scoring_res = await client.post(f"{FASTAPI_URL}/api/v1/scoring", json=chart_data, timeout=15.0)
            
            # بناء رسالة الرد النهائي للمستخدم برمجياً بشكل منسق
            response_text = f"✨ **النتائج الفلكية المستخرجة:**\n\n"
            response_text += f"🌅 الطالع (Ascendant): {chart_data.get('ascendant')}\n"
            response_text += f"🌌 وتد السماء (Midheaven): {chart_data.get('midheaven')}\n\n"
            response_text += f"🪐 **مواقع الكواكب والبيوت:**\n"
            
            planets = chart_data.get('planets', {})
            for p_name, p_info in planets.items():
                retro = " (تراجع)" if p_info.get('retrograde') else ""
                response_text += f"• {p_name}: {p_info.get('sign')} {p_info.get('degree')}° في البيت {p_info.get('house')}{retro}\n"

            if scoring_res.status_code == 200:
                score_data = scoring_res.json()
                response_text += f"\n📊 **التقييم والبروفايل الحسابي:**\n"
                response_text += f"• التقييم الإجمالي: {score_data.get('total_score', 'N/A')}\n"

            await update.message.reply_text(response_text, parse_mode="Markdown")

    except ValueError:
        await update.message.reply_text("❌ صيغة البيانات غير صحيحة. يرجى إرسال أرقام فقط مفصولة بفواصل.")
    except Exception as e:
        await update.message.reply_text(  f"⚠️ حدث خطأ أثناء الاتصال بالمحرك: {str(e)}")

def main() -> None:
    """تشغيل وإقلاع بوت التيليجرام برمجياً"""
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN variables is missing!")
        return

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("chart", chart_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot execution polling started...")
    application.run_polling()

if __name__ == '__main__':
    main()
          
