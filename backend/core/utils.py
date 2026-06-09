import re
import json
import logging
from typing import Any, Dict
from ninja.errors import HttpError
from django.core.files.uploadedfile import UploadedFile

# Configuración del logger para rastrear errores de hidratación
logger = logging.getLogger(__name__)

# Patrón estricto para validar que las claves de archivos sean 'file_' seguido de un UUID
FILE_KEY_PATTERN = re.compile(r"^file_[A-Za-z0-9_-]+$")


def parse_grouped_files(request_files: Any) -> dict:
    """
    Decodifica el array unificado de archivos enviados bajo la llave 'files'.
    El frontend codifica el token dentro del nombre del archivo como:
    'file_uuid___nombre_real.ext'.
    
    Extrae el token para la hidratación y restaura el nombre del archivo
    para el guardado en base de datos.
    """
    mapped_files = {}
    
    # 1. Si los archivos vienen como un array en la llave maestra "files"
    if "files" in request_files:
        # En Django request.FILES.getlist() extrae el array completo de MultiValueDict
        files_list = request_files.getlist("files") if hasattr(request_files, "getlist") else request_files["files"]
        # En caso files_list no sea iterable (por si acaso request_files es dict simple o parecido)
        if not isinstance(files_list, list):
            files_list = [files_list]

        for f in files_list:
            if hasattr(f, "name") and f.name and "___" in f.name:
                token, real_name = f.name.split("___", 1)
                f.name = real_name # Restauramos el nombre original visible a Django
                mapped_files[token] = f
            else:
                # Fallback, just in case
                name = getattr(f, "name", "unknown")
                mapped_files[name] = f
                
    # 2. Agregar cualquier archivo subido con la estrategia legacy / llaves separadas
    for k, v in request_files.items():
        if k != "files":
            mapped_files[k] = v

    return mapped_files


def hydrate_and_clean_payload(node: Any, request_files: Any) -> Any:
    """
    Formateador central recursivo para procesar Payloads de entrada:
    1. Limpieza: Convierte strings vacíos o con solo espacios en None.
    2. Hidratación: Reemplaza strings 'file_<uuid>' por objetos UploadedFile reales.
    3. Auto-Parseo: Si un campo llega como string pero parece JSON, intenta parsearlo.
    """
    # Siempre procesamos los archivos para garantizar que el dict está listo
    mapped_files = request_files if isinstance(request_files, dict) and not hasattr(request_files, "getlist") else parse_grouped_files(request_files)

    def _hydrate(subnode: Any) -> Any:
        if isinstance(subnode, dict):
            return {k: _hydrate(v) for k, v in subnode.items()}

        if isinstance(subnode, list):
            return [_hydrate(i) for i in subnode]

        if isinstance(subnode, str):
            if not subnode.strip():
                return None

            if FILE_KEY_PATTERN.match(subnode):
                if subnode not in mapped_files:
                    raise HttpError(
                        400,
                        f"Referencia de archivo rota: '{subnode}' no se encontró en la petición.",
                    )
                return mapped_files[subnode]

            if (subnode.startswith("{") and subnode.endswith("}")) or (
                subnode.startswith("[") and subnode.endswith("]")
            ):
                try:
                    parsed = json.loads(subnode)
                    return _hydrate(parsed)
                except (ValueError, TypeError):
                    pass

        return subnode

    return _hydrate(node)


def format_errors(exc_errors: list) -> Dict[str, str]:
    """
    Transforma la lista de errores de Pydantic en un diccionario plano
    que el frontend puede mapear directamente a sus inputs.

    Ejemplo: {"email": "formato de correo inválido"}
    """
    flattened = {}
    for error in exc_errors:
        loc = error.get("loc", [])
        field_name = str(loc[-1]) if loc else "non_field_errors"
        msg = error.get("msg", "Dato inválido")

        flattened[field_name] = msg

    return flattened
