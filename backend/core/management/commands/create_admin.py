"""
Management command to create a fixed admin superuser.

Usage:
    python manage.py create_admin --settings=config.settings.development
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

Usuario = get_user_model()


class Command(BaseCommand):
    help = "Create or update a fixed admin superuser (DNI: 00000000, password: admin)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force password reset even if user already exists with correct password",
        )

    def handle(self, *args, **options):
        dni = "00000000"
        password = "admin"

        defaults = {
            "nombres": "Admin",
            "apellidos": "Sistema",
            "email": "admin@example.com",
            "username": "admin",
            "is_staff": True,
            "is_superuser": True,
            "is_active": True,
        }

        user, created = Usuario.objects.update_or_create(
            username="admin",
            defaults=defaults,
        )

        # Always set the password to ensure it matches
        user.set_password(password)
        user.save(update_fields=["password"])

        if created:
            self.stdout.write(
                self.style.SUCCESS(f"Admin user created: username=admin, password={password}")
            )
        else:
            action = "updated" if options["force"] else "verified"
            self.stdout.write(
                self.style.SUCCESS(
                    f"Admin user {action}: username=admin, password={password}, "
                    f"is_staff={user.is_staff}, is_superuser={user.is_superuser}, "
                    f"is_active={user.is_active}"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Login credentials: username=admin, password={password}"
            )
        )