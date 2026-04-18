"""Punto de entrada de la aplicación."""

import logging

from app.config_loader import load_config
from app.processor import FileProcessor
from app.watcher import DirectoryWatcher
from app.watcher_manager import WatcherManager


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def build_watchers(config):
    """Crea un watcher por cada carpeta configurada."""

    watchers = []

    for profile in config.watchers:
        rule_profile = config.rule_profiles.get(profile.rules_profile) if profile.rules_profile else None

        processor = FileProcessor(
            destination_path=profile.destination_path,
            strategies_config=profile.strategies,
            rule_profile=rule_profile,
        )

        watchers.append(
            DirectoryWatcher(
                name=profile.name,
                watch_path=profile.watch_path,
                processor=processor,
                process_existing_on_startup=profile.process_existing_on_startup,
                recursive=profile.recursive,
                stable_wait_seconds=profile.stable_wait_seconds,
                stability_checks=profile.stability_checks,
            )
        )

    return watchers


def main():
    """Carga la configuración, inicia todos los watchers y mantiene viva la app."""

    config = load_config("config.json")
    watchers = build_watchers(config)
    manager = WatcherManager(watchers)
    manager.run_forever()


if __name__ == "__main__":
    main()
