from django.db import transaction
from decimal import Decimal
from customer_payment.utils import fix_customer_payment_balances
from customer_payment.models import CustomerPayment
from sales.models import SaleOrder
from .models import *
from .serializers import *
from .error_codes import *
from rest_framework.exceptions import ValidationError

@transaction.atomic
def create_customer(data):
    phone = data.get('phone')
    email = data.get('email')

    # Check if a customer with the given phone already exists
    if Customer.objects.filter(phone=phone).exists():
        raise ValidationError({
            "code": CustomerErrorCode.ALREADY_EXISTS.value,
            "message": "Customer with this phone number already exists.",
            "field": "phone"
        })

    # Check if a customer with the given email already exists
    if Customer.objects.filter(email=email).exists():
        raise ValidationError({
            "code": CustomerErrorCode.ALREADY_EXISTS.value,
            "message": "Customer with this email address already exists.",
            "field": "email"
        })

    # If valid, set balance to the value of balance_init
    data['balance'] = data.get('balance_init', Decimal("0.0"))

    # Create and return the customer
    serializer = CustomerSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    return serializer.save()

@transaction.atomic
def update_customer(uuid, data):
    try:
        # Fetch the customer by UUID
        customer = Customer.objects.get(uuid=uuid, deleted=False)
    except Customer.DoesNotExist:
        raise ValidationError({
            "code": CustomerErrorCode.NOT_FOUND.value,
            "message": "Customer not found.",
            "field": "uuid"
        })

    # Check for duplicate phone
    phone = data.get('phone')
    if phone and Customer.objects.filter(phone=phone).exclude(uuid=uuid).exists():
        raise ValidationError({
            "code": CustomerErrorCode.ALREADY_EXISTS.value,
            "message": "Customer with this phone number already exists.",
            "field": "phone"
        })

    # Check for duplicate email
    email = data.get('email')
    if email and Customer.objects.filter(email=email).exclude(uuid=uuid).exists():
        raise ValidationError({
            "code": CustomerErrorCode.ALREADY_EXISTS.value,
            "message": "Customer with this email address already exists.",
            "field": "email"
        })

    # Update balance if balance_init changes
    balance_init = data.get('balance_init')
    if balance_init is not None:
        balance_difference = Decimal(balance_init) - customer.balance_init
        customer.balance += balance_difference
    
    
    # Update the customer
    serializer = UpdateCustomerSerializer(customer, data=data, partial=True)
    serializer.is_valid(raise_exception=True)
    updated_customer = serializer.save()
    fix_customer_payment_balances(customer_uuid=uuid)
    return updated_customer

@transaction.atomic
def delete_customer(uuid):

    try:
        # Fetch the customer by UUID
        customer = Customer.objects.get(uuid=uuid, deleted=False)
    except Customer.DoesNotExist:
        raise ValidationError({
            "code": CustomerErrorCode.NOT_FOUND.value,
            "message": f"Customer with UUID {uuid} not found.",
            "field": "uuid"
        })
        
        # Check for associated payments
    has_payments = CustomerPayment.objects.filter(customer=customer).exists()
    if has_payments:
        raise ValidationError({
            "code": "HAS_PAYMENTS",
            "message": f"Customer with UUID {customer.name} has associated payments and cannot be deleted.",
            "field": ""
        })

    # Check for associated sales
    has_sales = SaleOrder.objects.filter(customer=customer).exists()
    if has_sales:
        raise ValidationError({
            "code": "HAS_SALES",
            "message": f"Customer with UUID {customer.name} has associated sales and cannot be deleted.",
            "field": ""
        })

    # Soft delete the customer
    customer.deleted = True
    customer.save()






