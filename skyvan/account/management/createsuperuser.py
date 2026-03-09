from django.contrib.auth.management.commands.createsuperuser import Command as CreateSuperuserCommand
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from getpass import getpass

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Creates a superuser with phone and password.'

    def handle(self, *args, **options):
        try:
            phone = input("Enter the phone number: ")
            password = getpass("Enter the password: ")
            confirm_password = getpass("Confirm the password: ")

            if password != confirm_password:
                self.stdout.write(self.style.ERROR(
                    "The passwords do not match."))
                return
            user_data = {
                'phone': phone,
                'password': password,
            }

            user = self.UserModel(**user_data)
            user.is_staff = True
            user.is_superuser = True
            user.set_password(password)
            user.save(using=self._db)
            if options['verbosity'] >= 1:
                self.stdout.write("Superuser created successfully.")
        except KeyboardInterrupt:
            self.stderr.write("\nOperation cancelled.")

        except ValidationError as e:
            self.stderr.write(str(e))
            self.handle(*args, **options)
