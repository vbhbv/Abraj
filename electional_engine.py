import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

class ElectionalAstrologyEngine:
    def __init__(self, astrology_engine: Any):
        """
        تهيئة محرك الاختيارات الفلكية الحقيقي القائم على الحسابات الفلكية الحية.
        """
        self.engine = astrology_engine
        
        # القواعد الحاكمة للتنجيم الاختياري الحقيقي
        self.decision_rules = {
            "financial": {
                "name": "الجانب المالي، الاستثماري والتجاري",
                "ruling_planets": ["Jupiter", "Venus", "Mercury"],
                "preferred_houses": [2, 8, 10, 11],
                "moon_signs": ["Taurus", "Virgo", "Capricorn", "Cancer"],
                "allow_waning": False,
                "description": "تأسيس الشركات، الاستثمار، توقيع العقود التجارية، وشراء النطاقات الرقمية."
            },
            "emotional": {
                "name": "الجانب العاطفي، العلاقات والزواج",
                "ruling_planets": ["Venus", "Moon"],
                "preferred_houses": [5, 7, 11],
                "moon_signs": ["Taurus", "Cancer", "Libra", "Pisces"],
                "allow_waning": False,
                "description": "عقد القران، الخطوبة، المصالحات، وتعميق الروابط الدبلوماسية والاجتماعية."
            },
            "confrontation": {
                "name": "المواجهات، القضايا والإنهاء والتخلص",
                "ruling_planets": ["Mars", "Saturn"],
                "preferred_houses": [6, 8, 12],
                "moon_signs": ["Aries", "Scorpio", "Capricorn"],
                "allow_waning": True,  # التناقص مطلوب للتخلص من القضايا والخصوم والأورام
                "description": "رفع القضايا القانونية، بتر العلاقات السامة، وتوقيت العمليات الجراحية والاستئصال."
            },
            "intellectual": {
                "name": "الدراسة، التفكير، التأليف والنشر الفلسفي",
                "ruling_planets": ["Mercury", "Jupiter"],
                "preferred_houses": [3, 9],
                "moon_signs": ["Gemini", "Libra", "Aquarius", "Virgo"],
                "allow_waning": False,
                "description": "البدء بالدراسات العليا، تأليف الكتب والبحوث، وإطلاق المنصات الفكرية والأرشيفية."
            },
            "general": {
                "name": "الأمور العامة والخطوات اليومية اعتيادية",
                "ruling_planets": ["Sun", "Jupiter"],
                "preferred_houses": [1, 5, 9],
                "moon_signs": ["Aries", "Leo", "Sagittarius", "Taurus", "Gemini", "Cancer", "Libra", "Aquarius", "Pisces"],
                "allow_waning": False,
                "description": "الخطوات اليومية العادية التي تتطلب بركة ودعم فلكي عام."
            }
        }

    def classify_user_intent_ai(self, user_text: str) -> str:
        """
        مُصنف دلالي مستند إلى الكلمات المفتاحية والسياق الفكري لتحليل نية السائل.
        """
        text = user_text.lower().strip()
        keywords = {
            "financial": ["متجر", "محل", "شراء", "بيع", "نطاق", "دومين", "فلوس", "مال", "تجارة", "مشروع", "استثمار", "عقد", "شركة"],
            "emotional": ["زواج", "خطوبة", "حب", "حبيب", "شريك", "عاطفة", "ارتباط", "عقد قران", "صلح", "صديق"],
            "confrontation": ["محكمة", "قضية", "محامي", "خلاف", "انفصال", "طلاق", "قطع", "مواجهة", "جراحة", "عملية"],
            "intellectual": ["كتاب", "تأليف", "نشر", "بحث", "دراسة", "جامعة", "امتحان", "فلسفة", "مقال", "علم", "أرشيف"]
        }
        for intent, keys in keywords.items():
            if any(key in text for key in keys):
                return intent
        return "general"

    def evaluate_astrological_fitness(self, chart: Dict[str, Any], rules: Dict[str, Any]) -> Tuple[float, List[str]]:
        """
        قلب التنجيم الفعلي: تقييم حي للخريطة العابرة بناءً على حسابات الاتصالات،
        مواقع الكواكب في البيوت، وحالة القمر الفلكية الحقيقية (خلو المسار والبرج).
        """
        score = 50.0  # نقطة البداية المحايدة
        reasons = []

        planets = chart.get("planets", {})
        aspects = chart.get("aspects", [])
        
        # 1. فحص القمر (أهم جرم في الاختيارات الفلكية)
        moon_data = planets.get("Moon", {})
        moon_sign = moon_data.get("sign")
        moon_is_waning = moon_data.get("is_waning", False) # هل القمر يتناقص (من البدر للمحاق)؟

        # مطابقة برج القمر مع طبيعة الحدث
        if moon_sign in rules["moon_signs"]:
            score += 15
            reasons.append(f"🌙 القمر في برج صديق وملائم للعمل ({moon_sign}).")
        else:
            score -= 10

        # مطابقة زيادة ونقصان طاقة نور القمر مع النية
        if moon_is_waning and not rules["allow_waning"]:
            score -= 15
            reasons.append("⚠️ القمر في طور التناقص (الهدم/الإنهاء)، غير مثالي لمشاريع الزيادة والنمو.")
        elif not moon_is_waning and not rules["allow_waning"]:
            score += 10
            reasons.append("📈 القمر في طور التزايد (النور ينمو)، ممتاز للتأسيس والوفرة المادية والمعنوية.")

        # فحص خلو مسار القمر الفلكي الحقيقي (Void of Course)
        # إذا كان القمر لا يصنع أي اتصالات رئيسية مقبلة قبل خروجه من البرج
        is_voc = moon_data.get("is_void_of_course", False)
        if is_voc:
            score -= 25
            reasons.append("🚨 تحذير تنجيمي: القمر خالي المسار! الأعمال التي تبدأ الآن لن تثمر أو ستتعطل تماماً.")

        # 2. فحص الاتصالات الحية (Aspects) للكواكب الحاكمة للحدث
        rulers = rules["ruling_planets"]
        for aspect in aspects:
            p1 = aspect.get("planet1")
            p2 = aspect.get("planet2")
            aspect_type = aspect.get("type") # 'trine', 'sextile', 'square', 'opposition', 'conjunction'
            
            # اتصالات سعيدة وميسرة مع الكواكب الحاكمة للنية
            if p1 in rulers or p2 in rulers:
                if aspect_type in ["trine", "sextile"]:
                    score += 12
                    reasons.append(f"✨ اتصال تثليث/تسديس سعيد وميسر بين {p1} و {p2} يدعم خطوتك.")
                elif aspect_type in ["square", "opposition"]:
                    score -= 15
                    reasons.append(f"⚡ اتصال تربيع/مقابلة نحس ومشدود بين {p1} و {p2} يشير إلى عراقيل حادة.")
                    
        # 3. فحص بيوت الكواكب السعيدة (تحديداً المشتري والزهرة)
        jupiter_house = planets.get("Jupiter", {}).get("house", 1)
        if jupiter_house in rules["preferred_houses"]:
            score += 8
            reasons.append(f"🪐 كوكب المشتري (السعد الأكبر) يحل في بيت قوي وداعم للخطوة (البيت {jupiter_house}).")

        # ضبط الحدود الرياضية للمؤشر
        final_score = max(5.0, min(score, 100.0))
        return final_score, reasons

    def generate_detailed_report(self, user_text: str, lat: float, lon: float) -> Tuple[str, str]:
        """
        الذكاء الاختياري الفعلي: فحص نافذة من 30 يوماً مقبلة، واستخراج أفضل أيام
        فلكية مدعومة هندسياً واتصالياً، وتوليد تقرير تنجيمي يليق بعقل باحث.
        """
        decision_key = self.classify_user_intent_ai(user_text)
        rules = self.decision_rules.get(decision_key, self.decision_rules["general"])
        
        start_date = datetime.utcnow()
        all_days_evaluated = []

        # مسح شامل لـ 30 يوماً قادمة بدلاً من 5 أيام عشوائية متكررة
        for day_offset in range(30):
            current_check = start_date + timedelta(days=day_offset)
            try:
                # استدعاء المحرك الحسابي الحقيقي لحساب مواقع الكواكب والزوايا في موقع المستخدم
                chart = self.engine.compute_natal_chart(current_check, lat, lon)
                score, reasons = self.evaluate_astrological_fitness(chart, rules)
                all_days_evaluated.append({
                    "date": current_check,
                    "score": score,
                    "reasons": reasons,
                    "chart": chart
                })
            except Exception as e:
                logger.error(f"Error computing raw chart on day {day_offset}: {e}")
                continue

        # فرز الأيام حسب الأعلى جودة وتوفيقاً فلكياً هندسياً
        all_days_evaluated.sort(key=lambda x: x["score"], reverse=True)
        
        if not all_days_evaluated:
            return "❌ عذراً، تعذر الاتصال بمحرك الحسابات الفلكية لتوليد التقرير حالياً.", "general"

        best_option = all_days_evaluated[0]
        second_best = all_days_evaluated[1] if len(all_days_evaluated) > 1 else None
        worst_option = all_days_evaluated[-1]

        # صياغة أسباب القبول الفلكي الفعلي
        reasons_bulleted = "\n".join(best_option["reasons"][:4]) if best_option["reasons"] else "• طاقات الكواكب والبيوت متزنة ومحايدة تماماً."

        # صياغة التقرير المعرفي الرصين للسائل
        report_text = (
            f"🪐 **مَحرك الاختيارات الفلكية الهندسي والتحليل الدلالي** 🪐\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🎯 **تحليل النية والقصد:**\n"
            f"← التصنيف الفلكي: ` {rules['name']} `\n"
            f"← نطاق التأثير المحلل: *{rules['description']}*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🌟 **أفضل توقيت تنجيمي حقيقي للإقدام وتوقيع البدء (خلال 30 يوماً):**\n"
            f"📅 **التاريخ المقترح:** {best_option['date'].strftime('%Y-%m-%d')} (توقيت غرينتش)\n"
            f"📊 **معدل التيسير الهندسي:** ` {best_option['score']:.1f}% `\n\n"
            f"🔭 **المسوغات والشهادات الفلكية الحية لهذا اليوم:**\n"
            f"{reasons_bulleted}\n\n"
        )

        if second_best and second_best["score"] > 60:
            report_text += (
                f"🥈 **الخيار البديل المتاح:**\n"
                f"📅 **التاريخ:** {second_best['date'].strftime('%Y-%m-%d')} (معدل تيسير: {second_best['score']:.1f}%)\n\n"
            )

        report_text += (
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🛑 **فترة النحوسة الكونية الكبرى (يُحذر من البدء فيها):**\n"
            f"📅 **التاريخ:** {worst_option['date'].strftime('%Y-%m-%d')}\n"
            f"📉 **معدل التيسير الهابط:** ` {worst_option['score']:.1f}% `\n"
            f"❌ **السبب الرئيسي:** تضارب حاد في اتصالات الكواكب الحاكمة أو رصد حالة خلو مسار تامة للقمر.\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏛 *تم حساب الزوايا والاتصالات الكوكبية بدقة هندسية بناءً على إحداثيات موقعك الجغرافي الحي لحصد أفضل طالع فلكي للبدء.*"
        )

        return report_text, decision_key
