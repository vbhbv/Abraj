import logging
import os
import io
import json
import random
import time
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Dict, Any, List

from fastapi import FastAPI, Request, Response
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode  
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


# =====================================================================
# محرك الخيرة الرقمية المرتبط بملف khira_data.json ونظام منع التكرار
# =====================================================================
class KhiraEngine:
    def __init__(self, json_path: str = "khira_data.json"):
        self.json_path = json_path
        self.cooldowns = {}
        self.cooldown_duration = 3600  # حظر التكرار لمدة ساعة واحدة (3600 ثانية)
        self.khira_data = self.load_khira_json()

    def load_khira_json(self) -> Dict[str, List[Dict[str, Any]]]:
        try:
            if os.path.exists(self.json_path):
                with open(self.json_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                logger.warning(f"⚠️ الملف {self.json_path} غير موجود، تم اعتماد هيكل افتراضي.")
                return {"good": [], "medium": [], "bad": []}
        except Exception as e:
            logger.error(f"Error loading Khira JSON file: {e}")
            return {"good": [], "medium": [], "bad": []}

    def check_cooldown(self, user_id: int) -> int:
        current_time = time.time()
        if user_id in self.cooldowns:
            time_passed = current_time - self.cooldowns[user_id]
            if time_passed < self.cooldown_duration:
                return int((self.cooldown_duration - time_passed) // 60)
        return 0

    def get_random_khira(self, user_id: int) -> Dict[str, Any]:
        categories = ["good", "medium", "bad"]
        weights = [0.50, 0.30, 0.20]
        chosen_category = random.choices(categories, weights=weights, k=1)[0]
        
        options_list = self.khira_data.get(chosen_category, [])
        if not options_list:
            return {}
            
        self.cooldowns[user_id] = time.time()
        return random.choice(options_list)

    @staticmethod
    def get_main_keyboard():
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔮 طلب خيرة جديدة", callback_data="khira_request")],
            [InlineKeyboardButton("📜 شروط وآداب الخيرة", callback_data="khira_rules")],
            [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_home")]
        ])

# تهيئة محرك الخيرة عالمياً
khira_engine = KhiraEngine()


# =====================================================================
# محرك التحليل الفلكي التركيبي الذكي (النقلة التقنية للمحترفين)
# =====================================================================
class AstrologySynthesisEngine:
    def __init__(self, json_path: str = "interpretations.json"):
        self.json_path = json_path
        self.interpretations = self.load_interpretations()
        self.connectors = [
            " يتكامل this التموقع بعمق مع وجوده في ",
            "، الأمر الذي ينعكس بشكل مباشر على شؤون ",
            "، مما يمنح طاقة this الكوكب تجسيداً عملياً داخل ",
            " ليصبح مسرحاً رئيسياً لـ "
        ]

    def load_interpretations(self) -> Dict[str, Any]:
        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading JSON file: {e}")
            return {}

    def calculate_element_balance(self, birth_data: Dict[str, str]) -> str:
        elements = {"نارية": 0, "ترابية": 0, "هوائية": 0, "مائية": 0}
        element_mapping = {
            "Aries": "نارية", "Leo": "نارية", "Sagittarius": "نارية",
            "Taurus": "ترابية", "Virgo": "ترابية", "Capricorn": "ترابية",
            "Gemini": "هوائية", "Libra": "هوائية", "Aquarius": "هوائية",
            "Cancer": "مائية", "Scorpio": "مائية", "Pisces": "مائية"
        }
        
        for planet in ["Sun", "Moon", "Mercury", "Venus", "Mars"]:
            sign = birth_data.get(planet)
            if sign in element_mapping:
                elements[element_mapping[sign]] += 1
                
        dominant_element = max(elements, key=elements.get)
        balance_reports = {
            "نارية": "🔥 تفوح خريطتك بطاقة نارية دافقة، مما يمنحك روحاً مبادرة، حماساً اشتعالياً، ورغبة مستمرة في قيادة واقعك وتحدي الركود.",
            "ترابية": "🪵 تهيمن العناصر الترابية على بنيتك الفلكية، مما يجعلك شخصاً شديد الواقعية، يبحث عن الأمان الملموس، ويتقن الصبر وبناء الاستقرار طويل الأمد.",
            "هوائية": "💨 طغيان الطابع الهوائي يمنحك عقلاً حاداً، وفضولاً معرفياً لا يهدأ، حيث تتنفس عبر الأفكار، التواصل، والتحليل المستمر للمحيط.",
            "مائية": "💧 الغلبة هنا للعنصر المائي؛ أنت تسبح في عالم من الحدس، المشاعر العميقة، والامتصاص النفسي لطاقات الآخرين، مما يمنحك بصيرة شفائية استثنائية."
        }
        return balance_reports.get(dominant_element, "")

    def detect_psychological_conflicts(self, birth_data: Dict[str, str]) -> List[str]:
        conflicts = []
        sun = birth_data.get("Sun")
        moon = birth_data.get("Moon")
        
        if sun == "Leo" and moon in ["Virgo", "Cancer", "Scorpio"]:
            conflicts.append(
                "🔄 **تناقض الهوية الداخلي:** تختبر صراعاً صامتاً بين شمسك في الأسد التي تعشق التقدير والظهور، وبين قمرك الباطني الذي يميل للتحفظ، الخصوصية، والتحليل خلف الكواليس."
            )
        if sun == "Aries" and moon == "Libra":
            conflicts.append(
                "🔄 **محور المواجهة والسلام:** روحك ممزقة بين رغبة شمسك في الحسم والمواجهة الشجاعة المباشرة، وبين حاجة قمرك في الميزان للمداراة، الدبلوماسية، والحفاظ على السلم مع الآخرين بأي ثمن."
            )
        return conflicts

    def synthesize_astrology_report(self, birth_data: Dict[str, str]) -> List[str]:
        messages_to_send = []
        header = "🔮 **التحليل الفلكي التركيبي للمحترفين** 🔮\n\n"
        header += self.calculate_element_balance(birth_data) + "\n\n"
        
        conflicts = self.detect_psychological_conflicts(birth_data)
        if conflicts:
            header += "⚠️ **رادار البصيرة الفلكية (التناقضات المكتشفة):**\n" + "\n".join(conflicts) + "\n\n"
            
        header += "📌 **التشريح التفصيلي للمواضع الفلكية:**\n"
        current_chunk = header
        
        for planet, sign in birth_data.items():
            if planet in ["house_1", "house_2"] or "_house" in planet:
                continue
                
            house = birth_data.get(f"{planet}_house", "1")
            sign_text = self.interpretations.get(planet, {}).get(sign, "")
            house_text = self.interpretations.get(planet, {}).get(str(house), "")
            
            if sign_text and house_text:
                combined_analysis = f"🪐 **{planet} في {sign} داخل البيت {house}:**\n{sign_text}{self.connectors[1]}{house}\n↳ *العمق الاستراتيجي:* {house_text}\n\n"
                
                if len(current_chunk) + len(combined_analysis) > 3500:
                    messages_to_send.append(current_chunk)
                    current_chunk = combined_analysis
                else:
                    current_chunk += combined_analysis
                    
        if current_chunk:
            messages_to_send.append(current_chunk)
            
        return messages_to_send


# كائن وسيط مرن لتخطي قيود Pydantic وتوحيد أسماء الحقول لملف الرسم
class FlexibleChartAdapter:
    def __init__(self, raw_chart: Any):
        self.ascendant = getattr(raw_chart, 'ascendant', 'Aries')
        self.ascendant_degree = getattr(raw_chart, 'ascendant_degree', 0.0)
        self.midheaven_degree = getattr(raw_chart, 'midheaven_degree', 270.0)
        self.houses = getattr(raw_chart, 'houses', {})
        
        self.planets = {}
        raw_planets = getattr(raw_chart, 'planets', {})
        for p_name, p_data in raw_planets.items():
            class PlanetAdapter:
                def __init__(self, data):
                    self.longitude = getattr(data, 'longitude', getattr(data, 'abs_degree', getattr(data, 'degree', 0.0)))
            self.planets[p_name] = PlanetAdapter(p_data)
            
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
    return {"status": "healthy", "bot": "Unified Bot is running via Webhook"}


# =====================================================================
# منطق معالجة القائمة الرئيسية وأمر /start المحدث
# =====================================================================
def get_start_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔮 قسم الأبراج والفلك", callback_data="go_astrology")],
        [InlineKeyboardButton("📖 قسم الخيرة الرقمية", callback_data="go_khira")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # مسح أي بيانات سابقة لبدء جلسة نظيفة عند كتابة /start
    context.user_data.clear()
    
    welcome_text = (
        "🔮 **مرحباً بك في البوت الشامل** 🔮\n\n"
        "الرجاء اختيار القسم الذي تود الدخول إليه من الأزرار أدناه:"
    )
    await update.message.reply_text(welcome_text, reply_markup=get_start_keyboard(), parse_mode=ParseMode.MARKDOWN)
    return ConversationHandler.END


# --- معالجة الانتقال إلى الخيرة الرقمية ---
async def khira_start_from_menu(query: Update.callback_query, context: ContextTypes.DEFAULT_TYPE):
    welcome_khira = (
        "✨ **خدمة الخيرة والاستخارة الرقمية** ✨\n\n"
        "«فَإِذَا عَزَمْتَ فَتَوَكَّلْ عَلَى اللَّهِ ۚ إِنَّ اللَّهَ يُحِبُّ الْمُتَوَكِّلِينَ»\n\n"
        "يرجى استحضار النية، وقراءة سورة الفاتحة متبوعة بالصلاة على محمد وآل محمد، ثم اضغط على الزر أدناه لبدء الخيرة.\n\n"
        "⚠️ **تنويه إخلاء مسؤولية:**\n"
        "هذه الخدمة برمجية استرشادية رقمية مبنية على التفاؤل بالقرآن الكريم."
    )
    await query.edit_message_text(welcome_khira, reply_markup=khira_engine.get_main_keyboard(), parse_mode=ParseMode.MARKDOWN)


# --- بدء استمارة الأبراج من ضغطة زر ---
async def astrology_trigger_workflow(query: Update.callback_query, context: ContextTypes.DEFAULT_TYPE) -> int:
    await query.edit_message_text(
        "🔮 **نظام التحليل الفلكي الشامل**\n\n"
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
    
    await update.message.reply_text("⏳ جاري استخراج وحساب البيانات والمواضع الفلكية الحقيقية...")

    try:
        # حساب وحفظ البيانات الأساسية في الجلسة دون إرسال أي صورة تلقائياً
        chart_data = engine.compute_natal_chart(dt_utc, lat, lon)
        facts = [] 
        score_data = RulesEngine.evaluate(facts)
        total_score = score_data.total_score 

        context.user_data['last_chart'] = chart_data
        context.user_data['last_score'] = total_score
        context.user_data['lat'] = lat
        context.user_data['lon'] = lon

        # توليد رسالة الاختصار والترحيب المبدئي بقسم الفلك
        summary_msg = interpreter.get_minimal_summary(chart_data)
        score_display = "🚧 قيد الحساب" if total_score == 0 else f"{total_score}"
        summary_msg = summary_msg.replace("SCORE_PLACEHOLDER", score_display)
        
        # الأزرار الجديدة المحددة والمختصرة طبقاً لطلبك
        keyboard = [
            [InlineKeyboardButton("📜 قراءة برجك والتحليل الكامل", callback_data="menu_read_all")],
            [InlineKeyboardButton("🖼 توليد الخريطة الفلكية (صورة)", callback_data="menu_generate_image")],
            [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_home")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(summary_msg, reply_markup=reply_markup, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error during calculations: {e}", exc_info=True)
        await update.message.reply_text("❌ عذراً، حدث خطأ أثناء معالجة البيانات الفلكية داخلياً.")

    return ConversationHandler.END


# =====================================================================
# معالج ضغطات الأزرار الموحد والمختصر بالكامل
# =====================================================================
async def handle_menu_clicks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data

    # --- إدارة الصفحة الرئيسية والعودة ---
    if data == "main_home":
        await query.answer()
        context.user_data.clear()
        welcome_text = (
            "🔮 **مرحباً بك في البوت الشامل** 🔮\n\n"
            "الرجاء اختيار القسم الذي تود الدخول إليه من الأزرار أدناه:"
        )
        await query.edit_message_text(welcome_text, reply_markup=get_start_keyboard(), parse_mode=ParseMode.MARKDOWN)
        return

    elif data == "go_khira" or data == "khira_back":
        await query.answer()
        await khira_start_from_menu(query, context)
        return

    # --- معالجة أزرار نظام الخيرة المعتمدة على khira_data.json ---
    elif data == "khira_request":
        remaining = khira_engine.check_cooldown(user_id)
        if remaining > 0:
            await query.answer(
                f"⚠️ لا يمكن تكرار الخيرة في نفس الأمر هكذا!\nانتظر {remaining} دقيقة أو تدبر في نتيجتك الحالية أولاً.",
                show_alert=True
            )
            return

        chosen = khira_engine.get_random_khira(user_id)
        if not chosen:
            await query.answer("عذراً، لم يتم العثور على نصوص كافية داخل ملف khira_data.json", show_alert=True)
            return

        await query.answer("جاري سحب نتيجتك الآن...")
        result_text = (
            f"🔮 **نتيجـة الخيـرة الخاصـة بك**\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📖 **الآية الشريفة الصاعدة:**\n"
            f"**{chosen['verse']}**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 **الحكم والدرجة:**\n"
            f"درجة التيسير: {chosen['stars']}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💬 **التوجيه والتفسير:**\n"
            f"{chosen['interpretation']}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🤲 **الدعاء المستحب والعمل:**\n"
            f"_{chosen['dua']}_\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ *ملاحظة: الخيرة للاسترشاد والتفاؤل، والأمر كله بيد الله تعالى.*"
        )
        back_markup = InlineKeyboardMarkup([[InlineKeyboardButton("↩️ العودة لقائمة الخيرة", callback_data="khira_back")]])
        await query.edit_message_text(result_text, reply_markup=back_markup, parse_mode=ParseMode.MARKDOWN)
        return

    elif data == "khira_rules":
        await query.answer()
        rules_text = (
            "📜 **آداب وشروط عمل الخيرة:**\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "1️⃣ **النية الصادقة:** أن تكون حائراً فعلاً بين أمرين ولم تصل لقرار حاسم بعد الاستشارة والتدبر.\n"
            "2️⃣ **عدم التكرار:** لا تُكرر الخيرة في نفس الأمر إطلاقاً ما لم تتغير ظروف القضية جذرياً.\n"
            "3️⃣ **الرضا بالنتيجة:** تسليم الأمر لله تعالى والعمل بموجب التوجيه الصاعد بقلب مطمئن.\n"
            "4️⃣ **الطهارة والتوجه:** يُفضل استحضار النية والوضوء متوجهاً للقبلة المشرفة أثناء طلب الخيرة."
        )
        back_markup = InlineKeyboardMarkup([[InlineKeyboardButton("↩️ العودة لقائمة الخيرة", callback_data="khira_back")]])
        await query.edit_message_text(rules_text, reply_markup=back_markup, parse_mode=ParseMode.MARKDOWN)
        return

    # --- معالجة أزرار التحليل الفلكي والأبراج ---
    chart_data = context.user_data.get('last_chart')
    
    # قائمة العودة الخاصة بصفحة الأبراج بعد انتهاء الحساب
    astrology_back_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📜 قراءة برجك والتحليل الكامل", callback_data="menu_read_all")],
        [InlineKeyboardButton("🖼 توليد الخريطة الفلكية (صورة)", callback_data="menu_generate_image")],
        [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_home")]
    ])

    if not chart_data and data.startswith("menu_"):
        await query.answer()
        await query.message.reply_text("❌ انتهت صلاحية الجلسة، من فضلك أعد إدخال البيانات.")
        return

    try:
        # زر قراءة البرج والتحليل الشامل دفعة واحدة دون تقسيمات فرعية
        if data == "menu_read_all":
            await query.answer("جاري استخلاص وتحليل كافة المؤشرات الفلكية المتقدمة...")
            
            full_report = interpreter.get_detailed_report(chart_data)
            asc_sign = getattr(chart_data, 'ascendant', 'غير معروف')
            
            complete_analysis = (
                f"🪐 **التقرير الفلكي الشامل والكامل لخريطتك** 🪐\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"• **البرج الصاعد (الطالع):** {asc_sign}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{full_report}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"✨ انتهى التقرير النصي الشامل."
            )
            
            # إذا كان النص طويلاً جداً يتم إرساله مقسماً لضمان عدم تجاوز حدود التليجرام
            if len(complete_analysis) > 4000:
                parts = [complete_analysis[i:i+4000] for i in range(0, len(complete_analysis), 4000)]
                for i, part in enumerate(parts):
                    if i == len(parts) - 1:
                        await query.message.reply_text(part, reply_markup=astrology_back_markup, parse_mode="Markdown")
                    else:
                        await telegram_app.bot.send_message(chat_id=user_id, text=part, parse_mode="Markdown")
            else:
                await query.edit_message_text(complete_analysis, reply_markup=astrology_back_markup, parse_mode="Markdown")

        # زر توليد وإرسال الصورة البيانية فقط وحصرياً عند طلبه
        elif data == "menu_generate_image":
            await query.answer("جاري رسم وتوليد خريطتك الفلكية هندسياً الحية...")
            try:
                adapted_chart = FlexibleChartAdapter(chart_data)
                img_bytes_data = drawer.generate_chart_png(adapted_chart)
                
                img_buffer = io.BytesIO(img_bytes_data)
                img_buffer.name = "natal_chart.png"
                
                await telegram_app.bot.send_photo(
                    chat_id=user_id,
                    photo=img_buffer,
                    caption="🪐 **عجلة خريطتك الفلكية الحقيقية (Natal Wheel)**\nتم توليد الرسم البياني بناءً على طلبك الآن اعتماداً على درجات أجرامك وأوتادك الحقيقية.",
                    reply_markup=astrology_back_markup
                )
            except Exception as draw_err:
                logger.error(f"Error during manual chart drawing: {draw_err}", exc_info=True)
                await query.message.reply_text("⚠️ تعذر توليد ورسم الصورة حالياً، يرجى مراجعة التقرير النصي.", reply_markup=astrology_back_markup)

    except Exception as exc:
        logger.error(f"Error handling menu click {data}: {exc}", exc_info=True)
        await query.message.reply_text("⚠️ حدث خطأ داخلي أثناء استخلاص البيانات الفلكية.", reply_markup=astrology_back_markup)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("🚫 تم إلغاء العملية الحالية. يمكنك البدء من جديد بإرسال /start")
    return ConversationHandler.END


# =====================================================================
# تسجيل ومعالجة الـ Handlers للـ Conversation والأزرار
# =====================================================================
conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(astrology_trigger_workflow, pattern="^go_astrology$")],
    states={
        YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, p_year)],
        MONTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, p_month)],
        DAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, p_day)],
        KNOWS_TIME: [CallbackQueryHandler(p_knows_time)],
        TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, p_time)],
        LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, p_location)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
    per_message=False
)

telegram_app.add_handler(CommandHandler('start', start))
telegram_app.add_handler(conv_handler)
telegram_app.add_handler(CallbackQueryHandler(handle_menu_clicks))
