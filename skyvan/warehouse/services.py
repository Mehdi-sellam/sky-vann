from .models import Warehouse

def get_warhouses_list():
    return Warehouse.objects.filter(deleted=False)



