from typing import List
from models import ChartResult, AstrologicalFact

class FactsEngine:
    @staticmethod
    def extract_facts(chart: ChartResult) -> List[AstrologicalFact]:
        facts = []
        
        for p_name, p_data in chart.planets.items():
            code = f"{p_name.upper()}_H{p_data.house}"
            strength = 1.0 if p_name in ["Sun", "Moon"] else 0.7
            category = "career" if p_data.house in [10, 2, 6] else "personality"
            facts.append(AstrologicalFact(code=code, strength=strength, category=category))
            
        facts.append(AstrologicalFact(code=f"ASC_{chart.ascendant.upper()}", strength=0.95, category="personality"))
        
        for aspect in chart.aspects:
            p1, p2, a_type, orb = aspect.planet1.upper(), aspect.planet2.upper(), aspect.type.upper(), aspect.orb
            code = f"{p1}_{a_type}_{p2}"
            strength = round(max(0.1, 1.0 - (orb / 8.0)), 2)
            category = "emotion" if "MOON" in [p1, p2] else "personality"
            if "MARS" in [p1, p2] and a_type == "SQUARE":
                category = "competition"
            facts.append(AstrologicalFact(code=code, strength=strength, category=category))
            
        return facts
