import logging
from typing import Dict, List

import pytest  # type: ignore

from inveniautils.logging.formatters import CustomFormatter
from inveniautils.logging.handlers import CustomHandler
from tests.test_logging.utils import create_record


class TestCustomHandler:
    def test_init(self) -> None:
        handler: CustomHandler = CustomHandler(
            global_metadata={"ship": "Ever Given", "volcano": "Fagradalsfjall"}
        )

        assert len(handler.global_metadata) == 2
        assert handler.global_metadata["ship"] == "Ever Given"
        assert handler.global_metadata["volcano"] == "Fagradalsfjall"

    def test_set_metadata(self) -> None:
        cereals: List[str] = ["teff", "pearl millet", "spelt"]
        handler: CustomHandler = CustomHandler()

        handler.set_global_metadata(cereals=cereals, food=True)

        assert len(handler.global_metadata) == 2
        assert handler.global_metadata["cereals"] == cereals
        assert handler.global_metadata["food"]

    def test_overwrite_metadata(self) -> None:
        bibliophiles: List[str] = [
            "Jaques-Auguste de Thou",
            "Demetrio Canevari",
            "Diane de Poitiers",
        ]

        handler: CustomHandler = CustomHandler(
            global_metadata={"bibliophiles": [], "books": "Small Gods"}
        )
        handler.set_global_metadata(
            bibliophiles=bibliophiles, books="Cats Are Not Peas"
        )

        assert len(handler.global_metadata) == 2
        assert handler.global_metadata["bibliophiles"] == bibliophiles
        assert handler.global_metadata["books"] == "Cats Are Not Peas"

    def test_find_metadata(self) -> None:
        warblers: List[str] = ["Wilsonia", "Vermivora", "Myioborus"]
        owls: List[str] = ["Strigidae", "Tytonidae"]

        handler: CustomHandler = CustomHandler(
            global_metadata={"warblers": warblers, "owls": owls}
        )

        assert handler.find_global_metadata("warblers") == warblers
        assert handler.find_global_metadata("owls") == owls
        assert handler.find_global_metadata("penguins") is None

    def test_list_global_metadata(self) -> None:
        synonyms: Dict[str, List[str]] = {
            "saunter": ["stroll", "mosey"],
            "otiose": ["indolent", "idle"],
        }
        best_adjective: str = "best"

        handler: CustomHandler = CustomHandler(
            global_metadata={"synonyms": synonyms, "best_adjective": best_adjective}
        )

        assert handler.list_global_metadata() == [
            ("synonyms", synonyms),
            ("best_adjective", best_adjective),
        ]

    def test_reset_global_metadata(self) -> None:
        handler: CustomHandler = CustomHandler(
            global_metadata={"carracks": ["Victoria", "Great Michael", "Grace Dieu"]}
        )

        handler.reset_global_metadata()

        assert handler.global_metadata == {}

    def test_format_default(self) -> None:
        record: logging.LogRecord = create_record(
            "test_logger",
            20,
            "parliaments/UK.py",
            1710,
            "statutes created",
            (),
            "init_statutes",
        )

        handler: CustomHandler = CustomHandler(
            global_metadata={"statutes": ["Statute of Anne", "Statute of Mortmain"]}
        )
        output: str = handler.format(record)

        assert output == "statutes created\n['Statute of Anne', 'Statute of Mortmain']"

    def test_format_standard_formatter(self) -> None:
        record: logging.LogRecord = create_record(
            "test_logger",
            20,
            "businesses/bakery.py",
            175,
            "menu created",
            (),
            "create menu",
        )
        formatter: logging.Formatter = logging.Formatter()

        handler: CustomHandler = CustomHandler(
            global_metadata={"baked goods": ["Chocolate Cake", "Muffin", "Hardtack"]}
        )
        handler.setFormatter(formatter)
        output: str = handler.format(record)

        assert output == "menu created"

    def test_format_custom_formatter(self) -> None:
        record: logging.LogRecord = create_record(
            "test_logger",
            20,
            "fancy/pigeons.py",
            175,
            "pigeons fancied",
            (),
            "fancy pigeons",
        )
        formatter: CustomFormatter = CustomFormatter()

        handler: CustomHandler = CustomHandler(
            global_metadata={"fancy pigeons": ["Trumpeter", "Dragoon", "Pouter"]}
        )
        handler.setFormatter(formatter)
        output: str = handler.format(record)

        assert output == "pigeons fancied\n['Trumpeter', 'Dragoon', 'Pouter']"

    def test_emit(self) -> None:
        handler: CustomHandler = CustomHandler()

        record: logging.LogRecord = logging.LogRecord(
            "test", 10, "test", 10, "test", tuple(), None
        )

        with pytest.raises(NotImplementedError):
            handler.emit(record)
