"""Municipalidad and Ubigeo admin classes."""

from django.contrib import admin
from django.contrib.admin import RelatedOnlyFieldListFilter

from modules.entidades.domain.models import (
    ContactoMunicipalidad,
    Alcalde,
    GerenteUrbano,
    Municipalidad,
    UbigeoDepartamento,
    UbigeoProvincia,
    UbigeoDistrito,
)


class ContactoMunicipalidadInline(admin.TabularInline):
    """Inline for ContactoMunicipalidad (bridge table municipalidad ↔ contacto)."""

    model = ContactoMunicipalidad
    extra = 1
    readonly_fields = ["created_at", "updated_at"]


class AlcaldeInline(admin.TabularInline):
    """Inline for Alcalde (historical mayors with validity periods)."""

    model = Alcalde
    extra = 1
    readonly_fields = ["created_at", "updated_at"]


class GerenteUrbanoInline(admin.TabularInline):
    """Inline for GerenteUrbano (historical urban managers with validity periods)."""

    model = GerenteUrbano
    extra = 1
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Municipalidad)
class MunicipalidadAdmin(admin.ModelAdmin):
    """Admin for Municipalidad (standalone) with inlines for related entities."""

    list_display = ["codigo", "nombre", "provincia", "distrito"]
    search_fields = ["codigo", "nombre"]
    list_filter = [
        ("provincia", RelatedOnlyFieldListFilter),
        ("distrito", RelatedOnlyFieldListFilter),
    ]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [ContactoMunicipalidadInline, AlcaldeInline, GerenteUrbanoInline]


@admin.register(UbigeoDepartamento)
class UbigeoDepartamentoAdmin(admin.ModelAdmin):
    """Admin for UbigeoDepartamento (top level of ubigeo hierarchy)."""

    list_display = ["nombre"]
    search_fields = ["nombre"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(UbigeoProvincia)
class UbigeoProvinciaAdmin(admin.ModelAdmin):
    """Admin for UbigeoProvincia (second level of ubigeo hierarchy)."""

    list_display = ["nombre", "departamento"]
    search_fields = ["nombre", "departamento__nombre"]
    list_filter = ["departamento"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(UbigeoDistrito)
class UbigeoDistritoAdmin(admin.ModelAdmin):
    """Admin for UbigeoDistrito (third level of ubigeo hierarchy)."""

    list_display = ["nombre", "ubigeo", "provincia"]
    search_fields = ["nombre", "ubigeo", "provincia__nombre"]
    list_filter =         [("provincia__departamento", RelatedOnlyFieldListFilter)]
    readonly_fields = ["created_at", "updated_at"]
