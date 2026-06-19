"""
Pruebas para comandos de gestión de liquidaciones.

Estas pruebas verifican el comportamiento de carga de datos seed reales usando
solo seeds locales (--skip-endpoint) para evitar llamadas al endpoint externo del CIP.
"""

import pytest
from django.core.management import call_command

from modules.entidades.models import Municipalidad
from modules.liquidaciones.models import Delegado, MunicipalidadDelegado
from modules.usuarios.models import PerfilIngeniero


@pytest.mark.django_db
class TestLoadDelegadosReales:
    """Probar carga de datos seed con load_delegados_reales --skip-endpoint."""

    def test_seed_loads_correct_perfil_ingeniero_count(self):
        """
        Después de ejecutar load_delegados_reales --skip-endpoint, deberíamos tener
        exactamente 60 registros de PerfilIngeniero (uno por delegado).
        """
        call_command("load_delegados_reales", "--skip-endpoint")
        assert PerfilIngeniero.objects.count() == 60

    def test_seed_loads_correct_delegado_count(self):
        """
        Después de ejecutar load_delegados_reales --skip-endpoint, deberíamos tener
        exactamente 60 registros de Delegado.
        """
        call_command("load_delegados_reales", "--skip-endpoint")
        assert Delegado.objects.count() == 60

    def test_seed_loads_correct_municipalidad_count(self):
        """
        Después de ejecutar load_delegados_reales --skip-endpoint, deberíamos tener
        exactamente 101 registros de municipalidad con códigos MUN0001-MUN0101.
        """
        call_command("load_delegados_reales", "--skip-endpoint")
        assert Municipalidad.objects.count() == 101

    def test_seed_loads_municipalidad_codes_mun0001_to_mun0101(self):
        """
        Verifica que existan todos los 101 códigos de municipalidad MUN0001 a MUN0101.
        """
        call_command("load_delegados_reales", "--skip-endpoint")

        expected_codes = [f"MUN{i:04d}" for i in range(1, 102)]
        actual_codes = set(Municipalidad.objects.values_list("codigo", flat=True))

        missing = set(expected_codes) - actual_codes
        extra = actual_codes - set(expected_codes)

        assert not missing, f"Códigos de municipalidad faltantes: {sorted(missing)}"
        assert not extra, f"Códigos de municipalidad extra: {sorted(extra)}"

    def test_seed_loads_correct_municipalidad_delegado_assignment_count(self):
        """
        Después de ejecutar load_delegados_reales --skip-endpoint, deberíamos tener
        exactamente 551 registros de asignación municipalidad_delegado.
        """
        call_command("load_delegados_reales", "--skip-endpoint")
        assert MunicipalidadDelegado.objects.count() == 551

    def test_seed_is_idempotent(self):
        """
        Ejecutar el comando seed dos veces no debería duplicar registros.
        La segunda ejecución debería actualizar registros existentes, no crear nuevos.
        """
        call_command("load_delegados_reales", "--skip-endpoint")
        call_command("load_delegados_reales", "--skip-endpoint")

        assert PerfilIngeniero.objects.count() == 60
        assert Delegado.objects.count() == 60
        assert Municipalidad.objects.count() == 101
        assert MunicipalidadDelegado.objects.count() == 551

    def test_seed_delegados_have_valid_perfil_ingeniero_relationship(self):
        """
        Todo Delegado debe tener un PerfilIngeniero válido mediante relación OneToOne.
        """
        call_command("load_delegados_reales", "--skip-endpoint")

        delegados = Delegado.objects.select_related("perfil_ingeniero")
        for delegado in delegados:
            assert delegado.perfil_ingeniero is not None
            assert hasattr(delegado.perfil_ingeniero, "cip")
            assert len(delegado.perfil_ingeniero.cip) == 6

    def test_seed_municipalidad_delegado_assignments_are_active(self):
        """
        Las 551 asignaciones municipalidad_delegado deben estar marcadas como activas.
        """
        call_command("load_delegados_reales", "--skip-endpoint")

        inactive = MunicipalidadDelegado.objects.filter(activo=False).count()
        assert inactive == 0, f"Se encontraron {inactive} asignaciones inactivas"

    def test_seed_delegados_have_especialidad(self):
        """
        Todo Delegado debe tener una Especialidad asignada.
        """
        call_command("load_delegados_reales", "--skip-endpoint")

        without_especialidad = Delegado.objects.filter(especialidad__isnull=True).count()
        assert without_especialidad == 0, f"Se encontraron {without_especialidad} delegados sin especialidad"

    def test_seed_delegados_have_status_activo(self):
        """
        Todos los delegados cargados deben tener estado ACTIVO.
        """
        call_command("load_delegados_reales", "--skip-endpoint")

        from modules.liquidaciones.domain.constants import DelegadoStatus
        inactive = Delegado.objects.exclude(status=DelegadoStatus.ACTIVO).count()
        assert inactive == 0, f"Se encontraron {inactive} delegados no activos"


@pytest.mark.django_db
class TestSeedRealAll:
    """Probar comando de orquestación seed_real_all (usa --skip-endpoint por defecto)."""

    def test_seed_real_all_loads_all_data(self):
        """
        El comando seed_real_all debe cargar ubigeo + delegados,
        resultando en los recuentos de registros esperados.
        """
        call_command("seed_real_all")
        assert PerfilIngeniero.objects.count() == 60
        assert Delegado.objects.count() == 60
        assert Municipalidad.objects.count() == 101
        assert MunicipalidadDelegado.objects.count() == 551
