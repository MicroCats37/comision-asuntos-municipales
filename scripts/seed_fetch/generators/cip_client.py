"""Cliente HTTP para el endpoint de colegiados (CIP)."""

import time

import requests


class CipClient:
    """Cliente reutilizable para consultar el endpoint CIP.

    Uso:
        client = CipClient("http://host:port/api/v1/colegiado/{cip}")
        data = client.fetch("012345")
    """

    def __init__(self, endpoint_url: str, timeout: int = 30, delay: float = 0.3):
        self.endpoint_url = endpoint_url
        self.timeout = timeout
        self.delay = delay
        self.session = requests.Session()

    def fetch(self, cip: str) -> dict:
        """Consulta un CIP y devuelve el JSON del colegiado."""
        url = self.endpoint_url.format(cip=cip)
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        time.sleep(self.delay)
        return resp.json()

    def fetch_many(self, cips: list[str], skip_errors: bool = False) -> tuple[list[dict], list[dict]]:
        """Consulta varios CIPs. Devuelve (data_ok, errors)."""
        data: list[dict] = []
        errors: list[dict] = []
        for i, cip in enumerate(cips, 1):
            try:
                data.append(self.fetch(cip))
                print(f"[{i}/{len(cips)}] OK {cip}")
            except Exception as exc:  # noqa: BLE001
                errors.append({"cip": cip, "error": str(exc)})
                print(f"[{i}/{len(cips)}] ERROR {cip}: {exc}")
                if not skip_errors:
                    raise
        return data, errors
