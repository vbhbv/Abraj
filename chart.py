import swisseph as swe
from datetime import datetime
from models import ChartResult, PlanetData, AspectData
from utils import is_between_arc

class CoreAstrologyEngine:
    def __init__(self, ephe_path="./ephe"):
        swe.set_ephe_path(ephe_path)
        self.PLANETS = {
            'Sun': swe.SUN, 'Moon': swe.MOON, 'Mercury': swe.MERCURY,
            'Venus': swe.VENUS, 'Mars': swe.MARS, 'Jupiter': swe.JUPITER,
            'Saturn': swe.SATURN, 'Uranus': swe.URANUS, 'Neptune': swe.NEPTUNE, 'Pluto': swe.PLUTO,
            'Chiron': swe.CHIRON, 'NorthNode': swe.MEAN_NODE, 'Lilith': swe.MEAN_APOG  # التعديل الحرفي هنا
        }
        self.SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

    def _to_julian_day(self, dt: datetime) -> float:
        return swe.julday(dt.year, dt.month, dt.day, dt.hour + dt.minute / 60.0)

    def _determine_house(self, lon: float, cusps: list) -> int:
        for i in range(1, 12):
            if is_between_arc(cusps[i], cusps[i+1], lon):
                return i
        return 12

    def compute_natal_chart(self, dt_utc: datetime, lat: float, lon: float) -> ChartResult:
        jd = self._to_julian_day(dt_utc)
        cusps, ascmc = swe.houses(jd, lat, lon, b'P')
        
        planets_computed = {}
        for name, swe_id in self.PLANETS.items():
            res, _ = swe.calc_ut(jd, swe_id)
            long = res[0]
            planets_computed[name] = PlanetData(
                name=name, longitude=long, sign=self.SIGNS[int(long / 30)],
                degree=round(long % 30, 2), house=self._determine_house(long, cusps),
                retrograde=True if res[3] < 0 else False, speed=round(res[3], 4)
            )
            
        sn_long = (planets_computed['NorthNode'].longitude + 180.0) % 360.0
        planets_computed['SouthNode'] = PlanetData(
            name='SouthNode', longitude=sn_long, sign=self.SIGNS[int(sn_long / 30)],
            degree=round(sn_long % 30, 2), house=self._determine_house(sn_long, cusps),
            retrograde=planets_computed['NorthNode'].retrograde, speed=planets_computed['NorthNode'].speed
        )

        aspects_computed = self._compute_aspects_by_time_delta(jd, planets_computed)

        return ChartResult(
            ascendant=self.SIGNS[int(ascmc[0] / 30)], midheaven=self.SIGNS[int(ascmc[1] / 30)],
            planets=planets_computed, aspects=aspects_computed, houses={i: float(cusps[i]) for i in range(1, 13)}
        )

    def _compute_aspects_by_time_delta(self, jd_current: float, planets_current: dict) -> list:
        aspects = []
        names = list(planets_current.keys())
        ASPECT_TYPES = {0: 'Conjunction', 60: 'Sextile', 90: 'Square', 120: 'Trine', 180: 'Opposition'}
        
        jd_future = jd_current + (1.0 / 24.0)
        planets_future = {}
        for name, swe_id in self.PLANETS.items():
            res, _ = swe.calc_ut(jd_future, swe_id)
            planets_future[name] = res[0]
        planets_future['SouthNode'] = (planets_future['NorthNode'] + 180.0) % 360.0

        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                p1, p2 = planets_current[names[i]], planets_current[names[j]]
                diff = abs(p1.longitude - p2.longitude)
                if diff > 180: diff = 360 - diff
                
                for angle, aspect_name in ASPECT_TYPES.items():
                    orb = abs(diff - angle)
                    allowed_orb = 8.0 if 'Sun' in [p1.name, p2.name] or 'Moon' in [p1.name, p2.name] else 5.5
                    
                    if orb <= allowed_orb:
                        f_long1 = planets_future[p1.name]
                        f_long2 = planets_future[p2.name]
                        f_diff = abs(f_long1 - f_long2)
                        if f_diff > 180: f_diff = 360 - f_diff
                        future_orb = abs(f_diff - angle)
                        
                        is_applying = True if future_orb < orb else False
                        
                        aspects.append(AspectData(
                            planet1=p1.name, planet2=p2.name,
                            type=aspect_name, orb=round(orb, 2), applying=is_applying
                        ))
        return aspects
