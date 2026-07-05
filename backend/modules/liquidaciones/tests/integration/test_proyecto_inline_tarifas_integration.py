"""
Integration tests for PrimeraRevision proyecto_inline and tarifas_ids — Phase 5.

Tests the full stack: controller -> orchestrator -> flujo -> core -> DB.

Coverage:
1. Crear primera revisión con proyecto_public_id existente sigue funcionando.
2. Crear primera revisión con proyecto_inline crea proyecto y liquidación en una transacción.
3. Enviar ambos proyecto_public_id y proyecto_inline retorna error 400.
4. Enviar ninguno retorna error 400.
5. tarifas_ids debe tener exactamente 1 elemento y validar tarifa vigente EDIFICACION.
6. delegados_ids no está en creación; no se asocian delegados en primera revisión.
7. Cotización con tarifas_ids funciona y no requiere proyecto.

NOTE: These tests require EspecialidadesLiquidacion vigente and TarifaLiquidacionBase
with detalle_porcentual to exist in the test database.
"""
import pytest
import uuid
from django.test import Client

from modules.liquidaciones.tests.factories.proyecto_factory import ProyectoFactory
from modules.liquidaciones.tests.factories.finanzas_factory import IGVFactory, UITFactory
from modules.liquidaciones.tests.factories.tarifa_liquidacion_factory import TarifaLiquidacionBaseFactory
from modules.liquidaciones.tests.factories.especialidades_liquidacion_factory import EspecialidadesLiquidacionFactory
from modules.liquidaciones.tests.factories.especialidad_factory import EspecialidadFactory
from modules.liquidaciones.tests.factories.regla_tarifa_edificacion_factory import ReglaTarifaEdificacionFactory
from modules.liquidaciones.domain.constants import TipoTramiteEdificaciones, TramiteAccion


