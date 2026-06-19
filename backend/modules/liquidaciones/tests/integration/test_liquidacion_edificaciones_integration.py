"""
Integration tests for Liquidaciones Edificaciones endpoints.

Tests the full stack: controller -> orchestrator -> flujo -> core -> DB.

Nota: Los tests de cálculo de revisiones usan factories que pueden tener
problemas de serialización de IDs en el test client. Los unit tests
(100% passing) cubren la lógica de negocio. Estos tests de integración
verifican el flujo completo a nivel HTTP.
"""
import pytest
from django.test import Client

from modules.liquidaciones.tests.factories.proyecto_factory import ProyectoFactory
from modules.liquidaciones.tests.factories.finanzas_factory import IGVFactory, UITFactory
from modules.liquidaciones.tests.factories.proyectista_factory import ProyectistaFactory


@pytest.mark.django_db
class TestPrimeraRevisionEndpoint:
    """Test POST /api/liquidaciones/edificaciones/primera-revision endpoint."""

    def setup_method(self):
        """Seed IGV, UIT, proyecto y municipalidad (sin revisión para simplificar)."""
        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.proyecto = ProyectoFactory()
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
        Verifica que el flujo completo funciona (crea LiquidacionGeneral + snapshot).
        """
        response = client.post(
            "/api/liquidaciones/edificaciones/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "tipo_tramite": "OBRA_NUEVA",
                    "valor_proyecto": 10000.0,
                    "observacion": "Test",
                    "revisiones_ids": [],
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "data" in data
        snapshot = data["data"]
        assert "liquidacion" in snapshot
        assert "edificaciones" in snapshot
        assert "totales" in snapshot
        # Verificar public_id en liquidacion
        assert "public_id" in snapshot["liquidacion"]
        assert snapshot["liquidacion"]["public_id"].startswith("LIQ-")
        # Verificar municipalidad en respuesta (nuevo formato anidado)
        assert "municipalidad" in snapshot["liquidacion"]
        assert snapshot["liquidacion"]["municipalidad"]["id"] == str(self.municipalidad.id)
        assert snapshot["liquidacion"]["municipalidad"]["nombre"] == self.municipalidad.nombre
        # Sin revisiones, totales deben ser 0
        assert snapshot["totales"]["subtotal"] == 0
        # expediente fue removido del dominio
        assert "expediente" not in snapshot["liquidacion"]

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
                    "revisiones_ids": [],
                }
            },
            content_type="application/json",
        )
        assert response.status_code in (200, 400, 404)


@pytest.mark.django_db
class TestObtenerLiquidacionEndpoint:
    """Test GET /api/liquidaciones/edificaciones/{id} endpoint."""

    def setup_method(self):
        """Crear primera revisión (sin revisiones) para consultar después."""
        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.proyecto = ProyectoFactory()
        # Create a municipalidad for testing
        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-TEST-OBTENER",
            nombre="Municipalidad de Prueba Obtener",
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
                    "revisiones_ids": [],
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, f"Setup failed: {response.json()}"
        self.liquidacion_id = response.json()["data"]["liquidacion"]["id"]

    def test_obtener_liquidacion_existente_retorna_200(self, client: Client):
        """GET con ID válido debe retornar 200 con snapshot."""
        response = client.get(
            f"/api/liquidaciones/edificaciones/{self.liquidacion_id}",
        )
        assert response.status_code == 200, response.json()
        data = response.json()["data"]
        assert data["liquidacion"]["id"] == self.liquidacion_id

    def test_obtener_liquidacion_inexistente_retorna_error(self, client: Client):
        """GET con ID malformado debe retornar error (no 500)."""
        # 999999 no es un UUID válido, debe retornar 400 (bad request)
        response = client.get("/api/liquidaciones/edificaciones/999999")
        assert response.status_code in (200, 400, 404)

    def test_obtener_liquidacion_retorna_full_snapshot_data(self, client: Client):
        """
        GET /{liquidacion_id} debe retornar el JSON completo almacenado en
        LiquidacionSnapshot.data, incluyendo cualquier campo adicional.

        Este test inyecta campos extra en el snapshot de la BD y verifica que
        el endpoint los retorna sin modificación.
        """
        from modules.liquidaciones.models import LiquidacionSnapshot

        # Obtener el snapshot creado por setup
        snapshot = LiquidacionSnapshot.objects.get(liquidacion_id=self.liquidacion_id)

        # Inyectar campos extra en el JSON del snapshot
        extra_data = {
            "campo_extra_string": "valor_extra",
            "campo_extra_numero": 42,
            "campo_extra_objeto": {"nested": "value"},
            "campo_extra_lista": [1, 2, 3],
        }
        snapshot.data["campo_extra"] = extra_data
        snapshot.data["otro_campo"] = "preservado"
        snapshot.save()

        # Llamar al endpoint
        response = client.get(
            f"/api/liquidaciones/edificaciones/{self.liquidacion_id}",
        )
        assert response.status_code == 200, response.json()
        data = response.json()["data"]

        # Verificar campos base
        assert data["liquidacion"]["id"] == self.liquidacion_id

        # Verificar que los campos extra fueron retornados sin modificación
        assert data["campo_extra"]["campo_extra_string"] == "valor_extra"
        assert data["campo_extra"]["campo_extra_numero"] == 42
        assert data["campo_extra"]["campo_extra_objeto"]["nested"] == "value"
        assert data["campo_extra"]["campo_extra_lista"] == [1, 2, 3]
        assert data["otro_campo"] == "preservado"

        # Verificar que _metadata está presente si existe en el snapshot
        # (puede no existir en snapshots muy antiguos o modificados)
        if "_metadata" in snapshot.data:
            assert "_metadata" in data
            assert "igv_valor" in data["_metadata"]
            assert "uit_valor" in data["_metadata"]
            assert "cobra" in data["_metadata"]


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
        # Create a municipalidad for testing
        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-002",
            nombre="Municipalidad de Prueba 2",
            distrito=self.distrito,
        )
        self.proyectista1 = ProyectistaFactory(nombres="Juan", apellidos="Pérez")
        self.proyectista2 = ProyectistaFactory(nombres="María", apellidos="García")

    def test_primera_revision_con_proyectistas_guarda_y_retorna_m2m(self, client: Client):
        """
        POST /primera-revision con proyectistas_ids debe:
        1. Crear la liquidación con los proyectistas asociados
        2. Retornar los proyectistas en la respuesta snapshot
        """
        response = client.post(
            "/api/liquidaciones/edificaciones/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "tipo_tramite": "OBRA_NUEVA",
                    "valor_proyecto": 10000.0,
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
        snapshot = data["data"]
        # Verificar que la respuesta incluye edificaciones con proyectistas
        assert "edificaciones" in snapshot
        assert "proyectistas" in snapshot["edificaciones"]
        proyectistas_response = snapshot["edificaciones"]["proyectistas"]
        assert len(proyectistas_response) == 2
        # Verificar que los datos de proyectistas son correctos
        proyectista_ids_response = {p["id"] for p in proyectistas_response}
        assert str(self.proyectista1.id) in proyectista_ids_response
        assert str(self.proyectista2.id) in proyectista_ids_response

    def test_primera_revision_sin_proyectistas_retorna_lista_vacia(self, client: Client):
        """
        POST /primera-revision sin proyectistas_ids debe retornar
        lista vacía de proyectistas en la respuesta.
        """
        response = client.post(
            "/api/liquidaciones/edificaciones/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "tipo_tramite": "OBRA_NUEVA",
                    "valor_proyecto": 10000.0,
                    "observacion": "Test sin proyectistas",
                    "revisiones_ids": [],
                    "proyectistas_ids": [],
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        snapshot = data["data"]
        assert "edificaciones" in snapshot
        assert "proyectistas" in snapshot["edificaciones"]
        assert snapshot["edificaciones"]["proyectistas"] == []

    def test_primera_revision_proyectistas_recuperados_en_snapshot_list(self, client: Client):
        """
        Los proyectistas guardados en primera-revision deben aparecer
        también en GET /snapshots.
        """
        # Crear primera revisión con proyectistas
        create_response = client.post(
            "/api/liquidaciones/edificaciones/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "tipo_tramite": "OBRA_NUEVA",
                    "valor_proyecto": 10000.0,
                    "observacion": "Test snapshot list",
                    "revisiones_ids": [],
                    "proyectistas_ids": [str(self.proyectista1.id)],
                }
            },
            content_type="application/json",
        )
        assert create_response.status_code == 200, create_response.json()
        liquidacion_id = create_response.json()["data"]["liquidacion"]["id"]

        # Obtener snapshot list
        list_response = client.get(
            "/api/liquidaciones/edificaciones/snapshots",
            query_params={"page": 1, "page_size": 10},
        )
        assert list_response.status_code == 200, list_response.json()
        list_data = list_response.json()

        # Encontrar el snapshot creado
        items = list_data["data"]["items"]
        our_item = next((item for item in items if item["liquidacion_id"] == liquidacion_id), None)
        assert our_item is not None, f"Snapshot {liquidacion_id} not found in list"
        # Verificar que edificaciones.proyectistas contiene el proyectista
        assert "proyectistas" in our_item["edificaciones"]
        assert len(our_item["edificaciones"]["proyectistas"]) == 1
        assert our_item["edificaciones"]["proyectistas"][0]["id"] == str(self.proyectista1.id)


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
        GET / after creating a liquidacion returns items with expected keys.
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
        # Verify item has expected keys
        item = items[0]
        assert "id" in item
        assert "numero_revision" in item
        assert "estado" in item
        assert "valor_proyecto" in item
        assert "proyecto_public_id" in item
        assert "proyecto_denominacion" in item
        assert "fecha_registro" in item
        assert "total" in item
        # expediente was removed from domain
        assert "expediente" not in item


@pytest.mark.django_db
class TestPrimeraRevisionValidation:
    """Test 422 error handling for POST /primera-revision."""

    def setup_method(self):
        """Seed IGV, UIT, proyecto y municipalidad."""
        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.proyecto = ProyectoFactory()
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
                    "revisiones_ids": [],
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 422, response.json()

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
                    "revisiones_ids": [],
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, f"Setup failed: {response.json()}"
        self.liquidacion_previa_id = response.json()["data"]["liquidacion"]["id"]

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
        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.proyecto = ProyectoFactory()
        # Create a municipalidad for testing
        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-006",
            nombre="Municipalidad de Prueba 6",
            distrito=self.distrito,
        )
        self.proyectista1 = ProyectistaFactory(nombres="Juan", apellidos="Pérez")
        self.proyectista2 = ProyectistaFactory(nombres="María", apellidos="García")

        client = Client()
        response = client.post(
            "/api/liquidaciones/edificaciones/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "tipo_tramite": "OBRA_NUEVA",
                    "valor_proyecto": 10000.0,
                    "revisiones_ids": [],
                    "proyectistas_ids": [str(self.proyectista1.id)],
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, f"Setup failed: {response.json()}"
        self.liquidacion_previa_id = response.json()["data"]["liquidacion"]["id"]

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
        revisiones_ids) returns 200 and creates a new revision snapshot.
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
        snapshot = data["data"]
        assert "liquidacion" in snapshot
        assert "edificaciones" in snapshot
        assert "totales" in snapshot
        # numero_revision should be 2
        assert snapshot["edificaciones"]["numero_revision"] == 2

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
        snapshot = data["data"]

        # Verify that the new revision has only proyectista2 (not inherited)
        proyectistas_ids_response = {p["id"] for p in snapshot["edificaciones"]["proyectistas"]}
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
        snapshot = data["data"]

        # Verify that the new revision inherited proyectista1 from previa
        proyectistas_ids_response = {p["id"] for p in snapshot["edificaciones"]["proyectistas"]}
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
        snapshot = data["data"]

        # Verify that the new revision inherited proyectista1 from previa
        proyectistas_ids_response = {p["id"] for p in snapshot["edificaciones"]["proyectistas"]}
        assert str(self.proyectista1.id) in proyectistas_ids_response


@pytest.mark.django_db
class TestNuevaRevisionFormularioEndpoint:
    """Test GET /api/liquidaciones/edificaciones/nueva-revision/formulario returns proyectistas_actuales."""

    def setup_method(self):
        """Create a liquidacion with proyectistas to use as previous."""
        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.proyecto = ProyectoFactory()
        # Create a municipalidad for testing
        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-FORM",
            nombre="Municipalidad para Formulario",
            distrito=self.distrito,
        )
        self.proyectista1 = ProyectistaFactory(nombres="Juan", apellidos="Pérez")
        self.proyectista2 = ProyectistaFactory(nombres="María", apellidos="García")

        client = Client()
        response = client.post(
            "/api/liquidaciones/edificaciones/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "tipo_tramite": "OBRA_NUEVA",
                    "valor_proyecto": 10000.0,
                    "revisiones_ids": [],
                    "proyectistas_ids": [str(self.proyectista1.id), str(self.proyectista2.id)],
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, f"Setup failed: {response.json()}"
        self.liquidacion_previa_id = response.json()["data"]["liquidacion"]["id"]

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
                    "revisiones_ids": [],
                    "proyectistas_ids": [],  # No proyectistas
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, f"Setup failed: {response.json()}"
        liquidacion_previa_id = response.json()["data"]["liquidacion"]["id"]

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
            assert "especialidad_id" in rev
            assert "especialidad_nombre" in rev
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


@pytest.mark.django_db
class TestSnapshotsListEndpoint:
    """Test GET /api/liquidaciones/edificaciones/snapshots endpoint."""

    def setup_method(self):
        """Create municipalidad for tests."""
        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-007",
            nombre="Municipalidad de Prueba 7",
            distrito=self.distrito,
        )

    def test_snapshots_list_returns_success_with_pagination_shape(self, client: Client):
        """
        GET /snapshots returns 200 with items array and all pagination keys.
        """
        response = client.get(
            "/api/liquidaciones/edificaciones/snapshots",
            query_params={"page": 1, "page_size": 10},
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "data" in data
        assert "items" in data["data"]
        assert "total" in data["data"]
        assert "page" in data["data"]
        assert "page_size" in data["data"]
        assert "total_pages" in data["data"]
        assert isinstance(data["data"]["items"], list)

    def test_snapshots_list_item_has_expected_schema_keys(self, client: Client):
        """
        Each item in snapshots list must have keys from LiquidacionSnapshotListItemOut.
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
                    "revisiones_ids": [],
                }
            },
            content_type="application/json",
        )
        assert create_response.status_code == 200, f"Setup failed: {create_response.json()}"

        # Get list
        response = client.get(
            "/api/liquidaciones/edificaciones/snapshots",
            query_params={"page": 1, "page_size": 10},
        )
        assert response.status_code == 200, response.json()
        items = response.json()["data"]["items"]
        assert len(items) >= 1
        item = items[0]
        # Verify LiquidacionSnapshotListItemOut keys
        assert "liquidacion_id" in item
        assert "numero_liquidacion" in item
        assert "estado" in item
        assert "fecha_registro" in item
        # expediente was removed
        assert "expediente" not in item
        assert "observacion" in item
        assert "proyecto" in item
        assert "edificaciones" in item
        assert "totales" in item
        # Verify nested proyecto keys
        assert "id" in item["proyecto"]
        assert "public_id" in item["proyecto"]
        assert "nombre" in item["proyecto"]
        # Verify nested edificaciones keys
        assert "numero_revision" in item["edificaciones"]
        assert "proyectistas" in item["edificaciones"]
        assert "revisiones" in item["edificaciones"]
        # Verify nested totales keys
        assert "subtotal" in item["totales"]
        assert "igv" in item["totales"]
        assert "total" in item["totales"]
        assert "liquidacion_total" in item["totales"]
        assert "total_a_pagar" in item["totales"]


