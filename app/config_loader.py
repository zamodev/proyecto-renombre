"""Carga y valida el archivo de configuración de la aplicación."""

import json
from pathlib import Path

from app.config_models import AppConfig
from app.exceptions import ConfigurationError


def load_config(config_path: str = "config.json") -> AppConfig:
    """Lee un archivo JSON y lo convierte en una configuración tipada."""

    path = Path(config_path)

    if not path.exists():
        raise ConfigurationError(f"No existe el archivo de configuración: {config_path}")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    return AppConfig.from_dict(data)
