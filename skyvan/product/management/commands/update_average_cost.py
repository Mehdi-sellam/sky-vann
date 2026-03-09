from django.core.management.base import BaseCommand
from django.db import transaction
from ...models import Product  # Update 'products' with your actual app name
from django.db import models


class Command(BaseCommand):
    help = "⚠️ ONE-TIME FIX: Updates average_cost with cost_price. DO NOT RUN AGAIN AFTER FIRST USE!"

    def handle(self, *args, **kwargs):
        self.stdout.write(
            self.style.WARNING("⚠️ WARNING: This command is for one-time use ONLY!")
        )
        self.stdout.write(
            self.style.WARNING(
                "⚠️ DO NOT RUN THIS COMMAND AGAIN AFTER THE FIRST EXECUTION!"
            )
        )
        confirmation = input("Type 'CONFIRM' to proceed: ").strip()
        if confirmation != "CONFIRM":
            self.stdout.write(self.style.ERROR("❌ Command aborted."))
            return

        with transaction.atomic():
            updated_count = Product.objects.update(average_cost=models.F("cost_price"))

        self.stdout.write(
            self.style.SUCCESS(f"Successfully updated {updated_count} products.")
        )
