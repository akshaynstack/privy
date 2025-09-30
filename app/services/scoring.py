# app/services/scoring.py
from typing import List, Tuple
import re

# Risk scoring weights (0-100 scale)
WEIGHTS = {
    "disposable_email": 70,       # Temporary email services
    "vpn_ip": 45,                 # VPN/Proxy users (many legitimate)
    "tor_exit": 85,               # Tor network users (high risk)
    "bad_isp": 35,                # Hosting providers
    "high_risk_country": 25,      # Geographic risk
    "multiple_from_ip": 30,       # Multiple signups from same IP
    "custom_blacklist": 100,      # Organization blacklist (instant block)
    "suspicious_email_pattern": 40, # Suspicious email patterns
    "new_domain": 20,             # Recently registered domains
    "free_email": 10,             # Free email providers (low risk)
}

# Free email providers (lower risk than disposable)
FREE_EMAIL_PROVIDERS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", 
    "aol.com", "icloud.com", "protonmail.com", "yandex.com",
    "mail.com", "zoho.com", "tutanota.com"
}

# Suspicious email patterns
SUSPICIOUS_PATTERNS = [
    r'^[a-z]+\d{4,}@',           # username followed by 4+ digits
    r'^\w{1,3}\d{3,}@',          # 1-3 chars + 3+ digits
    r'^[a-z]+[._-][a-z]+\d+@',   # firstname.lastname123 pattern
    r'^\d+[a-z]*@',             # starting with numbers
    r'^[a-z]*test[a-z]*\d*@',    # contains 'test'
    r'^temp[a-z]*\d*@',         # contains 'temp'
    r'^fake[a-z]*\d*@',         # contains 'fake'
]


def compute_score(hits: List[str], email: str = None, ip: str = None) -> Tuple[int, str, List[str]]:
    """Compute fraud risk score based on detected issues.
    
    Args:
        hits: List of detected fraud indicators
        email: Email address for additional pattern analysis
        ip: IP address for additional analysis
        
    Returns:
        Tuple of (score, risk_level, reasons)
    """
    score = 0
    reasons = list(hits)  # Copy the hits list
    
    # Add base scores from detected hits
    for hit in hits:
        score += WEIGHTS.get(hit, 0)
    
    # Additional email analysis
    if email:
        email_score, email_reasons = _analyze_email_patterns(email)
        score += email_score
        reasons.extend(email_reasons)
    
    # Additional IP analysis  
    if ip:
        ip_score, ip_reasons = _analyze_ip_patterns(ip)
        score += ip_score
        reasons.extend(ip_reasons)
    
    # Cap score at 100
    score = min(score, 100)
    
    # Determine risk level
    if score >= 80:
        level = "high"
    elif score >= 60:
        level = "medium"
    elif score >= 30:
        level = "low"
    else:
        level = "none"
    
    return score, level, reasons


def _analyze_email_patterns(email: str) -> Tuple[int, List[str]]:
    """Analyze email for suspicious patterns."""
    score = 0
    reasons = []
    
    if not email or '@' not in email:
        return 0, []
    
    local_part, domain = email.lower().split('@', 1)
    
    # Check for free email providers (low risk)
    if domain in FREE_EMAIL_PROVIDERS:
        score += WEIGHTS["free_email"]
        reasons.append("free_email")
    
    # Check for suspicious patterns in local part
    for pattern in SUSPICIOUS_PATTERNS:
        if re.match(pattern, email.lower()):
            score += WEIGHTS["suspicious_email_pattern"]
            reasons.append("suspicious_email_pattern")
            break  # Only count once
    
    # Check for very short local part (suspicious)
    if len(local_part) <= 2:
        score += 15
        reasons.append("short_email_local")
    
    # Check for very long local part (suspicious)
    if len(local_part) >= 30:
        score += 10
        reasons.append("long_email_local")
    
    # Check for excessive numbers in email
    digit_count = sum(c.isdigit() for c in local_part)
    if digit_count >= 5:
        score += 20
        reasons.append("excessive_numbers_email")
    
    return score, reasons


