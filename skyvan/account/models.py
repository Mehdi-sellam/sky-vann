from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.db import models
from uuid import uuid4
from .enums import UserRoles
from core.models import BaseModel


class UserManager(BaseUserManager):
    def create_user(self, phone, password=None, **extra_fields):
        """
        Creates and saves a User with the given phone and password.
        """
        if not phone:
            raise ValueError("The Phone field must be set")

        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        """
        Creates and saves a superuser with the given phone and password.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", UserRoles.ADMIN)  # Superusers are always Admins
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(phone, password, **extra_fields)


class User(AbstractBaseUser, BaseModel):
    uuid = models.UUIDField(default=uuid4, unique=True)
    last_name = models.CharField(max_length=30)
    first_name = models.CharField(max_length=30)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=15, unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    role = models.CharField(
        max_length=10,
        choices=UserRoles.CHOICES,
        default=UserRoles.ORGANIZATION_USER,
    )
    is_owner = models.BooleanField(default=False)
    organization = models.ForeignKey(
        "organisation.Organisation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,  # Admins won't have an organization
        related_name="users",
    )
    USERNAME_FIELD = "phone"

    objects = UserManager()

    def natural_key(self):
        if self.email:
            return (self.email,)
        if self.phone:
            return (self.phone,)
        return ()

    def has_perm(self, perm, obj=None):
        """Returns True if the user has a specific permission (For Django Admin)."""
        return self.is_superuser  # Only superusers have all permissions

    def has_module_perms(self, app_label):
        """Returns True if the user has permissions to view the app `app_label` in Admin."""
        return self.is_superuser  # Only superusers can access modules

    def get_username(self):
        if self.email:
            return self.email
        if self.phone:
            return self.phone
        return None
    @property
    def has_van(self):
        """Check if the user has a van assigned."""
        return self.van_assignments.filter(is_active=True).exists()
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def __str__(self):
        """Return phone number for better display in Django Admin dropdown."""
        return f"{self.phone}"  # ✅ Shows phone in dropdown

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
