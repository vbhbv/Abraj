import logging
import os
import io
import cairosvg
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, Response
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

from chart import CoreAstrologyEngine
from scoring import RulesEngine
from interpreter import AstrologicalInterpreter
from drawer import AstrologyChartDrawer

# 1. إعداد السجلات (Logging)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 2. تعريف مراحل المحادثة (Conversation States)
YEAR, MONTH, DAY, KNOWS_TIME, TIME, LOCATION = range(6)

# 3. تهيئة المحركات الأساسية
engine = CoreAstrologyEngine()
interpreter = AstrologicalInterpreter()
drawer = AstrologyChartDrawer()

# التوكن والمتغيرات الخاصة بالـ Webhook
TOKEN = "7523578617:AAHECJgxEx-9FB9GN2lWoyJJHrunbzH-BwU"
WEBHOOK_URL = "https://Abraj-production.up.railway.app/webhook"

# بناء تطبيق التليجرام عالمياً ليتمكن FastAPI من قراءته
telegram_app = Application.builder().token(TOKEN).build()

# كائن وسيط مرن لتخطي قيود Pydantic وتوحيد أسماء الحقول لملف الرسم
class FlexibleChartAdapter:
    def __init__(self, raw_chart: Any):
        self.ascendant = getattr(raw_chart, 'ascendant', 'Aries')
        self.ascendant_degree = getattr(raw_chart, 'ascendant_degree', 0.0)
        self.midheaven_degree = getattr(raw_chart, 'midheaven_degree', 270.0)
        self.houses = getattr(raw_chart, 'houses', {})
        
        # نسخ وتكييف الكواكب
        self.planets = {}
        raw_planets = getattr(raw_chart, 'planets', {})
        for p_name, p_data in raw_planets.items():
            class PlanetAdapter:
                def __init__(self, data):
                    self.longitude = getattr(data, 'longitude', getattr(data, 'abs_degree', getattr(data, 'degree', 0.0)))
            self.planets[p_name] = PlanetAdapter(p_data)
            
        # نسخ وتكييف الاتصالات (Aspects) وحل مشكلة p1 و p2 ديناميكياً
        self.aspects = []
        raw_aspects = getattr(raw_chart, 'aspects', [])
        for aspect in raw_aspects:
            class AspectAdapter:
                def __init__(self, asp):
                    self.p1 = getattr(asp, 'p1', getattr(asp, 'planet1', getattr(asp, 'p1_name', None)))
                    self.p2 = getattr(asp, 'p2', getattr(asp, 'planet2', getattr(asp, 'p2_name', None)))
                    self.type = getattr(asp, 'type', getattr(asp, 'aspect_type', 'Conjunction'))
                    self.orb = getattr(asp, 'orb', 0.0)
            
            adapted_asp = AspectAdapter(aspect)
            if adapted_asp.p1 and adapted_asp.p2:
                self.aspects.append(adapted_asp)

# 4. إدارة دورة حياة FastAPI والتليجرام (Lifespan)
@asynccontextmanager
async def lifespan(app: FastAPI):
    await telegram_app.initialize()
    await telegram_app.bot.set_webhook(url=WEBHOOK_URL)
    logger.info(f"✅ Webhook successfully set to: {WEBHOOK_URL}")
    await telegram_app.start()
    yield
    await telegram_app.stop()
    await telegram_app.shutdown()

app = FastAPI(lifespan=lifespan)

@app.post("/webhook")
async def webhook_handler(request: Request):
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return Response(status_code=200)

@app.get("/")
async def root_handler():
    return {"status": "healthy", "bot": "Astrology Bot is running via Webhook"}

# --- منطق المحادثة الفلكية والمراحل ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "🔮 **مرحباً بك في نظام التحليل الفلكي الشامل**\n\n"
        "سنقوم بإعداد خريطتك الشخصية العميقة واستخراج ملامحك الفلكية بدقة.\n"
        "ابدأ بإرسال **سنة ميلادك** بالأرقام (مثال: `1998`):"
    )
    return YEAR

