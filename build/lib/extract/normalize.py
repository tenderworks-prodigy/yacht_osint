import logging

BUILDER_MAP = {
    "Feadship": ["Koninklijke De Vries", "Royal Van Lent"],
    "Oceanco": [],
    "Lürssen Yachts": [],
    "Xtenders": ["X-Tenders", "Xtenders B.V."],
    "Compass Tenders": ["Compass"],
}


def normalize_builder(name: str) -> str:
    for canonical, aliases in BUILDER_MAP.items():
        if name == canonical or name in aliases:
            return canonical
    return name


def run():
    logging.getLogger(__name__).info("stub")
