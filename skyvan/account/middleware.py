from django.utils.deprecation import MiddlewareMixin
from rest_framework_simplejwt.authentication import JWTAuthentication


class OrganisationMiddleware(MiddlewareMixin):
    """Middleware to attach organisation_id to request"""

    def process_request(self, request):
        """Extract `organisation_id` from JWT token and attach it to `request.organisation_id`."""

        jwt_authenticator = JWTAuthentication()
        try:
            auth_result = jwt_authenticator.authenticate(request)
            if auth_result is not None:
                request.user, validated_token = auth_result  # ✅ Authenticate user
                request.auth = validated_token
            else:
                request.user = None
                request.auth = None
        except Exception:
            request.user = None
            request.auth = None

        # ✅ Extract `organisation_id` from token payload
        request.organisation_id = (
            request.auth.get("organisation_id") if request.auth else None
        )
