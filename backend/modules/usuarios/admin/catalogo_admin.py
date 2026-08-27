"""Catalog admin classes for usuarios module."""

from django.contrib import admin

from modules.usuarios.domain.models import (
    Capitulo,
    EspecialidadIngeniero,
    EspecialidadRevision,
    IngenieroHabilitacion,
)


@admin.register(Capitulo)
class CapituloAdmin(admin.ModelAdmin):
    """Admin for Capitulo (CIP professional chapter)."""

    list_display = ["registro_id", "abreviacion", "nombre", "grupo_envio_intitucional"]
    search_fields = ["registro_id", "abreviacion", "nombre"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(EspecialidadIngeniero)
class EspecialidadIngenieroAdmin(admin.ModelAdmin):
    """Admin for EspecialidadIngeniero (professional specialty by chapter)."""

    list_display = ["codigo", "nombre", "capitulo"]
    search_fields = ["codigo", "nombre", "capitulo__nombre"]
    list_filter = ["capitulo"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(EspecialidadRevision)
class EspecialidadRevisionAdmin(admin.ModelAdmin):
    """Admin for EspecialidadRevision (calculation specialty for tariffs)."""

    list_display = ["slug", "nombre"]
    search_fields = ["slug", "nombre"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(IngenieroHabilitacion)
class IngenieroHabilitacionAdmin(admin.ModelAdmin):
    """Admin for IngenieroHabilitacion (CIP habilitation history)."""

    list_display = [
        "perfil_ingeniero",
        "ultimo_periodo_pagado_cip",
        "condicion_cip",
        "fecha_busqueda",
    ]
    search_fields = [
        "perfil_ingeniero__nombres",
        "perfil_ingeniero__apellido_paterno",
        "perfil_ingeniero__cip",
    ]
    list_filter = ["condicion_cip", "fecha_busqueda"]
    readonly_fields = ["created_at", "updated_at"]
