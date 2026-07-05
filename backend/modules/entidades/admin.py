"""Admin — registro de modelos de entidades."""

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import (
    Entidad,
    Institucion,
    PersonaNatural,
    ContactoEntidad,
    # Otros modelos
    Alcalde,
    Banco,
    ContactoBanco,
    Contacto,
    GerenteUrbano,
    Municipalidad,
    ContactoMunicipalidad,
    MunicipalidadProvincial,
    MunicipalidadDistrital,
    UbigeoDepartamento,
    UbigeoProvincia,
    UbigeoDistrito,
)


@admin.register(Entidad)
class EntidadAdmin(SimpleHistoryAdmin):
    list_display = [
        "numero_documento",
        "tipo_documento",
        "razon_social",
        "direccion",
    ]
    list_filter = ["tipo_documento"]
    search_fields = ["numero_documento", "razon_social"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["tipo_documento", "razon_social"]


@admin.register(Institucion)
class InstitucionAdmin(SimpleHistoryAdmin):
    list_display = [
        "numero_documento",
        "razon_social",
        "nombre_comercial",
        "tipo_contribuyente",
        "direccion",
    ]
    list_filter = ["tipo_contribuyente"]
    search_fields = ["numero_documento", "razon_social", "nombre_comercial"]
    readonly_fields = ["created_at", "updated_at", "tipo_documento"]
    fields = [
        "tipo_documento",
        "numero_documento",
        "razon_social",
        "nombre_comercial",
        "tipo_contribuyente",
        "direccion",
        "created_at",
        "updated_at",
    ]
    ordering = ["razon_social"]

    def get_queryset(self, request):
        # Mostrar solo instituciones (RUC) en este admin
        return Institucion.objects.all()


@admin.register(PersonaNatural)
class PersonaNaturalAdmin(SimpleHistoryAdmin):
    list_display = ["numero_documento", "razon_social", "direccion"]
    list_filter = []
    search_fields = ["numero_documento", "razon_social"]
    readonly_fields = ["created_at", "updated_at", "tipo_documento"]
    fields = [
        "tipo_documento",
        "numero_documento",
        "razon_social",
        "direccion",
        "created_at",
        "updated_at",
    ]
    ordering = ["razon_social"]

    def get_queryset(self, request):
        # Mostrar solo personas naturales (DNI) en este admin
        return PersonaNatural.objects.all()


# Compatibilidad hacia atrás: mantener nombres antiguos registrados.
# Nota: Empresa es un alias de Entidad, así que no se registra por separado
# para evitar errores "AlreadyRegistered".


@admin.register(Municipalidad)
class MunicipalidadAdmin(SimpleHistoryAdmin):
    list_display = ["codigo", "nombre", "provincia", "distrito", "activo"]
    list_filter = ["activo"]
    search_fields = ["codigo", "nombre"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["nombre"]


@admin.register(MunicipalidadProvincial)
class MunicipalidadProvincialAdmin(SimpleHistoryAdmin):
    list_display = ["codigo", "nombre", "provincia", "activo"]
    list_filter = ["activo"]
    search_fields = ["codigo", "nombre"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["nombre"]


@admin.register(MunicipalidadDistrital)
class MunicipalidadDistritalAdmin(SimpleHistoryAdmin):
    list_display = ["codigo", "nombre", "distrito", "activo"]
    list_filter = ["activo"]
    search_fields = ["codigo", "nombre"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["nombre"]


@admin.register(Banco)
class BancoAdmin(SimpleHistoryAdmin):
    list_display = ["codigo", "nombre", "activo"]
    list_filter = ["activo"]
    search_fields = ["codigo", "nombre"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["nombre"]


@admin.register(Contacto)
class ContactoAdmin(SimpleHistoryAdmin):
    list_display = [
        "nombres",
        "apellidos",
        "dni",
        "cargo",
        "telefono",
        "celular",
        "email",
    ]
    search_fields = ["nombres", "apellidos", "dni", "cargo", "email"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["nombres", "apellidos"]


@admin.register(ContactoEntidad)
class ContactoEntidadAdmin(SimpleHistoryAdmin):
    list_display = ["entidad", "contacto", "principal", "activo"]
    list_filter = ["principal", "activo"]
    search_fields = [
        "entidad__razon_social",
        "entidad__numero_documento",
        "contacto__nombres",
        "contacto__apellidos",
    ]
    readonly_fields = ["created_at", "updated_at"]
    autocomplete_fields = ["entidad", "contacto"]


# Compatibilidad hacia atrás: ContactoEmpresa es un alias de ContactoEntidad,
# así que no se registra por separado para evitar errores "AlreadyRegistered".


@admin.register(ContactoMunicipalidad)
class ContactoMunicipalidadAdmin(SimpleHistoryAdmin):
    list_display = ["municipalidad", "contacto", "principal", "activo"]
    list_filter = ["principal", "activo"]
    search_fields = [
        "municipalidad__nombre",
        "contacto__nombres",
        "contacto__apellidos",
    ]
    readonly_fields = ["created_at", "updated_at"]
    autocomplete_fields = ["municipalidad", "contacto"]


@admin.register(ContactoBanco)
class ContactoBancoAdmin(SimpleHistoryAdmin):
    list_display = ["banco", "contacto", "principal", "activo"]
    list_filter = ["principal", "activo"]
    search_fields = ["banco__nombre", "contacto__nombres", "contacto__apellidos"]
    readonly_fields = ["created_at", "updated_at"]
    autocomplete_fields = ["banco", "contacto"]


@admin.register(Alcalde)
class AlcaldeAdmin(SimpleHistoryAdmin):
    list_display = ["nombre", "municipalidad", "periodo_inicio", "periodo_fin"]
    list_filter = ["municipalidad"]
    search_fields = ["nombre", "municipalidad__nombre"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-periodo_inicio"]
    autocomplete_fields = ["municipalidad"]


@admin.register(GerenteUrbano)
class GerenteUrbanoAdmin(SimpleHistoryAdmin):
    list_display = ["nombre", "municipalidad", "periodo_inicio", "periodo_fin"]
    list_filter = ["municipalidad"]
    search_fields = ["nombre", "municipalidad__nombre"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-periodo_inicio"]
    autocomplete_fields = ["municipalidad"]


@admin.register(UbigeoDepartamento)
class UbigeoDepartamentoAdmin(SimpleHistoryAdmin):
    list_display = ["nombre"]
    search_fields = ["nombre"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["nombre"]


@admin.register(UbigeoProvincia)
class UbigeoProvinciaAdmin(SimpleHistoryAdmin):
    list_display = ["nombre", "departamento"]
    list_filter = ["departamento"]
    search_fields = ["nombre", "departamento__nombre"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["departamento__nombre", "nombre"]
    autocomplete_fields = ["departamento"]


@admin.register(UbigeoDistrito)
class UbigeoDistritoAdmin(SimpleHistoryAdmin):
    list_display = ["nombre", "provincia", "ubigeo"]
    list_filter = ["provincia__departamento"]
    search_fields = ["nombre", "provincia__nombre", "ubigeo"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["provincia__departamento__nombre", "provincia__nombre", "nombre"]
    autocomplete_fields = ["provincia"]
