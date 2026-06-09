"""Admin — minimal registration for entidades models."""

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import (
    Empresa,
    Municipalidad,
    Banco,
    Contacto,
    EmpresaContacto,
    MunicipalidadContacto,
    BancoContacto,
)


@admin.register(Empresa)
class EmpresaAdmin(SimpleHistoryAdmin):
    list_display = ["ruc", "razon_social", "nombre_comercial", "distrito", "activo"]
    list_filter = ["activo", "distrito"]
    search_fields = ["ruc", "razon_social", "nombre_comercial", "email"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["razon_social"]


@admin.register(Municipalidad)
class MunicipalidadAdmin(SimpleHistoryAdmin):
    list_display = ["codigo", "nombre", "alcalde", "activo"]
    list_filter = ["activo"]
    search_fields = ["codigo", "nombre", "alcalde"]
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
    list_display = ["nombres", "apellidos", "cargo", "telefono", "celular", "email", "activo"]
    list_filter = ["activo"]
    search_fields = ["nombres", "apellidos", "cargo", "email"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["nombres", "apellidos"]


@admin.register(EmpresaContacto)
class EmpresaContactoAdmin(SimpleHistoryAdmin):
    list_display = ["empresa", "contacto", "principal", "activo"]
    list_filter = ["principal", "activo"]
    search_fields = ["empresa__razon_social", "contacto__nombres", "contacto__apellidos"]
    readonly_fields = ["created_at", "updated_at"]
    autocomplete_fields = ["empresa", "contacto"]


@admin.register(MunicipalidadContacto)
class MunicipalidadContactoAdmin(SimpleHistoryAdmin):
    list_display = ["municipalidad", "contacto", "principal", "activo"]
    list_filter = ["principal", "activo"]
    search_fields = ["municipalidad__nombre", "contacto__nombres", "contacto__apellidos"]
    readonly_fields = ["created_at", "updated_at"]
    autocomplete_fields = ["municipalidad", "contacto"]


@admin.register(BancoContacto)
class BancoContactoAdmin(SimpleHistoryAdmin):
    list_display = ["banco", "contacto", "principal", "activo"]
    list_filter = ["principal", "activo"]
    search_fields = ["banco__nombre", "contacto__nombres", "contacto__apellidos"]
    readonly_fields = ["created_at", "updated_at"]
    autocomplete_fields = ["banco", "contacto"]
