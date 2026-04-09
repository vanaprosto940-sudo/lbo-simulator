"""Abstract data provider interface and implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod

from lbo_simulator.models.schemas import CompanyProfileSchema


class DataProvider(ABC):
    """Abstract base class for data providers."""

    @abstractmethod
    def get_company_profile(self, company_name: str) -> CompanyProfileSchema:
        """Get financial profile for a company."""
        ...

    @abstractmethod
    def get_macro_data(self) -> dict:
        """Get macroeconomic data (rates, spreads, GDP)."""
        ...
