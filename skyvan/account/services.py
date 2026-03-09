from django.db import transaction
from rest_framework.exceptions import (
    ValidationError,
    NotFound,
    APIException,
    PermissionDenied,
)
from .models import User, UserRoles
import uuid
from django.db import transaction, IntegrityError, DatabaseError
from .error_codes import UserErrorCode

 
def get_all_organization_users():
    """Fetch all active organization users."""
    return User.objects.filter(role=UserRoles.ORGANIZATION_USER, deleted=False)


def get_organization_user_by_uuid(user_uuid: uuid.UUID):
    """Fetch a single organization user by UUID."""
    try:
        return User.objects.get(
            uuid=user_uuid, deleted=False, role=UserRoles.ORGANIZATION_USER
        )
    except User.DoesNotExist:
        raise NotFound(
            {
                "code": UserErrorCode.NOT_FOUND.value,
                "message": "A user not found.",
                "field": "uuid",
            }
        )


def create_organization_user(validated_data):
    """Service to create an organization user."""
    # get organisation for request
    try:
        organization = None
        user = User.objects.create(
            uuid=validated_data.get("uuid"),
            phone=validated_data["phone"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            email=validated_data.get("email", ""),
            organization=organization,
            role=UserRoles.ORGANIZATION_USER,
        )
        user.set_password(validated_data["password"])
        user.save()
        return user
    except IntegrityError:
        raise APIException(
            {
                "code": "INTEGRITY_ERROR",
                "message": "Database integrity error occurred while create Organization User.",
                "field": "UUID",
            }
        )
    except DatabaseError:
        raise APIException(
            {
                "code": "DATABASE_ERROR",
                "message": "A database error occurred. Please try again.",
                "field": "UUID",
            }
        )
    except Exception as e:
        raise APIException(
            {
                "code": "UNKNOWN_ERROR",
                "message": f"An unexpected error occurred: {str(e)}",
                "field": "UUID",
            }
        )


def update_organization_user(user: User, validated_data, requestor: User):
    """Service to update an organization user with duplicate phone number check and password hashing."""

    # Prevent users from changing their own `is_active` status
    if (
        requestor.is_authenticated
        and user.uuid == requestor.uuid
        and "is_active" in validated_data
    ):
        raise ValidationError(
            {
                "code": UserErrorCode.PERMISSION_DENIED.value,
                "message": "You cannot change your own active status.",
                "field": "is_active",
            }
        )
    # Check if phone number is being changed and already exists
    new_phone = validated_data.get("phone")
    if new_phone and new_phone != user.phone:
        if User.objects.filter(phone=new_phone).exclude(uuid=user.uuid).exists():
            raise ValidationError(
                {
                    "code": UserErrorCode.DUPLICATE_PHONE_EMAIL.value,
                    "message": "A user with this phone number already exists.",
                    "field": "phone",
                }
            )
    try:
        # Hash password if provided
        password = validated_data.pop("password", None)
        if password:
            user.set_password(password)

        # Update other fields
        for key, value in validated_data.items():
            setattr(user, key, value)

        user.save()
        return user
    except IntegrityError:
        raise APIException(
            {
                "code": UserErrorCode.USER_DELETION_FAILED.value,
                "message": "Cannot delete user due to existing references.",
                "field": "uuid",
            }
        )

    except DatabaseError:
        raise APIException(
            {
                "code": UserErrorCode.SERVER_ERROR.value,
                "message": "A database error occurred. Please try again.",
                "field": "general",
            }
        )

    except Exception as e:
        raise APIException(
            {
                "code": UserErrorCode.SERVER_ERROR.value,
                "message": f"An unexpected error occurred: {str(e)}",
                "field": "UUID",
            }
        )


def delete_organization_user(uuid: uuid.UUID, requestor: User):
    """Soft delete an organization user."""

    user = get_organization_user_by_uuid(uuid)
    # prevent to delete owner
    if (
        not requestor.is_authenticated
        and user.is_owner
        and user.is_owner.uuid != requestor.uuid
    ):
        raise PermissionDenied(
            {
                "code": UserErrorCode.PERMISSION_DENIED.value,
                "message": "You cannot delete owner account.",
                "field": "uuid",
            }
        )
    if requestor.is_authenticated and uuid == requestor.uuid:
        raise PermissionDenied(
            {
                "code": UserErrorCode.PERMISSION_DENIED.value,
                "message": "You cannot delete your own account.",
                "field": "uuid",
            }
        )
    try:
        user.deleted = True  # Soft delete
        user.save()
        return user
    except IntegrityError:
        raise APIException(
            {
                "code": UserErrorCode.USER_DELETION_FAILED.value,
                "message": "Cannot delete user due to existing references.",
                "field": "uuid",
            }
        )

    except DatabaseError:
        raise APIException(
            {
                "code": UserErrorCode.SERVER_ERROR.value,
                "message": "A database error occurred. Please try again.",
                "field": "general",
            }
        )

    except Exception as e:
        raise APIException(
            {
                "code": UserErrorCode.SERVER_ERROR.value,
                "message": f"An unexpected error occurred: {str(e)}",
                "field": "UUID",
            }
        )
