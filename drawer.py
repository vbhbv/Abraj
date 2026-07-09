import math
import io
from typing import Dict, Any, List
from PIL import Image, ImageDraw, ImageFont

class AstrologyChartDrawer:
    def __init__(self, size: int = 900):
        self.size = size
        self.cx = size / 2
        self.cy = size / 2
        
        # نظام الحلقات الشامل
        self.r_outer = 420       
        self.r_zodiac_out = 410  
        self.r_zodiac_in = 350   
        self.r_planets_in = 290  
        self.r_houses_in = 250   
        
        # تم استبدال الرموز بالاختصارات النصية الفلكية العالمية المكونة من 3 أحرف لضمان القراءة
        self.ZODIAC_UNICODE = {
            "Aries": "ARI", "Taurus": "TAU", "Gemini": "GEM", "Cancer": "CAN",
            "Leo": "LEO", "Virgo": "VIR", "Libra": "LIB", "Scorpio": "SCO",
            "Sagittarius": "SAG", "Capricorn": "CAP", "Aquarius": "AQU", "Pisces": "PIS"
        }
        
        self.PLANET_UNICODE = {
            "Sun": "SUN", "Moon": "MOO", "Mercury": "MER", "Venus": "VEN", 
            "Mars": "MAR", "Jupiter": "JUP", "Saturn": "SAT", "Uranus": "URA", 
            "Neptune": "NEP", "Pluto": "PLU", "Chiron": "CHI", "NorthNode": "NOD",
            "Lilith": "LIL"
        }

        self.ASPECT_COLORS = {
            "Conjunction": (255, 215, 0),    
            "Sextile": (0, 255, 127),        
            "Square": (255, 69, 0),          
            "Trine": (30, 144, 255),         
            "Opposition": (148, 0, 211)       
        }

    def _to_radians(self, degrees: float) -> float:
        return math.radians(degrees)

    def _get_coordinates(self, angle_deg: float, radius: float) -> tuple:
        rad = self._to_radians(180.0 - angle_deg)
        x = self.cx + radius * math.cos(rad)
        y = self.cy + radius * math.sin(rad)
        return round(x, 2), round(y, 2)

    def _format_degree(self, num_deg: float) -> str:
        degrees = int(num_deg)
        minutes = int(round((num_deg - degrees) * 60))
        if minutes == 60:
            degrees += 1
            minutes = 0
        return f"{degrees}°{minutes:02d}'"

    def _resolve_collisions(self, planets_angles: List[Dict[str, Any]], min_dist: float = 8.5) -> List[Dict[str, Any]]:
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
        # 1. إنشاء الخلفية
        image = Image.new("RGBA", (self.size, self.size), (13, 17, 23, 255))
        image_draw = ImageDraw.Draw(image)
        
        # استخدام الخط الافتراضي مع أحجام مناسبة للنصوص الإنجليزية المدمجة بكافة السيرفرات
        try:
            font_zodiac = ImageFont.load_default(size=14)
            font_planet = ImageFont.load_default(size=13)
            font_text = ImageFont.load_default(size=11)
        except Exception:
            font_zodiac = font_planet = font_text = ImageFont.load_default()

        asc_deg = getattr(chart_data, 'ascendant_degree', 0.0)
        
        # 2. رسم الحلقات
        image_draw.ellipse([self.cx - self.r_outer, self.cy - self.r_outer, self.cx + self.r_outer, self.cy + self.r_outer], outline=(33, 38, 45, 255), width=1)
        image_draw.ellipse([self.cx - self.r_zodiac_out, self.cy - self.r_zodiac_out, self.cx + self.r_zodiac_out, self.cy + self.r_zodiac_out], outline=(48, 54, 61, 255), width=2)
        image_draw.ellipse([self.cx - self.r_zodiac_in, self.cy - self.r_zodiac_in, self.cx + self.r_zodiac_in, self.cy + self.r_zodiac_in], fill=(22, 27, 34, 255), outline=(48, 54, 61, 255), width=2)
        image_draw.ellipse([self.cx - self.r_planets_in, self.cy - self.r_planets_in, self.cx + self.r_planets_in, self.cy + self.r_planets_in], outline=(48, 54, 61, 255), width=1)
        image_draw.ellipse([self.cx - self.r_houses_in, self.cy - self.r_houses_in, self.cx + self.r_houses_in, self.cy + self.r_houses_in], fill=(13, 17, 23, 255), outline=(33, 38, 45, 255), width=2)

        # 3. رسم قطاعات الأبراج الـ 12
        for i in range(12):
            sign_start_deg = i * 30.0
            rel_angle = sign_start_deg - asc_deg
            x1, y1 = self._get_coordinates(rel_angle, self.r_zodiac_in)
            x2, y2 = self._get_coordinates(rel_angle, self.r_zodiac_out)
            image_draw.line([(x1, y1), (x2, y2)], fill=(48, 54, 61, 255), width=2)
            
            mid_angle = rel_angle + 15.0
            signs_keys = list(self.ZODIAC_UNICODE.keys())
            sym = self.ZODIAC_UNICODE[signs_keys[i]]
            sx, sy = self._get_coordinates(mid_angle, (self.r_zodiac_out + self.r_zodiac_in) / 2)
            image_draw.text((sx, sy), sym, fill=(201, 209, 217, 255), font=font_zodiac, anchor="mm")

        # 4. رسم خطوط البيوت الـ 12 وتسمية الأوتاد
        if hasattr(chart_data, 'houses') and chart_data.houses:
            axis_labels = {1: "ASC", 10: "MC", 7: "DSC", 4: "IC"}
            for h_num, h_deg in chart_data.houses.items():
                rel_angle = h_deg - asc_deg
                x1, y1 = self._get_coordinates(rel_angle, self.r_houses_in)
                x2, y2 = self._get_coordinates(rel_angle, self.r_zodiac_in)
                
                is_axis = h_num in [1, 4, 7, 10]
                stroke_w = 4 if is_axis else 1
                stroke_c = (255, 123, 114, 255) if is_axis else (48, 54, 61, 255)
                image_draw.line([(x1, y1), (x2, y2)], fill=stroke_c, width=stroke_w)
                
                if is_axis:
                    tx, ty = self._get_coordinates(rel_angle + 3, self.r_houses_in - 20)
                    image_draw.text((tx, ty), axis_labels[h_num], fill=(255, 123, 114, 255), font=font_text, anchor="mm")
                else:
                    hx, hy = self._get_coordinates(rel_angle + 15, self.r_houses_in + 20)
                    image_draw.text((hx, hy), str(h_num), fill=(88, 166, 255, 255), font=font_text, anchor="mm")

        # 5. رسم خطوط الاتصالات الداخلية
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
                    
                    image_draw.line([(x1, y1), (x2, y2)], fill=color_rgba, width=2)

        # 6. فك اشتباك تكتل درجات الكواكب
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

        resolved_planets = self._resolve_collisions(raw_planets_data, min_dist=8.5)

        # 7. رسم الأجرام والدرجات الفلكية
        for p in resolved_planets:
            sym = self.PLANET_UNICODE[p['name']]
            
            dot_x, dot_y = self._get_coordinates(p['orig_angle'], self.r_houses_in + 4)
            image_draw.ellipse([dot_x - 3, dot_y - 3, dot_x + 3, dot_y + 3], fill=(88, 166, 255, 255))
            
            px, py = self._get_coordinates(p['curr_angle'], (self.r_zodiac_in + self.r_planets_in) / 2)
            image_draw.text((px, py), sym, fill=(255, 255, 255, 255), font=font_planet, anchor="mm")
            
            formatted_txt = self._format_degree(p['display_deg'])
            dx, dy = self._get_coordinates(p['curr_angle'], self.r_planets_in + 15)
            image_draw.text((dx, dy), formatted_txt, fill=(139, 148, 158, 255), font=font_text, anchor="mm")

        # البصمة الفلكية
        image_draw.text((self.cx, self.cy), "AL-RAFID ASTRO", fill=(33, 38, 45, 255), font=font_text, anchor="mm")

        # 8. حفظ وإخراج الصورة كـ Bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        return img_byte_arr.getvalue()
