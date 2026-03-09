import os
import pandas as pd
from django.core.management.base import BaseCommand
from supplier.models import Supplier
from decimal import Decimal
import uuid


class Command(BaseCommand):
    help = "Import Suppliers into the database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--delete-all",
            action="store_true",
            help="Delete all existing suppliers before importing new ones",
        )

    def handle(self, *args, **options):
        # Delete all customers if the flag is provided
        if options["delete_all"]:
            Supplier.objects.all().delete()
            self.stdout.write(self.style.WARNING("⚠️ All existing suppliers deleted."))

        # Get the absolute path of the command file
        base_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(
            base_dir, "fournisseur.xls"
        )  # Change to actual file name

        # Check if file exists
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        # Read Excel file
        df = pd.read_excel(file_path, engine="xlrd")

        # Ensure dataframe is not empty
        if df.empty:
            self.stdout.write(self.style.ERROR("The file is empty!"))
            return

        suppliers = []

        # Process data using column index
        for index, row in df.iterrows():
            try:
                name = str(row.iloc[1]).strip()  # Column 1: Name
                phone = str(row.iloc[2]).strip()  # Column 2: Phone Number
                address = row.iloc[3]  # Read address from the row

                if pd.isna(address):  # Check if address is NaN
                    address = ""  # Replace NaN with an empty string
                else:
                    address = str(
                        address
                    ).strip()  # Convert to string and remove spaces
                balance_str = str(row.iloc[4]).strip()  # Column 4: Balance

                # Convert to Decimal safely
                try:
                    balance = Decimal(balance_str)
                except:
                    balance = Decimal("0.0")  # Default to 0 if conversion fails

                balance_init = balance

                suppliers.append(
                    Supplier(
                        uuid=uuid.uuid4(),  # Generate a new UUID
                        name=name,
                        phone=phone,
                        address=address,
                        balance_init=balance_init,
                        balance=balance,
                    )
                )

                print(
                    f"✅ Name: {name}\n📞 Phone: {phone}\n🏠 Address: {address}\n💰 Balance: {balance}\n"
                )

            except IndexError:
                self.stdout.write(
                    self.style.ERROR(f"⚠️ Skipping row {index} due to missing data.")
                )

        if suppliers:
            Supplier.objects.bulk_create(
                suppliers, batch_size=500
            )  # Optimize batch insert
            self.stdout.write(
                self.style.SUCCESS(f"🎉 Successfully added {len(suppliers)} suppliers.")
            )
        else:
            self.stdout.write(self.style.WARNING("⚠️ No valid data found to import."))
