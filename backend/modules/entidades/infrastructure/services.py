"""
Infrastructure Services — Implementaciones de puertos para servicios externos.

- SunatClientSimulator: Simulador con datos mock para desarrollo
- ReniecClientSimulator: Simulador con datos mock para desarrollo

# TODO: Implementar clientes reales cuando se tengan las credenciales API:
# - RealSunatClient: Cliente real que consulta la API de SUNAT
# - RealReniecClient: Cliente real que consulta la API de RENIEC
"""

import hashlib
import random
from datetime import date

from ..domain.ports import ISunatClient, IReniecClient
from ..domain.results import SunatInstitucionResult, ReniecPersonaResult


class SunatClientSimulator(ISunatClient):
    """
    Simulador del cliente SUNAT con datos mock para desarrollo.

    Proporciona datos determinísticos para probar el flujo completo
    sin depender de la API real de SUNAT.

    - RUCs hardcoded tienen datos mock determinísticos existentes.
    - Cualquier otro RUC válido (11 dígitos) genera datos mock determinísticos
      basados en el RUC (mismo RUC siempre devuelve los mismos datos).
    """

    # Datos mock de instituciones — RUC válido de ejemplo
    _SIMULADOS = {
        "20492913151": {
            "ruc": "20492913151",
            "razon_social": "MUNICIPALIDAD PROVINCIAL DE LIMA",
            "nombre_comercial": "MPL",
            "estado": "ACTIVO",
            "tipo_contribuyente": "GOBIERNO LOCAL",
            "direccion": "AV. PCM S/N",
            "departamento": "LIMA",
            "provincia": "LIMA",
            "distrito": "LIMA",
        },
        "20131312957": {
            "ruc": "20131312957",
            "razon_social": "COLEGIO DE INGENIEROS DEL PERU",
            "nombre_comercial": "CIP",
            "estado": "ACTIVO",
            "tipo_contribuyente": "ORDENANZA",
            "direccion": "AV. REPUBLICA DE CHILE 356, LIMA",
            "departamento": "LIMA",
            "provincia": "LIMA",
            "distrito": "LIMA",
        },
        "20600099773": {
            "ruc": "20600099773",
            "razon_social": "CONSORCIO CAM LIMA NORTE",
            "nombre_comercial": "CAM LN",
            "estado": "ACTIVO",
            "tipo_contribuyente": "CONTRATISTA",
            "direccion": "AV. TUPAC AMARU 1234",
            "departamento": "LIMA",
            "provincia": "LIMA",
            "distrito": "INDEPENDENCIA",
        },
    }

    # Datos base para generación determinística
    _RAZONES_SOCIALES = [
        "EMPRESA CONSTRUCTORA",
        "SERVICIOS GENERALES",
        "INDUSTRIA MANUFACTURERA",
        "COMERCIO AL POR MAYOR",
        "COMERCIO AL POR MENOR",
        "TRANSPORTES Y LOGISTICA",
        "SERVICIOS PROFESIONALES",
        "AGRICULTURA Y GANADERIA",
        "PESCA Y ACUICULTURA",
        "MINERIA Y CANTERAS",
        "ENERGIA Y AGUA",
        "CONSTRUCCION",
        "HOSTELERIA Y RESTAURACION",
        "ACTIVIDADES INMOBILIARIAS",
        "EDUCACION",
        "SALUD",
        "ENTRETENIMIENTO",
        "ADMINISTRACION PUBLICA",
    ]

    _NOMBRES_COMERCIALES = [
        "ABC",
        "XYZ",
        "PRIMAX",
        "GRIFO",
        "PLAZA",
        "CENTRAL",
        "NORTE",
        "SUR",
        "ESTE",
        "OESTE",
    ]

    _ESTADOS = ["ACTIVO", "ACTIVO", "ACTIVO", "BAJA", "SUSPENSION"]
    _TIPOS_CONTRIBUYENTE = [
        "ORDENANZA",
        "GOBIERNO LOCAL",
        "GOBIERNO NACIONAL",
        "CONTRATISTA",
        "EMPRESA PRIVADA",
    ]
    _DEPARTAMENTOS = ["LIMA", "AREQUIPA", "CUSCO", "TRUJILLO", "PIURA", "ICA"]
    _PROVINCIAS = ["LIMA", "AREQUIPA", "CUSCO", "TRUJILLO", "PIURA", "ICA"]
    _DISTRITOS = ["LIMA", "MIRAFLORES", "SAN ISIDRO", "SURCO", "LA VICTORIA"]

    async def get_institucion(self, ruc: str) -> SunatInstitucionResult:
        """
        Simula la consulta de institución por RUC.

        Args:
            ruc: Número de RUC (11 dígitos).

        Returns:
            SunatInstitucionResult con datos mock.

        Note:
            - Si el RUC está en datos hardcoded, devuelve esos datos.
            - Para cualquier otro RUC válido de 11 dígitos, genera datos
              determinísticos basados en el RUC.
        """
        data = self._SIMULADOS.get(ruc)
        if data:
            return SunatInstitucionResult(**data)

        # Generar datos determinísticos para RUCs no hardcoded
        return self._generar_institucion_determinista(ruc)

    def _generar_institucion_determinista(self, ruc: str) -> SunatInstitucionResult:
        """
        Genera datos mock determinísticos basados en el RUC.

        Usa hash del RUC como seed para que el mismo RUC siempre
        devuelva los mismos datos.
        """
        # Crear seed determinístico a partir del RUC
        seed = int(hashlib.md5(ruc.encode()).hexdigest(), 16)
        rng = random.Random(seed)

        razon_social = f"{rng.choice(self._RAZONES_SOCIALES)} S.A.C."
        nombre_comercial = f"{rng.choice(self._NOMBRES_COMERCIALES)} {rng.randint(1, 999)}"
        estado = rng.choice(self._ESTADOS)
        tipo_contribuyente = rng.choice(self._TIPOS_CONTRIBUYENTE)

        # Generar dirección fake
        direccion = f"AV. {ruc[:4]} NRO. {rng.randint(100, 999)}"
        departamento = rng.choice(self._DEPARTAMENTOS)
        provincia = rng.choice(self._PROVINCIAS)
        distrito = rng.choice(self._DISTRITOS)

        return SunatInstitucionResult(
            ruc=ruc,
            razon_social=razon_social,
            nombre_comercial=nombre_comercial,
            estado=estado,
            tipo_contribuyente=tipo_contribuyente,
            direccion=direccion,
            departamento=departamento,
            provincia=provincia,
            distrito=distrito,
        )


