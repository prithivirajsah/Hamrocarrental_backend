from sqlalchemy import create_engine
from sqlalchemy.exc import IllegalStateChangeError
from sqlalchemy.orm import sessionmaker, declarative_base
import urllib.parse
import asyncio

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
    pool_recycle=3600,  # Recycle connections after 1 hour to prevent stale connections
    pool_size=5,        # Limit pool size to prevent timeout issues
    max_overflow=10,    # Allow overflow connections up to 10
    connect_args={
        "sslmode": "require",
        "connect_timeout": 30,  # Connection timeout in seconds
    },
    execution_options={"isolation_level": "AUTOCOMMIT"},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    except asyncio.CancelledError:
        # Handle cancellation during shutdown gracefully
        try:
            db.rollback()
        except Exception:
            pass
        try:
            db.close()
        except Exception:
            pass
        raise
    except Exception:
        # Ensure pending transaction state does not leak between requests.
        try:
            db.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            db.close()
        except (IllegalStateChangeError, asyncio.CancelledError):
            # Can happen during shutdown/cancellation while connection checkout is in progress.
            try:
                db.invalidate()
            except Exception:
                pass
        except Exception:
            pass