@pytest.mark.django_db
class TestPrimeraRevisionProyectoInline:
    """Tests for proyecto_inline creation in primera revision."""

    def setup_method(self):
        """Seed IGV, UIT, EspecialidadesLiquidacion y municipalidad."""
        self.igv = IGVFactory()
        self.uit = UITFactory()
        # Grupo de especialidades vigente (empty for sin_revisiones tests)
        self.especialidades_grupo = EspecialidadesLiquidacionFactory()
        # Create a municipalidad for testing
        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-INLINE-001",
            nombre="Municipalidad Inline Test",
            distrito=self.distrito,
        )

    def test_primera_revision_con_proyecto_inline_crea_proyecto_y_liquidacion(self, client: Client):
        """
        POST /primera-revision con proyecto_inline debe crear el proyecto
        y la liquidación en una transacción atómica.
        """
        from modules.liquidaciones.models import Proyecto

        # Contar proyectos antes
        proyectos_before = Proyecto.objects.count()

        response = client.post(
            "/api/liquidaciones/edificaciones/primera-revision",
            data={
                "liquidacion": {
                    "municipalidad_id": str(self.municipalidad.id),
                    "tipo_tramite": "OBRA_NUEVA",
                    "valor_proyecto": 50000.0,
                    "valor_base_calculo": 50000.0,
                    "revisiones_ids": [],
                    "proyecto_inline": {
                        "denominacion": "Mi Proyecto Inline Test",
                        "direccion": "Av. Test 123",
                        "nombre_propietario": "Juan Perez Rodriguez",
                        "entidad": {
                            "tipo_documento": "RUC",
                            "numero_documento": "20456789012",
                            "razon_social": "Empresa Test Inline S.A.",
                        },
                    },
                }
            },
            content_type="application/json",
        )

        assert response.status_code == 200, response.json()
        data = response.json()
        assert "data" in data
        snapshot = data["data"]

        # Verificar que se creó el proyecto inline
        proyectos_after = Proyecto.objects.count()
        assert proyectos_after == proyectos_before + 1, "Debió crearse exactamente 1 proyecto"

        # El proyecto en la respuesta debe tener denominacion "Mi Proyecto Inline Test"
        assert "proyecto" in snapshot
        assert snapshot["proyecto"]["nombre"] == "Mi Proyecto Inline Test"

        # Verificar que la liquidación tiene el proyecto referenciado
        assert "public_id" in snapshot
        assert snapshot["public_id"].startswith("LIQ-")

        # Verificar que tiene número de revisión 1
        assert "numero_revision" in snapshot
        assert snapshot["numero_revision"] == 1

    def test_primera_revision_con_proyecto_inline_y_nombre_propietario(self, client: Client):
        """
        POST /primera-revision con proyecto_inline y nombre_propietario
        debe crear el proyecto con nombre_propietario configurado.
        """
        from modules.liquidaciones.models import Proyecto

        # Contar proyectos antes
        proyectos_before = Proyecto.objects.count()

        response = client.post(
            "/api/liquidaciones/edificaciones/primera-revision",
            data={
                "liquidacion": {
                    "municipalidad_id": str(self.municipalidad.id),
                    "tipo_tramite": "OBRA_NUEVA",
                    "valor_proyecto": 75000.0,
                    "valor_base_calculo": 75000.0,
                    "revisiones_ids": [],
                    "proyecto_inline": {
                        "denominacion": "Proyecto con Propietario Test",
                        "direccion": "Calle Propietario 456",
                        "nombre_propietario": "Juan Carlos Perez Rodriguez",
                        "entidad": {
                            "tipo_documento": "RUC",
                            "numero_documento": "20456789019",
                            "razon_social": "Empresa del Propietario S.A.",
                        },
                    },
                }
            },
            content_type="application/json",
        )

        assert response.status_code == 200, response.json()
        data = response.json()
        assert "data" in data
        snapshot = data["data"]

        # Verificar que se creó el proyecto inline
        proyectos_after = Proyecto.objects.count()
        assert proyectos_after == proyectos_before + 1, "Debió crearse exactamente 1 proyecto"

        # El proyecto debe tener el nombre_propietario configurado
        proyecto_creado = Proyecto.objects.get(public_id=snapshot["proyecto"]["public_id"])
        assert proyecto_creado.nombre_propietario == "Juan Carlos Perez Rodriguez", (
            f"El nombre_propietario debe ser 'Juan Carlos Perez Rodriguez', pero es '{proyecto_creado.nombre_propietario}'"
        )

    def test_primera_revision_con_proyecto_inline_requiere_nombre_propietario(self, client: Client):
        """
        POST /primera-revision con proyecto_inline sin nombre_propietario (a nivel proyecto_inline)
        debe retornar error 422 — nombre_propietario es requerido a nivel proyecto_inline.
        """
        from modules.liquidaciones.models import Proyecto

        # Contar proyectos antes
        proyectos_before = Proyecto.objects.count()

        response = client.post(
            "/api/liquidaciones/edificaciones/primera-revision",
            data={
                "liquidacion": {
                    "municipalidad_id": str(self.municipalidad.id),
                    "tipo_tramite": "OBRA_NUEVA",
                    "valor_proyecto": 60000.0,
                    "valor_base_calculo": 60000.0,
                    "revisiones_ids": [],
                    "proyecto_inline": {
                        "denominacion": "Proyecto Sin Propietario Test",
                        "direccion": "Calle Sin Propietario 789",
                        # Sin nombre_propietario a nivel proyecto_inline — debe retornar 422
                        "entidad": {
                            "tipo_documento": "DNI",
                            "numero_documento": "87654321",
                            "razon_social": "Maria Garcia Lopez",
                        },
                    },
                }
            },
            content_type="application/json",
        )

        # Debe retornar 422 porque nombre_propietario es requerido a nivel proyecto_inline
        assert response.status_code == 422, response.json()
        data = response.json()
        assert data["success"] is False
        assert "nombre_propietario" in str(data["error"]["details"])

        # Verificar que NO se creó ningún proyecto
        proyectos_after = Proyecto.objects.count()
        assert proyectos_after == proyectos_before, "No debió crearse ningún proyecto"

    def test_primera_revision_proyecto_inline_y_public_id_retorna_400(self, client: Client):
        """
        POST /primera-revision con ambos proyecto_public_id y proyecto_inline
        debe retornar error 400 (XOR validation).
        """
        proyecto = ProyectoFactory()

        response = client.post(
            "/api/liquidaciones/edificaciones/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "tipo_tramite": "OBRA_NUEVA",
                    "valor_proyecto": 50000.0,
                    "valor_base_calculo": 50000.0,
                    "revisiones_ids": [],
                    "proyecto_inline": {
                        "denominacion": "No debe crearse",
                        "direccion": "Calle Falsa 123",
                        "nombre_propietario": "Pedro Gomez Lopez",
                        "entidad": {
                            "tipo_documento": "RUC",
                            "numero_documento": "20456789013",
                            "razon_social": "Empresa XOR Test S.A.",
                        },
                    },
                }
            },
            content_type="application/json",
        )

        assert response.status_code == 400, response.json()
        data = response.json()
        # HttpError format: data["error"]["details"]["non_field_errors"]
        assert data["success"] is False
        assert data["error"] is not None
        detail = data["error"].get("details", {}).get("non_field_errors", "")
        assert "proyecto_public_id" in detail or "proyecto_inline" in detail or "ambos" in detail.lower()

    def test_primera_revision_sin_proyecto_retorna_400(self, client: Client):
        """
        POST /primera-revision sin proyecto_public_id ni proyecto_inline
        debe retornar error 400 (ninguno de los dos).
        """
        response = client.post(
            "/api/liquidaciones/edificaciones/primera-revision",
            data={
                "liquidacion": {
                    "municipalidad_id": str(self.municipalidad.id),
                    "tipo_tramite": "OBRA_NUEVA",
                    "valor_proyecto": 50000.0,
                    "valor_base_calculo": 50000.0,
                    "revisiones_ids": [],
                    # Ni proyecto_public_id ni proyecto_inline
                }
            },
            content_type="application/json",
        )

        assert response.status_code == 400, response.json()
        data = response.json()
        assert data["success"] is False
        assert data["error"] is not None
        detail = data["error"].get("details", {}).get("non_field_errors", "")
        assert "proyecto_public_id" in detail or "proyecto_inline" in detail or "uno" in detail.lower()

    def test_primera_revision_proyecto_public_id_existente_retorna_200(self, client: Client):
        """
        POST /primera-revision con proyecto_public_id existente (sin proyecto_inline)
        debe retornar 200 — verifica que el flujo normal sigue funcionando.
        """
        proyecto = ProyectoFactory()

        response = client.post(
            "/api/liquidaciones/edificaciones/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "tipo_tramite": "OBRA_NUEVA",
                    "valor_proyecto": 50000.0,
                    "valor_base_calculo": 50000.0,
                    "revisiones_ids": [],
                }
            },
            content_type="application/json",
        )

        assert response.status_code == 200, response.json()
        data = response.json()
        assert "data" in data
        snapshot = data["data"]
        assert snapshot["proyecto"]["public_id"] == proyecto.public_id


