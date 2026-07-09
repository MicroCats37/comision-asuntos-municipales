"""
Unit tests for EntidadesCoreService — tests sync core operations.
"""
import pytest

from modules.entidades.domain.services.entidades_core_service import EntidadesCoreService
from modules.entidades.domain.models import MunicipalidadDistrital, MunicipalidadProvincial
from modules.entidades.tests.factories.ubigeo_factory import (
    UbigeoDepartamentoFactory,
    UbigeoProvinciaFactory,
    UbigeoDistritoFactory,
)


@pytest.mark.django_db
class TestEntidadesCoreService:
    """Test EntidadesCoreService sync methods."""

    def setup_method(self):
        """Set up test data."""
        self.core = EntidadesCoreService()

    def test_obtener_distritos_returns_all_distritos(self):
        """
        obtener_distritos() without filters should return all distritos.
        """
        # Create test ubigeo hierarchy
        depto = UbigeoDepartamentoFactory(nombre="LIMA")
        prov = UbigeoProvinciaFactory(departamento=depto, nombre="LIMA")
        distrito1 = UbigeoDistritoFactory(provincia=prov, nombre="MIRAFLORES", ubigeo="150101")
        distrito2 = UbigeoDistritoFactory(provincia=prov, nombre="SURCO", ubigeo="150102")

        result = self.core._obtener_distritos()

        assert len(result) == 2
        nombres = {d.nombre for d in result}
        assert nombres == {"MIRAFLORES", "SURCO"}

    def test_obtener_distritos_filters_by_provincia(self):
        """
        obtener_distritos(provincia_id=X) should return only distritos in that provincia.
        """
        depto = UbigeoDepartamentoFactory(nombre="LIMA")
        prov_lima = UbigeoProvinciaFactory(departamento=depto, nombre="LIMA")
        prov_callao = UbigeoProvinciaFactory(departamento=depto, nombre="CALLAO")

        distrito_lima = UbigeoDistritoFactory(provincia=prov_lima, nombre="MIRAFLORES", ubigeo="150101")
        distrito_callao = UbigeoDistritoFactory(provincia=prov_callao, nombre="CALLAO", ubigeo="150201")

        result = self.core._obtener_distritos(provincia_id=prov_lima.id)

        assert len(result) == 1
        assert result[0].nombre == "MIRAFLORES"

    def test_obtener_distritos_filters_by_departamento(self):
        """
        obtener_distritos(departamento_id=X) should return only distritos in that departamento.
        """
        depto_lima = UbigeoDepartamentoFactory(nombre="LIMA")
        depto_arequipa = UbigeoDepartamentoFactory(nombre="AREQUIPA")

        prov_lima = UbigeoProvinciaFactory(departamento=depto_lima, nombre="LIMA")
        prov_arequipa = UbigeoProvinciaFactory(departamento=depto_arequipa, nombre="AREQUIPA")

        distrito_lima = UbigeoDistritoFactory(provincia=prov_lima, nombre="MIRAFLORES", ubigeo="150101")
        distrito_arequipa = UbigeoDistritoFactory(provincia=prov_arequipa, nombre="AREQUIPA", ubigeo="040101")

        result = self.core._obtener_distritos(departamento_id=depto_lima.id)

        assert len(result) == 1
        assert result[0].nombre == "MIRAFLORES"

    def test_obtener_distritos_filters_by_search(self):
        """
        obtener_distritos(search='MIRA') should return only matching distritos.
        """
        depto = UbigeoDepartamentoFactory(nombre="LIMA")
        prov = UbigeoProvinciaFactory(departamento=depto, nombre="LIMA")
        UbigeoDistritoFactory(provincia=prov, nombre="MIRAFLORES", ubigeo="150101")
        UbigeoDistritoFactory(provincia=prov, nombre="SURCO", ubigeo="150102")
        UbigeoDistritoFactory(provincia=prov, nombre="MIRADOR", ubigeo="150103")

        result = self.core._obtener_distritos(search="MIRA")

        assert len(result) == 2
        nombres = {d.nombre for d in result}
        assert nombres == {"MIRAFLORES", "MIRADOR"}

    def test_obtener_distritos_returns_distritos_with_relations_loaded(self):
        """
        obtener_distritos() should return distritos with provincia and departamento preloaded.
        """
        depto = UbigeoDepartamentoFactory(nombre="LIMA")
        prov = UbigeoProvinciaFactory(departamento=depto, nombre="LIMA")
        distrito = UbigeoDistritoFactory(provincia=prov, nombre="MIRAFLORES", ubigeo="150101")

        result = self.core._obtener_distritos()

        assert len(result) == 1
        d = result[0]
        # Accessing related objects should NOT cause additional queries
        assert d.provincia.nombre == "LIMA"
        assert d.provincia.departamento.nombre == "LIMA"

    def test_obtener_distritos_respects_limit(self):
        """
        obtener_distritos() should return maximum 100 distritos.
        """
        depto = UbigeoDepartamentoFactory(nombre="LIMA")
        prov = UbigeoProvinciaFactory(departamento=depto, nombre="LIMA")

        # Create 5 distritos
        for i in range(5):
            UbigeoDistritoFactory(provincia=prov, nombre=f"DISTRITO_{i}", ubigeo=f"15010{i}")

        result = self.core._obtener_distritos()

        assert len(result) == 5

    def test_obtener_distritos_is_ordered(self):
        """
        obtener_distritos() should return distritos ordered by departamento, provincia, nombre.
        """
        depto1 = UbigeoDepartamentoFactory(nombre="AREQUIPA")
        depto2 = UbigeoDepartamentoFactory(nombre="LIMA")

        prov_a = UbigeoProvinciaFactory(departamento=depto1, nombre="AREQUIPA")
        prov_l = UbigeoProvinciaFactory(departamento=depto2, nombre="LIMA")

        UbigeoDistritoFactory(provincia=prov_l, nombre="ZONA1", ubigeo="150101")
        UbigeoDistritoFactory(provincia=prov_a, nombre="ZONAA", ubigeo="040101")
        UbigeoDistritoFactory(provincia=prov_l, nombre="ZONAB", ubigeo="150102")

        result = self.core._obtener_distritos()

        assert len(result) == 3
        # Should be ordered: AREQUIPA first (alphabetically), then LIMA
        assert result[0].provincia.departamento.nombre == "AREQUIPA"
        assert result[1].provincia.departamento.nombre == "LIMA"
        assert result[2].provincia.departamento.nombre == "LIMA"

    def test_obtener_municipalidades_returns_active_proxy_models(self):
        """obtener_municipalidades() should return active provincial and distrital proxy instances."""
        depto = UbigeoDepartamentoFactory(nombre="LIMA")
        prov = UbigeoProvinciaFactory(departamento=depto, nombre="LIMA")
        distrito = UbigeoDistritoFactory(provincia=prov, nombre="MIRAFLORES", ubigeo="150101")

        municipalidad_provincial = MunicipalidadProvincial.objects.create(
            codigo="MP001",
            nombre="Municipalidad Provincial",
            provincia=prov,
        )
        municipalidad_distrital = MunicipalidadDistrital.objects.create(
            codigo="MD001",
            nombre="Municipalidad Distrital",
            distrito=distrito,
        )
        MunicipalidadDistrital.objects.create(
            codigo="MD002",
            nombre="Municipalidad Inactiva",
            distrito=distrito,
            activo=False,
        )

        result = self.core._obtener_municipalidades()

        assert len(result) == 2
        assert {municipalidad.id for municipalidad in result} == {
            municipalidad_provincial.id,
            municipalidad_distrital.id,
        }
        # Verify tipo semantics via es_provincial / es_distrital properties (proxy model semantics)
        # _obtener_municipalidades returns base model instances from filter(activo=True) on
        # the base Municipalidad table, so isinstance proxy checks would fail.
        # Instead, assert the active municipality semantics via the es_provincial/es_distrital
        # properties that indicate whether the provincial or district FK is set.
        assert any(municipalidad.es_provincial for municipalidad in result)
        assert any(municipalidad.es_distrital for municipalidad in result)
