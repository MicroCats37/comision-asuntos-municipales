"""Banco admin with ContactoBanco inline."""

from django.contrib import admin

from modules.entidades.domain.models import Banco, ContactoBanco


class ContactoBancoInline(admin.TabularInline):
    """Inline for ContactoBanco (bridge table banco ↔ contacto)."""

    model = ContactoBanco
    extra = 1
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Banco)
class BancoAdmin(admin.ModelAdmin):
    """Admin for Banco with ContactoBanco as inline."""

    list_display = ["codigo", "nombre", "activo"]
    search_fields = ["codigo", "nombre"]
    list_filter = ["activo"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [ContactoBancoInline]
