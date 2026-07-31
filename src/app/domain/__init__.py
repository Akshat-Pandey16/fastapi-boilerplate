"""Domain records — what the service layer passes around.

These types are deliberately free of SQLAlchemy and MongoDB imports, which is
what lets one service work against any supported backend.
"""

from app.domain.user import UserRecord

__all__ = ["UserRecord"]
