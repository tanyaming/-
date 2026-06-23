from abc import ABC, abstractmethod
from typing import Any

from app.models.entities import VendorAccount


class VendorAdapter(ABC):
    def __init__(self, account: VendorAccount) -> None:
        self.account = account

    @abstractmethod
    def test_connection(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def fetch_vehicle_list(self) -> list[dict[str, Any]]:
        raise NotImplementedError

