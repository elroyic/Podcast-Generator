"""
Shared modules for the Podcast AI application.
"""

try:
    from .database import create_tables, get_db, get_db_session
    from .models import Base
    from .schemas import *
except ImportError:
    from database import create_tables, get_db, get_db_session
    from models import Base
    from schemas import *

__all__ = [
    "create_tables",
    "get_db", 
    "get_db_session",
    "Base",
]