def _analyze_ip_patterns(ip: str) -> Tuple[int, List[str]]:
    """Analyze IP for suspicious patterns."""
    score = 0
    reasons = []
    
    if not ip:
        return 0, []
    
    # Check for private/local IPs (should not happen in production)
    if _is_private_ip(ip):
        score += 50
        reasons.append("private_ip")
    
    # Check for common VPN/proxy IP ranges (basic heuristics)
    if _is_suspicious_ip_range(ip):
        score += 25
        reasons.append("suspicious_ip_range")
    
    return score, reasons


def _is_private_ip(ip: str) -> bool:
    """Check if IP is in private ranges."""
    try:
        parts = [int(x) for x in ip.split('.')]
        if len(parts) != 4:
            return False
        
        # Private IP ranges
        if parts[0] == 10:  # 10.0.0.0/8
            return True
        if parts[0] == 172 and 16 <= parts[1] <= 31:  # 172.16.0.0/12
            return True
        if parts[0] == 192 and parts[1] == 168:  # 192.168.0.0/16
            return True
        if parts[0] == 127:  # 127.0.0.0/8 (localhost)
            return True
            
        return False
    except (ValueError, IndexError):
        return False


def _is_suspicious_ip_range(ip: str) -> bool:
    """Check if IP is in commonly used VPN/proxy ranges."""
    try:
        parts = [int(x) for x in ip.split('.')]
        if len(parts) != 4:
            return False
        
        # Some common VPN/proxy ranges (basic detection)
        # Note: This is very basic - use commercial IP intelligence for better detection
        suspicious_ranges = [
            (185, 220, 101),  # Common proxy range
            (198, 7, 58),     # NordVPN range
            (185, 216, 35),   # ExpressVPN range
        ]
        
        for range_start in suspicious_ranges:
            if parts[0] == range_start[0] and parts[1] == range_start[1] and parts[2] == range_start[2]:
                return True
                
        return False
    except (ValueError, IndexError):
        return False


def get_risk_explanation(score: int, level: str) -> str:
    """Get human-readable explanation of risk level."""
    explanations = {
        "none": f"Low risk (score: {score}/100). Safe to proceed with normal flow.",
        "low": f"Low risk (score: {score}/100). Monitor user behavior but allow registration.",
        "medium": f"Medium risk (score: {score}/100). Recommend additional verification (CAPTCHA, email verification, 2FA).",
        "high": f"High risk (score: {score}/100). Consider blocking or requiring manual review."
    }
    return explanations.get(level, f"Unknown risk level: {level} (score: {score})")


def get_action_recommendations(score: int) -> dict:
    """Get detailed action recommendations based on score."""
    if score >= 80:
        return {
            "action": "block",
            "message": "High fraud risk detected. Registration blocked.",
            "recommendations": [
                "Block registration immediately",
                "Log details for investigation", 
                "Consider IP/email blocking",
                "Manual review if legitimate user"
            ]
        }
    elif score >= 60:
        return {
            "action": "challenge",
            "message": "Medium fraud risk detected. Additional verification required.",
            "recommendations": [
                "Require CAPTCHA verification",
                "Send email verification link",
                "Enable 2FA requirement",
                "Monitor subsequent actions"
            ]
        }
    elif score >= 30:
        return {
            "action": "monitor",
            "message": "Low fraud risk detected. Monitor user behavior.",
            "recommendations": [
                "Allow registration with monitoring",
                "Track user behavior patterns",
                "Flag for review if suspicious activity",
                "Consider velocity limits"
            ]
        }
    else:
        return {
            "action": "allow",
            "message": "Low fraud risk. Safe to proceed.",
            "recommendations": [
                "Allow normal registration flow",
                "Standard monitoring applies"
            ]
        }