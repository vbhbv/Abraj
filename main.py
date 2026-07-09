import logging
from datetime import datetime
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

# إعداد السجلات (Logging)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# تعريف مراحل المحادثة (Conversation States)
YEAR, MONTH, DAY, KNOWS_TIME, TIME, LOCATION = range(6)

# تهيئة المحركات الأساسية
engine = CoreAstrologyEngine()
interpreter = AstrologicalInterpreter()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """نقطة البداية ترحب بالمستخدم وتبدأ جمع البيانات step-by-step"""
    await update.message.reply_text(
        "🔮 **مرحباً بك في بوت التحليل الفلكي المتقدم**\n\n"
        "لسنا بحاجة لكتابة أسطر معقدة بعد الآن، سنقوم بإعداد خريطتك خطوة بخطوة.\n"
        "الآن، من فضلك أرسل **سنة ميلادك** بالأرقام (مثال: `1995`):"
    )
    return YEAR

async def p_year(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['year'] = int(update.message.text.strip())
    await update.message.reply_text("📆 ممتاز! الآن أرسل **شهر ميلادك** برقم من (1 إلى 12):")
    return MONTH

async def p_month(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['month'] = int(update.message.text.strip())
    await update.message.reply_text("🗓 رائع! أرسل الآن **يوم ميلادك** برقم من (1 إلى 31):")
    return DAY

async def p_day(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['day'] = int(update.message.text.strip())
    
    # سؤال تفاعلي حول معرفة وقت الولادة
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
        await query.edit_message_text("🕓 من فضلك أرسل وقت الولادة بتنسيق 24 ساعة (ساعة:دقيقة) مثال: `14:30` أو `08:15`:")
        return TIME
    else:
        # وضع الوقت غير المعروف: نعتمد 12:00 ظهراً كافتراض علمي مؤقت
        context.user_data['hour'] = 12
        context.user_data['minute'] = 0
        context.user_data['unknown_time'] = True
        await query.edit_message_text("📍 أخيراً، أرسل الإحداثيات الجغرافية لمكان ميلادك بتنسيق (خط العرض,خط الطول) مثال: `36.34,43.13`:")
        return LOCATION

async def p_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        time_str = update.message.text.strip()
        hour, minute = map(int, time_str.split(':'))
        context.user_data['hour'] = hour
        context.user_data['minute'] = minute
        context.user_data['unknown_time'] = False
    except ValueError:
        await update.message.reply_text("⚠️ تنسيق الوقت غير صحيح. يرجى إرساله مثل `14:30`:")
        return TIME

    await update.message.reply_text("📍 أخيراً، أرسل الإحداثيات الجغرافية لمكان ميلادك بتنسيق (خط العرض,خط الطول) مثال: `36.34,43.13`:")
    return LOCATION

async def p_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        loc_str = update.message.text.strip()
        lat, lon = map(float, loc_str.split(','))
    except ValueError:
        await update.message.reply_text("⚠️ تنسيق الإحداثيات غير صحيح. يرجى إرساله مثل `36.34,43.13`:")
        return LOCATION

    # تجميع كائن الوقت بالكامل
    dt_utc = datetime(
        context.user_data['year'],
        context.user_data['month'],
        context.user_data['day'],
        context.user_data['hour'],
        context.user_data['minute']
    )
    
    await update.message.reply_text("⏳ جاري استخراج البيانات وحساب المواقع الفلكية من المصادر الرسمية...")

    try:
        # حساب الخريطة فلكياً
        chart_data = engine.compute_natal_chart(dt_utc, lat, lon)
        
        # استخراج القواعد الحسابية والمؤشر الإجمالي
        facts = [] # هنا يمكنك تحويل مواضع الكواكب إلى كائنات AstrologicalFact لاحقاً إن أردت
        score_data = RulesEngine.evaluate(facts)
        chart_data.score = score_data.total_score # حقن النتيجة بالخريطة ديناميكياً

        # حفظ البيانات مؤقتاً في سياق ذاكرة المستخدم لعرضها عند ضغط الأزرار
        context.user_data['last_chart'] = chart_data

        # توليد الواجهة الرسومية المبسطة والأزرار التفاعلية
        summary_msg = interpreter.get_minimal_summary(chart_data)
        
        if context.user_data.get('unknown_time'):
            summary_msg += "\n\n⚠️ *تنبيه:* تم استخدام وقت افتراضي لعدم معرفة ساعة الولادة. (لم يتم حساب الطالع والبيوت بدقة)."

        keyboard = [
            [InlineKeyboardButton("🔹 الشخصية والعلاقات", callback_data="menu_personal")],
            [InlineKeyboardButton("🔹 العمل والمال", callback_data="menu_career")],
            [InlineKeyboardButton("🪐 الخريطة الكاملة (للمحترفين)", callback_data="menu_full_chart")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(summary_msg, reply_markup=reply_markup, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error during calculations: {e}", exc_info=True)
        await update.message.reply_text("❌ عذراً، حدث خطأ أثناء معالجة البيانات الفلكية داخلياً.")

    return ConversationHandler.END

async def handle_menu_clicks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الضغط على الأزرار التفاعلية وتحويل القوائم"""
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
        if context.user_data.get('unknown_time'):
            summary_msg += "\n\n⚠️ *تنبيه:* تم استخدام وقت افتراضي لعدم معرفة ساعة الولادة. (لم يتم حساب الطالع والبيوت بدقة)."
            
        keyboard = [
            [InlineKeyboardButton("🔹 الشخصية والعلاقات", callback_data="menu_personal")],
            [InlineKeyboardButton("🔹 العمل والمال", callback_data="menu_career")],
            [InlineKeyboardButton("🪐 الخريطة الكاملة (للمحترفين)", callback_data="menu_full_chart")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(summary_msg, reply_markup=reply_markup, parse_mode="Markdown")
        
    else:
        await query.message.reply_text("🚧 هذه الميزة (التحليل التفصيلي المخصص) قيد التطوير البرمجي حالياً وس تتاح قريباً!")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("🚫 تم إلغاء العملية. يمكنك البدء من جديد في أي وقت بإرسال /start")
    return ConversationHandler.END

def main():
    # ضع التوكن الخاص بالبوت هنا
    TOKEN = "7523578617:AAHECJgxEx-9FB9GN2lWoyJJHrunbzH-BwU"
    
    application = Application.builder().token(TOKEN).build()

    # إعداد معالج المحادثة متعدد الخطوات
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

    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(handle_menu_clicks, pattern="^menu_"))

    # بدء تشغيل البوت بسلاسة
    application.run_polling()

if __name__ == '__main__':
    main()
