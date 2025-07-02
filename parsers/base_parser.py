# parsers/base_parser.py
from abc import ABC, abstractmethod
from typing import List

from parsers.dto import VacancyDTO


class BaseParser(ABC):
    """Абстрактный базовый класс для всех парсеров."""

    @abstractmethod
    def parse(self, search_query: str) -> List[VacancyDTO]:
        """
        Абстрактный метод для парсинга вакансий.

        Args:
            search_query: Поисковый запрос (например, "Python Developer").

        Returns:
            Список объектов VacancyDTO.
        """
        raise NotImplementedError
