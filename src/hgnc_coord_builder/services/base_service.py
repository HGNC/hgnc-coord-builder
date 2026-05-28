"""Abstract base class for all service implementations."""

from abc import ABC, abstractmethod


class Service(ABC):
    """Define the contract for a batch-job service.

    All Phase 2 services MUST implement this interface.
    """

    @abstractmethod
    def run(self) -> None:
        """Execute the service's primary business logic."""
