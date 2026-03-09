from django.db import transaction
from transfer.models import TransferLine
from warehouse.models import StockHistory


@transaction.atomic
def add_transfer_line_with_stock_history(transfer_line_data, stock_history_data):
    try:
        # Create the TransferLine instance
        transfer_line = TransferLine.objects.create(**transfer_line_data)

        # Create the StockHistory instance
        stock_history = StockHistory(**stock_history_data)
        stock_history.action_object = transfer_line
        stock_history.save()
    except Exception as e:
        # Handle the error or raise it if needed
        raise e
