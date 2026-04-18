"""Excepciones personalizadas para la aplicación renombrador."""


class RenombradorError(Exception):
    """Excepción base para todos los errores específicos de la aplicación."""


class ConfigurationError(RenombradorError):
    """Se lanza cuando el archivo de configuración falta o es inválido."""


class StrategyBuildError(RenombradorError):
    """Se lanza cuando no se puede crear una estrategia desde la configuración."""


class FileProcessingError(RenombradorError):
    """Se lanza cuando un archivo no se puede validar, renombrar o mover."""


class FileStabilityError(RenombradorError):
    """Se lanza cuando un archivo no está lo bastante estable para procesarse con seguridad."""