async def p_year(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['year'] = int(update.message.text.strip())
    await update.message.reply_text("📆 ممتاز! الآن أرسل **شهر ميلادك** (رقم من 1 إلى 12):")
    return MONTH

async def p_month(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['month'] = int(update.message.text.strip())
    await update.message.reply_text("🗓 رائع! أرسل الآن **يوم ميلادك** برقم من (1 إلى 31):")
    return DAY

async def p_day(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['day'] = int(update.message.text.strip())
    
    keyboard = [
        [InlineKeyboardButton("✅ نعم، أعرفه بدقة", callback_data="knows_true")],
        [InlineKeyboardButton("❌ لا، غير معروف", callback_data="knows_false")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🕒 هل تعرف **وقت ولادتك الدقيق** (الساعة والدقيقة)؟", reply_markup=reply_markup)
    return KNOWS_TIME

async def p_knows_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    if query.data == "knows_true":
        await query.edit_message_text("🕓 أرسل وقت الولادة بتنسيق 24 ساعة (ساعة:دقيقة) مثال: `18:45`:")
        return TIME
    else:
        context.user_data['hour'] = 12
        context.user_data['minute'] = 0
        context.user_data['unknown_time'] = True
        await query.edit_message_text("📍 أرسل الإحداثيات الجغرافية لمكان ميلادك بتنسيق (خط العرض,خط الطول) مثال: `36.34,43.13`:")
        return LOCATION

async def p_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        time_str = update.message.text.strip()
        hour, minute = map(int, time_str.split(':'))
        context.user_data['hour'] = hour
        context.user_data['minute'] = minute
        context.user_data['unknown_time'] = False
    except ValueError:
        await update.message.reply_text("⚠️ تنسيق غير صحيح، يرجى إرساله مثل `14:30`:")
        return TIME

    await update.message.reply_text("📍 أرسل الإحداثيات الجغرافية لمكان ميلادك بتنسيق (خط العرض,خط الطول) مثال: `36.34,43.13`:")
    return LOCATION

async def p_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        loc_str = update.message.text.strip()
        lat, lon = map(float, loc_str.split(','))
    except ValueError:
        await update.message.reply_text("⚠️ التنسيق خاطئ، يرجى الإرسال هكذا `36.34,43.13`:")
        return LOCATION

    dt_utc = datetime(
        context.user_data['year'],
        context.user_data['month'],
        context.user_data['day'],
        context.user_data['hour'],
        context.user_data['minute']
    )
    
    await update.message.reply_text("⏳ جاري استخراج البيانات وحساب المواقع الفلكية من المصادر الرسمية...")

    try:
        # 1. حساب الخريطة الأساسية من محرك السويس إيفيمريس
        chart_data = engine.compute_natal_chart(dt_utc, lat, lon)
        
        # 2. استخراج وفحص النقاط من محرك القواعد
        facts = [] 
        score_data = RulesEngine.evaluate(facts)
        total_score = score_data.total_score 

        # حفظ البيانات والسكور منفصلين داخل جلسة المستخدم الحالية
        context.user_data['last_chart'] = chart_data
        context.user_data['last_score'] = total_score

        # 3. توليد الرسم ومعالجته الجذري بـ CairoSVG لمنع مشاكل العرض تماماً
        try:
            adapted_chart = FlexibleChartAdapter(chart_data)
            chart_svg_string = drawer.generate_chart_svg(adapted_chart)
            
            # التحويل الحقيقي إلى بايتات صورة PNG آمنة
            png_bytes = cairosvg.svg2png(bytestring=chart_svg_string.encode('utf-8'))
            img_buffer = io.BytesIO(png_bytes)
            img_buffer.name = "natal_chart.png"
            
            # إرسال الخريطة كصورة حقيقية لتظهر فوراً على أندرويد وآيفون
            await update.message.reply_photo(
                photo=img_buffer,
                caption="🪐 **عجلة خريطتك الفلكية الحقيقية (Natal Wheel)**\nتم رسمها هندسياً بدقة بالغة اعتماداً على درجات أجرامك وأوتادك الحقيقية لحظة ميلادك، وهي مدعومة الآن للعرض المباشر على جميع الهواتف."
            )
        except Exception as draw_err:
            logger.error(f"Error during chart drawing conversion or output: {draw_err}", exc_info=True)
            await update.message.reply_text("⚠️ تم حساب بياناتك بنجاح ولكن تعذر توليد الصورة، جاري إرسال التقرير النصي...")

        # 4. حل مشكلة دالة التفسير النصي للمستخدم
        summary_msg = interpreter.get_minimal_summary(chart_data)
        score_display = "🚧 قيد التطوير والحساب" if total_score == 0 else f"{total_score}"
        summary_msg = summary_msg.replace("SCORE_PLACEHOLDER", score_display)
        
        # 5. بناء مصفوفة الأزرار الجذابة التشويقية
        keyboard = [
            [InlineKeyboardButton("🧠 شخصيتك الحقيقية", callback_data="menu_personal"), InlineKeyboardButton("❤️ الحب والزواج", callback_data="menu_love")],
            [InlineKeyboardButton("💼 المهنة المناسبة", callback_data="menu_career"), InlineKeyboardButton("💰 المال والثروة", callback_data="menu_money")],
            [InlineKeyboardButton("🌟 نقاط القوة والضعف", callback_data="menu_features"), InlineKeyboardButton("🔮 التوقعات", callback_data="menu_predict")],
            [InlineKeyboardButton("🪐 الخريطة الكاملة (للمحترفين)", callback_data="menu_full_chart")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(summary_msg, reply_markup=reply_markup, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error during calculations: {e}", exc_info=True)
        await update.message.reply_text("❌ عذراً، حدث خطأ أثناء معالجة البيانات الفلكية داخلياً.")

    return ConversationHandler.END

async def handle_menu_clicks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chart_data = context.user_data.get('last_chart')
    if not chart_data:
        await query.message.reply_text("❌ انتهت صلاحية الجلسة، من فضلك أعد حساب الخريطة باستخدام الأمر /start")
        return

    if query.data == "menu_full_chart":
        detailed_report = interpreter.get_detailed_report(chart_data)
        keyboard = [[InlineKeyboardButton("⬅️ العودة للملخص", callback_data="menu_back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(detailed_report, reply_markup=reply_markup, parse_mode="Markdown")
        
    elif query.data == "menu_back":
        summary_msg = interpreter.get_minimal_summary(chart_data)
        
        total_score = context.user_data.get('last_score', 0)
        score_display = "🚧 قيد التطوير والحساب" if total_score == 0 else f"{total_score}"
        summary_msg = summary_msg.replace("SCORE_PLACEHOLDER", score_display)
            
        keyboard = [
            [InlineKeyboardButton("🧠 شخصيتك الحقيقية", callback_data="menu_personal"), InlineKeyboardButton("❤️ الحب والزواج", callback_data="menu_love")],
            [InlineKeyboardButton("💼 المهنة المناسبة", callback_data="menu_career"), InlineKeyboardButton("💰 المال والثروة", callback_data="menu_money")],
            [InlineKeyboardButton("🌟 نقاط القوة والضعف", callback_data="menu_features"), InlineKeyboardButton("🔮 التوقعات", callback_data="menu_predict")],
            [InlineKeyboardButton("🪐 الخريطة الكاملة (للمحترفين)", callback_data="menu_full_chart")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(summary_msg, reply_markup=reply_markup, parse_mode="Markdown")
        
    else:
        await query.message.reply_text("🚧 هذا القسم من تحليلك الفلكي يتم توليده ومطابقته برمجياً الآن وسيكون متاحاً في التحديث القادم!")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("🚫 تم إلغاء العملية. يمكنك البدء من جديد بإرسال /start")
    return ConversationHandler.END

# 5. تسجيل ومعالجة الـ Handlers
conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, p_year)],
        MONTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, p_month)],
        DAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, p_day)],
        KNOWS_TIME: [CallbackQueryHandler(p_knows_time)],
        TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, p_time)],
        LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, p_location)],
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)

telegram_app.add_handler(conv_handler)
telegram_app.add_handler(CallbackQueryHandler(handle_menu_clicks, pattern="^menu_"))
