from .models import Van, VanAssignment, VanInventory
from rest_framework.exceptions import ValidationError, NotFound
from django.db import transaction
import uuid
from .error_codes import VanErrorCode
from django.db.models.query import QuerySet
from django.utils import timezone
from account.services import get_organization_user_by_uuid
from django.utils import timezone
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied

def get_user_van(user):
    now = timezone.now()
    return (Van.objects.filter(assignments__user=user, assignments__is_active=True, assignments__end_datetime__gt=now,assignments__deleted=False) 
    )


def get_user_active_assignment(user):
    now = timezone.now()
    return (
        VanAssignment.objects
        .filter(end_datetime__gt=now, user=user, is_active=True, deleted=False)
        .order_by("-start_datetime")
        .first()
    )


def get_my_inventory(user):
    assignment = get_user_active_assignment(user)

    if not assignment or not assignment.van:
        raise PermissionDenied("No active van assignment found.")

    return VanInventory.objects.filter(van=assignment.van, deleted=False).select_related("product")


def get_van_list() -> QuerySet:
    """
    Retrieve all non-deleted vans.

    Returns:
        QuerySet: A queryset of active (non-deleted) Van instances.
    """
    return Van.objects.filter(deleted=False).prefetch_related("assignments")


def get_van_by_uuid(uuid: uuid.UUID) -> Van:
    try:
        return Van.objects.get(uuid=uuid, deleted=False)
    except Van.DoesNotExist:
        raise NotFound(
            {
                "code": VanErrorCode.NOT_FOUND.value,
                "message": f"Van with UUID {uuid} not found.",
                "field": "uuid",
            }
        )


@transaction.atomic
def create_van(validated_data):
    try:
        van = Van.objects.create(**validated_data)
        return van
    except Exception as e:
        raise ValidationError(
            {
                "code": VanErrorCode.CREATION_FAILED.value,
                "message": f"Error creating van: {str(e)}",
                "field": "van",
            }
        )

@transaction.atomic
def update_van(van: Van, validated_data):
    license_plate = validated_data.get("license_plate")

    if (
        Van.objects.filter(license_plate=license_plate, deleted=False)
        .exclude(uuid=van.uuid)
        .exists()
    ):
        raise ValidationError(
            {
                "code": VanErrorCode.UNIQUE.value,
                "message": f"A van with license plate '{license_plate}' already exists.",
                "field": "license_plate",
            }
        )
    try:
        for attr, value in validated_data.items():
            setattr(van, attr, value)
        van.save()
        return van
    except Exception as e:
        raise ValidationError(
            {
                "code": VanErrorCode.UPDATE_FAILED.value,
                "message": f"Error updating van: {str(e)}",
                "field": "van",
            }
        )


@transaction.atomic
def delete_van(uuid: uuid.UUID):
    van = get_van_by_uuid(uuid)

    if van.assignments.filter(is_active=True).exists():
        raise ValidationError(
            {
                "code": VanErrorCode.HAS_ACTIVE_ASSIGNMENT.value,
                "message": "Cannot delete van with active assignment.",
                "field": "van",
            }
        )

    if van.inventories.filter(quantity__gt=0).exists():
        raise ValidationError(
            {
                "code": VanErrorCode.HAS_STOCK.value,
                "message": "Cannot delete van with products still in inventory.",
                "field": "van",
            }
        )

    try:
        van.deleted = True
        van.save(update_fields=["deleted"])
        return van
    except Exception as e:
        raise ValidationError(
            {
                "code": VanErrorCode.DELETE_FAILED.value,
                "message": f"Failed to delete van: {str(e)}",
                "field": "van",
            }
        )

def get_all_van_assignments() -> QuerySet:
    """
    Retrieve all non-deleted van assignments.

    Returns:
        QuerySet: A queryset of all van assignments (not soft-deleted).
    """
    return VanAssignment.objects.select_related("van", "user").filter(deleted=False)