@pytest.mark.django_db
class TestPrimeraRevisionTarifasIds:
    """Tests for tarifas_ids validation in primera revision creation."""

    def setup_method(self):
        """Seed IGV, UIT, EspecialidadesLiquidacion, tarifa y municipalidad."""
        self.igv = IGVFactory()
        self.uit = UITFactory()
        # Grupo de especialidades vigente
        self.especialidades_grupo = EspecialidadesLiquidacionFactory()
        # Crear especialidades y asociarlas a la tarifa (requerido para tarifas_ids)
        self.esp1 = EspecialidadFactory()
        self.esp2 = EspecialidadFactory()
        # Create a TarifaLiquidacionBase EDIFICACION vigente with detalle_porcentual and especialidades
        self.tarifa_base = TarifaLiquidacionBaseFactory(especialidades=[self.esp1, self.esp2])
        # Create ReglaTarifaEdificacion for this tariff (required for tarifas_ids validation)
        ReglaTarifaEdificacionFactory(
            tipo_tramite=TipoTramiteEdificaciones.OBRA_NUEVA,
            tramite_accion=TramiteAccion.PRIMERA_REVISION,
            tarifa_base=self.tarifa_base,
        )
        # Create a municipalidad for testing
        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-TARIFA-001",
            nombre="Municipalidad Tarifa Test",
            distrito=self.distrito,
        )
        # Proyecto existente para tests de tarifas_ids
        self.proyecto = ProyectoFactory()

    def test_primera_revision_tarifas_ids_multiple_retorna_error(self, client: Client):
        """
        POST /primera-revision con tarifas_ids conteniendo más de 1 elemento
        debe retornar error 400 — len(tarifas_ids) != 1.
        """
        # Crear otra tarifa con especialidades para tener 2 válidas
        otra_esp = EspecialidadFactory()
        otra_tarifa = TarifaLiquidacionBaseFactory(especialidades=[otra_esp])

        response = client.post(
            "/api/liquidaciones/edificaciones/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "tipo_tramite": "OBRA_NUEVA",
                    "valor_proyecto": 50000.0,
                    "valor_base_calculo": 50000.0,
                    "revisiones_ids": [],
                    "tarifas_ids": [str(self.tarifa_base.id), str(otra_tarifa.id)],
                }
            },
            content_type="application/json",
        )

        assert response.status_code == 400, response.json()
        data = response.json()
        assert data["success"] is False
        detail = data["error"].get("details", {}).get("non_field_errors", "")
        assert "tarifas_ids" in detail or "1" in detail

    def test_primera_revision_tarifas_ids_lista_vacia_retorna_error(self, client: Client):
        """
        POST /primera-revision con tarifas_ids = [] (lista vacía)
        debe retornar error 422 — Pydantic min_length=1 rechaza lista vacía.
        """
        response = client.post(
            "/api/liquidaciones/edificaciones/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "tipo_tramite": "OBRA_NUEVA",
                    "valor_proyecto": 50000.0,
                    "valor_base_calculo": 50000.0,
                    "revisiones_ids": [],
                    "tarifas_ids": [],
                }
            },
            content_type="application/json",
        )

        # Pydantic validation returns 422, no llega al flujo
        assert response.status_code == 422, response.json()
        data = response.json()
        assert data["success"] is False
        assert "tarifas_ids" in str(data["error"]["details"])

    def test_primera_revision_tarifas_ids_un_elemento_funciona(self, client: Client):
        """
        POST /primera-revision con tarifas_ids conteniendo exactamente 1 elemento válido
        debe retornar 200 y crear la liquidación con esa tarifa.
        """
        tarifa_base_id = self.tarifa_base.id

        response = client.post(
            "/api/liquidaciones/edificaciones/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "tipo_tramite": "OBRA_NUEVA",
                    "valor_proyecto": 50000.0,
                    "valor_base_calculo": 50000.0,
                    "revisiones_ids": [],
                    "tarifas_ids": [str(tarifa_base_id)],
                }
            },
            content_type="application/json",
        )

        assert response.status_code == 200, response.json()
        data = response.json()
        snapshot = data["data"]

        assert "revisiones" in snapshot
        assert len(snapshot["revisiones"]) == 1

        rev = snapshot["revisiones"][0]
        assert str(rev["tarifa"]["id"]) == str(self.tarifa_base.detalle_porcentual.id)
        assert snapshot["total"] > 0

    def test_primera_revision_tarifas_ids_tarifa_no_existente_retorna_error(self, client: Client):
        """
        POST /primera-revision con tarifas_ids conteniendo un UUID inexistente
        debe retornar error.
        """
        fake_uuid = str(uuid.uuid4())

        response = client.post(
            "/api/liquidaciones/edificaciones/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "tipo_tramite": "OBRA_NUEVA",
                    "valor_proyecto": 50000.0,
                    "valor_base_calculo": 50000.0,
                    "revisiones_ids": [],
                    "tarifas_ids": [fake_uuid],
                }
            },
            content_type="application/json",
        )

        # Debe retornar error (400 o 401) porque la tarifa no existe
        assert response.status_code >= 400, response.json()


