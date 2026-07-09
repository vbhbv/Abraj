import random
from typing import List, Dict
from models import AstrologicalFact, ProfileScores

class RulesEngine:
    @staticmethod
    def evaluate(facts: List[AstrologicalFact]) -> ProfileScores:
        scores = ProfileScores()
        for fact in facts:
            if fact.code == "SUN_H10":
                scores.career += 20
                scores.leadership += 15
            elif "MARS" in fact.code and "SQUARE" in fact.code:
                scores.anger += 12
                scores.competition += 18
            elif "ASC_LEO" in fact.code:
                scores.leadership += 10
        return scores

class ConflictResolver:
    @staticmethod
    def resolve_and_merge(facts: List[AstrologicalFact], interpretations_db: Dict) -> List[str]:
        compiled_paragraphs = []
        fact_codes = {f.code for f in facts}
        
        if "ASC_LEO" in fact_codes and "SUN_H12" in fact_codes:
            conflict_resolution = "تتمتع بحضور خارجي يحمل ملامح كاريزمية تلفت الأنظار، بيد أنك داخلياً تفضل الاحتفاظ بخصوصيتك العميقة بعيداً عن الصخب."
            compiled_paragraphs.append(conflict_resolution)
            fact_codes.discard("ASC_LEO")
            
        for fact in facts:
            if fact.code in fact_codes and fact.code in interpretations_db:
                fact_data = interpretations_db[fact.code]
                chosen_template = random.choice(fact_data["templates"])
                compiled_paragraphs.append(chosen_template)
                
        return compiled_paragraphs
      
