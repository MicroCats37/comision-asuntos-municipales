"""Contacto admin — reusable contact entity."""

from django.contrib import admin

from modules.entidades.domain.models import Contacto


@admin.register(Contacto)
class ContactoAdmin(admin.ModelAdmin):
    """Admin for Contacto (reusable across Entidad, Municipalidad, Banco)."""

    list_display = [
        "__str__",
        "dni",
        "cargo",
        "telefono",
        "celular",
        "email",
    ]
    search_fields = ["nombres", "apellidos", "dni", "email", "cargo"]
    list_filter = ["cargo"]
    readonly_fields = ["created_at", "updated_at"]