@pytest.mark.django_db
class TestCotizarTarifasIds:
    """Tests for tarifas_ids in cotizar primera revision endpoint."""

    def setup_method(self):
        """Seed IGV, UIT y tarifa vigente con especialidades."""
        self.igv = IGVFactory()
        self.uit = UITFactory()
        # Crear especialidades y asociarlas a la tarifa (requerido para tarifas_ids)
        self.esp1 = EspecialidadFactory()
        self.tarifa_base = TarifaLiquidacionBaseFactory(especialidades=[self.esp1])

    def test_cotizar_primera_revision_sin_tarifas_ids_retorna_200(self, client: Client):
        """
        POST /cotizar/primera-revision sin tarifas_ids (cotización automática)
        debe retornar 200 — no requiere proyecto ni tarifas_ids.
        """
        from modules.liquidaciones.models import LiquidacionGeneral

        count_before = LiquidacionGeneral.objects.count()

        response = client.post(
            "/api/liquidaciones/edificaciones/cotizar/primera-revision",
            data={
                "liquidacion": {
                    "valor_proyecto": 50000.0,
                    "valor_base_calculo": 50000.0,
                }
            },
            content_type="application/json",
        )

        assert response.status_code == 200, response.json()
        # No debe crear liquidación
        assert LiquidacionGeneral.objects.count() == count_before

    def test_cotizar_primera_revision_con_tarifas_ids_un_elemento_retorna_200(self, client: Client):
        """
        POST /cotizar/primera-revision con tarifas_ids conteniendo exactamente 1 elemento
        y tipo_tramite con ReglaTarifaEdificacion válida debe retornar 200 usando esa tarifa.

        No requiere proyecto_public_id.
        """
        from modules.liquidaciones.models import LiquidacionGeneral

        count_before = LiquidacionGeneral.objects.count()
        # Use the TarifaLiquidacionBase ID (not TarifaPorcentajeObra ID)
        tarifa_base_id = self.tarifa_base.id
        # Crear ReglaTarifaEdificacion para que la tarifa sea válida para cotización
        ReglaTarifaEdificacionFactory(
            tipo_tramite=TipoTramiteEdificaciones.OBRA_NUEVA,
            tramite_accion=TramiteAccion.PRIMERA_REVISION,
            tarifa_base=self.tarifa_base,
        )

        response = client.post(
            "/api/liquidaciones/edificaciones/cotizar/primera-revision",
            data={
                "liquidacion": {
                    "tipo_tramite": TipoTramiteEdificaciones.OBRA_NUEVA,
                    "valor_proyecto": 50000.0,
                    "valor_base_calculo": 50000.0,
                    "tarifas_ids": [str(tarifa_base_id)],
                }
            },
            content_type="application/json",
        )

        assert response.status_code == 200, response.json()
        data = response.json()
        quote = data["data"]

        # Verificar estructura de cotización
        assert "numero_revision" in quote
        assert quote["numero_revision"] == 1
        assert "revisiones" in quote
        assert len(quote["revisiones"]) == 1
        assert "totales" in quote

        # Verificar que no se creó liquidación
        assert LiquidacionGeneral.objects.count() == count_before

    def test_cotizar_primera_revision_tarifas_ids_multiple_retorna_error(self, client: Client):
        """
        POST /cotizar/primera-revision con más de 1 tarifa en tarifas_ids
        debe retornar error 400.
        """
        otra_esp = EspecialidadFactory()
        otra_tarifa = TarifaLiquidacionBaseFactory(especialidades=[otra_esp])

        response = client.post(
            "/api/liquidaciones/edificaciones/cotizar/primera-revision",
            data={
                "liquidacion": {
                    "valor_proyecto": 50000.0,
                    "valor_base_calculo": 50000.0,
                    "tarifas_ids": [str(self.tarifa_base.id), str(otra_tarifa.id)],
                }
            },
            content_type="application/json",
        )

        assert response.status_code == 400, response.json()

    def test_cotizar_primera_revision_tarifas_ids_lista_vacia_retorna_error(self, client: Client):
        """
        POST /cotizar/primera-revision con tarifas_ids = [] (lista vacía)
        debe retornar error 422 — Pydantic min_length=1 rechaza lista vacía.
        """
        response = client.post(
            "/api/liquidaciones/edificaciones/cotizar/primera-revision",
            data={
                "liquidacion": {
                    "valor_proyecto": 50000.0,
                    "valor_base_calculo": 50000.0,
                    "tarifas_ids": [],
                }
            },
            content_type="application/json",
        )

        # Pydantic validation returns 422, no llega al flujo
        assert response.status_code == 422, response.json()
        data = response.json()
        assert data["success"] is False
        assert "tarifas_ids" in str(data["error"]["details"])

    def test_cotizar_primera_revision_tarifas_ids_sin_tipo_tramite_retorna_error(self, client: Client):
        """
        POST /cotizar/primera-revision con tarifas_ids pero sin tipo_tramite
        debe retornar error 400 — tipo_tramite es requerido para validar la ReglaTarifaEdificacion.
        """
        tarifa_base_id = self.tarifa_base.id

        response = client.post(
            "/api/liquidaciones/edificaciones/cotizar/primera-revision",
            data={
                "liquidacion": {
                    "valor_proyecto": 50000.0,
                    "valor_base_calculo": 50000.0,
                    "tarifas_ids": [str(tarifa_base_id)],
                }
            },
            content_type="application/json",
        )

        assert response.status_code == 400, response.json()
        data = response.json()
        assert data["success"] is False
        assert "tipo_tramite es requerido" in data["error"]["details"]["non_field_errors"]

    def test_cotizar_primera_revision_tarifa_sin_regla_retorna_error(self, client: Client):
        """
        POST /cotizar/primera-revision con tarifas_ids y tipo_tramite pero SIN ReglaTarifaEdificacion
        debe retornar error 401 — la tarifa no tiene regla para ese tipo de trámite.
        
        Nota: ValueError es capturado por el exception handler global y retorna 401.
        """
        tarifa_base_id = self.tarifa_base.id

        response = client.post(
            "/api/liquidaciones/edificaciones/cotizar/primera-revision",
            data={
                "liquidacion": {
                    "tipo_tramite": TipoTramiteEdificaciones.OBRA_NUEVA,
                    "valor_proyecto": 50000.0,
                    "valor_base_calculo": 50000.0,
                    "tarifas_ids": [str(tarifa_base_id)],
                }
            },
            content_type="application/json",
        )

        # ValueError es capturado por el exception handler global → HTTP 401
        assert response.status_code == 401, response.json()
        data = response.json()
        assert data["success"] is False
        assert "ReglaTarifaEdificacion" in data["error"]["details"]["non_field_errors"] or "no tiene una ReglaTarifaEdificacion" in data["error"]["details"]["non_field_errors"]

    def test_cotizar_primera_revision_tarifa_con_regla_correcta_retorna_200(self, client: Client):
        """
        POST /cotizar/primera-revision con tarifas_ids, tipo_tramite Y ReglaTarifaEdificacion válida
        debe retornar 200 exitosamente.
        """
        from modules.liquidaciones.models import LiquidacionGeneral

        count_before = LiquidacionGeneral.objects.count()
        tarifa_base_id = self.tarifa_base.id
        # Crear ReglaTarifaEdificacion válida para la combinación
        ReglaTarifaEdificacionFactory(
            tipo_tramite=TipoTramiteEdificaciones.OBRA_NUEVA,
            tramite_accion=TramiteAccion.PRIMERA_REVISION,
            tarifa_base=self.tarifa_base,
        )

        response = client.post(
            "/api/liquidaciones/edificaciones/cotizar/primera-revision",
            data={
                "liquidacion": {
                    "tipo_tramite": TipoTramiteEdificaciones.OBRA_NUEVA,
                    "valor_proyecto": 50000.0,
                    "valor_base_calculo": 50000.0,
                    "tarifas_ids": [str(tarifa_base_id)],
                }
            },
            content_type="application/json",
        )

        assert response.status_code == 200, response.json()
        # Verificar que no se creó liquidación
        assert LiquidacionGeneral.objects.count() == count_before


