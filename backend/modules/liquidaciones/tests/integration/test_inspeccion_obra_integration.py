"""
Integration tests for Inspección de Obra liquidaciones via HTTP endpoint.

Tests the full stack: controller -> orchestrator -> flujo -> core -> DB.

Uses Django test client like existing edificaciones integration tests.
"""
import pytest
from decimal import Decimal

from django.test import Client

from modules.liquidaciones.tests.factories.proyecto_factory import ProyectoFactory
from modules.liquidaciones.tests.factories.finanzas_factory import IGVFactory, UITFactory
from modules.liquidaciones.tests.factories.tarifas_test_factory import (
    TarifaLiquidacionBaseVisitasFactory,
    TarifaPorCategoriaVisitasFactory,
    ReglaTarifaInspeccionObraFactory,
)
from modules.liquidaciones.models import (
    LiquidacionGeneral,
    LiquidacionInspeccionObra,
    LiquidacionPorCategoriaVisitas,
    LiquidacionProyectista,
)
from modules.liquidaciones.tests.factories.especialidad_factory import EspecialidadFactory


@pytest.mark.django_db
class TestInspeccionObraEndpoint:
    """Test POST /api/liquidaciones/inspeccion-obra/ endpoint."""

    def setup_method(self):
        """Seed IGV, UIT, proyecto, municipalidad, tarifa, y liquidación previa."""
        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.proyecto = ProyectoFactory()

        # Create municipalidad
        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-IO-001",
            nombre="Municipalidad de Prueba IO",
            distrito=self.distrito,
        )

        # Create tarifa visitas + regla for INSPECCION_OBRA + categoria A
        self.tarifa_base = TarifaLiquidacionBaseVisitasFactory(
            tipo_liquidacion="INSPECCION_OBRA",
        )
        if not hasattr(self.tarifa_base, 'detalle_visitas') or self.tarifa_base.detalle_visitas is None:
            TarifaPorCategoriaVisitasFactory(tarifa_base=self.tarifa_base)

        from modules.liquidaciones.domain.constants import TramiteAccion
        ReglaTarifaInspeccionObraFactory(
            tarifa_base=self.tarifa_base,
            categoria='A',
            tramite_accion=TramiteAccion.PRIMERA_REVISION,
        )

        # Phase 1: Create a previous liquidation (liquidacion_previa)
        # This represents the "previous liquidation" that IO creation is now based on
        self.liquidacion_previa = LiquidacionGeneral.objects.create(
            proyecto=self.proyecto,
            municipalidad=self.municipalidad,
            igv=self.igv,
            uit=self.uit,
            tipo_liquidacion="INSPECCION_OBRA",
            estado="PENDIENTE",
            numero_revision=0,  # Liquidación previa sin número de revisión
        )

    def test_crear_inspeccion_obra_retorna_200(self, client: Client):
        """
        POST /api/liquidaciones/inspeccion-obra/primera-revision debe retornar 200.
        Phase 1: La creación requiere liquidacion_previa_id.
        """
        response = client.post(
            "/api/liquidaciones/inspeccion-obra/primera-revision",
            data={
                "liquidacion": {
                    "liquidacion_previa_id": str(self.liquidacion_previa.id),
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "cantidad_visitas": 3,
                    "categoria": "A",
                    "expediente": "EXP-IO-001",
                    "observacion": "Test Inspeccion Obra",
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "data" in data

    def test_crear_inspeccion_obra_crea_liquidacion_general(self, client: Client):
        """
        POST debe crear LiquidacionGeneral.
        Phase 1: La creación requiere liquidacion_previa_id.
        """
        count_before = LiquidacionGeneral.objects.count()

        response = client.post(
            "/api/liquidaciones/inspeccion-obra/primera-revision",
            data={
                "liquidacion": {
                    "liquidacion_previa_id": str(self.liquidacion_previa.id),
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "cantidad_visitas": 3,
                    "categoria": "A",
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        count_after = LiquidacionGeneral.objects.count()
        assert count_after == count_before + 1

    def test_crear_inspeccion_obra_crea_liquidacion_inspeccion_obra(self, client: Client):
        """
        POST debe crear LiquidacionInspeccionObra.
        Phase 1: La creación requiere liquidacion_previa_id.
        """
        count_before = LiquidacionInspeccionObra.objects.count()

        response = client.post(
            "/api/liquidaciones/inspeccion-obra/primera-revision",
            data={
                "liquidacion": {
                    "liquidacion_previa_id": str(self.liquidacion_previa.id),
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "cantidad_visitas": 3,
                    "categoria": "A",
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        count_after = LiquidacionInspeccionObra.objects.count()
        assert count_after == count_before + 1

    def test_crear_inspeccion_obra_crea_liquidacion_por_visitas(self, client: Client):
        """
        POST debe crear LiquidacionPorCategoriaVisitas.
        Phase 1: La creación requiere liquidacion_previa_id.
        """
        count_before = LiquidacionPorCategoriaVisitas.objects.count()

        response = client.post(
            "/api/liquidaciones/inspeccion-obra/primera-revision",
            data={
                "liquidacion": {
                    "liquidacion_previa_id": str(self.liquidacion_previa.id),
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "cantidad_visitas": 3,
                    "categoria": "A",
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        count_after = LiquidacionPorCategoriaVisitas.objects.count()
        assert count_after == count_before + 1

    def test_crear_inspeccion_obra_respuesta_tiene_estructura_correcta(self, client: Client):
        """
        La respuesta debe tener la estructura correcta con flat list item:
        id, public_id, tipo_liquidacion, estado, fecha_registro,
        proyecto, municipalidad, valores{subtotal,igv,total,total_a_pagar},
        revisiones[0]{tarifa{costo_por_visita,cantidad_visitas,categoria}}.
        Phase 1: La creación requiere liquidacion_previa_id.
        """
        response = client.post(
            "/api/liquidaciones/inspeccion-obra/primera-revision",
            data={
                "liquidacion": {
                    "liquidacion_previa_id": str(self.liquidacion_previa.id),
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "cantidad_visitas": 3,
                    "categoria": "A",
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        snapshot = data["data"]

        # Flat list item structure
        assert "id" in snapshot
        assert "public_id" in snapshot
        assert "tipo_liquidacion" in snapshot
        assert snapshot["tipo_liquidacion"] == "inspeccion-obra"
        assert "estado" in snapshot
        assert "fecha_registro" in snapshot
        # proyecto nested
        assert "proyecto" in snapshot
        assert "nombre" in snapshot["proyecto"]
        # municipalidad
        assert "municipalidad" in snapshot
        assert "nombre" in snapshot["municipalidad"]
        # valores financieros
        valores = snapshot["valores"]
        assert valores["subtotal"] > 0
        assert valores["igv"] > 0
        assert valores["total"] > valores["subtotal"]
        assert valores["total_a_pagar"] == valores["total"]
        # Revision con tarifa de visitas
        assert "revisiones" in snapshot
        assert len(snapshot["revisiones"]) > 0
        tarifa = snapshot["revisiones"][0]["tarifa"]
        assert tarifa is not None
        assert "costo_por_visita" in tarifa
        assert "cantidad_visitas" in tarifa
        assert "categoria" in tarifa
        assert tarifa["categoria"] == "A"


@pytest.mark.django_db
class TestInspeccionObraProyectistas:
    """Test proyectistas inline in IO creation via POST /primera-revision."""

    def setup_method(self):
        """Seed IGV, UIT, proyecto, municipalidad, especialidad, y liquidación previa."""
        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.proyecto = ProyectoFactory()

        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-IO-PRO-001",
            nombre="Municipalidad de Prueba IO Proyectistas",
            distrito=self.distrito,
        )

        # Create especialidad for inline proyectistas
        self.especialidad = EspecialidadFactory()

        # Create tarifa visitas + regla for INSPECCION_OBRA + categoria A
        self.tarifa_base = TarifaLiquidacionBaseVisitasFactory(
            tipo_liquidacion="INSPECCION_OBRA",
        )
        if not hasattr(self.tarifa_base, 'detalle_visitas') or self.tarifa_base.detalle_visitas is None:
            TarifaPorCategoriaVisitasFactory(tarifa_base=self.tarifa_base)

        from modules.liquidaciones.domain.constants import TramiteAccion
        ReglaTarifaInspeccionObraFactory(
            tarifa_base=self.tarifa_base,
            categoria='A',
            tramite_accion=TramiteAccion.PRIMERA_REVISION,
        )

        # Phase 1: Create a previous liquidation (liquidacion_previa)
        self.liquidacion_previa = LiquidacionGeneral.objects.create(
            proyecto=self.proyecto,
            municipalidad=self.municipalidad,
            igv=self.igv,
            uit=self.uit,
            tipo_liquidacion="INSPECCION_OBRA",
            estado="PENDIENTE",
            numero_revision=0,
        )

    def test_crear_io_con_proyectistas_vacios_retorna_200(self, client: Client):
        """
        POST /primera-revision con proyectistas=[] (vacío) debe retornar 200.
        Phase 1: La creación requiere liquidacion_previa_id.
        """
        response = client.post(
            "/api/liquidaciones/inspeccion-obra/primera-revision",
            data={
                "liquidacion": {
                    "liquidacion_previa_id": str(self.liquidacion_previa.id),
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "cantidad_visitas": 2,
                    "categoria": "A",
                    "expediente": "EXP-IO-PRO-001",
                    "proyectistas": [],
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()

    def test_crear_io_con_proyectistas_inline_valido_retorna_200(self, client: Client):
        """
        POST /primera-revision con proyectistas inline (CIP válido, habilitado)
        debe retornar 200 y crear la asociación LiquidacionProyectista.
        Phase 1: La creación requiere liquidacion_previa_id.
        """
        response = client.post(
            "/api/liquidaciones/inspeccion-obra/primera-revision",
            data={
                "liquidacion": {
                    "liquidacion_previa_id": str(self.liquidacion_previa.id),
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "cantidad_visitas": 2,
                    "categoria": "A",
                    "expediente": "EXP-IO-PRO-002",
                    "proyectistas": [
                        {
                            "cip": "000001",
                            "especialidad_id": str(self.especialidad.id),
                            "descripcion": "Proyectista de prueba",
                        }
                    ],
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        # Flat list item response: data.data is the LiquidacionIOListItemOut directly
        liquidacion_id = data["data"]["id"]

        # Verify LiquidacionProyectista was created and associated
        lp_count = LiquidacionProyectista.objects.filter(
            liquidacion_general_id=liquidacion_id
        ).count()
        assert lp_count == 1, f"Expected 1 LiquidacionProyectista, got {lp_count}"

        lp = LiquidacionProyectista.objects.get(liquidacion_general_id=liquidacion_id)
        assert lp.proyectista is not None
        assert lp.proyectista.perfil_ingeniero.cip == "000001"

    def test_crear_io_con_cip_invalido_retorna_error(self, client: Client):
        """
        POST /primera-revision con CIP no reconocido (no existe en CIP simulator)
        debe retornar error (no 200).
        Phase 1: La creación requiere liquidacion_previa_id.
        """
        response = client.post(
            "/api/liquidaciones/inspeccion-obra/primera-revision",
            data={
                "liquidacion": {
                    "liquidacion_previa_id": str(self.liquidacion_previa.id),
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "cantidad_visitas": 2,
                    "categoria": "A",
                    "expediente": "EXP-IO-PRO-003",
                    "proyectistas": [
                        {
                            "cip": "999999",
                            "especialidad_id": str(self.especialidad.id),
                            "descripcion": "CIP inexistente",
                        }
                    ],
                }
            },
            content_type="application/json",
        )
        # CIP no reconocido → HttpError 404 o similar (no 200)
        assert response.status_code != 200, (
            f"Expected non-200 for invalid CIP, got {response.status_code}: {response.json()}"
        )


# =============================================================================
# Phase 2: IO creation derives proyecto/municipalidad from liquidacion previa
# =============================================================================


@pytest.mark.django_db
class TestInspeccionObraPhase2Derivacion:
    """
    Phase 2: Verify that IO creation derives proyecto and municipalidad
    from the previous liquidation, NOT from deprecated payload fields.

    These tests prove the derivation chain:
    liquidacion_previa_id → liquidacion_previa (proyecto + municipalidad) → new IO
    """

    def setup_method(self):
        """Seed IGV, UIT, proyecto, municipalidad, tarifa, y liquidación previa."""
        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.proyecto = ProyectoFactory()

        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-PHASE2-001",
            nombre="Municipalidad Phase 2 Test",
            distrito=self.distrito,
        )

        # Create tarifa visitas + regla for INSPECCION_OBRA + categoria A
        self.tarifa_base = TarifaLiquidacionBaseVisitasFactory(
            tipo_liquidacion="INSPECCION_OBRA",
        )
        if not hasattr(self.tarifa_base, 'detalle_visitas') or self.tarifa_base.detalle_visitas is None:
            TarifaPorCategoriaVisitasFactory(tarifa_base=self.tarifa_base)

        from modules.liquidaciones.domain.constants import TramiteAccion
        ReglaTarifaInspeccionObraFactory(
            tarifa_base=self.tarifa_base,
            categoria='A',
            tramite_accion=TramiteAccion.PRIMERA_REVISION,
        )

        # Create a previous liquidation that will be the source of proyecto/municipalidad
        self.liquidacion_previa = LiquidacionGeneral.objects.create(
            proyecto=self.proyecto,
            municipalidad=self.municipalidad,
            igv=self.igv,
            uit=self.uit,
            tipo_liquidacion="INSPECCION_OBRA",
            estado="PENDIENTE",
            numero_revision=0,
        )

    def test_proyecto_derivado_de_liquidacion_previa(self, client: Client):
        """
        Phase 2: El proyecto de la nueva IO debe ser el mismo de liquidacion_previa,
        sin importar el valor de proyecto_public_id en el payload (deprecated).
        """
        # Crear un segundo proyecto diferente para verificar que NO se usa
        from modules.liquidaciones.tests.factories.proyecto_factory import ProyectoFactory
        otro_proyecto = ProyectoFactory()

        response = client.post(
            "/api/liquidaciones/inspeccion-obra/primera-revision",
            data={
                "liquidacion": {
                    "liquidacion_previa_id": str(self.liquidacion_previa.id),
                    # Deprecated payload fields - should be IGNORED
                    "proyecto_public_id": otro_proyecto.public_id,
                    "municipalidad_id": "00000000-0000-0000-0000-000000000000",
                    "cantidad_visitas": 3,
                    "categoria": "A",
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()

        # Verificar que el proyecto es el DE la liquidacion_previa, NO otro_proyecto
        liquidacion_nueva = LiquidacionGeneral.objects.get(id=data["data"]["id"])
        assert liquidacion_nueva.proyecto.id == self.proyecto.id, (
            f"El proyecto debería ser el de liquidacion_previa ({self.proyecto.id}), "
            f"pero es {liquidacion_nueva.proyecto.id}"
        )
        assert liquidacion_nueva.proyecto.id != otro_proyecto.id, (
            "El proyecto debería ser el de liquidacion_previa, NO otro_proyecto"
        )

    def test_municipalidad_derivada_de_liquidacion_previa(self, client: Client):
        """
        Phase 2: La municipalidad de la nueva IO debe ser la misma de liquidacion_previa,
        sin importar el valor de municipalidad_id en el payload (deprecated).
        """
        # Crear otra municipalidad para verificar que NO se usa
        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        otro_distrito = UbigeoDistritoFactory()
        otra_municipalidad = Municipalidad.objects.create(
            codigo="MUN-OTRA-001",
            nombre="Otra Municipalidades",
            distrito=otro_distrito,
        )

        response = client.post(
            "/api/liquidaciones/inspeccion-obra/primera-revision",
            data={
                "liquidacion": {
                    "liquidacion_previa_id": str(self.liquidacion_previa.id),
                    "proyecto_public_id": self.proyecto.public_id,
                    # Deprecated payload field - should be IGNORED
                    "municipalidad_id": str(otra_municipalidad.id),
                    "cantidad_visitas": 3,
                    "categoria": "A",
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()

        # Verificar que la municipalidad es la DE liquidacion_previa, NO otra_municipalidad
        liquidacion_nueva = LiquidacionGeneral.objects.get(id=data["data"]["id"])
        assert liquidacion_nueva.municipalidad.id == self.municipalidad.id, (
            f"La municipalidad debería ser la de liquidacion_previa ({self.municipalidad.id}), "
            f"pero es {liquidacion_nueva.municipalidad.id}"
        )
        assert liquidacion_nueva.municipalidad.id != otra_municipalidad.id, (
            "La municipalidad debería ser la de liquidacion_previa, NO otra_municipalidad"
        )

    def test_liquidacion_previa_vinculada_via_liquidaciones_previas_m2m(self, client: Client):
        """
        Phase 2: La nueva IO debe estar vinculada a la liquidacion_previa
        via el campo M2M liquidaciones_previas.
        """
        response = client.post(
            "/api/liquidaciones/inspeccion-obra/primera-revision",
            data={
                "liquidacion": {
                    "liquidacion_previa_id": str(self.liquidacion_previa.id),
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "cantidad_visitas": 3,
                    "categoria": "A",
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()

        liquidacion_nueva = LiquidacionGeneral.objects.get(id=data["data"]["id"])

        # Verificar que liquidacion_nueva.liquidaciones_previas contiene a liquidacion_previa
        previas = list(liquidacion_nueva.liquidaciones_previas.all())
        assert len(previas) == 1, (
            f"Expected 1 liquidacion_previa, got {len(previas)}: {previas}"
        )
        assert previas[0].id == self.liquidacion_previa.id, (
            f"La liquidacion_previa vinculada debería ser {self.liquidacion_previa.id}, "
            f"pero es {previas[0].id}"
        )

    def test_numero_revision_es_1_y_tramite_accion_es_primera_revision(self, client: Client):
        """
        Phase 2: La nueva IO debe tener numero_revision=1 y tramite_accion=PRIMERA_REVISION.
        Esto NO es nueva revisión - es Inspección de Obra normal basada en liquidación previa.
        """
        response = client.post(
            "/api/liquidaciones/inspeccion-obra/primera-revision",
            data={
                "liquidacion": {
                    "liquidacion_previa_id": str(self.liquidacion_previa.id),
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "cantidad_visitas": 3,
                    "categoria": "A",
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()

        liquidacion_nueva = LiquidacionGeneral.objects.get(id=data["data"]["id"])
        liq_io = LiquidacionInspeccionObra.objects.get(liquidacion=liquidacion_nueva)

        # numero_revision debe ser 1
        assert liquidacion_nueva.numero_revision == 1, (
            f"numero_revision debería ser 1, pero es {liquidacion_nueva.numero_revision}"
        )

        # tramite_accion debe ser PRIMERA_REVISION
        from modules.liquidaciones.domain.constants import TramiteAccion
        assert liq_io.tramite_accion == TramiteAccion.PRIMERA_REVISION, (
            f"tramite_accion debería ser PRIMERA_REVISION, pero es {liq_io.tramite_accion}"
        )

    def test_error_si_liquidacion_previa_no_existe(self, client: Client):
        """
        Phase 2: Si liquidacion_previa_id no existe, debe retornar error.
        """
        import uuid
        id_inexistente = str(uuid.uuid4())

        response = client.post(
            "/api/liquidaciones/inspeccion-obra/primera-revision",
            data={
                "liquidacion": {
                    "liquidacion_previa_id": id_inexistente,
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "cantidad_visitas": 3,
                    "categoria": "A",
                }
            },
            content_type="application/json",
        )
        # Debe fallar con 404 NotFound
        assert response.status_code == 404, (
            f"Expected 404 for non-existent liquidacion_previa_id, got {response.status_code}: {response.json()}"
        )

    def test_error_si_liquidacion_previa_sin_proyecto(self, client: Client):
        """
        Phase 2: Si la liquidacion_previa no tiene proyecto, debe fallar.

        NOTA: El campo LiquidacionGeneral.proyecto tiene FK con null=False (DB constraint).
        No se puede crear una LiquidacionGeneral sin proyecto via ORM.
        La validación 'if not liquidacion_previa.proyecto' existe en el flujo
        (raise NotFoundError) y se probaría si existiera un registro huérfano en BD
        (data integrity issue fuera de la aplicación).
        Este test documenta la existencia de esa validación via code inspection.
        """
        # La validación existe en flujo: if not liquidacion_previa.proyecto: raise NotFoundError
        # No se puede crear el pre-condition via ORM (DB constraint null=False en ForeignKey)
        # Verificar que el flujo tiene esta validación mirando su código fuente
        import inspect
        from modules.liquidaciones.domain.services.flujos.inspeccion_obra_flujo import InspeccionObraFlujo
        source = inspect.getsource(InspeccionObraFlujo._proceso_creacion)
        assert "if not liquidacion_previa.proyecto" in source, (
            "El flujo debería validar que liquidacion_previa.proyecto existe"
        )

    def test_error_si_liquidacion_previa_sin_municipalidad(self, client: Client):
        """
        Phase 2: Si la liquidacion_previa no tiene municipalidad, debe fallar.
        """
        # Crear liquidacion previa SIN municipalidad
        liquidacion_sin_municipalidad = LiquidacionGeneral.objects.create(
            proyecto=self.proyecto,
            municipalidad=None,  # Sin municipalidad
            igv=self.igv,
            uit=self.uit,
            tipo_liquidacion="INSPECCION_OBRA",
            estado="PENDIENTE",
            numero_revision=0,
        )

        response = client.post(
            "/api/liquidaciones/inspeccion-obra/primera-revision",
            data={
                "liquidacion": {
                    "liquidacion_previa_id": str(liquidacion_sin_municipalidad.id),
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "cantidad_visitas": 3,
                    "categoria": "A",
                }
            },
            content_type="application/json",
        )
        # Debe fallar - la liquidacion previa sin municipalidad no puede generar IO
        assert response.status_code == 404, (
            f"Expected 404 for liquidacion_previa without municipalidad, got {response.status_code}: {response.json()}"
        )


# =============================================================================
# Phase 3: Search previous liquidations by document number
# =============================================================================


@pytest.mark.django_db
class TestInspeccionObraBuscarPrevias:
    """Test GET /api/liquidaciones/inspeccion-obra/buscar-previas endpoint.

    NOTE: The endpoint now searches for EDIFICACION and HABILITACION_URBANA liquidations
    (general liquidations that can provide common data for IO creation),
    not INSPECCION_OBRA liquidations.
    """

    def setup_method(self):
        """Seed IGV, UIT, proyecto, municipalidad, y liquidación general EDIFICACION."""
        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.proyecto = ProyectoFactory()

        # Create municipalidad
        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-IO-BUS-001",
            nombre="Municipalidad de Prueba IO Buscar Previas",
            distrito=self.distrito,
        )

        # Create a general liquidation (EDIFICACION) that can serve as previa for IO
        self.liquidacion_previa = LiquidacionGeneral.objects.create(
            proyecto=self.proyecto,
            municipalidad=self.municipalidad,
            igv=self.igv,
            uit=self.uit,
            tipo_liquidacion="EDIFICACION",
            estado="PENDIENTE",
            numero_revision=1,
        )

    def test_buscar_previas_por_documento_retorna_200(self, client: Client):
        """
        GET /buscar-previas?numero_documento=X debe retornar 200.
        """
        response = client.get(
            f"/api/liquidaciones/inspeccion-obra/buscar-previas?numero_documento={self.proyecto.entidad.numero_documento}",
        )
        assert response.status_code == 200, response.json()

    def test_buscar_previas_filtra_por_numero_documento(self, client: Client):
        """
        GET /buscar-previas debe filtrar por numero_documento de la entidad.
        Solo retorna liquidaciones con matching numero_documento.
        """
        # Buscar con el número de documento correcto
        response = client.get(
            f"/api/liquidaciones/inspeccion-obra/buscar-previas?numero_documento={self.proyecto.entidad.numero_documento}",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert data["data"]["total"] == 1, f"Expected 1 liquidacion, got {data['data']['total']}"

        # Buscar con número de documento inexistente
        response = client.get(
            "/api/liquidaciones/inspeccion-obra/buscar-previas?numero_documento=99999999",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert data["data"]["total"] == 0, f"Expected 0 liquidaciones for non-existent document, got {data['data']['total']}"

    def test_buscar_previas_filtra_por_tipo_liquidacion(self, client: Client):
        """
        GET /buscar-previas solo debe retornar liquidaciones de tipo EDIFICACION o HABILITACION_URBANA.
        Otros tipos de liquidación no deben aparecer.
        """
        # Crear una liquidación de otro tipo (INSPECCION_OBRA) - no debe aparecer
        LiquidacionGeneral.objects.create(
            proyecto=self.proyecto,
            municipalidad=self.municipalidad,
            igv=self.igv,
            uit=self.uit,
            tipo_liquidacion="INSPECCION_OBRA",
            estado="PENDIENTE",
            numero_revision=0,
        )

        response = client.get(
            f"/api/liquidaciones/inspeccion-obra/buscar-previas?numero_documento={self.proyecto.entidad.numero_documento}",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        # Solo la liquidacion_previa (EDIFICACION) debe aparecer, no la INSPECCION_OBRA
        assert data["data"]["total"] == 1, f"Expected 1 (EDIFICACION), got {data['data']['total']}"
        assert data["data"]["items"][0]["tipo_liquidacion"] == "edificacion"

    def test_buscar_previas_respuesta_tiene_estructura_correcta(self, client: Client):
        """
        La respuesta de /buscar-previas debe tener la estructura LiquidacionGeneralListItemOut.
        """
        response = client.get(
            f"/api/liquidaciones/inspeccion-obra/buscar-previas?numero_documento={self.proyecto.entidad.numero_documento}",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        item = data["data"]["items"][0]

        # Estructura LiquidacionGeneralListItemOut
        assert "id" in item
        assert "public_id" in item
        assert "tipo_liquidacion" in item
        assert item["tipo_liquidacion"] == "edificacion"
        assert "estado" in item
        assert "numero_revision" in item
        assert item["numero_revision"] == 1
        assert "fecha_registro" in item
        assert "proyecto" in item
        assert "municipalidad" in item
        assert "valores" in item
        # Valores financieros
        valores = item["valores"]
        assert "subtotal" in valores
        assert "igv" in valores
        assert "total" in valores
        assert "total_a_pagar" in valores

    def test_buscar_previas_con_paginacion(self, client: Client):
        """
        GET /buscar-previas debe soportar paginación.
        """
        # Crear más liquidaciones previas para DIFERENTES proyectos
        # pero con el MISMO numero_documento (misma entidad)
        # para que todas sean encontradas en la búsqueda
        from modules.liquidaciones.tests.factories.entidad_factory import EntidadFactory
        from modules.liquidaciones.tests.factories.proyecto_factory import ProyectoFactory

        shared_entidad = EntidadFactory(
            tipo_documento="RUC",
            numero_documento="12345678901",  # RUC compartido
            razon_social="Empresa Compartida SAC",
        )

        # Crear 3 proyectos adicionales con la misma entidad (mismo numero_documento)
        otros_proyectos = []
        for i in range(3):
            otro_proyecto = ProyectoFactory(entidad=shared_entidad)
            otros_proyectos.append(otro_proyecto)
            LiquidacionGeneral.objects.create(
                proyecto=otro_proyecto,
                municipalidad=self.municipalidad,
                igv=self.igv,
                uit=self.uit,
                tipo_liquidacion="EDIFICACION",
                estado="PENDIENTE",
                numero_revision=1,
            )

        # Buscar por el numero_documento compartido
        numero_doc = shared_entidad.numero_documento

        # Primera página con page_size=2
        response = client.get(
            f"/api/liquidaciones/inspeccion-obra/buscar-previas?numero_documento={numero_doc}&page=1&page_size=2",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        # 3 total: solo las que comparten la entidad con tipo EDIFICACION
        assert data["data"]["total"] == 3, f"Expected 3 (only those with shared entidad), got {data['data']['total']}"
        assert len(data["data"]["items"]) == 2
        assert data["data"]["page"] == 1
        assert data["data"]["page_size"] == 2
        assert data["data"]["total_pages"] == 2

    def test_buscar_previas_sin_numero_documento_retorna_error(self, client: Client):
        """
        GET /buscar-previas sin numero_documento debe retornar 422 o error de validación.
        """
        response = client.get(
            "/api/liquidaciones/inspeccion-obra/buscar-previas",
        )
        # Ninja retorna 422 para parámetros requeridos faltantes
        assert response.status_code == 422, (
            f"Expected 422 for missing numero_documento, got {response.status_code}: {response.json()}"
        )

    def test_buscar_previas_retorna_todas_las_liquidaciones_del_proyecto(self, client: Client):
        """
        GET /buscar-previas retorna todas las liquidaciones EDIFICACION/HABILITACION_URBANA
        para el proyecto, sin filtro de latest_per_project (a diferencia del old IO list).
        """
        # Crear otra liquidacion para el mismo proyecto (EDIFICACION con different revision)
        LiquidacionGeneral.objects.create(
            proyecto=self.proyecto,
            municipalidad=self.municipalidad,
            igv=self.igv,
            uit=self.uit,
            tipo_liquidacion="EDIFICACION",
            estado="PENDIENTE",
            numero_revision=2,  # Más reciente que la del setup (revision=1)
        )

        response = client.get(
            f"/api/liquidaciones/inspeccion-obra/buscar-previas?numero_documento={self.proyecto.entidad.numero_documento}",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        # Deben retornar 2 liquidaciones (ambas EDIFICACION para el mismo proyecto)
        assert data["data"]["total"] == 2, (
            f"Expected 2 liquidaciones, got {data['data']['total']}. "
            f"El endpoint buscar-previas no filtra por latest_per_project."
        )

