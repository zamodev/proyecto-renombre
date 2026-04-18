"""Modelos tipados de configuración para la aplicación."""

import re
from dataclasses import dataclass
from typing import Optional

from app.exceptions import ConfigurationError


DEFAULT_PIPELINE = [
    {"name": "NormalizeFilenameStrategy", "params": {}},
    {"name": "ApplyPatternFixesStrategy", "params": {}},
    {"name": "ResolveAliasStrategy", "params": {}},
    {"name": "ParseDocumentNameStrategy", "params": {}},
    {"name": "BuildCanonicalNameStrategy", "params": {}},
    {"name": "ValidateBusinessRulesStrategy", "params": {}},
]


@dataclass(frozen=True)
class PatternFixRule:
    """Regla de autocorrección estructural basada en expresiones regulares."""

    name: str
    match: str
    replace: str
    description: str = ""
    enabled: bool = True

    def compiled_match(self) -> re.Pattern[str]:
        """Compila y devuelve el patrón de búsqueda de la regla."""

        return re.compile(self.match)


@dataclass(frozen=True)
class CleanupRules:
    """Reglas de limpieza mecánica aplicadas al nombre del archivo."""

    uppercase: bool = True
    replace_spaces_with_underscore: bool = True
    replace_hyphen_with_underscore: bool = True
    collapse_multiple_underscores: bool = True
    remove_special_characters: bool = True
    remove_prefixes: tuple[str, ...] = ()


@dataclass(frozen=True)
class AutoFixPolicy:
    """Políticas de autocorrección permitidas para el perfil."""

    allow_pattern_fixes: bool = True
    allow_alias_fix: bool = True
    allow_separator_fix: bool = True
    allow_case_fix: bool = True
    allow_special_character_fix: bool = True
    allow_extension_normalization: bool = False
    allow_rub_guessing: bool = False
    allow_cedula_guessing: bool = False


@dataclass(frozen=True)
class DocumentTypeRule:
    """Reglas de negocio para un tipo documental."""

    name: str
    requires_cedula: bool
    default_extension: str
    allowed_extensions: tuple[str, ...]


@dataclass(frozen=True)
class RuleProfile:
    """Perfil reutilizable con reglas documentales y autocorrecciones."""

    name: str
    document_types: dict[str, DocumentTypeRule]
    rub_patterns: tuple[str, ...]
    cedula_pattern: str
    pattern_fixes: tuple[PatternFixRule, ...]
    alias_map: dict[str, str]
    cleanup_rules: CleanupRules
    auto_fix_policy: AutoFixPolicy

    def compiled_rub_patterns(self) -> tuple[re.Pattern[str], ...]:
        """Compila y devuelve las expresiones regulares válidas para RUB."""

        return tuple(re.compile(pattern) for pattern in self.rub_patterns)

    def compiled_cedula_pattern(self) -> re.Pattern[str]:
        """Compila y devuelve la expresión regular de cédula."""

        return re.compile(self.cedula_pattern)


@dataclass(frozen=True)
class WatchProfile:
    """Configuración de una sola carpeta vigilada."""

    name: str
    watch_path: str
    destination_path: str
    rules_profile: Optional[str] = None
    strategies: Optional[list[dict]] = None
    process_existing_on_startup: bool = True
    recursive: bool = False
    stable_wait_seconds: int = 1
    stability_checks: int = 3


@dataclass(frozen=True)
class AppConfig:
    """Configuración principal de la aplicación."""

    watchers: list[WatchProfile]
    rule_profiles: dict[str, RuleProfile]

    @classmethod
    def from_dict(cls, data: dict) -> "AppConfig":
        if not isinstance(data, dict):
            raise ConfigurationError("La configuración debe ser un objeto JSON válido.")

        watchers_data = data.get("watchers")
        if not isinstance(watchers_data, list) or not watchers_data:
            raise ConfigurationError("'watchers' debe ser una lista no vacía.")

        profiles_data = data.get("rule_profiles", {})
        if not isinstance(profiles_data, dict):
            raise ConfigurationError("'rule_profiles' debe ser un objeto JSON.")

        rule_profiles = {
            name: _build_rule_profile(name, profile_data)
            for name, profile_data in profiles_data.items()
        }

        watchers = [
            _build_watch_profile(watcher_data, index=index, rule_profiles=rule_profiles)
            for index, watcher_data in enumerate(watchers_data, start=1)
        ]
        return cls(watchers=watchers, rule_profiles=rule_profiles)


