import json
from django.http import HttpRequest
from .utils import hydrate_and_clean_payload

def extract_and_hydrate_payload(request: HttpRequest) -> dict:
    """
    Dependencia que unifica el procesamiento del Request para obtener un dict limpio.
    """
    content_type = getattr(request, 'content_type', None) or request.META.get('CONTENT_TYPE', '')

    # 1. Caso JSON Puro
    if 'application/json' in content_type:
        payload = json.loads(request.body) if request.body else {}
        return hydrate_and_clean_payload(payload, {})

    # 2. Caso Multipart o Form-Encoded con protocolo 'data'
    data_str = request.POST.get('data')
    if data_str:
        try:
            payload = json.loads(data_str)
            return hydrate_and_clean_payload(payload, request.FILES)
        except ValueError:
            from ninja.errors import HttpError
            raise HttpError(400, "El campo 'data' no es un JSON válido.")

    # 3. Caso Formulario tradicional (sin campo 'data')
    return hydrate_and_clean_payload(request.POST.dict(), request.FILES)
