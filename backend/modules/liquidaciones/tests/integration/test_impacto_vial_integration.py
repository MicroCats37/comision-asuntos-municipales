"""
Integration tests for Impacto Vial liquidaciones via HTTP endpoint.

Tests the full stack: controller -> orchestrator -> flujo -> core -> DB.

Uses Django test client like existing edificaciones integration tests.
"""
import pytest
from decimal import Decimal

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
    LiquidacionImpactoVial,
    LiquidacionPorMetroCuadrado,
    LiquidacionPorcentajeObra,
    LiquidacionProyectista,
)
from modules.liquidaciones.tests.factories.especialidad_factory import EspecialidadFactory


@pytest.mark.django_db
@pytest.mark.skip(reason="IV migró a cálculo porcentual (LiquidacionPorcentajeObra). Tests M2 obsoletos. Ver TestImpactoVialPorcentajeEndpoint.")
class TestImpactoVialEndpoint:
    """Test POST /api/liquidaciones/impacto-vial/ endpoint."""

    def setup_method(self):
        """Seed IGV, UIT, proyecto, and municipalidad."""
        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.proyecto = ProyectoFactory()

        # Create municipalidad
        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-IV-001",
            nombre="Municipalidad de Prueba IV",
            distrito=self.distrito,
        )

        # Create tarifa M2 + regla for IMPACTO_VIAL
        self.tarifa_base = TarifaLiquidacionBaseM2Factory(
            tipo_liquidacion="IMPACTO_VIAL",
        )
        if not hasattr(self.tarifa_base, 'detalle_m2') or self.tarifa_base.detalle_m2 is None:
            TarifaPorMetroCuadradoFactory(tarifa_base=self.tarifa_base)

        from modules.liquidaciones.domain.constants import TramiteAccion
        ReglaTarifaLiquidacionFactory(
            tarifa_base=self.tarifa_base,
            tramite_accion=TramiteAccion.PRIMERA_REVISION,
        )

    def test_crear_impacto_vial_retorna_200(self, client: Client):
        """
        POST /api/liquidaciones/impacto-vial/primera-revision debe retornar 200.
        """
        response = client.post(
            "/api/liquidaciones/impacto-vial/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "area_solicitada": 150.0,
                    "expediente": "EXP-IV-001",
                    "observacion": "Test Impacto Vial",
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "data" in data

    def test_crear_impacto_vial_crea_liquidacion_general(self, client: Client):
        """
        POST debe crear LiquidacionGeneral.
        """
        count_before = LiquidacionGeneral.objects.count()

        response = client.post(
            "/api/liquidaciones/impacto-vial/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "area_solicitada": 150.0,
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        count_after = LiquidacionGeneral.objects.count()
        assert count_after == count_before + 1

    def test_crear_impacto_vial_crea_liquidacion_impacto_vial(self, client: Client):
        """
        POST debe crear LiquidacionImpactoVial.
        """
        count_before = LiquidacionImpactoVial.objects.count()

        response = client.post(
            "/api/liquidaciones/impacto-vial/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "area_solicitada": 150.0,
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        count_after = LiquidacionImpactoVial.objects.count()
        assert count_after == count_before + 1

    def test_crear_impacto_vial_crea_liquidacion_por_m2(self, client: Client):
        """
        POST debe crear LiquidacionPorMetroCuadrado.
        """
        count_before = LiquidacionPorMetroCuadrado.objects.count()

        response = client.post(
            "/api/liquidaciones/impacto-vial/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "area_solicitada": 150.0,
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        count_after = LiquidacionPorMetroCuadrado.objects.count()
        assert count_after == count_before + 1

    def test_crear_impacto_vial_respuesta_tiene_estructura_correcta(self, client: Client):
        """
        La respuesta debe tener la estructura correcta con liquidacion, totales, etc.
        """
        response = client.post(
            "/api/liquidaciones/impacto-vial/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "area_solicitada": 150.0,
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        snapshot = data["data"]

        assert "liquidacion" in snapshot
        assert "tipo_liquidacion" in snapshot
        assert snapshot["tipo_liquidacion"] == "IMPACTO_VIAL"
        assert "totales" in snapshot
        assert "subtotal" in snapshot["totales"]

    def test_impacto_vial_no_igv_total_igual_subtotal(self, client: Client):
        """
        Impacto Vial (M2) debe tener igv_monto=0 y total=subtotal.
        No se aplica IGV a liquidaciones por metro cuadrado.
        """
        response = client.post(
            "/api/liquidaciones/impacto-vial/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "area_solicitada": 150.0,
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        snapshot = data["data"]

        totales = snapshot["totales"]
        # M2 specialties: igv_monto = 0
        assert totales["igv"] == 0, "M2 liquidaciones no deben tener IGV"
        # total = subtotal (sin IGV)
        assert totales["total"] == totales["subtotal"], "total debe igualar subtotal para M2"
        # total_a_pagar debe ser igual al total (sin IGV)
        assert totales["total_a_pagar"] == totales["subtotal"]

    def test_impacto_vial_derecho_maximo_caps_subtotal(self, client: Client):
        """
        Cuando area_solicitada * costo_por_m2 supera derecho_maximo,
        el subtotal/derecho debe quedar capped en derecho_maximo,
        con igv=0 y total=derecho_maximo.
        """
        from modules.liquidaciones.tests.factories.tarifas_test_factory import (
            TarifaPorMetroCuadradoFactory,
        )

        # Override existing TarifaPorMetroCuadrado on self.tarifa_base:
        # derecho_maximo=10000.00 (IMPACTO_VIAL seed value)
        # costo_por_m2=50 * 250m2 = 12500 > 10000 → capped
        from modules.liquidaciones.domain.models.liquidacion.tarifas_reglas import (
            TarifaPorMetroCuadrado as TarifaPorMetroCuadradoModel,
        )
        TarifaPorMetroCuadradoModel.objects.update_or_create(
            tarifa_base=self.tarifa_base,
            defaults={
                "costo_por_m2": Decimal("50.0000"),
                "area_m2": Decimal("100.00"),
                "derecho_minimo": Decimal("500.00"),
                "derecho_maximo": Decimal("10000.00"),
            },
        )

        response = client.post(
            "/api/liquidaciones/impacto-vial/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "area_solicitada": 250.0,
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        snapshot = data["data"]

        totales = snapshot["totales"]
        # IGV stays 0 for M2
        assert totales["igv"] == 0, "M2 liquidaciones no deben tener IGV"
        # subtotal must be capped at derecho_maximo = 10000.00
        assert totales["subtotal"] == Decimal("10000.00"), (
            f"subtotal debe ser 10000.00 (derecho_maximo),got {totales['subtotal']}"
        )
        # total = subtotal (no IGV)
        assert totales["total"] == totales["subtotal"]
        # total_a_pagar = subtotal
        assert totales["total_a_pagar"] == totales["subtotal"]
        # derecho in calculo_m2 must also be capped at derecho_maximo
        assert "calculo_m2" in snapshot, "calculo_m2 must be present in snapshot"
        assert snapshot["calculo_m2"]["derecho"] == Decimal("10000.00"), (
            f"calculo_m2.derecho must be 10000.00 (derecho_maximo), got {snapshot['calculo_m2']['derecho']}"
        )


@pytest.mark.django_db
@pytest.mark.skip(reason="IV migró a cálculo porcentual (LiquidacionPorcentajeObra). Tests M2 obsoletos. Ver TestImpactoVialPorcentajeEndpoint.")
class TestImpactoVialProyectistas:
    """Test proyectistas inline in IV creation via POST /primera-revision."""

    def setup_method(self):
        """Seed IGV, UIT, proyecto, municipalidad, and especialidad."""
        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.proyecto = ProyectoFactory()

        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-IV-PRO-001",
            nombre="Municipalidad de Prueba IV Proyectistas",
            distrito=self.distrito,
        )

        # Create especialidad for inline proyectistas
        self.especialidad = EspecialidadFactory()

        # Create tarifa M2 + regla for IMPACTO_VIAL
        self.tarifa_base = TarifaLiquidacionBaseM2Factory(
            tipo_liquidacion="IMPACTO_VIAL",
        )
        if not hasattr(self.tarifa_base, 'detalle_m2') or self.tarifa_base.detalle_m2 is None:
            TarifaPorMetroCuadradoFactory(tarifa_base=self.tarifa_base)

        from modules.liquidaciones.domain.constants import TramiteAccion
        ReglaTarifaLiquidacionFactory(
            tarifa_base=self.tarifa_base,
            tramite_accion=TramiteAccion.PRIMERA_REVISION,
        )

    def test_crear_iv_con_proyectistas_vacios_retorna_200(self, client: Client):
        """
        POST /primera-revision con proyectistas=[] (vacío) debe retornar 200.
        """
        response = client.post(
            "/api/liquidaciones/impacto-vial/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "area_solicitada": 100.0,
                    "expediente": "EXP-IV-PRO-001",
                    "proyectistas": [],
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()

    def test_crear_iv_con_proyectistas_inline_valido_retorna_200(self, client: Client):
        """
        POST /primera-revision con proyectistas inline (CIP válido, habilitado)
        debe retornar 200 y crear la asociación LiquidacionProyectista.
        """
        response = client.post(
            "/api/liquidaciones/impacto-vial/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "area_solicitada": 100.0,
                    "expediente": "EXP-IV-PRO-002",
                    "proyectistas": [
                        {
                            "cip": "000002",
                            "especialidad_id": str(self.especialidad.id),
                            "descripcion": "Proyectista IV de prueba",
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
        assert lp.proyectista.perfil_ingeniero.cip == "000002"

    def test_crear_iv_con_cip_invalido_retorna_error(self, client: Client):
        """
        POST /primera-revision con CIP no reconocido (no existe en CIP simulator)
        debe retornar error (no 200).
        """
        response = client.post(
            "/api/liquidaciones/impacto-vial/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "area_solicitada": 100.0,
                    "expediente": "EXP-IV-PRO-003",
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
# OBSOLETE — IV ahora usa LiquidacionPorcentajeObra (Edificaciones-style)
# =============================================================================
# Los tests de abajo (TestImpactoVialPorcentajeEndpoint) reemplazan estos.
# IV ya no usa area_solicitada ni LiquidacionPorMetroCuadrado.
# Marcados como @pytest.mark.skip — el M2 flow para IV fue deprecated.
# HU y MS siguen usando M2 — esos tests heredados siguen siendo válidos para ellos.


@pytest.mark.django_db
class TestImpactoVialPorcentajeEndpoint:
    """Test POST /api/liquidaciones/impacto-vial/primera-revision con cálculo porcentual."""

    def setup_method(self):
        """Seed IGV, UIT, proyecto, municipalidad y tarifa porcentual."""
        self.igv = IGVFactory()
        self.uit = UITFactory()
        self.proyecto = ProyectoFactory()

        from modules.entidades.tests.factories.ubigeo_factory import UbigeoDistritoFactory
        from modules.entidades.models import Municipalidad
        self.distrito = UbigeoDistritoFactory()
        self.municipalidad = Municipalidad.objects.create(
            codigo="MUN-IV-PCT-001",
            nombre="Municipalidad de Prueba IV Porcentaje",
            distrito=self.distrito,
        )

        # Crear tarifa porcentual (no M2) para IMPACTO_VIAL
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
            tipo_liquidacion="IMPACTO_VIAL",
        )
        # TarifaLiquidacionBaseFactory crea TarifaPorcentajeObra automáticamente via
        # detalle_porcentual RelatedFactory
        ReglaTarifaEdificacionFactory(
            tipo_tramite=TipoTramiteEdificaciones.OBRA_NUEVA,
            tramite_accion=TramiteAccion.PRIMERA_REVISION,
            tarifa_base=self.tarifa_base,
        )

    def test_crear_iv_porcentaje_retorna_200(self, client: Client):
        """
        POST /primera-revision con valor_proyecto debe retornar 200.
        IV ahora usa cálculo porcentual (Edificaciones-style).
        """
        response = client.post(
            "/api/liquidaciones/impacto-vial/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "valor_proyecto": 100000.0,
                    "expediente": "EXP-IV-PCT-001",
                    "observacion": "Test IV porcentaje",
                }
            },
            content_type="application/json",
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "data" in data

    def test_crear_iv_porcentaje_crea_liquidacion_general(self, client: Client):
        """
        POST debe crear LiquidacionGeneral para IV porcentual.
        """
        count_before = LiquidacionGeneral.objects.count()

        response = client.post(
            "/api/liquidaciones/impacto-vial/primera-revision",
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

    def test_crear_iv_porcentaje_crea_liquidacion_impacto_vial(self, client: Client):
        """
        POST debe crear LiquidacionImpactoVial.
        """
        count_before = LiquidacionImpactoVial.objects.count()

        response = client.post(
            "/api/liquidaciones/impacto-vial/primera-revision",
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
        count_after = LiquidacionImpactoVial.objects.count()
        assert count_after == count_before + 1

    def test_crear_iv_porcentaje_respuesta_flat_list_item(self, client: Client):
        """
        La respuesta es un flat list item (LiquidacionIVListItemOut) con los campos
        necesarios para post-create PDF sin refetch.

        Estructura: id, public_id, tipo_liquidacion, estado, fecha_registro,
        proyecto{valor_proyecto}, municipalidad, valores{subtotal,igv,total,total_a_pagar},
        revisiones[0]{tarifa{porcentaje_liquidacion,porcentaje_minimo_uit,derecho_minimo}}.
        """
        response = client.post(
            "/api/liquidaciones/impacto-vial/primera-revision",
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
        assert snapshot["tipo_liquidacion"] == "impacto-vial"
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

    def test_impacto_vial_porcentaje_igv_mayor_cero_total_mayor_subtotal(self, client: Client):
        """
        IV porcentual debe tener igv > 0 y total > subtotal.
        (Antes IV era M2 con igv=0; ahora es porcentaje con IGV como Edificaciones.)
        Estructura: valores{subtotal,igv,total,total_a_pagar} en flat list item.
        """
        response = client.post(
            "/api/liquidaciones/impacto-vial/primera-revision",
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
            f"IV porcentual debe tener igv > 0, got {valores['igv']}"
        )
        # total debe ser mayor que subtotal (porque total = subtotal + igv)
        assert valores["total"] > valores["subtotal"], (
            f"total ({valores['total']}) debe ser mayor que subtotal ({valores['subtotal']})"
        )
        # total_a_pagar debe incluir igv
        assert valores["total_a_pagar"] == valores["total"]

    def test_impacto_vial_porcentaje_derecho_minimo_en_tarifa(self, client: Client):
        """
        La respuesta flat list item incluye derecho_minimo en revisiones[0].tarifa.
        El derecho real (>= derecho_minimo) se refleja en valores.subtotal.
        """
        # valor_proyecto = 1000.0, porcentaje = 0.05 (5%) → 50
        # derecho_minimo default de TarifaPorcentajeObraFactory es 500.00
        # Entonces 1000 * 0.05 = 50 < 500 → derecho debería ser 500 (mínimo)
        response = client.post(
            "/api/liquidaciones/impacto-vial/primera-revision",
            data={
                "liquidacion": {
                    "proyecto_public_id": self.proyecto.public_id,
                    "municipalidad_id": str(self.municipalidad.id),
                    "valor_proyecto": 1000.0,  # 1000 * 0.05 = 50 < 500 (derecho_minimo)
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

    def test_impacto_vial_porcentaje_derecho_maximo_en_tarifa(self, client: Client):
        """
        La respuesta flat list item incluye derecho_maximo en revisiones[0].tarifa.
        El derecho real (capped a derecho_maximo) se refleja en valores.subtotal.
        """
        # Override derecho_maximo a 1000.00
        from modules.liquidaciones.domain.models.liquidacion.liquidacion import TarifaPorcentajeObra
        TarifaPorcentajeObra.objects.update(
            derecho_maximo=Decimal("1000.00"),
        )
        # valor_proyecto = 100000.0, porcentaje = 0.05 → 5000 > 1000 (capped)
        response = client.post(
            "/api/liquidaciones/impacto-vial/primera-revision",
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
