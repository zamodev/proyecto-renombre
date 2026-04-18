"""Estrategia que valida el nombre final del archivo contra una expresión regular."""

import re

from app.models import FileContext
from app.strategies.base import FileStrategy


class ValidateFilenamePatternStrategy(FileStrategy):
    """Rechaza archivos cuyo nombre final no coincide con el patrón configurado."""

    def __init__(self, pattern: str):
        self.pattern = re.compile(pattern)

    def apply(self, context: FileContext) -> FileContext:
        if not self.pattern.fullmatch(context.filename):
            raise ValueError(
                f"Nombre de archivo no válido: {context.filename}. "
                f"Debe cumplir el patrón: {self.pattern.pattern}"
            )
        return context
