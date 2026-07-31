"""Repository (data-access) layer.

``protocols`` defines what the service layer may call; ``sql`` and ``mongo``
hold the implementations. Only the protocol is re-exported here — importing an
adapter would drag in a driver the deployment may not have installed.
"""

from app.repositories.protocols import UserRepository

__all__ = ["UserRepository"]
