import re
from collections import defaultdict
from config import KEYWORD_RULES, SCORING_WEIGHTS

class SmartRanker:
    def __init__(self):
        # Pre-compile regex for speed
        self.patterns = {}
        for cat, rules in KEYWORD_RULES.items():
            self.patterns[cat] = [re.compile(r, re.IGNORECASE) for r in rules]

    def process_article(self, article):
        """
        1. Calculate Score based on Keywords.
        2. Assign Primary Category.
        """
        text = (article.get('title', '') + " " + article.get('summary', '')).lower()
        
        score = 10.0 # Base score
        matches = []
        cat_counts = defaultdict(int)
        
        for cat, regex_list in self.patterns.items():
            for regex in regex_list:
                if regex.search(text):
                    # Add weight
                    weight = SCORING_WEIGHTS.get(cat, 0)
                    if cat == "NOISE": 
                        score = -50.0 # Instant kill
                    else:
                        score += weight
                    
                    if cat != "NOISE":
                        cat_counts[cat] += 1
                        matches.append(cat)

        # Determine Category
        if score < 0:
            final_cat = "NOISE"
        elif not cat_counts:
            final_cat = "GENERAL"
        else:
            # Pick category with most hits, or highest priority if tie
            # Sort by count desc, then by weight desc
            sorted_cats = sorted(
                cat_counts.keys(), 
                key=lambda c: (cat_counts[c], SCORING_WEIGHTS.get(c, 0)), 
                reverse=True
            )
            final_cat = sorted_cats[0]

        article['score'] = round(score, 1)
        article['category'] = final_cat
        return article

    def rank_list(self, articles):
        return [self.process_article(a) for a in articles]