def get_van_assignment_by_uuid(uuid: uuid.UUID) -> VanAssignment:
    """
    Retrieve a VanAssignment instance by UUID.

    Args:
        uuid (uuid.UUID): UUID of the van assignment.

    Returns:
        VanAssignment: The assignment instance if found.

    Raises:
        ValidationError: If the assignment is not found or is soft deleted.
    """
    try:
        return VanAssignment.objects.get(uuid=uuid, deleted=False)
    except VanAssignment.DoesNotExist:
        raise NotFound(
            {
                "code": VanErrorCode.NOT_FOUND.value,
                "message": f"VanAssignment with UUID {uuid} not found.",
                "field": "uuid",
            }
        )

def create_van_assignment(validated_data):
    uuid = validated_data.get("uuid")
    if VanAssignment.objects.filter(uuid=uuid).exists():
        raise ValidationError(
            {
                "code": VanErrorCode.NOT_FOUND.value,
                "message": "Assignment with this UUID already exists.",
                "field": "uuid",
            }
        )

    van_uuid = validated_data.pop("van_uuid")
    user_uuid = validated_data.pop("user_uuid")
    van = get_van_by_uuid(van_uuid)
    user = get_organization_user_by_uuid(user_uuid)
    if VanAssignment.objects.filter(
        van=van, is_active=True, start_datetime=validated_data["start_datetime"]
    ).exists():
        raise ValidationError(
            {
                "code": VanErrorCode.DUPLICATE_START.value,
                "message": "This van already has an assignment with the same start time.",
                "field": "start_datetime",
            }
        )
    # Business rule: no overlapping for van
    if VanAssignment.objects.filter(
        van=van,
        is_active=True,
        start_datetime__lt=validated_data["end_datetime"],
        end_datetime__gt=validated_data["start_datetime"],
    ).exists():
        raise ValidationError(
            {
                "code": VanErrorCode.OVERLAPPING_ASSIGNMENT.value,
                "message": "This van already has an active assignment during that time.",
                "field": "van",
            }
        )

    # Business rule: no overlapping for user driver
    if VanAssignment.objects.filter(
        user=user,
        is_active=True,
        start_datetime__lt=validated_data["end_datetime"],
        end_datetime__gt=validated_data["start_datetime"],
    ).exists():
        raise ValidationError(
            {
                "code": VanErrorCode.OVERLAPPING_ASSIGNMENT.value,
                "message": "This driver already has an active assignment during that time.",
                "field": "user",
            }
        )
    return VanAssignment.objects.create(van=van, user=user, **validated_data)

def close_van_assignment(assignment: VanAssignment) -> VanAssignment:
    if not assignment.is_active:
        raise ValidationError(
            {
                "code": VanErrorCode.ALREADY_CLOSED.value,
                "message": "This assignment is already closed.",
                "field": "van_assignment",
            }
        )

    assignment.end_datetime = timezone.now()
    assignment.is_active = False
    assignment.save(update_fields=["end_datetime", "is_active"])
    return assignment

def update_van_assignment(assignment: VanAssignment, validated_data):
    try:
        for field, value in validated_data.items():
            setattr(assignment, field, value)
        assignment.save()
        return assignment
    except Exception as e:
        raise ValidationError(
            {
                "code": VanErrorCode.UPDATE_FAILED.value,
                "message": f"Failed to update van assignment: {str(e)}",
                "field": "van_assignment",
            }
        )

def delete_van_assignment(assignment: VanAssignment) -> VanAssignment:

    if assignment.is_active:
        raise ValidationError(
            {
                "code": VanErrorCode.CANNOT_DELETE_ACTIVE.value,
                "message": "Cannot delete an active assignment. Please close it first.",
                "field": "assignment",
            }
        )

    assignment.deleted = True
    assignment.save(update_fields=["deleted"])
    return assignment

def get_van_inventory_by_van_uuid(van):
    return van.inventories.filter(deleted=False).select_related(
        "product"
    )
