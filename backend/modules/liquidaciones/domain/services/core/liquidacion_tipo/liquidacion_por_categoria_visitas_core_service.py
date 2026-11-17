"""
Core Service para el motor de Liquidación por Categoría de Visitas.
Maneja la lógica matemática y la persistencia de la tabla de Tipo.

MOTOR ÚNICO DE COTIZACIÓN DE VISITAS (Inspección de Obra)
==========================================================
`calcular_cotizacion_visitas_estrategia(contexto)` es el único motor aritmético
del motor de Visitas. Recibe un contexto tipado ya RESUELTO (modo, cantidad de
visitas, tarifa, UIT, IGV y crédito) y devuelve la proyección efímera: valor
completo de B + bloque de continuidad.

Reglas del motor (invariantes normativos del cambio):

- IV-1  diferencia_neto == quantize(valor_completo_neto − credito_neto)
- IV-2  diferencia_bruto == quantize(valor_completo_bruto − credito_bruto)
- IV-3  credito_neto >= 0 y credito_bruto >= 0
- IV-4  credito_bruto == quantize(credito_neto × (1+g)) o el bruto fue provisto
        explícitamente (crédito congelado)
- IV-5  diferencia_neto >= 0 y diferencia_bruto >= 0 → el crédito NO puede
        superar el valor completo de B (400)
- IV-6  valor_completo_neto == quantize(monto_neto_visitas) y
        valor_completo_bruto == quantize(valor_completo_neto × (1+g))
- IV-7  (NORMAL) total == subtotal × (1+g) SIN cuantizar → byte-compatibilidad
- IV-8  el bruto declarado `total_pagado_previa` es > 0 y <= 9999999999.99

El motor NO consulta la base de datos ni "hoy": los valores (IGV, UIT, tarifa)
los resuelve el llamador y se los entrega ya resueltos, de modo que la
cotización y lo que se persiste usan EXACTAMENTE el mismo IGV.

`calcular_cotizacion_visitas` se conserva como FACHADA de compatibilidad
(cotizar-edición, import legacy y tests) y delega en la aritmética pura, sin
cambiar una sola cifra.
"""
from typing import Optional
from decimal import Decimal
from injector import inject

from core.exceptions import BusinessError
from core.types import BaseSchema

