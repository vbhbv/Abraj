import random
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message

# ==========================================
# 1. قاعدة بيانات الخيرة (مرتبة وموسعة ومصحوبة بالدعاء والنجوم)
# ==========================================
KHIRA_DATA = {
    "good": [
        {
            "id": 1,
            "stars": "⭐⭐⭐⭐⭐ (ممتازة جداً)",
            "verse": "«وَمَا تَفْعَلُوا مِنْ خَيْرٍ فَإِنَّ اللَّهَ بِهِ عَلِيمٌ»",
            "interpretation": "الأمر الذي تنوي القيام به مبارك وفيه خير كثير لك ولآخرتك. توكل على الله واشرع في مسعاك دون تردد أو خوف.",
            "dua": "اللهم يسّر لي أمري، وسهّل لي دربي، وأنزل عليّ من بركاتك وجد بفضلك عليّ."
        },
        {
            "id": 2,
            "stars": "⭐⭐⭐⭐ (مباركة وصالحة)",
            "verse": "«إِنْ يَعْلَمِ اللَّهُ فِي قُلُوبِكُمْ خَيْرًا يُؤْتِكُمْ خَيْرًا»",
            "interpretation": "نيتك طيبة ومسعاك محفوف بالتوفيق والبركة والقبول. استعن بالكتمان والعمل الصالح وستجد تيسيراً قريباً.",
            "dua": "اللهم اجعل في قلبي نوراً، وفي عملي بركة، وأعطني من فضلك العظيم ما تقرّ به عيني."
        }
    ],
    "medium": [
        {
            "id": 3,
            "stars": "⭐⭐⭐ (وسط - تحتاج صبراً)",
            "verse": "«وَعَسَىٰ أَن تَكْرَهُوا شَيْئًا وَهُوَ خَيْرٌ لَّكُمْ ۖ وَعَسَىٰ أَن تُحِبُّوا شَيْئًا وَهُوَ شَرٌّ لَّكُمْ»",
            "interpretation": "الأمر يحتاج إلى صبر ومواجهة بعض العقبات أو التأخير في البداية. لا تستعجل النتائج والتزم بالتأني والتدبر قبل الإقدام.",
            "dua": "اللهم رضّني بقضائك، وصبرني على بلائك، واجعل عاقبة أمري خيراً وتيسيراً."
        }
    ],
    "bad": [
        {
            "id": 4,
            "stars": "⭐ (نهي - غير صالحة)",
            "verse": "«وَيَدْعُ الْإِنسَانُ بِالشَّرِّ دُعَاءَهُ بِالْخَيْرِ ۖ وَكَانَ الْإِنسَانُ عَجُولًا»",
            "interpretation": "الظاهر قد يبدو لك حسناً ومغرياً، لكن العاقبة تنطوي على تعب أو خسارة غير متوقعة. ننصحك بالتأجيل أو صرف النظر عنها تماماً.",
            "dua": "اللهم خِر لي واختر لي، واصرف عني السوء والندامة حيث كان، ثم أرضني بقضائك."
        }
    ]
}

# ==========================================
# 2. نظام منع التكرار (Cooldown) في الذاكرة
# ==========================================
cooldowns = {}
COOLDOWN_DURATION = 3600  # المدة بالثواني (3600 ثانية = ساعة كاملة)

# دالة توليد لوحة التحكم الرئيسية
def get_khira_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔮 طلب خيرة جديدة", callback_data="request_khira")],
        [InlineKeyboardButton("📜 شروط الخيرة وآدابها", callback_data="khira_rules")]
    ])

# ==========================================
# 3. معالجات الأوامر والرسائل (Handlers)
# ==========================================

