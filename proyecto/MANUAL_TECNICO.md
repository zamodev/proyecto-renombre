# Manual Técnico — File MVP (Renombrador Documental)

## 1. Descripción General

**File MVP** es un servicio Python que monitorea carpetas en tiempo real, valida los nombres de los archivos entrantes contra un estándar documental configurable, aplica autocorrecciones conocidas y mueve los archivos válidos a una carpeta destino. Los archivos que no cumplen el estándar se dejan en origen con un registro del motivo de rechazo.

---

## 2. Requisitos del Sistema

| Componente | Versión mínima |
|---|---|
| Python | 3.9.12 |
| watchdog | 4.0.1 |

Instalación de dependencias:

```bash
pip install -r requirements.txt
```

---

## 3. Instalación y Ejecución

Desde la carpeta `proyecto/`:

```bash
py -m app.main
```

La aplicación carga `config.json`, construye un watcher por cada entrada en `watchers` y se mantiene activa hasta `Ctrl+C`.

---

## 4. Estructura de Módulos

```
proyecto/
├── config.json              # Configuración de watchers y perfiles de reglas
├── requirements.txt
└── app/
    ├── main.py              # Punto de entrada: carga config, crea watchers
    ├── config_loader.py     # Lee y valida config.json
    ├── config_models.py     # Dataclasses tipados: RuleProfile, DocumentTypeRule, etc.
    ├── models.py            # FileContext y ProcessingStatus
    ├── processor.py         # FileProcessor: ejecuta el pipeline sobre un archivo
    ├── registry.py          # STRATEGY_REGISTRY: mapeo nombre → clase
    ├── watcher.py           # DirectoryWatcher + FileHandler (integración watchdog)
    ├── watcher_manager.py   # WatcherManager: ciclo de vida de los watchers
    ├── exceptions.py        # Jerarquía de excepciones propias
    └── strategies/
        ├── base.py                      # Interfaz FileStrategy (ABC)
        ├── normalize_filename.py        # Paso 1 del pipeline
        ├── apply_pattern_fixes.py       # Paso 2
        ├── resolve_alias.py             # Paso 3
        ├── parse_document_name.py       # Paso 4
        ├── build_canonical_name.py      # Paso 5
        ├── validate_business_rules.py   # Paso 6
        ├── remove_spaces.py             # Estrategia auxiliar
        ├── uppercase_name.py            # Estrategia auxiliar
        ├── validate_extension.py        # Estrategia auxiliar
        └── validate_filename_pattern.py # Estrategia auxiliar
```

### Responsabilidad de cada módulo clave

| Módulo | Responsabilidad |
|---|---|
| `main.py` | Orquesta la inicialización completa |
| `config_loader.py` | Deserializa `config.json` a objetos tipados |
| `processor.py` | Aplica las estrategias en cadena y mueve el archivo |
| `watcher.py` | Escucha eventos del sistema de archivos (creación/movimiento) |
| `watcher_manager.py` | Administra el ciclo de vida de múltiples watchers |
| `registry.py` | Resuelve el nombre de una estrategia a su clase Python |
| `models.py` | `FileContext`: estado mutable del archivo en el pipeline |

---

## 5. Pipeline de Procesamiento

El pipeline se ejecuta secuencialmente sobre cada archivo detectado. Cada estrategia recibe un `FileContext` y devuelve un `FileContext` (posiblemente modificado).

```
Archivo detectado
      │
      ▼
[FileHandler] verifica estabilidad del archivo (tamaño estable N veces)
      │
      ▼
[FileProcessor.process()]
      │
      ├─ 1. NormalizeFilenameStrategy
      │       → mayúsculas, reemplaza guiones/espacios por _, colapsa __ múltiples,
      │         elimina caracteres especiales, elimina prefijos de ruido
      │
      ├─ 2. ApplyPatternFixesStrategy
      │       → aplica reglas regex configurables para corregir errores estructurales
      │         (ej. "EMBRQL..." → "ASEMB_RQL...")
      │
      ├─ 3. ResolveAliasStrategy
      │       → reemplaza aliases configurados en el tipo documental
      │         (ej. "AS_EMB" → "ASEMB")
      │
      ├─ 4. ParseDocumentNameStrategy
      │       → separa el nombre en tokens: [tipo_documental, RUB, cédula/fecha]
      │         y rellena document_type, rub, cedula en el contexto
      │
      ├─ 5. BuildCanonicalNameStrategy
      │       → reconstruye el nombre en formato estándar a partir de los tokens
      │
      └─ 6. ValidateBusinessRulesStrategy
              → valida: tipo documental conocido, RUB contra patrones regex,
                cédula requerida/formato, extensión permitida
              → si hay errores → status = REJECTED
              → si hubo fixes → status = AUTO_FIXED
              → si todo OK → status = VALID
      │
      ▼
┌─ REJECTED → archivo permanece en origen, se registra el motivo
└─ VALID / AUTO_FIXED → shutil.move() al destino configurado
```

### Verificación de estabilidad de archivos

Antes de procesar, `FileHandler._wait_until_stable()` verifica que el tamaño del archivo no cambie durante `stability_checks` intervalos de `stable_wait_seconds` segundos. Esto evita procesar archivos que todavía se están copiando.

---

## 6. Configuración (`config.json`)

### Estructura de alto nivel

```json
{
  "watchers": [ ... ],
  "rule_profiles": { ... }
}
```

### Sección `watchers`

Cada watcher define una carpeta monitoreada:

