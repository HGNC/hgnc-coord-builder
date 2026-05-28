"""Abstract base class for all repository implementations."""

from abc import ABC, abstractmethod


class Repository(ABC):
    """Marker base class for repository abstractions.

    All database-accessing classes MUST inherit from this ABC
    so that services can type-hint against the abstraction.
    """

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the underlying data store is reachable."""