@Client.on_message(filters.command("khira") & filters.private)
async def start_khira(client: Client, message: Message):
    welcome_text = (
        "✨ **مرحباً بك في خدمة الخيرة والاستخارة الرقمية** ✨\n\n"
        "«فَإِذَا عَزَمْتَ فَتَوَكَّلْ عَلَى اللَّهِ ۚ إِنَّ اللَّهَ يُحِبُّ الْمُتَوَكِّلِينَ»\n\n"
        "يرجى استحضار النية، وقراءة سورة الفاتحة متبوعة بالصلاة على محمد وآل محمد، ثم اضغط على الزر أدناه لبدء الخيرة.\n\n"
        "⚠️ **تنويه إخلاء مسؤولية:**\n"
        "هذه الخدمة برمجية استرشادية رقمية مبنية على التفاؤل بالقرآن الكريم، وليست بديلاً عن الاستخارة الشرعية الفقهية ولا تقدم حكماً دينياً ملزماً. القرار النهائي يعود لك بعد التدبر والاستشارة."
    )
    await message.reply_text(welcome_text, reply_markup=get_khira_keyboard())


@Client.on_callback_query()
async def handle_khira_callbacks(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    if data == "request_khira":
        current_time = time.time()
        
        # تفعيل فحص منع تكرار الخيرة
        if user_id in cooldowns:
            time_passed = current_time - cooldowns[user_id]
            if time_passed < COOLDOWN_DURATION:
                remaining_time = int((COOLDOWN_DURATION - time_passed) // 60)
                await callback_query.answer(
                    f"⚠️ لا يمكن تكرار الخيرة في نفس الأمر هكذا!\nانتظر {remaining_time} دقيقة أو تدبر في نتيجتك الحالية أولاً.",
                    show_alert=True
                )
                return

        # نظام الأوزان لضمان عدالة العشوائية (جيد: 50%، وسط: 30%، نهي: 20%)
        categories = ["good", "medium", "bad"]
        weights = [0.50, 0.30, 0.20] 
        
        chosen_category = random.choices(categories, weights=weights, k=1)[0]
        options_list = KHIRA_DATA.get(chosen_category, [])
        
        if not options_list:
            await callback_query.answer("عذراً، حدث خطأ غير متوقع في معالجة البيانات.", show_alert=True)
            return
            
        chosen = random.choice(options_list)
        
        # تسجيل الوقت الحالي للمستخدم لمنع التلاعب
        cooldowns[user_id] = current_time
        
        # تنسيق واجهة المستخدم الاحترافية والمنظمة (Scannable)
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
        
        back_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("↩️ العودة للقائمة الرئيسية", callback_data="back_to_main")]
        ])
        
        await callback_query.message.edit_text(result_text, reply_markup=back_keyboard)
        
    elif data == "khira_rules":
        rules_text = (
            "📜 **آداب وشروط عمل الخيرة:**\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "1️⃣ **النية الصادقة:** أن تكون حائراً فعلاً بين أمرين ولم تصل لقرار حاسم بعد الاستشارة والتدبر.\n"
            "2️⃣ **عدم التكرار:** لا تُكرر الخيرة في نفس الأمر إطلاقاً ما لم تتغير المعطيات أو ظروف القضية جذرياً.\n"
            "3️⃣ **الرضا بالنتيجة:** تسليم الأمر لله تعالى والعمل بموجب التوجيه الصاعد بقلب مطمئن.\n"
            "4️⃣ **الطهارة والتوجه:** يُفضل استحضار النية والوضوء متوجهاً للقبلة المشرفة أثناء طلب الخيرة."
        )
        back_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("↩️ العودة", callback_data="back_to_main")]])
        await callback_query.message.edit_text(rules_text, reply_markup=back_keyboard)
        
    elif data == "back_to_main":
        welcome_text = (
            "✨ **خدمة الخيرة والاستخارة الرقمية** ✨\n\n"
            "يرجى استحضار النية والضغط على الزر أدناه لبدء الخيرة.\n\n"
            "⚠️ *تنويه: الخدمة رقمية استرشادية للتفاؤل فقط ولا تحمل طابعاً إلزامياً دينيّاً.*"
        )
        await callback_query.message.edit_text(welcome_text, reply_markup=get_khira_keyboard())