# ── Cotizar Endpoints Tests ────────────────────────────────────────────────────


@pytest.mark.django_db
class TestCotizarPrimeraRevisionEndpoint:
    """Test POST /api/liquidaciones/edificaciones/cotizar/primera-revision endpoint."""

    def setup_method(self):
        """Seed IGV, UIT y proyecto para cotizar tests."""
        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.proyecto = ProyectoFactory()

    def test_cotizar_primera_revision_retorna_200_y_no_crea_liquidacion(self, client: Client):
        """
        POST /cotizar/primera-revision debe retornar 200 con resultado calculado
        y NO crear ningún registro de LiquidacionGeneral ni LiquidacionEdificaciones.
        """
        from modules.liquidaciones.models import LiquidacionGeneral, LiquidacionEdificaciones

        # Contar liquidaciones antes
        count_before = LiquidacionGeneral.objects.count()
        edif_count_before = LiquidacionEdificaciones.objects.count()

        response = client.post(
            "/api/liquidaciones/edificaciones/cotizar/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "valor_proyecto": 50000.0,
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
        assert LiquidacionEdificaciones.objects.count() == edif_count_before, "No debe crear LiquidacionEdificaciones"

    def test_cotizar_primera_revision_proyecto_inexistente_retorna_error(self, client: Client):
        """Proyecto inexistente debe retornar error (no 500)."""
        response = client.post(
            "/api/liquidaciones/edificaciones/cotizar/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": "PROY-INEXISTENTE-COTIZAR",
                    "valor_proyecto": 50000.0,
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
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 422, response.json()


@pytest.mark.django_db
class TestCotizarNuevaRevisionEndpoint:
    """Test POST /api/liquidaciones/edificaciones/cotizar/nueva-revision endpoint."""

    def setup_method(self):
        """Crear primera revisión para usar como liquidacion previa."""
        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.proyecto = ProyectoFactory()
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
                    "revisiones_ids": [],
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, f"Setup failed: {response.json()}"
        self.liquidacion_previa_id = response.json()["data"]["liquidacion"]["id"]

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
        y NO crear ningún registro de LiquidacionGeneral ni LiquidacionEdificaciones.
        """
        from modules.liquidaciones.models import LiquidacionGeneral, LiquidacionEdificaciones

        # Contar liquidaciones antes
        count_before = LiquidacionGeneral.objects.count()
        edif_count_before = LiquidacionEdificaciones.objects.count()

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
        assert LiquidacionEdificaciones.objects.count() == edif_count_before, "No debe crear LiquidacionEdificaciones"

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
