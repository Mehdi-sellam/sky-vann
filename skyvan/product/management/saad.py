
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'test command.'

    def handle(self, *args, **options):
       print("Enter the phone number: ")