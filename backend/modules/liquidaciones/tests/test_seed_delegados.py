"""
Pruebas para comandos de gestión de liquidaciones.

Estas pruebas verifican el comportamiento de carga de datos seed reales usando
solo seeds locales (--skip-endpoint) para evitar llamadas al endpoint externo del CIP.
"""

import json
import pytest
from pathlib import Path
from django.conf import settings
from django.core.management import call_command

from modules.entidades.models import Municipalidad
from modules.liquidaciones.models import Delegado, MunicipalidadDelegado
from modules.usuarios.models import PerfilIngeniero


def _get_seed_counts():
    """
    Carga los archivos de seed y retorna las cuentas reales.
    
    Returns dict con:
        - delegate_count: número de delegados en el seed
        - municipalidad_count: número de municipalidades
        - assignment_count: número de asignaciones
        - expected_codes: códigos de municipalidad esperados
    """
    seed_path = Path(settings.BASE_DIR) / 'modules' / 'liquidaciones' / 'seeds' / 'delegados_reales.json'
    with open(seed_path, encoding='utf-8') as f:
        data = json.load(f)
    
    delegate_count = len(data.get('delegados', []))
    municipalidad_count = len(data.get('municipalidades', []))
    assignment_count = len(data.get('asignaciones', []))
    expected_codes = sorted([m['codigo'] for m in data.get('municipalidades', [])])
    
    return {
        'delegate_count': delegate_count,
        'municipalidad_count': municipalidad_count,
        'assignment_count': assignment_count,
        'expected_codes': expected_codes,
    }


@pytest.mark.django_db
class TestLoadDelegadosReales:
    """Probar carga de datos seed con load_delegados_reales --skip-endpoint."""

    def test_seed_loads_correct_perfil_ingeniero_count(self):
        """
        Después de ejecutar load_delegados_reales --skip-endpoint, deberíamos tener
        un registro de PerfilIngeniero por cada delegado en el seed.
        """
        counts = _get_seed_counts()
        call_command("load_delegados_reales", "--skip-endpoint")
        assert PerfilIngeniero.objects.count() == counts['delegate_count']

    def test_seed_loads_correct_delegado_count(self):
        """
        Después de ejecutar load_delegados_reales --skip-endpoint, deberíamos tener
        exactamente un registro de Delegado por cada delegado en el seed.
        """
        counts = _get_seed_counts()
        call_command("load_delegados_reales", "--skip-endpoint")
        assert Delegado.objects.count() == counts['delegate_count']

    def test_seed_loads_correct_municipalidad_count(self):
        """
        Después de ejecutar load_delegados_reales --skip-endpoint, deberíamos tener
        exactamente el número de registros de municipalidad que contiene el seed.
        """
        counts = _get_seed_counts()
        call_command("load_delegados_reales", "--skip-endpoint")
        assert Municipalidad.objects.count() == counts['municipalidad_count']

    def test_seed_loads_municipalidad_codes_from_seed(self):
        """
        Verifica que existan todos los códigos de municipalidad presentes en el seed.
        """
        counts = _get_seed_counts()
        call_command("load_delegados_reales", "--skip-endpoint")

        expected_codes = set(counts['expected_codes'])
        actual_codes = set(Municipalidad.objects.values_list("codigo", flat=True))

        missing = expected_codes - actual_codes
        extra = actual_codes - expected_codes

        assert not missing, f"Códigos de municipalidad faltantes: {sorted(missing)}"
        assert not extra, f"Códigos de municipalidad extra: {sorted(extra)}"

    def test_seed_loads_correct_municipalidad_delegado_assignment_count(self):
        """
        Después de ejecutar load_delegados_reales --skip-endpoint, deberíamos tener
        exactamente el número de asignaciones municipalidad_delegado que contiene el seed.
        """
        counts = _get_seed_counts()
        call_command("load_delegados_reales", "--skip-endpoint")
        assert MunicipalidadDelegado.objects.count() == counts['assignment_count']

    def test_seed_is_idempotent(self):
        """
        Ejecutar el comando seed dos veces no debería duplicar registros.
        La segunda ejecución debería actualizar registros existentes, no crear nuevos.
        """
        counts = _get_seed_counts()
        call_command("load_delegados_reales", "--skip-endpoint")
        call_command("load_delegados_reales", "--skip-endpoint")

        assert PerfilIngeniero.objects.count() == counts['delegate_count']
        assert Delegado.objects.count() == counts['delegate_count']
        assert Municipalidad.objects.count() == counts['municipalidad_count']
        assert MunicipalidadDelegado.objects.count() == counts['assignment_count']

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
        Todas las asignaciones municipalidad_delegado deben estar marcadas como activas.
        """
        counts = _get_seed_counts()
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
        resultando en los recuentos de registros del seed.
        """
        counts = _get_seed_counts()
        call_command("seed_real_all")
        assert PerfilIngeniero.objects.count() == counts['delegate_count']
        assert Delegado.objects.count() == counts['delegate_count']
        assert Municipalidad.objects.count() == counts['municipalidad_count']
        assert MunicipalidadDelegado.objects.count() == counts['assignment_count']
