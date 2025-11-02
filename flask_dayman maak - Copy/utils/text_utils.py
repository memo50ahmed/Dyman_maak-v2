import re
from rapidfuzz import fuzz

def normalize_english(text):
    """Clean and normalize English text"""
    if not text:
        return ""
    text = text.lower().strip()
    # Remove punctuation and special symbols
    text = re.sub(r'[^a-z0-9\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text

def find_best_place_match(user_message, places, threshold=70):
    """Find the best matching place using fuzzy matching"""
    norm_msg = normalize_english(user_message)
    best = None
    best_score = 0

    for p in places:
        candidates = [
            getattr(p, "name_place", "") or "",
            getattr(p, "short_name", "") or "",
            getattr(p, "city", "") or "",
            getattr(p, "place_type", "") or ""
        ]
        for cand in candidates:
            score = fuzz.token_sort_ratio(norm_msg, normalize_english(cand))
            if score > best_score:
                best_score = score
                best = p

    if best and best_score >= threshold:
        return best, best_score
    return None, best_score
