from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    # Ensure password is not longer than 72 bytes for bcrypt
    if len(password.encode('utf-8')) > 72:
        raise ValueError("Password is too long. Please use a password with 72 characters or fewer.")
    return pwd_context.hash(password)