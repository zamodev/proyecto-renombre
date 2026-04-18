"""Estrategia que acepta únicamente extensiones de archivo permitidas."""

from app.models import FileContext
from app.strategies.base import FileStrategy


class ValidateExtensionStrategy(FileStrategy):
    """Rechaza archivos cuya extensión no está permitida explícitamente."""

    def __init__(self, allowed_extensions: list[str]):
        self.allowed_extensions = {ext.lower() for ext in allowed_extensions}

    def apply(self, context: FileContext) -> FileContext:
        if context.suffix not in self.allowed_extensions:
            raise ValueError(
                f"Extensión no permitida: {context.suffix}. "
                f"Permitidas: {sorted(self.allowed_extensions)}"
            )
        return context
