# app/main.py
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from database_connection import engine, Base
from models.user import User  # noqa: F401
from models.contact import ContactMessage  # noqa: F401
from routers.auth import router as auth_router
from routers.contact import router as contact_router
from routers.user import router as user_router

# Create DB tables (for SQLite / development). 
# In production, use Alembic migrations.
Base.metadata.create_all(bind=engine)

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

# Include Routers
app.include_router(auth_router)
app.include_router(contact_router)
app.include_router(user_router)

@app.get("/")
def root():
    return {"message": "HamroRental API is running!"}