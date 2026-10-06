"""
LiquidacionRelacionCoreService — core service for LiquidacionRelacionGrupo and LiquidacionRelacionMiembro.

Sync service (no @transaction.atomic of its own) — caller provides the transaction.

Responsibilities:
- Create groups with unique codigo (retry on IntegrityError)
- Add members to groups
- Obtain/create groups for nueva revision with backfill
- Query group membership

Location: domain/services/core/liquidacion_general/
"""

from typing import Optional

from django.db import IntegrityError

from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion_relacion_grupo import (
    LiquidacionRelacionGrupo,
)
from modules.liquidaciones.domain.models.liquidacion.liquidacion_general.liquidacion_relacion_miembro import (
    LiquidacionRelacionMiembro,
)
from modules.liquidaciones.domain.models.liquidacion import LiquidacionGeneral
from modules.liquidaciones.domain.services.core.liquidacion_general.liquidacion_relacion_codigo_helper import (
    generar_codigo_grupo,
)


class LiquidacionRelacionCoreService:
    """
    Core service for relation group and member operations.

    Sync — no @transaction.atomic own. Caller wraps multi-write
    operations in transaction.atomic where needed.

    This service is injected into flujos via DI (singleton scope).
    """

    # ── Group creation ────────────────────────────────────────────────────────

    def crear_grupo(self) -> LiquidacionRelacionGrupo:
        """
        Create a new LiquidacionRelacionGrupo with a unique codigo.

        Generates a new code and retries on unique constraint violation
        (theoretical concurrent collision — low probability but handled).

        Returns:
            LiquidacionRelacionGrupo: the created group instance.
        """
        max_intentos = 5
        for intento in range(max_intentos):
            codigo = generar_codigo_grupo()
            try:
                grupo = LiquidacionRelacionGrupo.objects.create(codigo=codigo)
                return grupo
            except IntegrityError:
                if intento == max_intentos - 1:
                    raise

    def crear_grupo_con_reintento(self) -> tuple[LiquidacionRelacionGrupo, bool]:
        """
        Create a new group with retry logic.

        Returns:
            tuple: (grupo, fue_reintentado)
                - grupo: the created group instance
                - fue_reintentado: True if a retry was needed due to IntegrityError
        """
        max_intentos = 5
        fue_reintentado = False
        for intento in range(max_intentos):
            codigo = generar_codigo_grupo()
            try:
                grupo = LiquidacionRelacionGrupo.objects.create(codigo=codigo)
                return grupo, fue_reintentado
            except IntegrityError:
                fue_reintentado = True
                if intento == max_intentos - 1:
                    raise
        # Should not reach here
        raise RuntimeError("Unexpected exit in crear_grupo_con_reintento")

    # ── Member operations ────────────────────────────────────────────────────

    def agregar_miembro(
        self,
        grupo: LiquidacionRelacionGrupo,
        liquidacion: LiquidacionGeneral,
        relacion_key: str,
        numero_revision: int,
    ) -> LiquidacionRelacionMiembro:
        """
        Add a liquidacion as a member of a group.

        Args:
            grupo: the group to add the member to
            liquidacion: the LiquidacionGeneral instance
            relacion_key: the relation key (e.g., "PO-OBRA", "HU", "MS")
            numero_revision: the revision number of this liquidacion

        Returns:
            LiquidacionRelacionMiembro: the created member instance.

        Raises:
            IntegrityError: if (grupo, relacion_key, numero_revision) unique
                           constraint is violated, or liquidacion already has a group.
        """
        return LiquidacionRelacionMiembro.objects.create(
            grupo=grupo,
            liquidacion=liquidacion,
            relacion_key=relacion_key,
            numero_revision=numero_revision,
        )

    # ── Group queries ────────────────────────────────────────────────────────

    def obtener_grupo_de_liquidacion(
        self,
        liquidacion: LiquidacionGeneral,
    ) -> Optional[LiquidacionRelacionMiembro]:
        """
        Get the relation membership for a liquidacion, if any.

        Returns:
            LiquidacionRelacionMiembro if found, None otherwise.
        """
        try:
            return LiquidacionRelacionMiembro.objects.select_related("grupo").get(
                liquidacion=liquidacion
            )
        except LiquidacionRelacionMiembro.DoesNotExist:
            return None

    # ── Combined group + member operations ────────────────────────────────────

    def crear_grupo_con_miembro(
        self,
        liquidacion: LiquidacionGeneral,
        relacion_key: str,
        numero_revision: int,
    ) -> tuple[LiquidacionRelacionGrupo, LiquidacionRelacionMiembro]:
        """
        Create a new group and immediately add a member to it.

        This is the standard path for primera revision: a new group is created
        and the first liquidacion becomes its sole member.

        Args:
            liquidacion: the LiquidacionGeneral instance (already saved)
            relacion_key: the relation key for this liquidacion
            numero_revision: revision number (typically 1 for primera revision)

        Returns:
            tuple: (grupo, miembro)
        """
        grupo = self.crear_grupo()
        miembro = self.agregar_miembro(
            grupo=grupo,
            liquidacion=liquidacion,
            relacion_key=relacion_key,
            numero_revision=numero_revision,
        )
        return grupo, miembro

    def agregar_miembro_a_grupo_de_previa(
        self,
        liquidacion_previa: "LiquidacionGeneral",
        liquidacion_nueva: "LiquidacionGeneral",
        relacion_key: str,
        numero_revision: int,
        relacion_key_previa: str | None = None,
    ) -> tuple["LiquidacionRelacionMiembro", bool]:
        """
        Add a new liquidacion member to the group of a previous liquidacion.

        If the previous liquidacion has no group yet (edge case), this method:
        1. Creates a new group
        2. Backfills the previous liquidacion as a member with its own relation_key
        3. Adds the new liquidacion as a member

        This ensures that even "islands" (liquidaciones created before this feature
        existed) can be incorporated into the relation group system.

        Args:
            liquidacion_previa: the existing LiquidacionGeneral that the new one is based on
            liquidacion_nueva: the new LiquidacionGeneral to add to the group
            relacion_key: the relation key for the new liquidacion
            numero_revision: revision number for the new liquidacion
            relacion_key_previa: optional relation key for the previous liquidacion
                                when backfilling a group. Defaults to relacion_key.

        Returns:
            tuple: (miembro_nuevo, fue_backfill)
                - miembro_nuevo: the created member for the new liquidacion
                - fue_backfill: True if a backfill was performed (previa had no group)
        """
        # Try to find the group's member for the previous liquidacion
        miembro_previo = self.obtener_grupo_de_liquidacion(liquidacion_previa)

        if miembro_previo is not None:
            # Previous liquidacion has a group — add new member to it
            grupo = miembro_previo.grupo
            fue_backfill = False
        else:
            # Backfill scenario: previous liquidacion has no group yet.
            # Create a group and backfill the previous liquidacion first.
            grupo, _ = self.crear_grupo_con_miembro(
                liquidacion=liquidacion_previa,
                relacion_key=relacion_key_previa or relacion_key,
                numero_revision=liquidacion_previa.numero_revision,
            )
            fue_backfill = True

        # Now add the new liquidacion as a member of this group
        miembro_nuevo = self.agregar_miembro(
            grupo=grupo,
            liquidacion=liquidacion_nueva,
            relacion_key=relacion_key,
            numero_revision=numero_revision,
        )
        return miembro_nuevo, fue_backfill

    # ── Member deletion ────────────────────────────────────────────────────

    def eliminar_miembros_de_liquidacion(
        self,
        liquidacion: "LiquidacionGeneral",
    ) -> tuple[int, int]:
        """
        Physically delete all LiquidacionRelacionMiembro rows for a given liquidacion.

        Called when a LiquidacionGeneral is soft-deleted. If the deleted member(s)
        were the last/only members in their group(s), the group(s) are also deleted.
        If a group still has other members, it is retained.

        Args:
            liquidacion: the LiquidacionGeneral being soft-deleted

        Returns:
            tuple: (members_deleted, groups_deleted)
                - members_deleted: number of LiquidacionRelacionMiembro rows deleted
                - groups_deleted: number of LiquidacionRelacionGrupo rows deleted
                  (groups that became empty after member deletion)
        """
        # Collect affected group ids BEFORE deleting members so we can check emptiness
        miembros = LiquidacionRelacionMiembro.objects.filter(liquidacion=liquidacion)
        group_ids_to_check = list(miembros.values_list("grupo_id", flat=True))

        # Delete the member rows
        members_deleted, _ = miembros.delete()

        # Delete groups that now have zero members
        groups_deleted = 0
        for group_id in group_ids_to_check:
            remaining = LiquidacionRelacionMiembro.objects.filter(grupo_id=group_id).count()
            if remaining == 0:
                LiquidacionRelacionGrupo.objects.filter(id=group_id).delete()
                groups_deleted += 1

        return members_deleted, groups_deleted
