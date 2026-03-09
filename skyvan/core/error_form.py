from django.core.exceptions import ValidationError
class ErrorForm(ValidationError):
    def __init__(self, code, message, field):
        self.code = code
        self.message = message
        self.field = field
        super().__init__(self.message)

    def to_dict(self):
        return {"code": self.code, "message": self.message, "field": self.field}