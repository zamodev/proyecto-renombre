"""Estrategia que convierte a mayúsculas el nombre base del archivo."""

from app.models import FileContext
from app.strategies.base import FileStrategy


class UppercaseNameStrategy(FileStrategy):
    """Convierte a mayúsculas el nombre base del archivo y conserva la extensión."""

    def apply(self, context: FileContext) -> FileContext:
        context.update_filename(f"{context.stem.upper()}{context.suffix}")
        return context
