from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

from database_connection import Base

# Load models so SQLAlchemy can resolve foreign-key tables in metadata.
from models.user import User  # noqa: F401
from models.post import Post  # noqa: F401
from models.booking import Booking  # noqa: F401


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    testing_session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    Base.metadata.create_all(bind=engine)
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
