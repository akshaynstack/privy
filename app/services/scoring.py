# app/services/scoring.py
WEIGHTS = {
    "disposable_email": 70,
    "vpn_ip": 60,
    "tor_exit": 80,
    "bad_isp": 40,
    "multiple_from_ip": 30,
    "custom_blacklist": 100,
}

def compute_score(hits: list[str]):
    score = 0
    reasons = []
    for h in hits:
        score += WEIGHTS.get(h, 0)
        reasons.append(h)
    score = min(score, 100)
    if score >= 80:
        level = "high"
    elif score >= 60:
        level = "medium"
    elif score >= 30:
        level = "low"
    else:
        level = "none"
    return score, level, reasons