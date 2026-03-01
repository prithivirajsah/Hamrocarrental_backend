# app/utils.py
import re
from typing import Tuple, List
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    # bcrypt limitation: max 72 bytes, raise clear error
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password is too long (max 72 bytes for bcrypt)")
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    if len(plain_password.encode("utf-8")) > 72:
        return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except (ValueError, TypeError):
        return False

def validate_password_strength(password: str) -> Tuple[bool, List[str]]:
    errors = []
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")
    if not re.search(r"\d", password):
        errors.append("Password must contain at least one number")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        errors.append("Password must contain at least one special character")
    weak_patterns = ["123456", "password", "qwerty", "abc123", "admin"]
    for p in weak_patterns:
        if p in password.lower():
            errors.append("Password contains common weak pattern")
            break
    if re.search(r"(.)\1{3,}", password):
        errors.append("Password cannot have more than 3 consecutive identical characters")
    return (len(errors) == 0, errors)

def get_password_requirements() -> dict:
    return {
        "min_length": 8,
        "require_uppercase": True,
        "require_lowercase": True,
        "require_number": True,
        "require_special": True,
        "special_characters": "!@#$%^&*(),.?\":{}|<>",
        "max_consecutive_chars": 3,
        "forbidden_patterns": ["123456", "password", "qwerty", "abc123", "admin"]
    }
