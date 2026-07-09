import math
import io
from typing import Dict, Any, List
# استيراد مكتبة Pillow القياسية للرسم المباشر بصيغة بايتات
from PIL import Image, ImageDraw, ImageFont

class AstrologyChartDrawer:
    def __init__(self, size: int = 900):
        self.size = size
        self.cx = size / 2
        self.cy = size / 2
        
        # نظام الحلقات الأربع الاحترافي الشامل (Radii Rings)
        self.r_outer = 420       # إطار المتحدث الخارجي
        self.r_zodiac_out = 410  # حد حلقة الأبراج الخارجي
        self.r_zodiac_in = 350   # حد حلقة الأبراج الداخلي / حد حلقة الكواكب الخارجي
        self.r_planets_in = 290  # حد حلقة الكواكب الداخلي / حد حلقة البيوت الخارجي
        self.r_houses_in = 250   # حد حلقة البيوت الداخلي / بداية مساحة الاتصالات
        
        self.ZODIAC_UNICODE = {
            "Aries": "♈", "Taurus": "♉", "Gemini": "♊", "Cancer": "♋",
            "Leo": "♌", "Virgo": "♍", "Libra": "♎", "Scorpio": "♏",
            "Sagittarius": "♐", "Capricorn": "♑", "Aquarius": "♒", "Pisces": "♓"
        }
        
        self.PLANET_UNICODE = {
            "Sun": "☉", "Moon": "☽", "Mercury": "☿", "Venus": "♀", 
            "Mars": "♂", "Jupiter": "♃", "Saturn": "♄", "Uranus": "♅", 
            "Neptune": "♆", "Pluto": "♇", "Chiron": "⚷", "NorthNode": "☊",
            "Lilith": "⚸"
        }

        self.ASPECT_COLORS = {
            "Conjunction": (255, 215, 0),    # ذهبي
            "Sextile": (0, 255, 127),        # أخضر
            "Square": (255, 69, 0),          # برتقالي محمر
            "Trine": (30, 144, 255),         # أزرق
            "Opposition": (148, 0, 211)       # بنفسجي
        }

    def _to_radians(self, degrees: float) -> float:
        return math.radians(degrees)

    def _get_coordinates(self, angle_deg: float, radius: float) -> tuple:
        """تحويل من قطبي إلى ديكارتي مع تدوير النظام لتبدأ الدائرة دائماً من الطالع"""
        rad = self._to_radians(180.0 - angle_deg)
        x = self.cx + radius * math.cos(rad)
        y = self.cy + radius * math.sin(rad)
        return round(x, 2), round(y, 2)

    def _format_degree(self, num_deg: float) -> str:
        """تحويل الدرجة العشرية إلى صيغة فلكية كلاسيكية مثل 24°46'"""
        degrees = int(num_deg)
        minutes = int(round((num_deg - degrees) * 60))
        if minutes == 60:
            degrees += 1
            minutes = 0
        return f"{degrees}°{minutes:02d}'"

    def _resolve_collisions(self, planets_angles: List[Dict[str, Any]], min_dist: float = 7.5) -> List[Dict[str, Any]]:
        """خوارزمية ذكية مخصصة لمنع تداخل رموز الكواكب والدرجات تقائياً"""
        sorted_planets = sorted(planets_angles, key=lambda x: x['orig_angle'])
        n = len(sorted_planets)
        if n <= 1:
            return sorted_planets

        for _ in range(5):
            for i in range(n):
                next_idx = (i + 1) % n
                p1 = sorted_planets[i]
                p2 = sorted_planets[next_idx]
                
                diff = (p2['curr_angle'] - p1['curr_angle']) % 360
                if diff > 180:
                    diff = 360 - diff
                
                if diff < min_dist:
                    overlap = min_dist - diff
                    p1['curr_angle'] = (p1['curr_angle'] - overlap / 2) % 360
                    p2['curr_angle'] = (p2['curr_angle'] + overlap / 2) % 360
                    
        return sorted_planets

    def generate_chart_png(self, chart_data: Any) -> bytes:
        """توليد بايتات صورة PNG حقيقية مباشرة متوافقة كلياً مع ملف main.py والأندرويد"""
        # 1. إنشاء خلفية الصورة الداكنة اللطيفة الفلكية الموازية لكود الـ SVG الأصلي
        image = Image.new("RGBA", (self.size, self.size), (13, 17, 23, 255))
        draw = ImageDraw.Draw(image)
        
        # محاولة تحميل خط يدعم الرموز الفلكية (Unicode) بشكل افتراضي، وإلا يعتمد على النظام
        try:
            font_zodiac = ImageFont.load_default(size=28)
            font_planet = ImageFont.load_default(size=22)
            font_text = ImageFont.load_default(size=12)
        except Exception:
            font_zodiac = font_planet = font_text = ImageFont.load_default()

        asc_deg = getattr(chart_data, 'ascendant_degree', 0.0)
        
        # 2. رسم الحلقات الأربع المركزية الفلكية الشاملة
        draw.ellipse([self.cx - self.r_outer, self.cy - self.r_outer, self.cx + self.r_outer, self.cy + self.r_outer], stroke=(33, 38, 45, 255), width=1)
        draw.ellipse([self.cx - self.r_zodiac_out, self.cy - self.r_zodiac_out, self.cx + self.r_zodiac_out, self.cy + self.r_zodiac_out], stroke=(48, 54, 61, 255), width=2)
        draw.ellipse([self.cx - self.r_zodiac_in, self.cy - self.r_zodiac_in, self.cx + self.r_zodiac_in, self.cy + self.r_zodiac_in], fill=(22, 27, 34, 255), stroke=(48, 54, 61, 255), width=2)
        draw.ellipse([self.cx - self.r_planets_in, self.cy - self.r_planets_in, self.cx + self.r_planets_in, self.cy + self.r_planets_in], stroke=(48, 54, 61, 255), width=1)
        draw.ellipse([self.cx - self.r_houses_in, self.cy - self.r_houses_in, self.cx + self.r_houses_in, self.cy + self.r_houses_in], fill=(13, 17, 23, 255), stroke=(33, 38, 45, 255), width=2)

        # 3. رسم قطاعات الأبراج الـ 12 المتساوية والرموز التعبيرية للأبراج
        for i in range(12):
            sign_start_deg = i * 30.0
            rel_angle = sign_start_deg - asc_deg
            x1, y1 = self._get_coordinates(rel_angle, self.r_zodiac_in)
            x2, y2 = self._get_coordinates(rel_angle, self.r_zodiac_out)
            draw.line([(x1, y1), (x2, y2)], fill=(48, 54, 61, 255), width=2)
            
            mid_angle = rel_angle + 15.0
            signs_keys = list(self.ZODIAC_UNICODE.keys())
            sym = self.ZODIAC_UNICODE[signs_keys[i]]
            sx, sy = self._get_coordinates(mid_angle, (self.r_zodiac_out + self.r_zodiac_in) / 2)
            draw.text((sx, sy), sym, fill=(201, 209, 217, 255), font=font_zodiac, anchor="mm")

        # 4. رسم خطوط البيوت الـ 12 وتسمية الأوتاد الأساسية للأبراج
        if hasattr(chart_data, 'houses') and chart_data.houses:
            axis_labels = {1: "ASC", 10: "MC", 7: "DSC", 4: "IC"}
            for h_num, h_deg in chart_data.houses.items():
                rel_angle = h_deg - asc_deg
                x1, y1 = self._get_coordinates(rel_angle, self.r_houses_in)
                x2, y2 = self._get_coordinates(rel_angle, self.r_zodiac_in)
                
                is_axis = h_num in [1, 4, 7, 10]
                stroke_w = 4 if is_axis else 1
                stroke_c = (255, 123, 114, 255) if is_axis else (48, 54, 61, 255)
                draw.line([(x1, y1), (x2, y2)], fill=stroke_c, width=stroke_w)
                
                if is_axis:
                    tx, ty = self._get_coordinates(rel_angle + 3, self.r_houses_in - 20)
                    draw.text((tx, ty), axis_labels[h_num], fill=(255, 123, 114, 255), font=font_text, anchor="mm")
                else:
                    hx, hy = self._get_coordinates(rel_angle + 15, self.r_houses_in + 20)
                    draw.text((hx, hy), str(h_num), fill=(88, 166, 255, 255), font=font_text, anchor="mm")

        # 5. رسم خطوط الاتصالات الداخلية الكلاسيكية الفلكية العميقة
        if hasattr(chart_data, 'aspects') and chart_data.aspects:
            for aspect in chart_data.aspects:
                if aspect.p1 in chart_data.planets and aspect.p2 in chart_data.planets:
                    p1_deg = chart_data.planets[aspect.p1].longitude
                    p2_deg = chart_data.planets[aspect.p2].longitude
                    
                    a1 = p1_deg - asc_deg
                    a2 = p2_deg - asc_deg
                    
                    x1, y1 = self._get_coordinates(a1, self.r_houses_in)
                    x2, y2 = self._get_coordinates(a2, self.r_houses_in)
                    
                    orb = getattr(aspect, 'orb', 0.0)
                    opacity = int(max(0.2, round(1.0 - (orb / 8.0), 2)) * 255)
                    
                    base_rgb = self.ASPECT_COLORS.get(aspect.type, (139, 148, 158))
                    color_rgba = (base_rgb[0], base_rgb[1], base_rgb[2], opacity)
                    
                    draw.line([(x1, y1), (x2, y2)], fill=color_rgba, width=2)

        # 6. توزيع وفك اشتباك تكتل درجات الكواكب الفلكية لمنع التداخل
        raw_planets_data = []
        for p_name, p_data in chart_data.planets.items():
            if p_name in self.PLANET_UNICODE:
                p_abs_deg = p_data.longitude
                raw_planets_data.append({
                    'name': p_name,
                    'orig_angle': p_abs_deg - asc_deg,
                    'curr_angle': p_abs_deg - asc_deg,
                    'display_deg': p_data.longitude % 30
                })

        resolved_planets = self._resolve_collisions(raw_planets_data, min_dist=7.5)

        # 7. رسم الأجرام والدرجات الفلكية بصرياً بدقة البكسل المتناسقة
        for p in resolved_planets:
            sym = self.PLANET_UNICODE[p['name']]
            
            dot_x, dot_y = self._get_coordinates(p['orig_angle'], self.r_houses_in + 4)
            draw.ellipse([dot_x - 3, dot_y - 3, dot_x + 3, dot_y + 3], fill=(88, 166, 255, 255))
            
            px, py = self._get_coordinates(p['curr_angle'], (self.r_zodiac_in + self.r_planets_in) / 2)
            draw.text((px, py), sym, fill=(255, 255, 255, 255), font=font_planet, anchor="mm")
