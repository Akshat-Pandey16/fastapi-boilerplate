"""SQLAlchemy ORM models.

Importing this package ensures every model class is registered with the
shared ``Base.metadata`` so Alembic's autogenerate sees them.
"""

from app.db.base import Base
from app.models.user import User

__all__ = ["Base", "User"]