class RealSunatClient(ISunatClient):
    """
    Cliente real que consulta la API de SUNAT.

    # TODO: Implementar cuando se tengan las credenciales y endpoint de la API SUNAT.
    Requiere:
    - SUNAT_API_BASE_URL en settings
    - Autenticación (API key o token OAuth)
    - Manejo de rate limiting
    """

    async def get_institucion(self, ruc: str) -> SunatInstitucionResult:
        """
        Consulta la API real de SUNAT.

        Raises:
            NotImplementedError: Aún no implementado.
        """
        raise NotImplementedError(
            "RealSunatClient aún no implementado. "
            "Usar SunatClientSimulator para desarrollo."
        )


class ReniecClientSimulator(IReniecClient):
    """
    Simulador del cliente RENIEC con datos mock para desarrollo.

    Proporciona datos determinísticos para probar el flujo completo
    sin depender de la API real de RENIEC.

    - DNIs hardcoded tienen datos mock determinísticos existentes.
    - Cualquier otro DNI válido (8 dígitos) genera datos mock determinísticos
      basados en el DNI (mismo DNI siempre devuelve los mismos datos).
    """

    # Datos mock de personas — DNIs válidos de ejemplo
    _SIMULADOS = {
        "45406196": {
            "dni": "45406196",
            "nombres": "DENNIS JOEL",
            "apellidos": "ZARATE TORRES",
            "nombre_completo": "ZARATE TORRES, DENNIS JOEL",
            "genero": "M",
            "fecha_nacimiento": date(1986, 8, 24),
            "direccion": "LAS PALMAS 135 LA CAPILLA",
            "ubigeo": "150101",
        },
        "12345678": {
            "dni": "12345678",
            "nombres": "CARLOS MANUEL",
            "apellidos": "PEREZ GOMEZ",
            "nombre_completo": "PEREZ GOMEZ, CARLOS MANUEL",
            "genero": "M",
            "fecha_nacimiento": date(1990, 3, 15),
            "direccion": "AV. AREQUIPA 123",
            "ubigeo": "150101",
        },
        "87654321": {
            "dni": "87654321",
            "nombres": "MARIA ELENA",
            "apellidos": "LOPEZ SANCHEZ",
            "nombre_completo": "LOPEZ SANCHEZ, MARIA ELENA",
            "genero": "F",
            "fecha_nacimiento": date(1983, 11, 7),
            "direccion": "JR. LIMA 456",
            "ubigeo": "150201",
        },
    }

    # Datos base para generación determinística
    _NOMBRES = [
        "JUAN",
        "CARLOS",
        "MIGUEL",
        "LUIS",
        "JOSE",
        "MARIA",
        "ELENA",
        "ANA",
        "PATRICIA",
        "LORENA",
        "FERNANDO",
        "RODRIGO",
        "VERONICA",
        "CARMEN",
        "FRANCISCO",
    ]

    _APELLIDOS = [
        "GARCIA",
        "PEREZ",
        "LOPEZ",
        "SANCHEZ",
        "RODRIGUEZ",
        "MARTINEZ",
        "TORRES",
        "RAMIREZ",
        "FLORES",
        "VARGAS",
        "HUAMAN",
        "QUISPE",
        "MENDOZA",
        "CASTILLO",
        "JIMENEZ",
    ]

    _GENEROS = ["M", "F"]

    async def get_persona(self, dni: str) -> ReniecPersonaResult:
        """
        Simula la consulta de persona por DNI.

        Args:
            dni: Número de DNI (8 dígitos).

        Returns:
            ReniecPersonaResult con datos mock.

        Note:
            - Si el DNI está en datos hardcoded, devuelve esos datos.
            - Para cualquier otro DNI válido de 8 dígitos, genera datos
              determinísticos basados en el DNI.
        """
        data = self._SIMULADOS.get(dni)
        if data:
            return ReniecPersonaResult(**data)

        # Generar datos determinísticos para DNIs no hardcoded
        return self._generar_persona_determinista(dni)

    def _generar_persona_determinista(self, dni: str) -> ReniecPersonaResult:
        """
        Genera datos mock determinísticos basados en el DNI.

        Usa hash del DNI como seed para que el mismo DNI siempre
        devuelva los mismos datos.
        """
        seed = int(hashlib.md5(dni.encode()).hexdigest(), 16)
        rng = random.Random(seed)

        nombres = f"{rng.choice(self._NOMBRES)} {rng.choice(self._NOMBRES)}"
        apellido_paterno = rng.choice(self._APELLIDOS)
        apellido_materno = rng.choice(self._APELLIDOS)
        apellidos = f"{apellido_paterno} {apellido_materno}"
        nombre_completo = f"{apellidos}, {nombres}"
        genero = rng.choice(self._GENEROS)

        # Generar fecha de nacimiento aleatoria pero determinística (entre 1970-2000)
        year = rng.randint(1970, 2000)
        month = rng.randint(1, 12)
        day = rng.randint(1, 28)  # Usar 28 para evitar problemas con meses cortos
        fecha_nacimiento = date(year, month, day)

        # Generar dirección fake
        direccion = f"JR. {apellido_paterno} NRO. {rng.randint(100, 999)}"
        ubigeo = f"15{rng.randint(0, 9)}{rng.randint(0, 9)}{rng.randint(0, 9)}{rng.randint(0, 9)}"

        return ReniecPersonaResult(
            dni=dni,
            nombres=nombres,
            apellidos=apellidos,
            nombre_completo=nombre_completo,
            genero=genero,
            fecha_nacimiento=fecha_nacimiento,
            direccion=direccion,
            ubigeo=ubigeo,
        )


class RealReniecClient(IReniecClient):
    """
    Cliente real que consulta la API de RENIEC.

    # TODO: Implementar cuando se tengan las credenciales y endpoint de la API RENIEC.
    Requiere:
    - RENIEC_API_BASE_URL en settings
    - Autenticación (API key o token)
    - Manejo de rate limiting
    """

    async def get_persona(self, dni: str) -> ReniecPersonaResult:
        """
        Consulta la API real de RENIEC.

        Raises:
            NotImplementedError: Aún no implementado.
        """
        raise NotImplementedError(
            "RealReniecClient aún no implementado. "
            "Usar ReniecClientSimulator para desarrollo."
        )