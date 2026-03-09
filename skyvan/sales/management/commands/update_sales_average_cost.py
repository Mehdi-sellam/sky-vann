from django.core.management.base import BaseCommand
from django.db import transaction
from sales.models import SaleLine
from product.models import Product
from django.db.models import F


class Command(BaseCommand):
    help = "⚠️ ONE-TIME FIX: Updates SaleLine average_cost with the current Product average_cost. DO NOT RUN AGAIN!"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        confirmation = input("Type 'CONFIRM' to proceed: ").strip()
        if confirmation != "CONFIRM":
            self.stdout.write(self.style.ERROR("❌ Command aborted. No changes made."))
            return

        try:
            with transaction.atomic():
                sale_lines = SaleLine.objects.select_related("product").all()
                updated_count = 0

                for sale_line in sale_lines:
                    if sale_line.product and sale_line.product.average_cost is not None:
                        sale_line.average_cost = sale_line.product.average_cost
                        sale_line.save(update_fields=["average_cost"])
                        updated_count += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Successfully updated {updated_count} SaleLine records."
                    )
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Update failed: {e}"))