from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.liquidacion_tipo import (
    LiquidacionPorCategoriaVisitas,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_tipo.tarifas_reglas import (
    TarifaLiquidacionBase,
    TarifaPorCategoriaVisitas,
)
from modules.liquidaciones.domain.constants import ModoCotizacionVisitas, TipoLiquidacion
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion import (
    LiquidacionGeneral,
)
from modules.finanzas.domain.models.impuestos import UIT, IGV
from modules.liquidaciones.domain.schemas.liquidacion_tipo.liquidacion_visitas_data import (
    LiquidacionCategoriaVisitasData,
)
from modules.liquidaciones.domain.services.core.liquidacion_tipo.liquidacion_continuidad_visitas_core_service import (
    quantize_money,
)


# ── Tipos canónicos del motor único de cotización de Visitas ──────────────────


class CotizacionVisitasContexto(BaseSchema):
    """
    Entrada canónica del motor único de cotización de Visitas (IO).

    Todo llega RESUELTO: el modo, la cantidad de visitas, la tarifa y su
    porcentaje de UIT, el valor de la UIT, el IGV efectivo de la ruta y el
    crédito. El motor NO consulta la base de datos ni "hoy".
    """

    modo: str = ModoCotizacionVisitas.NORMAL

    # ── Valor completo de B (origen del cálculo) ─────────────────────────────
    cantidad_visitas: int
    porcentaje_uit: Decimal
    uit_valor: Decimal
    igv_porcentaje: Decimal

    # ── Identidad de la tarifa y de las variables financieras (eco) ──────────
    categoria: str
    tarifa_id: str
    uit_id: Optional[str] = None
    igv_id: Optional[str] = None

    # ── Crédito (mutuamente excluyentes por regla de precedencia) ───────────
    total_pagado_previa: Optional[Decimal] = None   # BRUTO declarado (prioridad 1)
    credito_neto: Optional[Decimal] = None           # NETO ya resuelto (prioridad 2)
    credito_bruto: Optional[Decimal] = None          # BRUTO del crédito congelado (prioridad 2)


class CotizacionVisitasContinuidadData(BaseSchema):
    """Cifras autoritativas de la continuidad (netas y brutas)."""

    total_pagado_previa: Decimal
    valor_completo_neto: Decimal
    valor_completo_bruto: Decimal
    credito_neto: Decimal
    credito_bruto: Decimal
    diferencia_neto: Decimal
    diferencia_bruto: Decimal
    igv_porcentaje: Decimal


class CotizacionVisitasEstrategiaData(BaseSchema):
    """
    Salida canónica del motor único de cotización de Visitas.

    `monto_bruto`/`subtotal`/`total` son el VALOR COMPLETO de B (misma semántica
    que antes). `continuidad` es None en NORMAL.
    """

    modo: str
    cantidad_visitas: int
    categoria: str
    costo_por_visita: Decimal
    tarifa_id: str
    monto_bruto: Decimal
    subtotal: Decimal
    total: Decimal
    uit: dict
    igv: dict
    continuidad: Optional[CotizacionVisitasContinuidadData] = None


class LiquidacionPorCategoriaVisitasCoreService:
    @inject
    def __init__(self):
        pass

    def get_tarifas_vigentes(self) -> list[TarifaPorCategoriaVisitas]:
        """Obtiene todas las tarifas vigentes para la categoría de visitas."""
        bases = TarifaLiquidacionBase.objects.vigentes().filter(
            tipo_liquidacion__codigo=TipoLiquidacion.INSPECCION_OBRA
        )
        return list(
            TarifaPorCategoriaVisitas.objects.filter(
                tarifa_base__in=bases
            ).select_related("tarifa_base")
        )

    def get_tarifa_por_id(self, tarifa_id: str) -> Optional[TarifaPorCategoriaVisitas]:
        """Busca y retorna una tarifa específica por ID. Returns None if not found."""
        try:
            return TarifaPorCategoriaVisitas.objects.get(id=tarifa_id)
        except TarifaPorCategoriaVisitas.DoesNotExist:
            return None

    def calcular_subtotal_visitas(
        self,
        cantidad_visitas: int,
        tarifa: TarifaPorCategoriaVisitas,
        uit_vigente: UIT,
    ) -> Decimal:
        """
        Fórmula matemática para Visitas: cantidad_visitas * (porcentaje_uit * valor_uit)
        """
        costo_por_visita = tarifa.porcentaje_uit * Decimal(str(uit_vigente.valor))
        return Decimal(str(cantidad_visitas)) * costo_por_visita

    # ── Aritmética pura (sin acceso a la base de datos) ──────────────────────

    @staticmethod
    def calcular_cotizacion_visitas_puro(
        cantidad_visitas: int,
        porcentaje_uit: Decimal,
        categoria: str,
        tarifa_id: str,
        uit_valor: Decimal,
        igv_porcentaje: Decimal,
        *,
        uit_id: Optional[str] = None,
        igv_id: Optional[str] = None,
    ) -> CotizacionVisitasEstrategiaData:
        """
        Aritmética vigente del motor de Visitas (modo NORMAL), en memoria pura.

        `total` NO se cuantiza: es la aritmética vigente byte-compatible
        (`total = subtotal × (1 + g)`), igual que antes de este cambio.

        `uit_id`/`igv_id` son opcionales porque solo se usan para el ECO de las
        variables financieras de la respuesta (`datos.variables_financieras`).
        """
        costo_por_visita = porcentaje_uit * uit_valor
        subtotal = Decimal(str(cantidad_visitas)) * costo_por_visita
        total = subtotal * (Decimal("1") + igv_porcentaje)

        return CotizacionVisitasEstrategiaData(
            modo=ModoCotizacionVisitas.NORMAL,
            cantidad_visitas=cantidad_visitas,
            categoria=categoria,
            costo_por_visita=costo_por_visita,
            tarifa_id=tarifa_id,
            monto_bruto=subtotal,
            subtotal=subtotal,
            total=total,
            uit={"id": uit_id, "valor": float(uit_valor)},
            igv={"id": igv_id, "valor": float(igv_porcentaje)},
            continuidad=None,
        )

    def calcular_cotizacion_visitas(
        self,
        cantidad_visitas: int,
        tarifa_visitas_id: str,
        uit_vigente: UIT,
        igv_vigente: "IGV",
    ) -> Optional["CotizacionVisitasResult"]:
        """
        FACHADA de compatibilidad del motor de Visitas.

        Resuelve la tarifa y delega en la aritmética pura. Las cifras NO
        cambian: es exactamente la aritmética vigente.
        PURE computation - returns None if tariff not found.
        """
        tarifa = self.get_tarifa_por_id(tarifa_visitas_id)
        if not tarifa:
            return None

        estrategia = self.calcular_cotizacion_visitas_puro(
            cantidad_visitas=cantidad_visitas,
            porcentaje_uit=Decimal(str(tarifa.porcentaje_uit)),
            categoria=tarifa.categoria_visitas,
            tarifa_id=str(tarifa.id),
            uit_valor=Decimal(str(uit_vigente.valor)),
            igv_porcentaje=Decimal(str(igv_vigente.valor)),
            uit_id=str(uit_vigente.id),
            igv_id=str(igv_vigente.id),
        )
        return self.resultado_desde_estrategia(estrategia)

    # ── Motor único de cotización por modo ───────────────────────────────────

    @staticmethod
    def construir_contexto_visitas(
        *,
        modo: str = ModoCotizacionVisitas.NORMAL,
        cantidad_visitas: int,
        porcentaje_uit: Decimal,
        uit_valor: Decimal,
        igv_porcentaje: Decimal,
        categoria: str,
        tarifa_id: str,
        total_pagado_previa: Optional[Decimal] = None,
        credito_neto: Optional[Decimal] = None,
        credito_bruto: Optional[Decimal] = None,
        uit_id: Optional[str] = None,
        igv_id: Optional[str] = None,
    ) -> CotizacionVisitasContexto:
        """
        FÁBRICA ÚNICA del contexto del motor.

        Todos los call sites (cotización de alta, cotización de edición, alta y
        PATCH) arman el contexto con esta factory: el motor recibe SIEMPRE la
        misma forma de entrada.
        """
        return CotizacionVisitasContexto(
            modo=modo,
            cantidad_visitas=cantidad_visitas,
            porcentaje_uit=porcentaje_uit,
            uit_valor=uit_valor,
            igv_porcentaje=igv_porcentaje,
            categoria=categoria,
            tarifa_id=tarifa_id,
            total_pagado_previa=total_pagado_previa,
            credito_neto=credito_neto,
            credito_bruto=credito_bruto,
            uit_id=uit_id,
            igv_id=igv_id,
        )

    def calcular_cotizacion_visitas_estrategia(
        self,
        contexto: CotizacionVisitasContexto,
    ) -> CotizacionVisitasEstrategiaData:
        """
        MOTOR ÚNICO de cotización de Visitas (IO).

        Recibe el contexto ya resuelto y devuelve la proyección efímera
        (valor completo de B + bloque de continuidad). Es la única fuente de
        aritmética del motor de Visitas: preview, alta y edición deben invocar
        este método.

        - NORMAL: la aritmética vigente, SIN cuantizar (compatibilidad).
        - CONTINUAR: todo cuantizado a 2 decimales (ROUND_HALF_UP); el bruto
          declarado por el cliente se convierte en crédito neto/bruto con el
          IGV efectivo de la ruta.

        Los invariantes se verifican ANTES de devolver
        (verificar_invariantes_visitas): nunca se devuelven cifras que no
        cierran.
        """
        if contexto.modo == ModoCotizacionVisitas.NORMAL:
            cotizacion = self._calcular_modo_normal(contexto)
        elif contexto.modo == ModoCotizacionVisitas.CONTINUAR:
            cotizacion = self._calcular_modo_continuar(contexto)
        else:
            raise BusinessError(
                f"Modo de cotización no soportado: {contexto.modo}",
                code="IO_MODO_COTIZACION_NO_SOPORTADO",
            )

        self.verificar_invariantes_visitas(cotizacion, contexto)
        return cotizacion

    @staticmethod
    def calcular_credito_continuidad(
        total_pagado_previa: Decimal,
        igv_porcentaje: Decimal,
    ) -> tuple[Decimal, Decimal]:
        """
        Deriva el par (crédito NETO, crédito BRUTO) desde el bruto declarado.

        El bruto declarado es el monto BRUTO pagado en la IO previa (IGV
        incluido). El servidor es la autoridad de la conversión:

            credito_neto  = quantize(bruto ÷ (1 + g))
            credito_bruto = quantize(credito_neto × (1 + g))

        La conversión NO es idempotente al céntimo: el bruto derivado puede
        diferir del declarado en <= 0.01 (redondeo de la división). Por eso el
        motor devuelve SIEMPRE las cifras derivadas y el bruto declarado solo
        se devuelve como eco informativo.
        """
        g = Decimal(str(igv_porcentaje))
        credito_neto = quantize_money(
            Decimal(str(total_pagado_previa)) / (Decimal("1") + g)
        )
        credito_bruto = quantize_money(credito_neto * (Decimal("1") + g))
        return credito_neto, credito_bruto

    @staticmethod
    def resolver_credito_continuidad(
        contexto: CotizacionVisitasContexto,
    ) -> tuple[Decimal, Decimal]:
        """
        REGLA ÚNICA de resolución del crédito (un solo lugar para los tres
        caminos: cotización, alta y PATCH).

        1. `total_pagado_previa` (BRUTO declarado) → MANDA.
        2. `credito_neto` (NETO ya resuelto) → se usa tal cual; el bruto se
           deriva salvo que venga provisto (crédito congelado).
        3. Sin crédito → (0, 0).
        """
        g = Decimal(str(contexto.igv_porcentaje))
        if contexto.total_pagado_previa is not None:
            return LiquidacionPorCategoriaVisitasCoreService.calcular_credito_continuidad(
                contexto.total_pagado_previa, g
            )
        if contexto.credito_neto is not None:
            credito_neto = Decimal(str(contexto.credito_neto))
            if contexto.credito_bruto is not None:
                return credito_neto, Decimal(str(contexto.credito_bruto))
            return credito_neto, quantize_money(credito_neto * (Decimal("1") + g))
        return Decimal("0"), Decimal("0")

    @staticmethod
    def _calcular_modo_normal(
        contexto: CotizacionVisitasContexto,
    ) -> CotizacionVisitasEstrategiaData:
        """
        NORMAL — delega en la aritmética vigente, sin cuantizar.

        Ninguna cifra de NORMAL se mueve: `total = subtotal × (1 + g)` tal
        como antes (garantía de byte-compatibilidad, IV-7).
        """
        return LiquidacionPorCategoriaVisitasCoreService.calcular_cotizacion_visitas_puro(
            cantidad_visitas=contexto.cantidad_visitas,
            porcentaje_uit=contexto.porcentaje_uit,
            categoria=contexto.categoria,
            tarifa_id=contexto.tarifa_id,
            uit_valor=contexto.uit_valor,
            igv_porcentaje=contexto.igv_porcentaje,
            uit_id=contexto.uit_id,
            igv_id=contexto.igv_id,
        )

    @staticmethod
    def _calcular_modo_continuar(
        contexto: CotizacionVisitasContexto,
    ) -> CotizacionVisitasEstrategiaData:
        """
        CONTINUAR — TODO cuantizado a 2 decimales (ROUND_HALF_UP).

            valor_completo_neto  = quantize(monto_neto_visitas)
            valor_completo_bruto = quantize(valor_completo_neto × (1 + g))
            credito_neto         = quantize(total_pagado_previa ÷ (1 + g))
            credito_bruto        = quantize(credito_neto × (1 + g))
            diferencia_neto      = quantize(valor_completo_neto − credito_neto)
            diferencia_bruto     = quantize(valor_completo_bruto − credito_bruto)

        El bloque `calculo` de la respuesta lleva el VALOR COMPLETO de B:
        `monto_bruto = subtotal = valor_completo_neto` y
        `total = valor_completo_bruto`.
        """
        g = Decimal(str(contexto.igv_porcentaje))
        costo_por_visita = contexto.porcentaje_uit * contexto.uit_valor
        monto_neto_visitas = Decimal(str(contexto.cantidad_visitas)) * costo_por_visita

        valor_completo_neto = quantize_money(monto_neto_visitas)
        valor_completo_bruto = quantize_money(valor_completo_neto * (Decimal("1") + g))

        credito_neto, credito_bruto = LiquidacionPorCategoriaVisitasCoreService.resolver_credito_continuidad(
            contexto
        )

        diferencia_neto = quantize_money(valor_completo_neto - credito_neto)
        diferencia_bruto = quantize_money(valor_completo_bruto - credito_bruto)

        continuidad = CotizacionVisitasContinuidadData(
            total_pagado_previa=(
                Decimal(str(contexto.total_pagado_previa))
                if contexto.total_pagado_previa is not None
                else credito_bruto
            ),
            valor_completo_neto=valor_completo_neto,
            valor_completo_bruto=valor_completo_bruto,
            credito_neto=credito_neto,
            credito_bruto=credito_bruto,
            diferencia_neto=diferencia_neto,
            diferencia_bruto=diferencia_bruto,
            igv_porcentaje=g,
        )

        return CotizacionVisitasEstrategiaData(
            modo=ModoCotizacionVisitas.CONTINUAR,
            cantidad_visitas=contexto.cantidad_visitas,
            categoria=contexto.categoria,
            costo_por_visita=costo_por_visita,
            tarifa_id=contexto.tarifa_id,
            monto_bruto=valor_completo_neto,
            subtotal=valor_completo_neto,
            total=valor_completo_bruto,
            uit={"id": contexto.uit_id, "valor": float(contexto.uit_valor)},
            igv={"id": contexto.igv_id, "valor": float(g)},
            continuidad=continuidad,
        )

    def verificar_invariantes_visitas(
        self,
        cotizacion: CotizacionVisitasEstrategiaData,
        contexto: CotizacionVisitasContexto,
    ) -> None:
        """
        Verifica los invariantes normativos de la cotización de Visitas.

        Levanta `BusinessError` (400) ANTES de cualquier escritura: nunca se
        devuelven cifras que no cierran.
        """
        g = Decimal(str(contexto.igv_porcentaje))

        # IV-8 — el bruto declarado es un dato de entrada acotado.
        if contexto.total_pagado_previa is not None:
            declarado = Decimal(str(contexto.total_pagado_previa))
            if declarado <= 0 or declarado > Decimal("9999999999.99"):
                raise BusinessError(
                    "El monto bruto pagado en la liquidación previa debe ser mayor "
                    "a cero y no superar 9999999999.99.",
                    code="IO_INVARIANTE_TOTAL_PAGADO_PREVIA",
                )

        continuidad = cotizacion.continuidad

        if continuidad is None:
            # IV-7 — NORMAL: el total NO se cuantiza (byte-compatibilidad).
            if cotizacion.total != cotizacion.subtotal * (Decimal("1") + g):
                raise BusinessError(
                    "El total de la cotización no coincide con el subtotal "
                    "aplicando el IGV.",
                    code="IO_INVARIANTE_TOTAL_NORMAL",
                )
            return

        # IV-1 — la diferencia neta es la resta cuantizada del par derivado.
        if continuidad.diferencia_neto != quantize_money(
            continuidad.valor_completo_neto - continuidad.credito_neto
        ):
            raise BusinessError(
                "La diferencia neta no coincide con el valor completo menos el "
                "crédito.",
                code="IO_INVARIANTE_DIFERENCIA_NETA",
            )

        # IV-2 — la diferencia bruta es la resta cuantizada del par derivado.
        if continuidad.diferencia_bruto != quantize_money(
            continuidad.valor_completo_bruto - continuidad.credito_bruto
        ):
            raise BusinessError(
                "La diferencia bruta no coincide con el valor completo menos el "
                "crédito.",
                code="IO_INVARIANTE_DIFERENCIA_BRUTA",
            )

        # IV-3 — el crédito no es negativo.
        if continuidad.credito_neto < 0 or continuidad.credito_bruto < 0:
            raise BusinessError(
                "El crédito de la continuidad no puede ser negativo.",
                code="IO_INVARIANTE_CREDITO_NO_NEGATIVO",
            )

        # IV-4 — el bruto del crédito es el par del neto, salvo que haya sido
        # provisto explícitamente (crédito congelado).
        if (
            contexto.total_pagado_previa is None
            and contexto.credito_bruto is None
            and continuidad.credito_bruto
            != quantize_money(continuidad.credito_neto * (Decimal("1") + g))
        ):
            raise BusinessError(
                "El crédito bruto no coincide con el crédito neto aplicando el IGV.",
                code="IO_INVARIANTE_CREDITO_BRUTO",
            )

        # IV-5 — el crédito NO puede superar el valor completo del trabajo.
        if continuidad.diferencia_neto < 0 or continuidad.diferencia_bruto < 0:
            raise BusinessError(
                "El crédito no puede superar el valor completo del trabajo.",
                code="IO_INVARIANTE_CREDITO_MAYOR_VALOR_COMPLETO",
            )

        # IV-6 — el valor completo de B es el derivado de la aritmética vigente.
        monto_neto_visitas = Decimal(str(contexto.cantidad_visitas)) * (
            contexto.porcentaje_uit * contexto.uit_valor
        )
        if continuidad.valor_completo_neto != quantize_money(monto_neto_visitas):
            raise BusinessError(
                "El valor completo neto no coincide con el cálculo de las visitas.",
                code="IO_INVARIANTE_VALOR_COMPLETO_NETO",
            )
        if continuidad.valor_completo_bruto != quantize_money(
            continuidad.valor_completo_neto * (Decimal("1") + g)
        ):
            raise BusinessError(
                "El valor completo bruto no coincide con el valor completo neto "
                "aplicando el IGV.",
                code="IO_INVARIANTE_VALOR_COMPLETO_BRUTO",
            )

    @staticmethod
    def resultado_desde_estrategia(
        estrategia: CotizacionVisitasEstrategiaData,
    ) -> "CotizacionVisitasResult":
        """
        Proyecta la salida del motor al DTO de dominio que viaja al presenter.

        Es el único puente entre la proyección efímera del motor y el contrato
        interno de cotización (`CotizacionVisitasResult`).
        """
        from modules.liquidaciones.domain.results.liquidacion_tipo.cotizacion import (
            CotizacionVisitasContinuidadResult,
            CotizacionVisitasResult,
        )

        continuidad = None
        if estrategia.continuidad is not None:
            bloque = estrategia.continuidad
            continuidad = CotizacionVisitasContinuidadResult(
                total_pagado_previa=bloque.total_pagado_previa,
                valor_completo_neto=bloque.valor_completo_neto,
                valor_completo_bruto=bloque.valor_completo_bruto,
                credito_neto=bloque.credito_neto,
                credito_bruto=bloque.credito_bruto,
                diferencia_neto=bloque.diferencia_neto,
                diferencia_bruto=bloque.diferencia_bruto,
                igv_porcentaje=bloque.igv_porcentaje,
            )

        return CotizacionVisitasResult(
            cantidad_visitas=estrategia.cantidad_visitas,
            categoria=estrategia.categoria,
            costo_por_visita=estrategia.costo_por_visita,
            tarifa_id=estrategia.tarifa_id,
            monto_bruto=estrategia.monto_bruto,
            subtotal=estrategia.subtotal,
            total=estrategia.total,
            uit=estrategia.uit,
            igv=estrategia.igv,
            modo_cotizacion=estrategia.modo,
            continuidad=continuidad,
        )

    def crear_liquidacion_tipo_visitas(
        self,
        liquidacion_general: LiquidacionGeneral,
        data: LiquidacionCategoriaVisitasData,
    ) -> LiquidacionPorCategoriaVisitas:
        """
        Guarda la instancia de LiquidacionPorCategoriaVisitas (El motor de Tipo).
        NOTA: No lleva @transaction.atomic porque eso lo controla el Flujo.

        Null-tariff path (legacy/manual IO):
        - When tarifa_visitas_id is None and override totals are provided by caller,
          the flujo passes null categoria/porcentaje_uit.
        - This creates a LiquidacionPorCategoriaVisitas with null FK and null fields,
          which is valid for legacy records with CATEGORIA=0 or unmatched tariffs.
        """
        tarifa = None
        porcentaje_uit = None
        categoria = data.datos.categoria
        if categoria in {"C1", "C2", "C3", "C4"}:
            categoria = categoria[1:]

        if data.tarifa and data.tarifa.tarifa_visitas_id:
            tarifa = self.get_tarifa_por_id(data.tarifa.tarifa_visitas_id)
            if tarifa:
                porcentaje_uit = tarifa.porcentaje_uit
                categoria = tarifa.categoria_visitas
                if categoria in {"C1", "C2", "C3", "C4"}:
                    categoria = categoria[1:]

        liquidacion_visitas = LiquidacionPorCategoriaVisitas.objects.create(
            liquidacion_general=liquidacion_general,
            cantidad_visitas=data.datos.cantidad_visitas,
            porcentaje_uit=porcentaje_uit,
            categoria=categoria,
            tarifa_aplicada=tarifa,
        )
        return liquidacion_visitas
