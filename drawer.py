import math
from typing import Dict, Any, List

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
            "Conjunction": "#FFD700", "Sextile": "#00FF7F", "Square": "#FF4500",
            "Trine": "#1E90FF", "Opposition": "#9400D3"
        }

    def _to_radians(self, degrees: float) -> float:
        return math.radians(degrees)

    def _get_coordinates(self, angle_deg: float, radius: float) -> tuple:
        """تحويل من قطبي إلى ديكارتي مع تدوير النظام لتبدأ الدائرة دائماً من الطالع"""
        # تثبيت الطالع عند زاوية 180 درجة هندسياً (يسار الشاشة تماماً)
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

        for _ in range(5):  # 5 دورات فحص كافية لفك التجمعات (Stelliums)
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

    def generate_chart_svg(self, chart_data: Any) -> str:
        """توليد كود الـ SVG النقي بالكامل هندسياً وبدقة عالية"""
        asc_deg = getattr(chart_data, 'ascendant_degree', 0.0)
        mc_deg = getattr(chart_data, 'midheaven_degree', 0.0)
        
        svg_elements = []
        
        svg_elements.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.size} {self.size}" width="100%" height="100%" '
            f'shape-rendering="geometricPrecision" text-rendering="geometricPrecision">'
            f'<rect width="100%" height="100%" fill="#0d1117"/>'
            f'<style>'
            f'.zodiac-sym {{ font-family: "Arial", "Segoe UI Symbol"; font-size: 28px; fill: #c9d1d9; text-anchor: middle; dominant-baseline: middle; }}'
            f'.planet-sym {{ font-family: "Arial", "Segoe UI Symbol"; font-size: 22px; fill: #ffffff; text-anchor: middle; dominant-baseline: middle; }}'
            f'.planet-deg {{ font-family: "monospace", "sans-serif"; font-size: 11px; fill: #8b949e; text-anchor: middle; }}'
            f'.house-num {{ font-family: "sans-serif"; font-size: 13px; fill: #58a6ff; font-weight: bold; text-anchor: middle; dominant-baseline: middle; }}'
            f'.axis-text {{ font-family: "sans-serif"; font-size: 14px; fill: #ff7b72; font-weight: bold; text-anchor: middle; dominant-baseline: middle; }}'
            f'</style>'
        )

        # رسم الحلقات الأربع
        svg_elements.append(f'<circle cx="{self.cx}" cy="{self.cy}" r="{self.r_outer}" stroke="#21262d" stroke-width="1" fill="none"/>')
        svg_elements.append(f'<circle cx="{self.cx}" cy="{self.cy}" r="{self.r_zodiac_out}" stroke="#30363d" stroke-width="2" fill="none"/>')
        svg_elements.append(f'<circle cx="{self.cx}" cy="{self.cy}" r="{self.r_zodiac_in}" stroke="#30363d" stroke-width="2" fill="#161b22"/>')
        svg_elements.append(f'<circle cx="{self.cx}" cy="{self.cy}" r="{self.r_planets_in}" stroke="#30363d" stroke-width="1.5" fill="none"/>')
        svg_elements.append(f'<circle cx="{self.cx}" cy="{self.cy}" r="{self.r_houses_in}" stroke="#21262d" stroke-width="2" fill="#0d1117"/>')

        # رسم قطاعات الأبراج الـ 12 بالتساوي
        for i in range(12):
            sign_start_deg = i * 30.0
            rel_angle = sign_start_deg - asc_deg
            x1, y1 = self._get_coordinates(rel_angle, self.r_zodiac_in)
            x2, y2 = self._get_coordinates(rel_angle, self.r_zodiac_out)
            svg_elements.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#30363d" stroke-width="1.5"/>')
            
            mid_angle = rel_angle + 15.0
            signs_keys = list(self.ZODIAC_UNICODE.keys())
            sym = self.ZODIAC_UNICODE[signs_keys[i]]
            sx, sy = self._get_coordinates(mid_angle, (self.r_zodiac_out + self.r_zodiac_in) / 2)
            svg_elements.append(f'<text x="{sx}" y="{sy}" class="zodiac-sym">{sym}</text>')

        # رسم خطوط البيوت الـ 12 وتسمية الأوتاد
        if hasattr(chart_data, 'houses') and chart_data.houses:
            axis_labels = {1: "ASC", 10: "MC", 7: "DSC", 4: "IC"}
            for h_num, h_deg in chart_data.houses.items():
                rel_angle = h_deg - asc_deg
                x1, y1 = self._get_coordinates(rel_angle, self.r_houses_in)
                x2, y2 = self._get_coordinates(rel_angle, self.r_zodiac_in)
                
                is_axis = h_num in [1, 4, 7, 10]
                stroke_w = "3.5" if is_axis else "1"
                stroke_c = "#ff7b72" if is_axis else "#30363d"
                svg_elements.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke_c}" stroke-width="{stroke_w}"/>')
                
                if is_axis:
                    tx, ty = self._get_coordinates(rel_angle + 3, self.r_houses_in - 20)
                    svg_elements.append(f'<text x="{tx}" y="{ty}" class="axis-text">{axis_labels[h_num]}</text>')
                else:
                    hx, hy = self._get_coordinates(rel_angle + 15, self.r_houses_in + 20)
                    svg_elements.append(f'<text x="{hx}" y="{hy}" class="house-num">{h_num}</text>')

        # رسم خطوط الاتصالات الداخلية مع Opacity ديناميكي حسب الـ Orb
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
                    opacity = max(0.15, round(1.0 - (orb / 8.0), 2))
                    
                    color = self.ASPECT_COLORS.get(aspect.type, "#8b949e")
                    dash = 'stroke-dasharray="4,3"' if aspect.type in ["Square", "Opposition"] else ""
                    
                    svg_elements.append(
                        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="2" {dash} opacity="{opacity}"/>'
                    )

        # تجهيز بيانات الكواكب لفك الاشتباك والتداخل
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

        # رسم رموز الكواكب والدرجات الدقيقة
        for p in resolved_planets:
            sym = self.PLANET_UNICODE[p['name']]
            
            dot_x, dot_y = self._get_coordinates(p['orig_angle'], self.r_houses_in + 4)
            svg_elements.append(f'<circle cx="{dot_x}" cy="{dot_y}" r="2.5" fill="#58a6ff"/>')
            
            px, py = self._get_coordinates(p['curr_angle'], (self.r_zodiac_in + self.r_planets_in) / 2)
            svg_elements.append(f'<text x="{px}" y="{py}" class="planet-sym">{sym}</text>')
            
            formatted_txt = self._format_degree(p['display_deg'])
            dx, dy = self._get_coordinates(p['curr_angle'], self.r_planets_in + 15)
            svg_elements.append(f'<text x="{dx}" y="{dy}" class="planet-deg">{formatted_txt}</text>')

        # بصمة البوت التجارية في المركز
        svg_elements.append(f'<text x="{self.cx}" y="{self.cy + 6}" font-family="sans-serif" font-size="13" fill="#21262d" font-weight="bold" text-anchor="middle" letter-spacing="4">AL-RAFID ASTRO</text>')
        
        svg_elements.append('</svg>')
        return "\n".join(svg_elements)
