from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import urllib.parse

# Safely encode password (optional but good practice)
password = "npg_1m5ruyjfqxRF"
encoded_password = urllib.parse.quote_plus(password)

DATABASE_URL = f"postgresql://neondb_owner:{encoded_password}@ep-wild-dream-ad9iewrn-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

# Critical fixes for Neon + pooler compatibility
engine = create_engine(
    DATABASE_URL,
    echo=False,                   
    future=True,
    pool_pre_ping=True,     
    connect_args={
        "sslmode": "require",
    },
    execution_options={"isolation_level": "AUTOCOMMIT"},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()