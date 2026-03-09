from django.db import transaction
from django.core.exceptions import ValidationError
from decimal import Decimal
from purchases.models import PurchaseOrder
from supplier_payment.models import SupplierPayment
from supplier_payment.utils import fix_supplier_payment_balances
from .models import Supplier
from core.models import BaseModel
from django.conf import settings

def get_supplier_list():
    return (Supplier.objects.filter(deleted=False).order_by("-created_at"))

@transaction.atomic
def create_supplier(data):
    """
    Create a new supplier, validate data, and handle balance initialization.
    """
    # Validate email and phone uniqueness
    email = data.get('email')
    phone = data.get('phone')

    if email and Supplier.objects.filter(email=email).exists():
        raise ValidationError({"code": "already_exists", "message": "Supplier with this email address already exists.", "field": "email"})
    
    if phone and Supplier.objects.filter(phone=phone).exists():
        raise ValidationError({"code": "already_exists", "message": "Supplier with this phone number already exists.", "field": "phone"})
    
    # Initialize balance
    balance_init = data.get('balance_init', Decimal("0.0"))
    data['balance'] = balance_init

    # Create Supplier instance
    supplier = Supplier.objects.create(**data)
    return supplier

@transaction.atomic
def update_supplier(uuid, data):
    """
    Update an existing supplier's details by UUID, with email/phone uniqueness check.
    """
    try:
        supplier = Supplier.objects.get(uuid=uuid, deleted=False)
    except Supplier.DoesNotExist:
        raise ValidationError({"code": "not_found", "message": f"Supplier with UUID {uuid} not found.", "field": "uuid"})

    email = data.get('email', supplier.email)
    phone = data.get('phone', supplier.phone)

# Check for unique email and phone 

    if email:
        existing_supplier = Supplier.objects.filter(email=email).exclude(uuid=supplier.uuid).first()
        if existing_supplier:
            raise ValidationError({"code": "already_exists", "message": "Supplier with this email address already exists.", "field": "email"})
    if phone:
        existing_supplier = Supplier.objects.filter(phone=phone).exclude(uuid=supplier.uuid).first()
        if existing_supplier:
            raise ValidationError({"code": "already_exists", "message": "Supplier with this phone number already exists.", "field": "phone"})

    # Update balance if balance_init is provided or modified
    balance_init = data.get('balance_init')
    if balance_init is not None:
        supplier.balance_init = balance_init
    
    supplier.name = data.get('name', supplier.name)
    supplier.email = email
    supplier.phone = phone
    supplier.address = data.get('address', supplier.address)

    supplier.save()
    fix_supplier_payment_balances(supplier_uuid=uuid)
    
    return supplier

@transaction.atomic
def delete_supplier(uuid):

    try:
        supplier = Supplier.objects.get(uuid=uuid, deleted=False)
    except Supplier.DoesNotExist:
        raise ValidationError({"code": "not_found", "message": f"Supplier with UUID {uuid} not found.", "field": "uuid"})
    # Check for associated payments
    has_payments = SupplierPayment.objects.filter(supplier=supplier).exists()
    if has_payments:
        raise ValidationError({
            "code": "HAS_PAYMENTS",
            "message": f"Supplier with UUID {supplier.name}has associated payments and cannot be deleted.",
            "field": ""
        })

    # Check for associated purchases
    has_purchases = PurchaseOrder.objects.filter(supplier=supplier).exists()
    if has_purchases:
        raise ValidationError({
            "code": "HAS_SALES",
            "message": f"Supplier with UUID {supplier.name} has associated purchases and cannot be deleted.",
            "field": ""
        })
    supplier.deleted = True
    supplier.save()