def _build_watch_profile(
    data: dict,
    index: int,
    rule_profiles: dict[str, RuleProfile],
) -> WatchProfile:
    if not isinstance(data, dict):
        raise ConfigurationError(f"La entrada del watcher {index} debe ser un objeto JSON.")

    name = data.get("name") or f"watcher-{index}"
    watch_path = data.get("watch_path")
    destination_path = data.get("destination_path")
    rules_profile = data.get("rules_profile")
    strategies = data.get("strategies")

    if not watch_path or not destination_path:
        raise ConfigurationError(
            f"El watcher '{name}' debe incluir 'watch_path' y 'destination_path'."
        )

    if rules_profile and rules_profile not in rule_profiles:
        raise ConfigurationError(
            f"El watcher '{name}' referencia el perfil inexistente '{rules_profile}'."
        )

    if strategies is not None and (not isinstance(strategies, list) or not strategies):
        raise ConfigurationError(
            f"El watcher '{name}' debe definir una lista válida de estrategias si la informa."
        )

    if strategies is None and rules_profile is not None:
        strategies = list(DEFAULT_PIPELINE)

    if strategies is None:
        raise ConfigurationError(
            f"El watcher '{name}' debe definir estrategias o un 'rules_profile'."
        )

    return WatchProfile(
        name=name,
        watch_path=watch_path,
        destination_path=destination_path,
        rules_profile=rules_profile,
        strategies=strategies,
        process_existing_on_startup=bool(data.get("process_existing_on_startup", True)),
        recursive=bool(data.get("recursive", False)),
        stable_wait_seconds=int(data.get("stable_wait_seconds", 1)),
        stability_checks=int(data.get("stability_checks", 3)),
    )


