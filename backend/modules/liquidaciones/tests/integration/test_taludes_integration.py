"""
Integration tests for Taludes liquidaciones via HTTP endpoint.

Tests the full stack: controller -> orchestrator -> flujo -> core -> DB.

Uses Django test client like existing edificaciones integration tests.
"""
import pytest

from django.test import Client

from modules.liquidaciones.tests.factories.proyecto_factory import ProyectoFactory
from modules.liquidaciones.tests.factories.finanzas_factory import IGVFactory, UITFactory
from modules.liquidaciones.tests.factories.tarifas_test_factory import (
    TarifaLiquidacionBaseM2Factory,
    TarifaPorMetroCuadradoFactory,
    ReglaTarifaLiquidacionFactory,
)
from modules.liquidaciones.models import (
    LiquidacionGeneral,
    LiquidacionTaludes,
    LiquidacionPorMetroCuadrado,
    LiquidacionPorcentajeObra,
    LiquidacionProyectista,
)
from modules.liquidaciones.tests.factories.especialidad_factory import EspecialidadFactory


@pytest.mark.django_db
@pytest.mark.skip(reason="Taludes migró a cálculo porcentual (LiquidacionPorcentajeObra). Tests M2 obsoletos. Ver TestTaludesPorcentajeEndpoint.")
class TestTaludesProyectistas:
    """Test proyectistas inline in Taludes creation via POST /primera-revision."""

    def setup_method(self):
        """Seed IGV, UIT, proyecto, municipalidad, and especialidad."""
        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.proyecto = ProyectoFactory()

        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-TAL-PRO-001",
            nombre="Municipalidad de Prueba Taludes Proyectistas",
            distrito=self.distrito,
        )

        # Create especialidad for inline proyectistas
        self.especialidad = EspecialidadFactory()

        # Create tarifa M2 + regla for TALUDES
        self.tarifa_base = TarifaLiquidacionBaseM2Factory(
            tipo_liquidacion="TALUDES",
        )
        if not hasattr(self.tarifa_base, 'detalle_m2') or self.tarifa_base.detalle_m2 is None:
            TarifaPorMetroCuadradoFactory(tarifa_base=self.tarifa_base)

        from modules.liquidaciones.domain.constants import TramiteAccion
        ReglaTarifaLiquidacionFactory(
            tarifa_base=self.tarifa_base,
            tramite_accion=TramiteAccion.PRIMERA_REVISION,
        )

    def test_crear_taludes_con_proyectistas_vacios_retorna_200(self, client: Client):
        """
        POST /primera-revision con proyectistas=[] (vacío) debe retornar 200.
        """
        response = client.post(
            "/api/liquidaciones/taludes/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "area_solicitada": 100.0,
                    "expediente": "EXP-TAL-PRO-001",
                    "proyectistas": [],
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()

    def test_crear_taludes_con_proyectistas_inline_valido_retorna_200(self, client: Client):
        """
        POST /primera-revision con proyectistas inline (CIP válido, habilitado)
        debe retornar 200 y crear la asociación LiquidacionProyectista.
        """
        response = client.post(
            "/api/liquidaciones/taludes/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "area_solicitada": 100.0,
                    "expediente": "EXP-TAL-PRO-002",
                    "proyectistas": [
                        {
                            "cip": "000001",
                            "especialidad_id": str(self.especialidad.id),
                            "descripcion": "Proyectista Taludes de prueba",
                        }
                    ],
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        liquidacion_id = data["data"]["liquidacion"]["id"]

        # Verify LiquidacionProyectista was created and associated
        lp_count = LiquidacionProyectista.objects.filter(
            liquidacion_general_id=liquidacion_id
        ).count()
        assert lp_count == 1, f"Expected 1 LiquidacionProyectista, got {lp_count}"

        lp = LiquidacionProyectista.objects.get(liquidacion_general_id=liquidacion_id)
        assert lp.proyectista is not None
        assert lp.proyectista.perfil_ingeniero.cip == "000001"

    def test_crear_taludes_con_cip_invalido_retorna_error(self, client: Client):
        """
        POST /primera-revision con CIP no reconocido (no existe en CIP simulator)
        debe retornar error (no 200).
        """
        response = client.post(
            "/api/liquidaciones/taludes/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "area_solicitada": 100.0,
                    "expediente": "EXP-TAL-PRO-003",
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
# Tests de porcentaje (Edificaciones-style) — Taludes ahora usa LiquidacionPorcentajeObra
# =============================================================================
# NOTA: Los tests de arriba (TestTaludesProyectistas) usan factories M2 y
# area_solicitada. Son tests heredados de la era M2. Taludes ahora usa
# porcentaje (valor_proyecto * % + IGV) similar a Edificaciones.
# Los tests de abajo prueban el nuevo comportamiento porcentual.


@pytest.mark.django_db
class TestTaludesPorcentajeEndpoint:
    """Test POST /api/liquidaciones/taludes/primera-revision con cálculo porcentual."""

    def setup_method(self):
        """Seed IGV, UIT, proyecto, municipalidad y tarifa porcentual."""
        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.proyecto = ProyectoFactory()

        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-TAL-PCT-001",
            nombre="Municipalidad de Prueba Taludes Porcentaje",
            distrito=self.distrito,
        )

        # Crear tarifa porcentual (no M2) para TALUDES
        # Production code ahora usa ReglaTarifaEdificacion (no ReglaTarifaLiquidacion)
        # para IV/Taludes con cálculo porcentual.
        from modules.liquidaciones.tests.factories.tarifa_liquidacion_factory import (
            TarifaLiquidacionBaseFactory,
        )
        from modules.liquidaciones.tests.factories.tarifas_test_factory import (
            ReglaTarifaEdificacionFactory,
        )
        from modules.liquidaciones.domain.constants import (
            TipoTramiteEdificaciones,
            TramiteAccion,
        )

        self.tarifa_base = TarifaLiquidacionBaseFactory(
            tipo_liquidacion="TALUDES",
        )
        # TarifaLiquidacionBaseFactory crea TarifaPorcentajeObra automáticamente via
        # detalle_porcentual RelatedFactory
        ReglaTarifaEdificacionFactory(
            tipo_tramite=TipoTramiteEdificaciones.OBRA_NUEVA,
            tramite_accion=TramiteAccion.PRIMERA_REVISION,
            tarifa_base=self.tarifa_base,
        )

    def test_crear_taludes_porcentaje_retorna_200(self, client: Client):
        """
        POST /primera-revision con valor_proyecto debe retornar 200.
        Taludes ahora usa cálculo porcentual (Edificaciones-style).
        """
        response = client.post(
            "/api/liquidaciones/taludes/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "valor_proyecto": 100000.0,
                    "expediente": "EXP-TAL-PCT-001",
                    "observacion": "Test Taludes porcentaje",
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "data" in data

    def test_crear_taludes_porcentaje_crea_liquidacion_general(self, client: Client):
        """
        POST debe crear LiquidacionGeneral para Taludes porcentual.
        """
        count_before = LiquidacionGeneral.objects.count()

        response = client.post(
            "/api/liquidaciones/taludes/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "valor_proyecto": 100000.0,
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        count_after = LiquidacionGeneral.objects.count()
        assert count_after == count_before + 1

    def test_crear_taludes_porcentaje_crea_liquidacion_taludes(self, client: Client):
        """
        POST debe crear LiquidacionTaludes.
        """
        count_before = LiquidacionTaludes.objects.count()

        response = client.post(
            "/api/liquidaciones/taludes/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "valor_proyecto": 100000.0,
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        count_after = LiquidacionTaludes.objects.count()
        assert count_after == count_before + 1

    def test_crear_taludes_porcentaje_respuesta_tiene_calculo_porcentaje(self, client: Client):
        """
        La respuesta debe contener calculo_porcentaje (Edificaciones-style).
        """
        response = client.post(
            "/api/liquidaciones/taludes/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "valor_proyecto": 100000.0,
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
        assert snapshot["tipo_liquidacion"] == "taludes"
        assert "estado" in snapshot
        assert "fecha_registro" in snapshot
        # valor_proyecto en proyecto anidado
        assert snapshot["proyecto"]["valor_proyecto"] == 100000.0
        # municipalidad
        assert "municipalidad" in snapshot
        assert "nombre" in snapshot["municipalidad"]
        # valores financieros (con IGV para porcentaje)
        valores = snapshot["valores"]
        assert valores["subtotal"] > 0
        assert valores["igv"] > 0  # Porcentaje tiene IGV
        assert valores["total"] > valores["subtotal"]  # total = subtotal + igv
        assert valores["total_a_pagar"] == valores["total"]
        # Revision con tarifa porcentual
        assert "revisiones" in snapshot
        assert len(snapshot["revisiones"]) > 0
        tarifa = snapshot["revisiones"][0]["tarifa"]
        assert tarifa is not None
        assert "porcentaje_liquidacion" in tarifa
        assert "porcentaje_minimo_uit" in tarifa
        assert "derecho_minimo" in tarifa

    def test_taludes_porcentaje_igv_mayor_cero_total_mayor_subtotal(self, client: Client):
        """
        Taludes porcentual debe tener igv > 0 y total > subtotal.
        (Antes Taludes era M2 con igv=0; ahora es porcentaje con IGV como Edificaciones.)
        Estructura: valores{subtotal,igv,total,total_a_pagar} en flat list item.
        """
        response = client.post(
            "/api/liquidaciones/taludes/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "valor_proyecto": 100000.0,
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        snapshot = data["data"]

        valores = snapshot["valores"]
        # IGV debe ser > 0 (Edificaciones-style con IGV)
        assert valores["igv"] > 0, (
            f"Taludes porcentual debe tener igv > 0, got {valores['igv']}"
        )
        # total debe ser mayor que subtotal (porque total = subtotal + igv)
        assert valores["total"] > valores["subtotal"], (
            f"total ({valores['total']}) debe ser mayor que subtotal ({valores['subtotal']})"
        )
        # total_a_pagar debe incluir igv
        assert valores["total_a_pagar"] == valores["total"]

    def test_taludes_porcentaje_derecho_minimo_en_tarifa(self, client: Client):
        """
        La respuesta flat list item incluye derecho_minimo en revisiones[0].tarifa.
        El derecho real (>= derecho_minimo) se refleja en valores.subtotal.
        """
        from decimal import Decimal
        # valor_proyecto = 1000.0, porcentaje = 0.05 → 50 < 500 (derecho_minimo)
        response = client.post(
            "/api/liquidaciones/taludes/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "valor_proyecto": 1000.0,
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        snapshot = data["data"]

        # derecho_minimo debe estar en la tarifa de la revisión
        tarifa = snapshot["revisiones"][0]["tarifa"]
        assert tarifa["derecho_minimo"] == Decimal("500.00"), (
            f"derecho_minimo debe ser 500.00, got {tarifa['derecho_minimo']}"
        )
        # valores.subtotal debe ser >= derecho_minimo (el derecho calculado >= mínimo legal)
        assert Decimal(str(snapshot["valores"]["subtotal"])) >= Decimal("500.00"), (
            f"subtotal ({snapshot['valores']['subtotal']}) debe ser >= derecho_minimo (500.00)"
        )

    def test_taludes_porcentaje_derecho_maximo_en_tarifa(self, client: Client):
        """
        La respuesta flat list item incluye derecho_maximo en revisiones[0].tarifa.
        El derecho real (capped a derecho_maximo) se refleja en valores.subtotal.
        """
        # Override derecho_maximo a 1000.00
        from modules.liquidaciones.domain.models.liquidacion.liquidacion import TarifaPorcentajeObra
        from decimal import Decimal
        TarifaPorcentajeObra.objects.update(
            derecho_maximo=Decimal("1000.00"),
        )
        # valor_proyecto = 100000.0, porcentaje = 0.05 → 5000 > 1000 (capped)
        response = client.post(
            "/api/liquidaciones/taludes/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "valor_proyecto": 100000.0,
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        snapshot = data["data"]

        # derecho_maximo debe estar en la tarifa de la revisión
        tarifa = snapshot["revisiones"][0]["tarifa"]
        assert tarifa["derecho_maximo"] is not None, (
            "derecho_maximo debe estar presente en tarifa"
        )
        assert Decimal(str(tarifa["derecho_maximo"])) == Decimal("1000.00"), (
            f"derecho_maximo debe ser 1000.00, got {tarifa['derecho_maximo']}"
        )
        # valores.subtotal debe ser capped a derecho_maximo = 1000.00
        assert Decimal(str(snapshot["valores"]["subtotal"])) <= Decimal("1000.00"), (
            f"subtotal ({snapshot['valores']['subtotal']}) debe estar capped a derecho_maximo (1000.00)"
        )