| Campo | Tipo | Descripción |
|---|---|---|
| `name` | string | Identificador del watcher (para logs) |
| `watch_path` | string | Carpeta origen a monitorear |
| `destination_path` | string | Carpeta destino para archivos válidos |
| `rules_profile` | string | Nombre del perfil de reglas a usar |
| `process_existing_on_startup` | bool | Si procesa archivos ya existentes al iniciar |
| `recursive` | bool | Si monitorea subcarpetas |
| `stable_wait_seconds` | int | Segundos entre chequeos de estabilidad |
| `stability_checks` | int | Número de chequeos iguales para considerar estable |

### Sección `rule_profiles`

Cada perfil define las reglas documentales reutilizables:

**`document_types`** — tipos documentales válidos:

```json
"ASEMB": {
  "requires_cedula": true,
  "default_extension": ".zip",
  "allowed_extensions": [".zip", ".pdf"]
}
```

**`rub_patterns`** — expresiones regulares que el RUB debe cumplir:

```json
["^RL\\d{8}$", "^RQL\\d{12}$"]
```

**`cedula_pattern`** — regex para validar cédula: `"^\\d{6,12}$"`

**`pattern_fixes`** — reglas de autocorrección estructural (regex):

```json
{
  "name": "emb_compacto_con_rub_y_cedula",
  "match": "...",
  "replace": "...",
  "description": "Corrige EMBRQL... → ASEMB_RQL...",
  "enabled": true
}
```

**`aliases`** — mapeo de alias documentales a tipo canónico:

```json
{ "AS_EMB": "ASEMB", "CR_EMB": "CREMB" }
```

**`cleanup_rules`** — limpieza mecánica del nombre:

```json
{
  "uppercase": true,
  "replace_spaces_with_underscore": true,
  "replace_hyphen_with_underscore": true,
  "collapse_multiple_underscores": true,
  "remove_special_characters": true,
  "remove_prefixes": ["COPIA_"]
}
```

**`autofix_policy`** — qué autocorrecciones están permitidas:

```json
{
  "allow_pattern_fixes": true,
  "allow_alias_fix": true,
  "allow_separator_fix": true,
  "allow_case_fix": true,
  "allow_extension_normalization": false,
  "allow_rub_guessing": false
}
```

---

## 7. Modelos de Datos

### `FileContext`

Estado mutable del archivo a lo largo del pipeline:

| Atributo | Tipo | Descripción |
|---|---|---|
| `source_path` | `Path` | Ruta original del archivo |
| `filename` | `str` | Nombre actual (puede cambiar) |
| `original_filename` | `str` | Nombre inmutable de origen |
| `tokens` | `list[str]` | Segmentos del nombre separados por `_` |
| `document_type` | `str?` | Tipo documental identificado |
| `rub` | `str?` | RUB extraído |
| `cedula` | `str?` | Cédula extraída |
| `fecha` | `str?` | Fecha extraída |
| `fixes_applied` | `list[str]` | Correcciones aplicadas (para auditoría) |
| `validation_errors` | `list[str]` | Errores encontrados |
| `status` | `str` | `PENDING` / `VALID` / `AUTO_FIXED` / `REJECTED` |

### `ProcessingStatus`

| Valor | Significado |
|---|---|
| `PENDING` | Aún no procesado |
| `VALID` | Cumple el estándar sin cambios |
| `AUTO_FIXED` | Se corrigió automáticamente y es válido |
| `REJECTED` | No cumple el estándar, permanece en origen |

---

## 8. Jerarquía de Excepciones

```
RenombradorError
├── ConfigurationError      → config.json inválido o faltante
├── StrategyBuildError      → nombre de estrategia desconocido o params inválidos
├── FileProcessingError     → error al procesar un archivo individual
└── FileStabilityError      → archivo no se estabilizó antes del timeout
```

Todos los errores son capturados en `FileHandler._handle_file()` y registrados con `logger.exception()` sin detener el watcher.

---

## 9. Logging

La aplicación usa el módulo estándar `logging` con nivel `INFO` por defecto. Formato:

```
2026-05-03 10:00:00,000 [INFO] app.processor: Archivo movido a: C:/destino/ASEMB_RQL123456789012_12345678.zip
2026-05-03 10:00:01,000 [WARNING] app.processor: Archivo rechazado: NOMBREDOC.pdf. Motivos: El RUB 'XX' no cumple los formatos permitidos.
```

---

## 10. Guía para Agregar una Nueva Estrategia

1. **Crear el archivo** en `app/strategies/mi_nueva_estrategia.py`:

```python
from app.models import FileContext, ProcessingStatus
from app.strategies.base import FileStrategy

class MiNuevaEstrategia(FileStrategy):
    def apply(self, context: FileContext) -> FileContext:
        if context.status == ProcessingStatus.REJECTED:
            return context
        # lógica aquí
        return context
```

2. **Registrarla** en `app/registry.py`:

```python
from app.strategies.mi_nueva_estrategia import MiNuevaEstrategia

STRATEGY_REGISTRY = {
    ...
    "MiNuevaEstrategia": MiNuevaEstrategia,
}
```

3. Si necesita acceso al `RuleProfile`, agregarla también a `PROFILE_AWARE_STRATEGIES` en `registry.py`. El constructor debe aceptar `rule_profile` como parámetro.

4. **Activarla** en `config.json` dentro del pipeline del watcher deseado:

```json
"strategies": [
  { "name": "NormalizeFilenameStrategy", "params": {} },
  { "name": "MiNuevaEstrategia", "params": {} }
]
```