def _build_rule_profile(name: str, data: dict) -> RuleProfile:
    if not isinstance(data, dict):
        raise ConfigurationError(f"El perfil '{name}' debe ser un objeto JSON.")

    document_types_data = data.get("document_types")
    rub_patterns_data = data.get("rub_patterns")
    cedula_pattern = data.get("cedula_pattern", r"^\d{6,12}$")
    alias_map_data = data.get("alias_map", {})
    pattern_fixes_data = data.get("pattern_fixes", [])
    cleanup_rules_data = data.get("cleanup_rules", {})
    auto_fix_policy_data = data.get("auto_fix_policy", {})

    if not isinstance(document_types_data, dict) or not document_types_data:
        raise ConfigurationError(
            f"El perfil '{name}' debe definir al menos un tipo documental en 'document_types'."
        )

    if not isinstance(rub_patterns_data, list) or not rub_patterns_data:
        raise ConfigurationError(
            f"El perfil '{name}' debe definir una lista no vacía en 'rub_patterns'."
        )

    document_types = {
        doc_name.upper(): _build_document_type_rule(doc_name.upper(), doc_data)
        for doc_name, doc_data in document_types_data.items()
    }

    alias_map = {
        alias.upper(): value.upper()
        for alias, value in alias_map_data.items()
    }

    if not isinstance(pattern_fixes_data, list):
        raise ConfigurationError(
            f"El perfil '{name}' debe definir 'pattern_fixes' como una lista si lo informa."
        )

    pattern_fixes = tuple(
        _build_pattern_fix_rule(index=index, data=pattern_fix_data)
        for index, pattern_fix_data in enumerate(pattern_fixes_data, start=1)
    )

    cleanup_rules = CleanupRules(
        uppercase=bool(cleanup_rules_data.get("uppercase", True)),
        replace_spaces_with_underscore=bool(
            cleanup_rules_data.get("replace_spaces_with_underscore", True)
        ),
        replace_hyphen_with_underscore=bool(
            cleanup_rules_data.get("replace_hyphen_with_underscore", True)
        ),
        collapse_multiple_underscores=bool(
            cleanup_rules_data.get("collapse_multiple_underscores", True)
        ),
        remove_special_characters=bool(
            cleanup_rules_data.get("remove_special_characters", True)
        ),
        remove_prefixes=tuple(
            prefix.upper() for prefix in cleanup_rules_data.get("remove_prefixes", [])
        ),
    )

    auto_fix_policy = AutoFixPolicy(
        allow_pattern_fixes=bool(auto_fix_policy_data.get("allow_pattern_fixes", True)),
        allow_alias_fix=bool(auto_fix_policy_data.get("allow_alias_fix", True)),
        allow_separator_fix=bool(auto_fix_policy_data.get("allow_separator_fix", True)),
        allow_case_fix=bool(auto_fix_policy_data.get("allow_case_fix", True)),
        allow_special_character_fix=bool(
            auto_fix_policy_data.get("allow_special_character_fix", True)
        ),
        allow_extension_normalization=bool(
            auto_fix_policy_data.get("allow_extension_normalization", False)
        ),
        allow_rub_guessing=bool(auto_fix_policy_data.get("allow_rub_guessing", False)),
        allow_cedula_guessing=bool(auto_fix_policy_data.get("allow_cedula_guessing", False)),
    )

    return RuleProfile(
        name=name,
        document_types=document_types,
        rub_patterns=tuple(rub_patterns_data),
        cedula_pattern=cedula_pattern,
        pattern_fixes=pattern_fixes,
        alias_map=alias_map,
        cleanup_rules=cleanup_rules,
        auto_fix_policy=auto_fix_policy,
    )


def _build_pattern_fix_rule(index: int, data: dict) -> PatternFixRule:
    if not isinstance(data, dict):
        raise ConfigurationError(
            f"La regla pattern_fixes #{index} debe ser un objeto JSON."
        )

    name = str(data.get("name") or f"pattern_fix_{index}")
    match = str(data.get("match", ""))
    replace = str(data.get("replace", ""))
    description = str(data.get("description", ""))
    enabled = bool(data.get("enabled", True))

    if not match:
        raise ConfigurationError(
            f"La regla pattern_fixes '{name}' debe incluir el campo 'match'."
        )

    try:
        re.compile(match)
    except re.error as exc:
        raise ConfigurationError(
            f"La regla pattern_fixes '{name}' tiene una expresión regular inválida."
        ) from exc

    if not replace:
        raise ConfigurationError(
            f"La regla pattern_fixes '{name}' debe incluir el campo 'replace'."
        )

    return PatternFixRule(
        name=name,
        match=match,
        replace=replace,
        description=description,
        enabled=enabled,
    )


def _build_document_type_rule(name: str, data: dict) -> DocumentTypeRule:
    if not isinstance(data, dict):
        raise ConfigurationError(f"El tipo documental '{name}' debe ser un objeto JSON.")

    default_extension = str(data.get("default_extension", "")).lower()
    allowed_extensions_data = data.get("allowed_extensions", [])

    if not default_extension.startswith("."):
        raise ConfigurationError(
            f"El tipo documental '{name}' debe incluir un 'default_extension' válido."
        )

    if not isinstance(allowed_extensions_data, list) or not allowed_extensions_data:
        raise ConfigurationError(
            f"El tipo documental '{name}' debe definir 'allowed_extensions'."
        )

    allowed_extensions = tuple(str(extension).lower() for extension in allowed_extensions_data)

    return DocumentTypeRule(
        name=name,
        requires_cedula=bool(data.get("requires_cedula", True)),
        default_extension=default_extension,
        allowed_extensions=allowed_extensions,
    )
