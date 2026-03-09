# app/main.py
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text

load_dotenv()

from database_connection import engine, Base
from models.user import User  # noqa: F401
from models.contact import ContactMessage  # noqa: F401
from models.post import Post  # noqa: F401
from models.booking import Booking  # noqa: F401
from routers.auth import router as auth_router
from routers.booking import router as booking_router
from routers.contact import router as contact_router
from routers.post import router as post_router
from routers.user import router as user_router
from routers.admin import router as admin_router


def _migrate_legacy_bookings_schema() -> None:
    """Bring older bookings table layouts up to the current API schema."""
    inspector = inspect(engine)
    if "bookings" not in inspector.get_table_names():
        return

    columns = {col["name"]: col for col in inspector.get_columns("bookings")}
    column_names = set(columns.keys())

    with engine.begin() as conn:
        if "post_id" not in column_names:
            conn.execute(text("ALTER TABLE bookings ADD COLUMN post_id INTEGER"))

        if "owner_id" not in column_names:
            conn.execute(text("ALTER TABLE bookings ADD COLUMN owner_id INTEGER"))

        if "return_location" not in column_names:
            conn.execute(text("ALTER TABLE bookings ADD COLUMN return_location VARCHAR"))
            if "dropoff_location" in column_names:
                conn.execute(
                    text(
                        "UPDATE bookings SET return_location = dropoff_location "
                        "WHERE return_location IS NULL"
                    )
                )

        if "start_date" not in column_names:
            conn.execute(text("ALTER TABLE bookings ADD COLUMN start_date DATE"))
            if "pickup_date" in column_names:
                conn.execute(
                    text(
                        "UPDATE bookings SET start_date = pickup_date "
                        "WHERE start_date IS NULL"
                    )
                )

        if "end_date" not in column_names:
            conn.execute(text("ALTER TABLE bookings ADD COLUMN end_date DATE"))
            if "return_date" in column_names:
                conn.execute(
                    text(
                        "UPDATE bookings SET end_date = return_date "
                        "WHERE end_date IS NULL"
                    )
                )

        if "total_days" not in column_names:
            conn.execute(text("ALTER TABLE bookings ADD COLUMN total_days INTEGER"))
            conn.execute(
                text(
                    "UPDATE bookings "
                    "SET total_days = GREATEST((end_date - start_date + 1), 1) "
                    "WHERE start_date IS NOT NULL AND end_date IS NOT NULL AND total_days IS NULL"
                )
            )

        if "price_per_day" not in column_names:
            conn.execute(text("ALTER TABLE bookings ADD COLUMN price_per_day DOUBLE PRECISION"))

        if "total_price" not in column_names:
            conn.execute(text("ALTER TABLE bookings ADD COLUMN total_price DOUBLE PRECISION"))

        conn.execute(
            text(
                "UPDATE bookings SET price_per_day = 0 "
                "WHERE price_per_day IS NULL"
            )
        )
        conn.execute(
            text(
                "UPDATE bookings SET total_price = COALESCE(total_days, 0) * price_per_day "
                "WHERE total_price IS NULL"
            )
        )

        if "note" not in column_names:
            conn.execute(text("ALTER TABLE bookings ADD COLUMN note TEXT"))

        # Legacy schemas may keep old columns as NOT NULL even though the current
        # API no longer writes to them (e.g. vehicle_type), causing insert errors.
        if engine.dialect.name == "postgresql":
            for legacy_column in ("vehicle_type", "pickup_date", "return_date", "dropoff_location"):
                legacy_meta = columns.get(legacy_column)
                if legacy_meta and legacy_meta.get("nullable") is False:
                    conn.execute(
                        text(f'ALTER TABLE bookings ALTER COLUMN "{legacy_column}" DROP NOT NULL')
                    )

# Create DB tables (for SQLite / development). 
# In production, use Alembic migrations.
Base.metadata.create_all(bind=engine)
_migrate_legacy_bookings_schema()

app = FastAPI(
    title="HamroRental API",
    description="A rental platform API for Nepal",
    version="1.0.0"
)

# Read environment (default: development)
ENV = os.getenv("ENVIRONMENT", "development")
DEBUG = ENV == "development"

# CORS Allowed Origins
if DEBUG:
    origins = ["*"]  # Allow everything during development
else:
    origins = [
        "https://hamrorental-frontend.vercel.app",
        "https://hamrorental.com.np",
        "https://*.onrender.com",
        "https://*.vercel.app",
        "https://*.netlify.app",
    ]

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include Routers
app.include_router(auth_router)
app.include_router(contact_router)
app.include_router(post_router)
app.include_router(booking_router)
app.include_router(user_router)
app.include_router(admin_router)

@app.get("/")
def root():
    return {"message": "HamroRental API is running!"}