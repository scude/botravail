from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class JobOffer:
    title: str
    url: str
    company: str | None
    location: str | None
    contract_type: str | None
    salary: str | None
    publication_date: str | None
    description: str | None


class BaseJobScraper(ABC):
    name: str

    @abstractmethod
    async def scrape_jobs(self, max_results: int = 20, headless: bool = True) -> list[JobOffer]:
        raise NotImplementedError
