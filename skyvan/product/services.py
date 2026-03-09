from .models import  Category, Product


def get_categories_list():
    return Category.objects.filter(deleted=False)

def get_product_list():
    return Product.objects.filter(deleted=False)

