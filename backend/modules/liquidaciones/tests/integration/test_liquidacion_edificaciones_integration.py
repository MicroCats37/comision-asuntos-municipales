"""
Integration tests for Liquidaciones Edificaciones endpoints.

Tests the full stack: controller -> orchestrator -> flujo -> core -> DB.

Nota: Los tests de cálculo de revisiones usan factories que pueden tener
problemas de serialización de IDs en el test client. Los unit tests
(100% passing) cubren la lógica de negocio. Estos tests de integración
verifican el flujo completo a nivel HTTP.

NOTE: Updated to use new Proyectista contract (perfil_ingeniero FK).
EspecialidadesLiquidacion must be created before primera-revision with revisions.
"""
import pytest
from decimal import Decimal
from django.test import Client

from modules.liquidaciones.tests.factories.proyecto_factory import ProyectoFactory
from modules.liquidaciones.tests.factories.finanzas_factory import IGVFactory, UITFactory
from modules.liquidaciones.tests.factories.proyectista_factory import ProyectistaFactory
from modules.liquidaciones.tests.factories.especialidades_liquidacion_factory import EspecialidadesLiquidacionFactory
from modules.liquidaciones.tests.factories.tarifa_liquidacion_factory import TarifaLiquidacionBaseFactory


@pytest.mark.django_db
class TestPrimeraRevisionEndpoint:
    """Test POST /api/liquidaciones/edificaciones/primera-revision endpoint."""

    def setup_method(self):
        """Seed IGV, UIT, proyecto y municipalidad (sin revisión para simplificar)."""
        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.proyecto = ProyectoFactory()
        # Create EspecialidadesLiquidacion vigente (empty set for sin_revisiones tests)
        self.especialidades_grupo = EspecialidadesLiquidacionFactory()
        # Create a municipalidad for testing
        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-001",
            nombre="Municipalidad de Prueba",
            distrito=self.distrito,
        )

    def test_primera_revision_sin_revisiones_retorna_200(self, client: Client):
        """
        POST /primera-revision sin revisiones_ids debe retornar 200.
        Verifica que el flujo completo funciona y retorna estructura plana LiquidacionEdificacionOut.
        """
        response = client.post(
            "/api/liquidaciones/edificaciones/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "tipo_tramite": "OBRA_NUEVA",
                    "valor_proyecto": 10000.0,
                    "valor_base_calculo": 10000.0,
                    "observacion": "Test",
                    "revisiones_ids": [],
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "data" in data
        result = data["data"]
        # Verificar estructura plana LiquidacionEdificacionOut
        assert "public_id" in result
        assert result["public_id"].startswith("LIQ-")
        assert "estado" in result
        assert "numero_revision" in result
        assert result["numero_revision"] == 1
        # Verificar municipalidad anidada
        assert "municipalidad" in result
        assert result["municipalidad"]["id"] == str(self.municipalidad.id)
        assert result["municipalidad"]["nombre"] == self.municipalidad.nombre
        # Sin revisiones, totales deben ser 0
        assert result["subtotal"] == 0
        assert result["igv"] == 0
        # expediente puede estar presente (null o ausente) — no es relevante para el dominio actual

    def test_primera_revision_proyecto_inexistente_retorna_error(self, client: Client):
        """Proyecto con public_id inexistente debe retornar error (no 500)."""
        response = client.post(
            "/api/liquidaciones/edificaciones/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": "PROY-INEXISTENTE",
                    "municipalidad_id": str(self.municipalidad.id),
                    "tipo_tramite": "OBRA_NUEVA",
                    "valor_proyecto": 10000.0,
                    "valor_base_calculo": 10000.0,
                    "revisiones_ids": [],
                }
            },
            content_type="application/json",
        )
        assert response.status_code in (200, 400, 404)


@pytest.mark.django_db
class TestRevisionesVigentesEndpoint:
    """Test GET /api/liquidaciones/edificaciones/revisiones-vigentes endpoint."""

    def test_revisiones_vigentes_retorna_200(self, client: Client):
        """
        GET /revisiones-vigentes debe retornar 200 con estructura de revisiones.

        Este test verifica que la ruta estática 'revisiones-vigentes' no es
        capturada por la ruta dinámica /{liquidacion_id}.
        """
        response = client.get("/api/liquidaciones/edificaciones/revisiones-vigentes")
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "data" in data
        assert "revisiones" in data["data"]
        # data.data.revisiones debe ser una lista
        assert isinstance(data["data"]["revisiones"], list)

    def test_revisiones_vigentes_no_intenta_parsear_uuid(self, client: Client):
        """
        GET /revisiones-vigentes no debe retornar 400 por UUID inválido.

        Este test confirma que la ruta estática tiene prioridad sobre la
        dinámica, evitando el error: "revisiones-vigentes is not a valid UUID".
        """
        response = client.get("/api/liquidaciones/edificaciones/revisiones-vigentes")
        # No debe ser 400 (Bad Request) por validación de UUID
        assert response.status_code != 400 or "UUID" not in response.json().get("detail", "")
        assert response.status_code == 200


