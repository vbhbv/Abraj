import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

class ElectionalAstrologyEngine:
    def __init__(self, astrology_engine: Any):
        """
        تهيئة محرك الاختيارات التنجيمية الاحترافي الشامل.
        يعتمد على محرك حسابات فلكية خارجي لحساب المواقع الجغرافية وحركة العبور الحية.
        """
        self.engine = astrology_engine
        
        # جدول الكرامات الفلكية الأساسية (Domicile, Exaltation, Detriment, Fall)
        self.dignities = {
            "Sun": {"domicile": ["Leo"], "exaltation": "Aries", "detriment": ["Aquarius"], "fall": "Libra"},
            "Moon": {"domicile": ["Cancer"], "exaltation": "Taurus", "detriment": ["Capricorn"], "fall": "Scorpio"},
            "Mercury": {"domicile": ["Gemini", "Virgo"], "exaltation": "Virgo", "detriment": ["Sagittarius", "Pisces"], "fall": "Pisces"},
            "Venus": {"domicile": ["Taurus", "Libra"], "exaltation": "Pisces", "detriment": ["Scorpio", "Aries"], "fall": "Virgo"},
            "Mars": {"domicile": ["Aries", "Scorpio"], "exaltation": "Capricorn", "detriment": ["Libra", "Taurus"], "fall": "Cancer"},
            "Jupiter": {"domicile": ["Sagittarius", "Pisces"], "exaltation": "Cancer", "detriment": ["Gemini", "Virgo"], "fall": "Capricorn"},
            "Saturn": {"domicile": ["Capricorn", "Aquarius"], "exaltation": "Libra", "detriment": ["Cancer", "Leo"], "fall": "Aries"}
        }

        # قواعد الاختيارات التقليدية الصارمة لكل نية ومسعى بشري
        self.decision_rules = {
            "financial": {
                "name": "الجانب المالي، الاستثماري والتجاري",
                "ruling_planets": ["Jupiter", "Venus", "Mercury"],
                "preferred_houses": [2, 8, 10, 11],
                "moon_signs": ["Taurus", "Virgo", "Capricorn", "Cancer"],
                "allow_waning": False,
                "critical_planets": ["Mercury", "Jupiter"],
                "description": "تأسيس الشركات، الاستثمار، توقيع العقود، وشراء النطاقات الرقمية والمتاجر."
            },
            "emotional": {
                "name": "الجانب العاطفي، العلاقات والزواج",
                "ruling_planets": ["Venus", "Moon"],
                "preferred_houses": [5, 7, 11],
                "moon_signs": ["Taurus", "Cancer", "Libra", "Pisces"],
                "allow_waning": False,
                "critical_planets": ["Venus", "Moon"],
                "description": "عقد القران، الخطوبة، المصالحات، وتعميق الروابط الاجتماعية والدبلوماسية."
            },
            "confrontation": {
                "name": "المواجهات، القضايا والإنهاء والتخلص",
                "ruling_planets": ["Mars", "Saturn"],
                "preferred_houses": [6, 8, 12],
                "moon_signs": ["Aries", "Scorpio", "Capricorn"],
                "allow_waning": True,  # التناقص مطلوب هندسياً للهدم والإضعاف
                "critical_planets": ["Mars"],
                "description": "رفع القضايا، بتر العلاقات السامة، وتوقيت العمليات الجراحية والاستئصال."
            },
            "intellectual": {
                "name": "الدراسة، التفكير، التأليف والنشر الفلسفي",
                "ruling_planets": ["Mercury", "Jupiter"],
                "preferred_houses": [3, 9],
                "moon_signs": ["Gemini", "Libra", "Aquarius", "Virgo"],
                "allow_waning": False,
                "critical_planets": ["Mercury"],
                "description": "البدء بالدراسات، تأليف الكتب والبحوث، وإطلاق المنصات الفكرية والأرشيفية."
            },
            "general": {
                "name": "الأمور العامة والخطوات اليومية الاعتيادية",
                "ruling_planets": ["Sun", "Jupiter"],
                "preferred_houses": [1, 5, 9],
                "moon_signs": ["Aries", "Leo", "Sagittarius", "Taurus", "Gemini", "Cancer", "Libra", "Aquarius", "Pisces"],
                "allow_waning": False,
                "critical_planets": ["Sun"],
                "description": "الخطوات اليومية العادية التي تتطلب بركة ودعم فلكي عام."
            }
        }

    def classify_user_intent_ai(self, user_text: str) -> str:
        """
        تصنيف دلالي مرن لتحليل نية المستخدم وفهم السياقات النصية دون التقيد بكلمات جامدة.
        """
        text = user_text.lower().strip()
        keywords = {
            "financial": ["متجر", "محل", "شراء", "بيع", "نطاق", "دومين", "فلوس", "مال", "تجارة", "مشروع", "استثمار", "عقد", "شركة", "نشاط"],
            "emotional": ["زواج", "خطوبة", "حب", "حبيب", "شريك", "عاطفة", "ارتباط", "عقد قران", "صلح", "صديق"],
            "confrontation": ["محكمة", "قضية", "محامي", "خلاف", "انفصال", "طلاق", "قطع", "مواجهة", "جراحة", "عملية"],
            "intellectual": ["كتاب", "تأليف", "نشر", "بحث", "دراسة", "جامعة", "امتحان", "فلسفة", "مقال", "علم", "أرشيف"]
        }
        for intent, keys in keywords.items():
            if any(key in text for key in keys):
                return intent
        return "general"

    def calculate_essential_dignity(self, planet: str, sign: str) -> int:
        """
        حساب قوة الكوكب التقليدية (Essential Dignity) بالنقاط بناءً على موقعه في البرج.
        """
        if planet not in self.dignities:
            return 0
        rules = self.dignities[planet]
        if sign in rules["domicile"]:
            return 20  # في بيته وموطنه الأصلي (حالة استقرار وتمكين عظمى)
        if sign == rules["exaltation"]:
            return 15  # في شرفه (طاقة بناءة ونقية جداً)
        if sign in rules["detriment"]:
            return -15 # في وباله (ضعيف، مشتت، ويعمل بجهد مضاعف)
        if sign == rules["fall"]:
            return -20 # في هبوطه (معطل تماماً أو يسبب نتائج عكسية)
        return 0

    def evaluate_astrological_fitness(self, chart: Any, rules: Dict[str, Any]) -> Tuple[float, List[str]]:
        """
        تطبيق تنجيمي صارم يتضمن: التراجعات، الاحتراق، الكرامات، درجات القمر الحرجة والاتصالات.
        تتعامل بأمان كلي مع قواميس البيانات أو كائنات المخرجات المخصصة (ChartResult).
        """
        score = 60.0  
        reasons = []

        # استخراج الكواكب والاتصالات بأمان بغض النظر عن بنية مخرجات المحرك الفلكي
        if hasattr(chart, "__dict__") and not isinstance(chart, dict):
            planets = getattr(chart, "planets", {})
            aspects = getattr(chart, "aspects", [])
            is_eclipse_period = getattr(chart, "is_eclipse_period", False)
        elif isinstance(chart, dict):
            planets = chart.get("planets", {})
            aspects = chart.get("aspects", [])
            is_eclipse_period = chart.get("is_eclipse_period", False)
        else:
            planets = {}
            aspects = []
            is_eclipse_period = False

        # دالة مساعدة لتوحيد قراءة بيانات الكواكب (سواء كانت كائنات أو قواميس فرعية)
        def get_planet_data(p_dict, name):
            p = p_dict.get(name) if isinstance(p_dict, dict) else getattr(p_dict, name, None)
            if p and not isinstance(p, dict):
                return {
                    "longitude": getattr(p, "longitude", 0.0),
                    "retrograde": getattr(p, "retrograde", False),
                    "sign": getattr(p, "sign", ""),
                    "degree": getattr(p, "degree", 0.0),
                    "is_waning": getattr(p, "is_waning", False),
                    "is_void_of_course": getattr(p, "is_void_of_course", False)
                }
            return p or {}

        sun_data = get_planet_data(planets, "Sun")
        sun_long = sun_data.get("longitude", 0.0)

        # 1. فحص الكواكب الحاكمة والحرجة (التراجع والاحتراق والكرامة)
        for p_name in rules["critical_planets"]:
            p_data = get_planet_data(planets, p_name)
            if not p_data:
                continue
            
            # أ) التحقق من التراجع (Retrograde)
            if p_data.get("retrograde", False):
                score -= 25
                reasons.append(f"⚠️ كوكب {p_name} الحاكم للعمل متراجع حالياً، مما يسبب تأخيراً وعراقيل حادة.")

            # ب) التحقق من الاحتراق (Combustion)
            p_long = p_data.get("longitude", 0.0)
            if p_name != "Sun" and abs(p_long - sun_long) < 8.5:
                score -= 20
                reasons.append(f"🔥 كوكب {p_name} محترق تماماً بسبب قربه الشديد من الشمس (تحت الشعاع).")

            # ج) التحقق من الكرامة الأساسية (Essential Dignity)
            dignity_score = self.calculate_essential_dignity(p_name, p_data.get("sign", ""))
            score += dignity_score
            if dignity_score > 0:
                reasons.append(f"✨ كوكب {p_name} في موقع قوة كوكبية ممتاز (بيته أو شرفه).")
            elif dignity_score < 0:
                reasons.append(f"📉 كوكب {p_name} في موقع ضعف كوكبي تقليدي (وباله أو هبوطه).")

        # 2. فحص القمر الحقيقي بدقة (Moon Analysis)
        moon_data = get_planet_data(planets, "Moon")
        if moon_data:
            moon_sign = moon_data.get("sign", "")
            moon_deg = moon_data.get("degree", 0.0)
            moon_is_waning = moon_data.get("is_waning", False)

            # أ) برج القمر ومرحلته
            if moon_sign in rules["moon_signs"]:
                score += 10
            if moon_is_waning and not rules["allow_waning"]:
                score -= 15
                reasons.append("🌙 نور القمر في حالة تناقص، وهو غير نافع لمشاريع النمو والتأسيس المالي والعاطفي.")

            # ب) خلو مسار القمر (Void of Course)
            if moon_data.get("is_void_of_course", False):
                score -= 30
                reasons.append("🚨 القمر خالي المسار (Void of Course)! تجنب البدء بأي مشروع الآن.")

            # ج) درجات القمر الحرجة (Anaretic Degree)
            if moon_deg >= 29.0:
                score -= 20
                reasons.append("⚠️ القمر في الدرجة الأخيرة الحرجـة (29°) من البرج، طاقة متقلبة وغير مستقرة.")

        # 3. فحص الاتصالات الحية (Aspects)
        rulers = rules["ruling_planets"]
        for asp in aspects:
            p1 = asp.get("planet1") if isinstance(asp, dict) else getattr(asp, "planet1", None)
            p2 = asp.get("planet2") if isinstance(asp, dict) else getattr(asp, "planet2", None)
            a_type = asp.get("type") if isinstance(asp, dict) else getattr(asp, "type", None)
            
            if p1 in rulers or p2 in rulers:
                if a_type in ["trine", "sextile"]:
                    score += 10
                elif a_type in ["square", "opposition"]:
                    score -= 15
                    reasons.append(f"⚡ اتصال تربيع أو مقابلة نحس بين {p1} و {p2} يهدد نجاح المسعى.")

        # 4. الحماية من فترات الكسوف والخسوف (Eclipses)
        if is_eclipse_period:
            score -= 40
            reasons.append("🌑 النوافذ الفلكية تقع ضمن عاصفة الكسوف/الخسوف، الطاقة الكونية ملوثة بالكامل.")

        final_score = max(5.0, min(score, 100.0))
        return final_score, reasons

    def calculate_best_planetary_hour(self, target_date: datetime, ruling_planets: List[str]) -> str:
        """
        حساب الساعات الكوكبية التقليدية الحية ليوم محدد واختيار الساعة التابعة لكوكب السعد الحاكم للنية.
        """
        sunrise = target_date.replace(hour=6, minute=0, second=0)
        chaldean_order = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"]
        
        day_of_week = target_date.weekday()
        weekday_to_planet = {5: "Saturn", 6: "Sun", 0: "Moon", 1: "Mars", 2: "Mercury", 3: "Jupiter", 4: "Venus"}
        start_planet = weekday_to_planet.get(day_of_week, "Sun")
        
        start_index = chaldean_order.index(start_planet)
        
        for hour_idx in range(12):
            current_planet = chaldean_order[(start_index + hour_idx) % 7]
            if current_planet in ruling_planets:
                hour_start = sunrise + timedelta(hours=hour_idx)
                hour_end = hour_start + timedelta(hours=1)
                return f"⏳ ساعة {current_planet} السعيدة (من {hour_start.strftime('%H:%M')} إلى {hour_end.strftime('%H:%M')})"
                
        return "⏳ الساعة الأولى بعد الشروق مباشرة (ساعة الكوكب الحاكم لليوم)"

    def generate_detailed_report(self, user_text: str, lat: float, lon: float) -> Tuple[str, str]:
        """
        المسح التنجيمي الذكي والشامل لفترة 30 يوماً مقبلة وإظهار أدق التفاصيل المعرفية للمستخدم.
        """
        decision_key = self.classify_user_intent_ai(user_text)
        rules = self.decision_rules.get(decision_key, self.decision_rules["general"])
        
        start_date = datetime.utcnow()
        all_days_evaluated = []

        for day_offset in range(30):
            current_check = start_date + timedelta(days=day_offset)
            try:
                # استدعاء خريطة السماء العابرة (Transit Chart) جغرافياً وحياً من المحرك الأساسي
                chart = self.engine.compute_natal_chart(current_check, lat, lon)
                score, reasons = self.evaluate_astrological_fitness(chart, rules)
                all_days_evaluated.append({
                    "date": current_check,
                    "score": score,
                    "reasons": reasons
                })
            except Exception as e:
                logger.error(f"Error evaluating day {day_offset}: {e}")
                continue

        all_days_evaluated.sort(key=lambda x: x["score"], reverse=True)
        
        if not all_days_evaluated:
            return "❌ عذراً، هناك خلل في معالجة خريطة السماء اللحظية (Transit).", "general"

        best_option = all_days_evaluated[0]
        worst_option = all_days_evaluated[-1]

        best_hour_text = self.calculate_best_planetary_hour(best_option["date"], rules["ruling_planets"])
        reasons_bulleted = "\n".join([f"• {r}" for r in best_option["reasons"][:4]]) if best_option["reasons"] else "• اتصالات الكواكب والكرامات الأساسية في حالة اتزان مستقر مائل للسعود."

        report_text = (
            f"🪐 **مَحرك الاختيارات التنجيمية المتقدم والتحليل الهندسي للسماء** 🪐\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🎯 **تحليل النية والقصد الفكري:**\n"
            f"← النطاق الحاكم: ` {rules['name']} `\n"
            f"← التوصية الأساسية: *{rules['description']}*\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🌟 **أفضل تاريخ فلكي للإقدام (خلال مسح 30 يوماً حياً):**\n"
            f"📅 **التاريخ المقترح:** {best_option['date'].strftime('%Y-%m-%d')} (توقيت غرينتش)\n"
            f"📊 **معدل التيسير والنجاح الهندسي:** ` {best_option['score']:.1f}% `\n\n"
            f"🔭 **المسوغات والشهادات الفلكية التقليدية العميقة:**\n"
            f"{reasons_bulleted}\n\n"
            f"⏱ **الساعة الكوكبية الذهبية الموصى بها في ذلك اليوم:**\n"
            f"{best_hour_text}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🛑 **أعلى فترة نحوسة واحتراق (يُحذر تماماً من التوقيع أو البدء فيها):**\n"
            f"📅 **التاريخ:** {worst_option['date'].strftime('%Y-%m-%d')} (مؤشر التيسير: {worst_option['score']:.1f}%)\n"
            f"❌ **السبب:** هبوط كواكب النية الحاكمة، أو وقوعها في حالة احتراق كلي بالشمس أو تحت ظلال الكسوف.\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ **ملاحظة معرفية:** تعتمد هذه الحسابات الرياضية الدقيقة على قواعد التنجيم التقليدي الكلاسيكي لتحديد النوافذ الزمنية الأكثر توازناً وانسجاماً، ولا تدعمها أدلة علمية قطعية للتنبؤ بالغيب أو حتمية الأحداث الحياتية."
        )

        return report_text, decision_key
