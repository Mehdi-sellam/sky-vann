import os
import pandas as pd
from django.core.management.base import BaseCommand
from product.models import Product, Category
from decimal import Decimal
import uuid
from warehouse.inventory import create_default_warehouse, increase_inventory_quantity


class Command(BaseCommand):
    help = "Import Products into the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--delete-all",
            action="store_true",
            help="Delete all existing Products before importing new ones",
        )

    def handle(self, *args, **options):
        # Delete all customers if the flag is provided
        if options["delete_all"]:
            Product.objects.all().delete()
            self.stdout.write(self.style.WARNING("⚠️ All existing Products deleted."))

        # Get the absolute path of the command file
        base_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(base_dir, "products.xls")  # Change to actual file name

        # Check if file exists
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        warehouse = create_default_warehouse()
        try:
            category = Category.objects.get(name="Catégorie par défaut")
        except Category.DoesNotExist:
            category = Category.objects.create(
                uuid=uuid.uuid4(),
                name="Catégorie par défaut",
                description="Catégorie par défaut",
            )

        # Read Excel file
        df = pd.read_excel(file_path, engine="xlrd")

        # Ensure dataframe is not empty
        if df.empty:
            self.stdout.write(self.style.ERROR("The file is empty!"))
            return

        # Process data using column index
        for index, row in df.iterrows():
            try:
                name = row.iloc[0]
                qte_stock = Decimal(str(row.iloc[1]).strip())
                cost_price = Decimal(row.iloc[2])
                price = Decimal(row.iloc[3])
                instance = Product.objects.create(
                    uuid=uuid.uuid4(),  # Generate a new UUID
                    name=name,
                    cost_price=cost_price,
                    price=price,
                    category=category,
                )

                increase_inventory_quantity(
                    product=instance,
                    quantity=qte_stock,
                    warehouse=warehouse,
                )
                print(
                    f"✅ Name: {name}\n📞 cost_price: {cost_price}\n🏠 price: {price}\n💰 category: {category.name}\n"
                )

            except IndexError:
                self.stdout.write(
                    self.style.ERROR(f"⚠️ Skipping row {index} due to missing data.")
                )

            self.stdout.write(self.style.SUCCESS(f"🎉 Successfully added products."))

        else:
            self.stdout.write(self.style.WARNING("⚠️ No valid data found to import."))
