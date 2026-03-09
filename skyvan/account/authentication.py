from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model


User = get_user_model()


class PhoneBackend(BaseBackend):
    def authenticate(self, request, username=None, phone=None, password=None, **kwargs):
        """
        Allows authentication using `phone` while also supporting `username` (for compatibility).
        """
        UserModel = get_user_model()

        if phone is None:
            phone = username
        try:
            user = UserModel.objects.get(phone=phone)
        except UserModel.DoesNotExist:
            return None

        if user.check_password(password):
            return user

        return None

    def get_user(self, user_id):
        """Retrieve user by ID."""
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
