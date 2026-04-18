"""Estrategia que reemplaza espacios por guiones bajos en el nombre del archivo."""

from app.models import FileContext
from app.strategies.base import FileStrategy


class RemoveSpacesStrategy(FileStrategy):
    """Normaliza el nombre base del archivo reemplazando espacios por guiones bajos."""

    def apply(self, context: FileContext) -> FileContext:
        new_stem = context.stem.replace(" ", "_")
        context.update_filename(f"{new_stem}{context.suffix}")
        return context
