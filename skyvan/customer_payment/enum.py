from enum import Enum

class PaymentTypeEnum(Enum):
    PAYMENT = "payment"
    SALE = "sale"
    RETURN_SALE = "return_sale"

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