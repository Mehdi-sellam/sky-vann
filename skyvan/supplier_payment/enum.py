from enum import Enum

class PaymentTypes(Enum):
    PAYMENT = "payment"
    PURCHASE = "purchase"
    RETURN_PURCHASE = "return_purchase"

    @classmethod
    def choices(cls):
        return [(item.value, item.name.capitalize()) for item in cls]


class PaymentMethods(Enum):
    CASH = "cash"  # Espèces
    CARD = "card" # Carte interbancaire (CIB)
    CHEQUE = "cheque"# Chèque bancaire
    BANK_TRANSFER = "bank_transfer"# Virement bancaire
 
    @classmethod
    def choices(cls):
        return [(item.value, item.name.capitalize()) for item in cls]