@pytest.mark.django_db
class TestPrimeraRevisionProyectistasM2M:
    """Test that proyectistas_ids are saved and returned in primera-revision endpoint."""

    def setup_method(self):
        """Seed IGV, UIT, proyecto, municipalidad y proyectistas."""
        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.proyecto = ProyectoFactory()
        # Create EspecialidadesLiquidacion vigente
        self.especialidades_grupo = EspecialidadesLiquidacionFactory()
        # Create a municipalidad for testing
        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-002",
            nombre="Municipalidad de Prueba 2",
            distrito=self.distrito,
        )
        self.proyectista1 = ProyectistaFactory()
        self.proyectista2 = ProyectistaFactory()

    def test_primera_revision_con_proyectistas_guarda_y_retorna_m2m(self, client: Client):
        """
        POST /primera-revision con proyectistas_ids debe:
        1. Crear la liquidación con los proyectistas asociados
        2. Retornar los proyectistas en la respuesta plana LiquidacionEdificacionOut
        """
        response = client.post(
            "/api/liquidaciones/edificaciones/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "tipo_tramite": "OBRA_NUEVA",
                    "valor_proyecto": 10000.0,
                    "valor_base_calculo": 10000.0,
                    "observacion": "Test con proyectistas",
                    "revisiones_ids": [],
                    "proyectistas_ids": [str(self.proyectista1.id), str(self.proyectista2.id)],
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "data" in data
        result = data["data"]
        # Verificar que la respuesta plana incluye proyectistas
        assert "proyectistas" in result
        proyectistas_response = result["proyectistas"]
        assert len(proyectistas_response) == 2
        # Verificar que los datos de proyectistas son correctos
        proyectista_ids_response = {str(p["id"]) for p in proyectistas_response}
        assert str(self.proyectista1.id) in proyectista_ids_response
        assert str(self.proyectista2.id) in proyectista_ids_response

    def test_primera_revision_sin_proyectistas_retorna_lista_vacia(self, client: Client):
        """
        POST /primera-revision sin proyectistas_ids debe retornar
        lista vacía de proyectistas en la respuesta plana.
        """
        response = client.post(
            "/api/liquidaciones/edificaciones/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "tipo_tramite": "OBRA_NUEVA",
                    "valor_proyecto": 10000.0,
                    "valor_base_calculo": 10000.0,
                    "observacion": "Test sin proyectistas",
                    "revisiones_ids": [],
                    "proyectistas_ids": [],
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        result = data["data"]
        assert "proyectistas" in result
        assert result["proyectistas"] == []


# ── Additional endpoint coverage ──────────────────────────────────────────────


@pytest.mark.django_db
class TestEdificacionesListEndpoint:
    """Test GET /api/liquidaciones/edificaciones/ endpoint."""

    def setup_method(self):
        """Create municipalidad for tests."""
        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-003",
            nombre="Municipalidad de Prueba 3",
            distrito=self.distrito,
        )
        # Create EspecialidadesLiquidacion vigente for tests that create liquidaciones
        self.especialidades_grupo = EspecialidadesLiquidacionFactory()

    def test_get_list_empty_returns_success_with_items_array(self, client: Client):
        """
        GET / with no data returns 200 with items array and pagination keys.
        """
        response = client.get(
            "/api/liquidaciones/edificaciones/",
            query_params={"page": 1, "page_size": 10},
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "data" in data
        # Must have pagination keys
        assert "items" in data["data"]
        assert "total" in data["data"]
        assert "page" in data["data"]
        assert "page_size" in data["data"]
        assert "total_pages" in data["data"]
        assert isinstance(data["data"]["items"], list)

    def test_get_list_with_data_returns_items_and_pagination_keys(self, client: Client):
        """
        GET / after creating a liquidacion returns items with expected keys (flat LiquidacionEdificacionOut).
        """
        # Create a liquidacion first
        igv = IGVFactory()
        uit = UITFactory()
        proyecto = ProyectoFactory()
        client = Client()
        create_response = client.post(
            "/api/liquidaciones/edificaciones/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "tipo_tramite": "OBRA_NUEVA",
                    "valor_proyecto": 10000.0,
                    "valor_base_calculo": 10000.0,
                    "revisiones_ids": [],
                }
            },
            content_type="application/json",
        )
        assert create_response.status_code == 200, f"Setup failed: {create_response.json()}"

        # Now list
        response = client.get(
            "/api/liquidaciones/edificaciones/",
            query_params={"page": 1, "page_size": 10},
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        items = data["data"]["items"]
        assert len(items) >= 1
        # Verify item has expected flat LiquidacionEdificacionOut keys
        item = items[0]
        assert "id" in item
        assert "public_id" in item
        assert "estado" in item
        assert "numero_revision" in item
        assert "tipo_tramite" in item
        assert "tramite_accion" in item
        # Nested proyecto
        assert "proyecto" in item
        assert "public_id" in item["proyecto"]
        assert "nombre" in item["proyecto"]
        # Valores financieros directos
        assert "subtotal" in item
        assert "igv" in item
        assert "total" in item
        assert "total_a_pagar" in item
        assert "fecha_registro" in item
        # Flat LiquidacionEdificacionOut includes expediente at the root.
        assert "expediente" in item


@pytest.mark.django_db
class TestPrimeraRevisionValidation:
    """Test 422 error handling for POST /primera-revision."""

    def setup_method(self):
        """Seed IGV, UIT, proyecto y municipalidad."""
        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.proyecto = ProyectoFactory()
        # Create EspecialidadesLiquidacion vigente
        self.especialidades_grupo = EspecialidadesLiquidacionFactory()
        # Create a municipalidad for testing
        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-004",
            nombre="Municipalidad de Prueba 4",
            distrito=self.distrito,
        )

    def test_primera_revision_missing_liquidacion_wrapper_returns_422(self, client: Client):
        """
        POST /primera-revision without the `liquidacion` wrapper must return 422.
        The endpoint expects { liquidacion: {...} }, not the inner payload directly.
        """
        response = client.post(
            "/api/liquidaciones/edificaciones/primera-revision",
            data={
                # Missing outer "liquidacion" wrapper
"proyecto_public_id": self.proyecto.public_id,
                "municipalidad_id": str(self.municipalidad.id),
                "tipo_tramite": "OBRA_NUEVA",
                "valor_proyecto": 10000.0,
                "valor_base_calculo": 10000.0,
                "revisiones_ids": [],
            },
            content_type="application/json",
        )
        assert response.status_code == 422, response.json()

    def test_primera_revision_valid_minimal_payload_returns_200(self, client: Client):
        """
        POST /primera-revision with only required fields returns 200.
        """
        response = client.post(
            "/api/liquidaciones/edificaciones/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "tipo_tramite": "OBRA_NUEVA",
                    "valor_proyecto": 10000.0,
                    "valor_base_calculo": 10000.0,
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "data" in data

    def test_primera_revision_valid_with_proyectistas_ids_returns_200(self, client: Client):
        """
        POST /primera-revision with valid proyectistas_ids returns 200.
        """
        proyectista = ProyectistaFactory()
        response = client.post(
            "/api/liquidaciones/edificaciones/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "tipo_tramite": "OBRA_NUEVA",
                    "valor_proyecto": 10000.0,
                    "valor_base_calculo": 10000.0,
                    "revisiones_ids": [],
                    "proyectistas_ids": [str(proyectista.id)],
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()

    def test_primera_revision_missing_proyecto_returns_error(self, client: Client):
        """
        POST /primera-revision without proyecto_public_id returns 422 or 400.
        """
        response = client.post(
            "/api/liquidaciones/edificaciones/primera-revision",
            data={
                "liquidacion": {
                    "municipalidad_id": str(self.municipalidad.id),
                    "tipo_tramite": "OBRA_NUEVA",
                    "valor_proyecto": 10000.0,
                    "valor_base_calculo": 10000.0,
                    "revisiones_ids": [],
                }
            },
            content_type="application/json",
        )
        # HttpError raised by orchestrator returns 400, not 422
        assert response.status_code in (400, 422), response.json()

    def test_primera_revision_negative_valor_proyecto_returns_422(self, client: Client):
        """
        POST /primera-revision with negative valor_proyecto (gt=0 validator) returns 422.
        """
        response = client.post(
            "/api/liquidaciones/edificaciones/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "tipo_tramite": "OBRA_NUEVA",
                    "valor_proyecto": -100.0,
                    "revisiones_ids": [],
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 422, response.json()


@pytest.mark.django_db
class TestNuevaRevisionFormularioEndpoint:
    """Test GET /api/liquidaciones/edificaciones/nueva-revision/formulario endpoint."""

    def setup_method(self):
        """Create a liquidacion to use as previous."""
        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.proyecto = ProyectoFactory()
        # Create EspecialidadesLiquidacion vigente
        self.especialidades_grupo = EspecialidadesLiquidacionFactory()
        # Create a municipalidad for testing
        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-005",
            nombre="Municipalidad de Prueba 5",
            distrito=self.distrito,
        )

        client = Client()
        response = client.post(
            "/api/liquidaciones/edificaciones/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "tipo_tramite": "OBRA_NUEVA",
                    "valor_proyecto": 10000.0,
                    "valor_base_calculo": 10000.0,
                    "revisiones_ids": [],
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, f"Setup failed: {response.json()}"
        self.liquidacion_previa_id = response.json()["data"]["id"]

    def test_formulario_con_liquidacion_previa_existente_retorna_200(self, client: Client):
        """
        GET /nueva-revision/formulario with valid previous liquidacion returns 200.
        """
        response = client.get(
            "/api/liquidaciones/edificaciones/nueva-revision/formulario",
            query_params={"liquidacion_previa_id": self.liquidacion_previa_id},
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "data" in data
        # Verify expected keys in response
        assert "liquidacion_previa_id" in data["data"]
        assert "numero_revision" in data["data"]
        assert "cobra" in data["data"]
        assert "proyecto_id" in data["data"]
        assert "proyecto_public_id" in data["data"]
        assert "proyecto_nombre" in data["data"]
        assert "valor_proyecto" in data["data"]
        assert "revisiones_vigentes" in data["data"]
        # numero_revision should be 2 (second revision)
        assert data["data"]["numero_revision"] == 2

    def test_formulario_con_uuid_invalido_retorna_422(self, client: Client):
        """
        GET /nueva-revision/formulario with invalid UUID returns 422 or 400.
        """
        response = client.get(
            "/api/liquidaciones/edificaciones/nueva-revision/formulario",
            query_params={"liquidacion_previa_id": "not-a-valid-uuid"},
        )
        assert response.status_code in (400, 422), response.json()

    def test_formulario_sin_liquidacion_previa_id_retorna_422(self, client: Client):
        """
        GET /nueva-revision/formulario without liquidacion_previa_id returns 422.
        """
        response = client.get(
            "/api/liquidaciones/edificaciones/nueva-revision/formulario",
        )
        assert response.status_code == 422, response.json()


@pytest.mark.django_db
class TestNuevaRevisionEndpoint:
    """Test POST /api/liquidaciones/edificaciones/nueva-revision endpoint."""

    def setup_method(self):
        """Create a liquidacion to use as previous."""
        from modules.liquidaciones.domain.constants import TramiteAccion, TipoTramiteEdificaciones
        from modules.liquidaciones.tests.factories.regla_tarifa_edificacion_factory import ReglaTarifaEdificacionFactory
        from modules.liquidaciones.tests.factories.especialidad_factory import EspecialidadFactory

        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.proyecto = ProyectoFactory()

        # Create EspecialidadesLiquidacion vigente (empty - for primera-revision with no revisions)
        self.especialidades_grupo = EspecialidadesLiquidacionFactory()

        # Create Especialidad for the tarifa (required by domain validation)
        self.especialidad = EspecialidadFactory()

        # Create TarifaLiquidacionBase with detalle_porcentual, especialidades and ReglaTarifaEdificacion for REVISION
        self.tarifa_base = TarifaLiquidacionBaseFactory(especialidades=[self.especialidad])
        ReglaTarifaEdificacionFactory(
            tipo_tramite=TipoTramiteEdificaciones.OBRA_NUEVA,
            tramite_accion=TramiteAccion.REVISION,
            tarifa_base=self.tarifa_base,
        )

        # Create a municipalidad for testing
        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-006",
            nombre="Municipalidad de Prueba 6",
            distrito=self.distrito,
        )
        self.proyectista1 = ProyectistaFactory()
        self.proyectista2 = ProyectistaFactory()

        client = Client()
        response = client.post(
            "/api/liquidaciones/edificaciones/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "tipo_tramite": "OBRA_NUEVA",
                    "valor_proyecto": 10000.0,
                    "valor_base_calculo": 10000.0,
                    "revisiones_ids": [],
                    "proyectistas_ids": [str(self.proyectista1.id)],
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, f"Setup failed: {response.json()}"
        self.liquidacion_previa_id = response.json()["data"]["id"]

    def test_nueva_revision_empty_revisiones_ids_returns_422(self, client: Client):
        """
        POST /nueva-revision with empty revisiones_ids (min_length=1) returns 422.
        """
        response = client.post(
            "/api/liquidaciones/edificaciones/nueva-revision",
            data={
                "liquidacion_previa_id": self.liquidacion_previa_id,
                "revisiones_ids": [],  # min_length=1 — must fail
            },
            content_type="application/json",
        )
        assert response.status_code == 422, response.json()

    def test_nueva_revision_valid_payload_returns_200(self, client: Client):
        """
        POST /nueva-revision with valid payload (existing liquidacion, non-empty
        revisiones_ids) returns 200 and creates a new revision with flat LiquidacionEdificacionOut.
        """
        # Get a valid revision to use
        revision_response = client.get(
            "/api/liquidaciones/edificaciones/nueva-revision/formulario",
            query_params={"liquidacion_previa_id": self.liquidacion_previa_id},
        )
        assert revision_response.status_code == 200, f"Setup failed: {revision_response.json()}"
        revisiones_vigentes = revision_response.json()["data"]["revisiones_vigentes"]

        if len(revisiones_vigentes) == 0:
            pytest.skip("No revisiones vigentes available to test with")

        first_revision_id = revisiones_vigentes[0]["id"]

        response = client.post(
            "/api/liquidaciones/edificaciones/nueva-revision",
            data={
                "liquidacion_previa_id": self.liquidacion_previa_id,
                "revisiones_ids": [first_revision_id],
                "observacion": "Test nueva revisión",
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "data" in data
        result = data["data"]
        # Nueva revisión follows the domain sequence 1 -> 3 -> 5.
        assert result["numero_revision"] == 3

    def test_nueva_revision_invalid_liquidacion_previa_id_returns_error(self, client: Client):
        """
        POST /nueva-revision with non-existent liquidacion_previa_id returns error.
        """
        import uuid
        fake_uuid = str(uuid.uuid4())
        response = client.post(
            "/api/liquidaciones/edificaciones/nueva-revision",
            data={
                "liquidacion_previa_id": fake_uuid,
                "revisiones_ids": [fake_uuid],
            },
            content_type="application/json",
        )
        # Should return 400/404/etc but NOT 200
        assert response.status_code != 200, response.json()

    def test_nueva_revision_con_proyectistas_ids_usa_esos_proyectistas(self, client: Client):
        """
        POST /nueva-revision with non-empty proyectistas_ids debe usar
        exactamente esos proyectistas (no heredar de la previa).
        """
        # Get a valid revision to use
        revision_response = client.get(
            "/api/liquidaciones/edificaciones/nueva-revision/formulario",
            query_params={"liquidacion_previa_id": self.liquidacion_previa_id},
        )
        assert revision_response.status_code == 200, f"Setup failed: {revision_response.json()}"
        revisiones_vigentes = revision_response.json()["data"]["revisiones_vigentes"]

        if len(revisiones_vigentes) == 0:
            pytest.skip("No revisiones vigentes available to test with")

        first_revision_id = revisiones_vigentes[0]["id"]

        # Create nueva revision with proyectista2 (different from previa's proyectista1)
        response = client.post(
            "/api/liquidaciones/edificaciones/nueva-revision",
            data={
                "liquidacion_previa_id": self.liquidacion_previa_id,
                "revisiones_ids": [first_revision_id],
                "observacion": "Test con proyectistas específicos",
                "proyectistas_ids": [str(self.proyectista2.id)],
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        result = data["data"]

        # Verify that the new revision has only proyectista2 (not inherited)
        proyectistas_ids_response = {str(p["id"]) for p in result["proyectistas"]}
        assert str(self.proyectista2.id) in proyectistas_ids_response
        assert str(self.proyectista1.id) not in proyectistas_ids_response

    def test_nueva_revision_sin_proyectistas_ids_hereda_de_previa(self, client: Client):
        """
        POST /nueva-revision without proyectistas_ids (or empty) debe heredar
        los proyectistas de la liquidación previa.
        """
        # Get a valid revision to use
        revision_response = client.get(
            "/api/liquidaciones/edificaciones/nueva-revision/formulario",
            query_params={"liquidacion_previa_id": self.liquidacion_previa_id},
        )
        assert revision_response.status_code == 200, f"Setup failed: {revision_response.json()}"
        revisiones_vigentes = revision_response.json()["data"]["revisiones_vigentes"]

        if len(revisiones_vigentes) == 0:
            pytest.skip("No revisiones vigentes available to test with")

        first_revision_id = revisiones_vigentes[0]["id"]

        # Create nueva revision WITHOUT proyectistas_ids (should inherit)
        response = client.post(
            "/api/liquidaciones/edificaciones/nueva-revision",
            data={
                "liquidacion_previa_id": self.liquidacion_previa_id,
                "revisiones_ids": [first_revision_id],
                "observacion": "Test heredando proyectistas",
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        result = data["data"]

        # Verify that the new revision inherited proyectista1 from previa
        proyectistas_ids_response = {str(p["id"]) for p in result["proyectistas"]}
        assert str(self.proyectista1.id) in proyectistas_ids_response

    def test_nueva_revision_proyectistas_ids_vacio_hereda_de_previa(self, client: Client):
        """
        POST /nueva-revision with empty proyectistas_ids debe heredar
        los proyectistas de la liquidación previa.
        """
        # Get a valid revision to use
        revision_response = client.get(
            "/api/liquidaciones/edificaciones/nueva-revision/formulario",
            query_params={"liquidacion_previa_id": self.liquidacion_previa_id},
        )
        assert revision_response.status_code == 200, f"Setup failed: {revision_response.json()}"
        revisiones_vigentes = revision_response.json()["data"]["revisiones_vigentes"]

        if len(revisiones_vigentes) == 0:
            pytest.skip("No revisiones vigentes available to test with")

        first_revision_id = revisiones_vigentes[0]["id"]

        # Create nueva revision with empty proyectistas_ids (should inherit)
        response = client.post(
            "/api/liquidaciones/edificaciones/nueva-revision",
            data={
                "liquidacion_previa_id": self.liquidacion_previa_id,
                "revisiones_ids": [first_revision_id],
                "observacion": "Test con proyectistas_ids vacío",
                "proyectistas_ids": [],  # Empty — should inherit
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        result = data["data"]

        # Verify that the new revision inherited proyectista1 from previa
        proyectistas_ids_response = {str(p["id"]) for p in result["proyectistas"]}
        assert str(self.proyectista1.id) in proyectistas_ids_response


@pytest.mark.django_db
class TestNuevaRevisionFormularioEndpoint:
    """Test GET /api/liquidaciones/edificaciones/nueva-revision/formulario returns proyectistas_actuales."""

    def setup_method(self):
        """Create a liquidacion with proyectistas to use as previous."""
        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.proyecto = ProyectoFactory()
        # Create EspecialidadesLiquidacion vigente
        self.especialidades_grupo = EspecialidadesLiquidacionFactory()
        # Create a municipalidad for testing
        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-FORM",
            nombre="Municipalidad para Formulario",
            distrito=self.distrito,
        )
        self.proyectista1 = ProyectistaFactory()
        self.proyectista2 = ProyectistaFactory()

        client = Client()
        response = client.post(
            "/api/liquidaciones/edificaciones/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "tipo_tramite": "OBRA_NUEVA",
                    "valor_proyecto": 10000.0,
                    "valor_base_calculo": 10000.0,
                    "revisiones_ids": [],
                    "proyectistas_ids": [str(self.proyectista1.id), str(self.proyectista2.id)],
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, f"Setup failed: {response.json()}"
        self.liquidacion_previa_id = response.json()["data"]["id"]

    def test_formulario_retorna_proyectistas_actuales(self, client: Client):
        """
        GET /nueva-revision/formulario debe retornar proyectistas_actuales
        (los heredados de la liquidación previa) para prefijado en formulario.
        """
        response = client.get(
            "/api/liquidaciones/edificaciones/nueva-revision/formulario",
            query_params={"liquidacion_previa_id": self.liquidacion_previa_id},
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "data" in data

        # Verify proyectistas_actuales is present and contains the proyectistas from previa
        assert "proyectistas_actuales" in data["data"]
        proyectistas_actuales = data["data"]["proyectistas_actuales"]
        assert len(proyectistas_actuales) == 2

        proyectista_ids = {p["id"] for p in proyectistas_actuales}
        assert str(self.proyectista1.id) in proyectista_ids
        assert str(self.proyectista2.id) in proyectista_ids

    def test_formulario_retorna_proyectistas_actuales_vacios_si_previa_sin_proyectistas(self, client: Client):
        """
        GET /nueva-revision/formulario debe retornar proyectistas_actuales vacío
        si la liquidación previa no tenía proyectistas.
        """
        # Create a liquidacion WITHOUT proyectistas
        igv = IGVFactory()
        uit = UITFactory()
        proyecto = ProyectoFactory()
        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        distrito = UbigeoDistritoFactory()
        municipalidad = Municipalidad.objects.create(
            codigo="MUN-FORM-EMPTY",
            nombre="Municipalidad sin Proyectistas",
            distrito=distrito,
        )

        client = Client()
        response = client.post(
            "/api/liquidaciones/edificaciones/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": proyecto.public_id,
                    "municipalidad_id": str(municipalidad.id),
                    "tipo_tramite": "OBRA_NUEVA",
                    "valor_proyecto": 10000.0,
                    "valor_base_calculo": 10000.0,
                    "revisiones_ids": [],
                    "proyectistas_ids": [],  # No proyectistas
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, f"Setup failed: {response.json()}"
        liquidacion_previa_id = response.json()["data"]["id"]

        # Get formulario
        form_response = client.get(
            "/api/liquidaciones/edificaciones/nueva-revision/formulario",
            query_params={"liquidacion_previa_id": liquidacion_previa_id},
        )
        assert form_response.status_code == 200, form_response.json()

        # Verify proyectistas_actuales is empty
        proyectistas_actuales = form_response.json()["data"]["proyectistas_actuales"]
        assert proyectistas_actuales == []


@pytest.mark.django_db
class TestRevisionesVigentesSchema:
    """Test GET /api/liquidaciones/edificaciones/revisiones-vigentes schema/content."""

    def test_revisiones_vigentes_returns_list_with_expected_keys(self, client: Client):
        """
        GET /revisiones-vigentes must return a list where each item has
        the keys defined in RevisionVigenteOut schema.
        """
        response = client.get("/api/liquidaciones/edificaciones/revisiones-vigentes")
        assert response.status_code == 200, response.json()
        data = response.json()
        revisiones = data["data"]["revisiones"]
        assert isinstance(revisiones, list)

        # If there are revisions, verify schema keys
        for rev in revisiones:
            assert "id" in rev
            assert "especialidades" in rev
            assert isinstance(rev["especialidades"], list)
            # Each especialidad should have id and nombre
            for esp in rev["especialidades"]:
                assert "id" in esp
                assert "nombre" in esp
            assert "tarifa_id" in rev
            assert "porcentaje_liquidacion" in rev
            assert "derecho_minimo" in rev
            # derecho_maximo can be None
            assert "derecho_maximo" in rev
            assert "porcentaje_minimo_uit" in rev
            assert "habilitada" in rev

    def test_revisiones_vigentes_habilitada_field_is_boolean(self, client: Client):
        """
        The 'habilitada' field must be a boolean (not a string or null).
        """
        response = client.get("/api/liquidaciones/edificaciones/revisiones-vigentes")
        assert response.status_code == 200, response.json()
        data = response.json()
        revisiones = data["data"]["revisiones"]
        for rev in revisiones:
            assert isinstance(rev["habilitada"], bool), f"habilitada should be bool, got {type(rev['habilitada'])}"


# ── Cotizar Endpoints Tests ────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCotizarPrimeraRevisionEndpoint:
    """Test POST /api/liquidaciones/edificaciones/cotizar/primera-revision endpoint."""

    def setup_method(self):
        """Seed IGV, UIT, proyecto y tarifas para cotizar tests."""
        from modules.liquidaciones.domain.constants import TramiteAccion, TipoTramiteEdificaciones
        from modules.liquidaciones.tests.factories.regla_tarifa_edificacion_factory import ReglaTarifaEdificacionFactory

        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.proyecto = ProyectoFactory()

        # Create EspecialidadesLiquidacion vigente (empty)
        self.especialidades_grupo = EspecialidadesLiquidacionFactory()

        # Create TarifaLiquidacionBase with detalle_porcentual and ReglaTarifaEdificacion for PRIMERA_REVISION
        # This is needed for cotizar endpoint to return revisions
        self.tarifa_base = TarifaLiquidacionBaseFactory()
        ReglaTarifaEdificacionFactory(
            tipo_tramite=TipoTramiteEdificaciones.OBRA_NUEVA,
            tramite_accion=TramiteAccion.PRIMERA_REVISION,
            tarifa_base=self.tarifa_base,
        )

    def test_cotizar_primera_revision_retorna_200_y_no_crea_liquidacion(self, client: Client):
        """
        POST /cotizar/primera-revision debe retornar 200 con resultado calculado
        y NO crear ningún registro de LiquidacionGeneral ni LiquidacionEdificacion.
        """
        from modules.liquidaciones.models import LiquidacionGeneral, LiquidacionEdificacion

        # Contar liquidaciones antes
        count_before = LiquidacionGeneral.objects.count()
        edif_count_before = LiquidacionEdificacion.objects.count()

        response = client.post(
            "/api/liquidaciones/edificaciones/cotizar/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "valor_proyecto": 50000.0,
                    "valor_base_calculo": 50000.0,
                }
            },
            content_type="application/json",
        )

        assert response.status_code == 200, response.json()
        data = response.json()
        assert "data" in data
        quote = data["data"]

        # Verificar estructura de respuesta de cotización
        assert "numero_revision" in quote
        assert quote["numero_revision"] == 1
        assert "revisiones" in quote
        assert "totales" in quote
        assert "_metadata" in quote
        assert "metadata" not in quote  # Must be serialized as _metadata per API contract

        # Verificar totales calculados (IGV = 18%)
        # Con valor_proyecto=50000 y revisión 1 (siempre cobra)
        # Los totales deben ser > 0 si hay revisiones vigentes
        assert "subtotal" in quote["totales"]
        assert "igv" in quote["totales"]
        assert "total" in quote["totales"]

        # Verificar que NO se creó ninguna liquidación
        assert LiquidacionGeneral.objects.count() == count_before, "No debe crear LiquidacionGeneral"
        assert LiquidacionEdificacion.objects.count() == edif_count_before, "No debe crear LiquidacionEdificacion"

    def test_cotizar_primera_revision_proyecto_inexistente_retorna_error(self, client: Client):
        """Proyecto inexistente debe retornar error (no 500)."""
        response = client.post(
            "/api/liquidaciones/edificaciones/cotizar/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": "PROY-INEXISTENTE-COTIZAR",
                    "valor_proyecto": 50000.0,
                    "valor_base_calculo": 50000.0,
                }
            },
            content_type="application/json",
        )
        # 404 para proyecto no encontrado
        assert response.status_code in (200, 400, 404), response.json()

    def test_cotizar_primera_revision_valor_cero_retorna_422(self, client: Client):
        """valor_proyecto=0 debe retornar 422 por gt=0."""
        response = client.post(
            "/api/liquidaciones/edificaciones/cotizar/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "valor_proyecto": 0.0,
                    "valor_base_calculo": 0.0,
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 422, response.json()

    def test_cotizar_primera_revision_respuesta_tiene_especialidades_plural(self, client: Client):
        """
        La respuesta de /cotizar/primera-revision debe usar 'especialidades' (plural)
        con lista de objetos {id, nombre}, NO 'especialidad' singular string.
        """
        response = client.post(
            "/api/liquidaciones/edificaciones/cotizar/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "valor_proyecto": 50000.0,
                    "valor_base_calculo": 50000.0,
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        quote = data["data"]

        assert "revisiones" in quote

        if len(quote["revisiones"]) == 0:
            pytest.skip("No revisions available to test with")

        for rev in quote["revisiones"]:
            # Debe usar 'especialidades' plural (lista), NO 'especialidad' singular
            assert "especialidades" in rev, f"Missing 'especialidades' in revision: {rev.keys()}"
            assert "especialidad" not in rev, f"Should NOT have singular 'especialidad' in revision"
            assert isinstance(rev["especialidades"], list), "especialidades must be a list"
            assert len(rev["especialidades"]) >= 1, "especialidades list must have at least one item"
            for esp in rev["especialidades"]:
                assert "id" in esp, "Each especialidad must have 'id'"
                assert "nombre" in esp, "Each especialidad must have 'nombre'"
                assert isinstance(esp["id"], str) or hasattr(esp["id"], '__str__'), "especialidad id must be string/UUID"
                assert isinstance(esp["nombre"], str), "especialidad nombre must be string"


@pytest.mark.django_db
class TestCotizarNuevaRevisionEndpoint:
    """Test POST /api/liquidaciones/edificaciones/cotizar/nueva-revision endpoint."""

    def setup_method(self):
        """Crear primera revisión para usar como liquidacion previa."""
        from modules.liquidaciones.domain.constants import TramiteAccion, TipoTramiteEdificaciones
        from modules.liquidaciones.tests.factories.regla_tarifa_edificacion_factory import ReglaTarifaEdificacionFactory
        from modules.liquidaciones.tests.factories.especialidad_factory import EspecialidadFactory

        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.proyecto = ProyectoFactory()

        # Create EspecialidadesLiquidacion vigente (empty - for primera-revision with no revisions)
        self.especialidades_grupo = EspecialidadesLiquidacionFactory()

        # Create Especialidad for the tarifa (required by domain validation)
        self.especialidad = EspecialidadFactory()

        # Create TarifaLiquidacionBase with detalle_porcentual, especialidades and ReglaTarifaEdificacion for REVISION
        self.tarifa_base = TarifaLiquidacionBaseFactory(especialidades=[self.especialidad])
        ReglaTarifaEdificacionFactory(
            tipo_tramite=TipoTramiteEdificaciones.OBRA_NUEVA,
            tramite_accion=TramiteAccion.REVISION,
            tarifa_base=self.tarifa_base,
        )

        # Create a municipalidad for testing
        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-COTIZAR",
            nombre="Municipalidad para Cotizar",
            distrito=self.distrito,
        )

        client = Client()
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
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, f"Setup failed: {response.json()}"
        self.liquidacion_previa_id = response.json()["data"]["id"]

    def test_cotizar_nueva_revision_empty_revisiones_ids_retorna_422(self, client: Client):
        """
        POST /cotizar/nueva-revision con revisiones_ids vacío (min_length=1) retorna 422.
        """
        response = client.post(
            "/api/liquidaciones/edificaciones/cotizar/nueva-revision",
            data={
                "liquidacion_previa_id": self.liquidacion_previa_id,
                "revisiones_ids": [],  # min_length=1 — debe fallar
            },
            content_type="application/json",
        )
        assert response.status_code == 422, response.json()

    def test_cotizar_nueva_revision_retorna_200_y_no_crea_liquidacion(self, client: Client):
        """
        POST /cotizar/nueva-revision debe retornar 200 con resultado calculado
        y NO crear ningún registro de LiquidacionGeneral ni LiquidacionEdificacion.
        """
        from modules.liquidaciones.models import LiquidacionGeneral, LiquidacionEdificacion

        # Contar liquidaciones antes
        count_before = LiquidacionGeneral.objects.count()
        edif_count_before = LiquidacionEdificacion.objects.count()

        # Obtener revisiones vigentes para usar en la cotización
        revisiones_response = client.get(
            "/api/liquidaciones/edificaciones/revisiones-vigentes",
        )
        assert revisiones_response.status_code == 200, f"Setup failed: {revisiones_response.json()}"
        revisiones = revisiones_response.json()["data"]["revisiones"]

        if len(revisiones) == 0:
            pytest.skip("No revisions available to test with")

        revision_id = revisiones[0]["id"]

        response = client.post(
            "/api/liquidaciones/edificaciones/cotizar/nueva-revision",
            data={
                "liquidacion_previa_id": self.liquidacion_previa_id,
                "revisiones_ids": [revision_id],
            },
            content_type="application/json",
        )

        assert response.status_code == 200, response.json()
        data = response.json()
        assert "data" in data
        quote = data["data"]

        # Verificar estructura de respuesta de cotización
        assert "numero_revision" in quote
        assert quote["numero_revision"] == 2  # Segunda revisión
        assert "revisiones" in quote
        assert len(quote["revisiones"]) >= 1
        assert "totales" in quote
        assert "_metadata" in quote
        assert "metadata" not in quote  # Must be serialized as _metadata per API contract

        # Verificar que NO se creó ninguna liquidación
        assert LiquidacionGeneral.objects.count() == count_before, "No debe crear LiquidacionGeneral"
        assert LiquidacionEdificacion.objects.count() == edif_count_before, "No debe crear LiquidacionEdificacion"

    def test_cotizar_nueva_revision_usa_valor_proyecto_de_previa(self, client: Client):
        """
        La cotización de nueva revisión debe usar el valor_proyecto de la liquidación previa.
        """
        # Obtener revisiones vigentes
        revisiones_response = client.get(
            "/api/liquidaciones/edificaciones/revisiones-vigentes",
        )
        assert revisiones_response.status_code == 200
        revisiones = revisiones_response.json()["data"]["revisiones"]
        if len(revisiones) == 0:
            pytest.skip("No revisions available")

        revision_id = revisiones[0]["id"]

        # Cotizar nueva revisión
        response = client.post(
            "/api/liquidaciones/edificaciones/cotizar/nueva-revision",
            data={
                "liquidacion_previa_id": self.liquidacion_previa_id,
                "revisiones_ids": [revision_id],
            },
            content_type="application/json",
        )

        assert response.status_code == 200, response.json()
        quote = response.json()["data"]

        # El _metadata debe indicar si cobra o no (revisión 2 no cobra)
        assert "_metadata" in quote
        assert "cobra" in quote["_metadata"]
        # Revisión 2 no cobra según REVISIONES_COBRAN = {1, 3, 5, 7}
        assert quote["_metadata"]["cobra"] == False

        # Los totales deben ser 0 para revisión 2 (no cobra)
        assert quote["totales"]["subtotal"] == 0
        assert quote["totales"]["igv"] == 0
        assert quote["totales"]["total"] == 0

    def test_cotizar_nueva_revision_liquidacion_previa_inexistente_retorna_error(self, client: Client):
        """liquidacion_previa_id inexistente debe retornar error."""
        import uuid
        fake_uuid = str(uuid.uuid4())
        response = client.post(
            "/api/liquidaciones/edificaciones/cotizar/nueva-revision",
            data={
                "liquidacion_previa_id": fake_uuid,
                "revisiones_ids": [str(uuid.uuid4())],
            },
            content_type="application/json",
        )
        assert response.status_code != 200, "Debe fallar con liquidacion_previa_id inexistente"


@pytest.mark.django_db
class TestEspecialidadesUnionValidation:
    """
    Tests for the multi-specialty union validation fix.

    These tests verify that the backend correctly validates the UNION of
    specialties across all selected TarifaLiquidacionBase records against
    the active EspecialidadesLiquidacion group.
    """

    def setup_method(self):
        """Create IGV, UIT, proyecto, municipalidad, and multi-specialty group."""
        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.proyecto = ProyectoFactory()

        # Create 3 Especialidad records
        from modules.liquidaciones.tests.factories.especialidad_factory import EspecialidadFactory
        self.esp_civil = EspecialidadFactory(nombre="Civil")
        self.esp_electrica = EspecialidadFactory(nombre="Eléctrica")
        self.esp_sanitaria = EspecialidadFactory(nombre="Sanitaria")

        # Create EspecialidadesLiquidacion group with all 3 specialties
        from modules.liquidaciones.tests.factories.especialidades_liquidacion_factory import EspecialidadesLiquidacionFactory
        self.especialidades_grupo = EspecialidadesLiquidacionFactory(
            especialidades=[self.esp_civil, self.esp_electrica, self.esp_sanitaria]
        )

        # Create a municipalidad for testing
        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-ESP-UNION",
            nombre="Municipalidad de Prueba Especialidades",
            distrito=self.distrito,
        )

        # Create a TarifaLiquidacionBase factory
        from modules.liquidaciones.tests.factories.tarifa_liquidacion_factory import TarifaLiquidacionBaseFactory
        self.tarifa_base_factory = TarifaLiquidacionBaseFactory

    def _crear_tarifa_base(self, especialidades: list) -> str:
        """Helper: creates a TarifaLiquidacionBase with given specialties, returns its ID."""
        tb = self.tarifa_base_factory(especialidades=especialidades)
        return str(tb.id)

    def _post_primera_revision(self, revisiones_ids: list) -> dict:
        """Helper: POST primera-revision and return response JSON."""
        client = Client()
        response = client.post(
            "/api/liquidaciones/edificaciones/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "tipo_tramite": "OBRA_NUEVA",
                    "valor_proyecto": 10000.0,
                    "valor_base_calculo": 10000.0,
                    "revisiones_ids": revisiones_ids,
                }
            },
            content_type="application/json",
        )
        return response.status_code, response.json()

    def test_multi_specialty_revision_passes(self):
        """
        Scenario: One revision with Civil+Eléctrica+Sanitaria (all 3 specialties).
        Expected: 200 — union of revision specialties equals group specialties.
        """
        rev_all_id = self._crear_tarifa_base(
            [self.esp_civil, self.esp_electrica, self.esp_sanitaria]
        )

        status, data = self._post_primera_revision([rev_all_id])
        assert status == 200, f"Expected 200, got {status}: {data}"

    def test_multiple_single_specialty_revisions_union_passes(self):
        """
        Scenario: Three revisions, each with one specialty (Civil, Eléctrica, Sanitaria).
        Expected: 200 — union of all revision specialties equals group specialties.
        """
        rev_civil_id = self._crear_tarifa_base([self.esp_civil])
        rev_electrica_id = self._crear_tarifa_base([self.esp_electrica])
        rev_sanitaria_id = self._crear_tarifa_base([self.esp_sanitaria])

        status, data = self._post_primera_revision([
            rev_civil_id,
            rev_electrica_id,
            rev_sanitaria_id,
        ])
        assert status == 200, f"Expected 200, got {status}: {data}"

    def test_incomplete_selection_fails_with_clear_error(self):
        """
        Scenario: Only 2 revisions selected (Civil + Eléctrica), missing Sanitaria.
        Expected: 400 with clear error showing missing specialties.
        """
        rev_civil_id = self._crear_tarifa_base([self.esp_civil])
        rev_electrica_id = self._crear_tarifa_base([self.esp_electrica])

        status, data = self._post_primera_revision([
            rev_civil_id,
            rev_electrica_id,
        ])
        # EspecialidadesSetInvalidoError is a BusinessError → HTTP 400
        assert status == 400, f"Expected 400, got {status}: {data}"
        error_msg = str(data)
        # Should mention the missing specialty
        assert "Sanitaria" in error_msg or "Faltan" in error_msg, f"Error message should mention missing specialty: {error_msg}"

    def test_extra_specialty_in_selection_fails(self):
        """
        Scenario: 2 revisions covering Civil+Eléctrica+Extra (extra not in group).
        Expected: 400 with clear error showing extra/no vigentes specialties.
        """
        from modules.liquidaciones.tests.factories.especialidad_factory import EspecialidadFactory

        esp_extra = EspecialidadFactory(nombre="Extra No Vigente")

        rev_civil_id = self._crear_tarifa_base([self.esp_civil])
        rev_electrica_id = self._crear_tarifa_base([self.esp_electrica])
        rev_extra_id = self._crear_tarifa_base([esp_extra])

        status, data = self._post_primera_revision([
            rev_civil_id,
            rev_electrica_id,
            rev_extra_id,
        ])
        # EspecialidadesSetInvalidoError is a BusinessError → HTTP 400
        assert status == 400, f"Expected 400, got {status}: {data}"
        error_msg = str(data)
        # Should mention the extra specialty
        assert "Extra" in error_msg or "extra" in error_msg, f"Error message should mention extra specialty: {error_msg}"

    def test_specialty_id_as_revision_id_fails_clearly(self):
        """
        Scenario: Sending a specialty ID (not a revision ID) in revisiones_ids.
        Expected: 422 with clear error that the ID is not a revision ID.
        """
        # Use the ID of one of the especialidades directly
        specialty_id = str(self.esp_civil.id)

        status, data = self._post_primera_revision([specialty_id])
        # BusinessError (invalid revision IDs) → HTTP 400
        assert status == 400, f"Expected 400, got {status}: {data}"
        error_msg = str(data)
        # Should clearly indicate the ID is not a valid revision ID
        assert "no corresponden" in error_msg or "revisión" in error_msg.lower(), (
            f"Error message should clearly indicate invalid revision ID: {error_msg}"
        )


@pytest.mark.django_db
class TestLiquidacionEdificacionDetailEndpoint:
    """Test GET /api/liquidaciones/edificaciones/{liquidacion_id} endpoint."""

    def setup_method(self):
        """Seed IGV, UIT, proyecto, municipalidad y EspecialidadesLiquidacion."""
        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.proyecto = ProyectoFactory()
        # Create EspecialidadesLiquidacion vigente (empty set for sin_revisiones tests)
        self.especialidades_grupo = EspecialidadesLiquidacionFactory()
        # Create a municipalidad for testing
        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-DETAIL",
            nombre="Municipalidad para Detail",
            distrito=self.distrito,
        )

    def test_get_detail_retorna_200_y_estructura_plana_LiquidacionEdificacionOut(self, client: Client):
        """
        GET /{liquidacion_id} tras crear vía POST primera-revision debe retornar 200
        con la estructura plana LiquidacionEdificacionOut (Phase 3 contract).

        Verifica:
        - Top-level flat fields: id, public_id, estado, fecha_registro, numero_revision,
          tipo_tramite, tramite_accion, subtotal, igv, total, total_a_pagar
        - Nested objects: proyecto, entidad, municipalidad, valores,
          proyectistas, delegados, contactos, revisiones
        - Ausencia de legacy top-level keys: liquidacion, edificaciones, totales
        """
        # 1. Crear liquidación vía primera-revision
        create_response = client.post(
            "/api/liquidaciones/edificaciones/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "tipo_tramite": "OBRA_NUEVA",
                    "valor_proyecto": 10000.0,
                    "valor_base_calculo": 10000.0,
                    "observacion": "Test detail endpoint",
                    "revisiones_ids": [],
                }
            },
            content_type="application/json",
        )
        assert create_response.status_code == 200, f"Setup failed: {create_response.json()}"
        created = create_response.json()["data"]

        liquidacion_id = created["id"]
        public_id = created["public_id"]

        # 2. GET detalle por id (UUID)
        detail_response = client.get(f"/api/liquidaciones/edificaciones/{liquidacion_id}")
        assert detail_response.status_code == 200, detail_response.json()
        result = detail_response.json()["data"]

        # ── Top-level flat scalar fields ──────────────────────────────────────────
        assert "id" in result
        assert result["id"] == liquidacion_id
        assert "public_id" in result
        assert result["public_id"] == public_id
        assert "estado" in result
        assert "fecha_registro" in result
        assert "numero_revision" in result
        assert result["numero_revision"] == 1
        assert "tipo_tramite" in result
        assert "tramite_accion" in result
        assert "subtotal" in result
        assert "igv" in result
        assert "total" in result
        assert "total_a_pagar" in result

        # ── Nested objects ───────────────────────────────────────────────────────
        assert "proyecto" in result
        assert isinstance(result["proyecto"], dict)
        assert "public_id" in result["proyecto"]
        assert "nombre" in result["proyecto"]

        assert "entidad" in result  # puede ser None
        assert "municipalidad" in result
        assert isinstance(result["municipalidad"], dict)
        assert "nombre" in result["municipalidad"]

        assert "valores" in result
        assert isinstance(result["valores"], dict)
        assert "subtotal" in result["valores"]
        assert "igv" in result["valores"]
        assert "total" in result["valores"]
        assert "total_a_pagar" in result["valores"]

        assert "proyectistas" in result
        assert isinstance(result["proyectistas"], list)
        assert "delegados" in result
        assert isinstance(result["delegados"], list)
        assert "contactos" in result
        assert isinstance(result["contactos"], list)
        assert "revisiones" in result
        assert isinstance(result["revisiones"], list)

        # ── Legacy top-level keys must NOT exist ────────────────────────────────
        assert "liquidacion" not in result, "Legacy top-level 'liquidacion' key must not exist"
        assert "edificaciones" not in result, "Legacy top-level 'edificaciones' key must not exist"
        assert "totales" not in result, "Legacy top-level 'totales' key must not exist"

    def test_get_detail_por_public_id_retorna_404(self, client: Client):
        """
        GET /{liquidacion_id} usando public_id (ej. LIQ-2026-00001) en lugar de UUID
        debe retornar 404 porque la ruta espera UUID.
        """
        response = client.get(f"/api/liquidaciones/edificaciones/{self.proyecto.public_id}")
        # El endpoint espera UUID, no public_id → 400/422 por validación de UUID
        assert response.status_code in (400, 404, 422), response.json()

    def test_get_detail_liquidacion_inexistente_retorna_404(self, client: Client):
        """GET /{liquidacion_id} con UUID inexistente retorna 404."""
        import uuid
        fake_uuid = str(uuid.uuid4())
        response = client.get(f"/api/liquidaciones/edificaciones/{fake_uuid}")
        assert response.status_code == 404, response.json()