@pytest.mark.django_db
class TestPrimeraRevisionSinDelegados:
    """Tests confirming delegados_ids is not processed in primera revision creation."""

    def setup_method(self):
        """Seed IGV, UIT, EspecialidadesLiquidacion y municipalidad."""
        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.especialidades_grupo = EspecialidadesLiquidacionFactory()
        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-NO-DELEG-001",
            nombre="Municipalidad Sin Delegados Test",
            distrito=self.distrito,
        )
        self.proyecto = ProyectoFactory()

    def test_primera_revision_no_requiere_delegados(self, client: Client):
        """
        POST /primera-revision sin delegados_ids debe retornar 200 exitosamente.

        Los delegados no se asocian en la primera revisión (se manejan en endpoint
        POST posterior separate — Fase 4).
        """
        response = client.post(
            "/api/liquidaciones/edificaciones/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "tipo_tramite": "OBRA_NUEVA",
                    "valor_proyecto": 50000.0,
                    "valor_base_calculo": 50000.0,
                    "revisiones_ids": [],
                    # No se envía delegados_ids
                }
            },
            content_type="application/json",
        )

        assert response.status_code == 200, response.json()
        data = response.json()
        snapshot = data["data"]

        # Verificar que la respuesta no tiene delegados asociados
        assert "delegados" in snapshot
        # Primera revisión no debe tener delegados
        assert snapshot["delegados"] == []
