from django.db import models


class SystemPermissions(models.Model):
    """
    Modelo proxy vacío. Actúa como ancla única para TODOS los permisos
    de negocio del sistema en la tabla auth_permission de Django.

    Ventajas:
    - No crea tabla real en la base de datos (managed = False).
    - Todos los permisos aparecen bajo 'Core | System Permissions' en el Admin.
    - El seed_roles los crea/asigna automáticamente usando SystemPermissions.all().
    - Las apps solo declaran sus permisos y el registro central los agrega aquí.

    Nota: Los codenames deben ser únicos y usar prefijos por módulo
    (ej: 'acc_', 'idn_', 'fin_', 'accs_') para evitar colisiones.
    """

    class Meta:
        managed = False
        # Desactivamos los permisos CRUD por defecto de Django (add, change, delete, view)
        default_permissions = ()
        # La lista de permisos se mantiene vacía aquí y se construye dinámicamente
        # mediante el comando seed_roles usando SystemPermissions.all() de core/permissions.py
        permissions = []
        verbose_name = "Permisos del Sistema"
        verbose_name_plural = "Permisos del Sistema"
