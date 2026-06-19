# Generated migration for username field changes
# Note: HistoricalUsuario keeps nullable username since historical records are audit snapshots
# and multiple history records can have the same DNI (different points in time)

import django.core.validators
from django.db import migrations, models


def populate_username_from_dni(apps, schema_editor):
    """Populate username field from dni for existing records in main table only."""
    Usuario = apps.get_model("usuarios", "Usuario")

    # Update Usuario records where username is null but dni is not null
    for user in Usuario.objects.filter(username__isnull=True, dni__isnull=False):
        user.username = user.dni
        user.save(update_fields=["username"])


def reverse_migration(apps, schema_editor):
    """Reverse: clear username fields (set to null) in main table only."""
    Usuario = apps.get_model("usuarios", "Usuario")
    Usuario.objects.filter(username__isnull=False).update(username=None)


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0001_initial"),
    ]

    operations = [
        # First, allow null temporarily on main table
        migrations.AlterField(
            model_name="usuario",
            name="username",
            field=models.CharField(
                max_length=8,
                null=True,
                unique=True,
                validators=[
                    django.core.validators.RegexValidator(
                        code="invalid_dni",
                        message="El DNI debe contener exactamente 8 dígitos numéricos.",
                        regex="^\\d{8}$",
                    )
                ],
                verbose_name="Nombre de usuario",
            ),
        ),
        # Populate username from dni for existing records
        migrations.RunPython(populate_username_from_dni, reverse_migration),
        # Now make username non-nullable on main table
        migrations.AlterField(
            model_name="usuario",
            name="username",
            field=models.CharField(
                max_length=8,
                unique=True,
                validators=[
                    django.core.validators.RegexValidator(
                        code="invalid_dni",
                        message="El DNI debe contener exactamente 8 dígitos numéricos.",
                        regex="^\\d{8}$",
                    )
                ],
                verbose_name="Nombre de usuario",
            ),
        ),
        # HistoricalUsuario: remove unique constraint and keep nullable
        # (audit snapshot, not used for auth, multiple records can have same DNI)
        migrations.AlterField(
            model_name="historicalusuario",
            name="username",
            field=models.CharField(
                max_length=8,
                null=True,
                validators=[
                    django.core.validators.RegexValidator(
                        code="invalid_dni",
                        message="El DNI debe contener exactamente 8 dígitos numéricos.",
                        regex="^\\d{8}$",
                    )
                ],
                verbose_name="Nombre de usuario",
            ),
        ),
    ]
