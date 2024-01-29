from enum import Enum


class BankType(str, Enum):
    SEP = "SEP"
    IDPAY = "IDPAY"


class CurrencyEnum(str, Enum):
    IRR = "IRR"
    IRT = "IRT"

    @classmethod
    def rial_to_toman(cls, amount):
        return amount / 10

    @classmethod
    def toman_to_rial(cls, amount):
        return amount * 10


class PaymentStatus(str, Enum):
    WAITING = "Waiting"
    REDIRECT_TO_BANK = "Redirect to bank"
    RETURN_FROM_BANK = "Return from bank"
    CANCEL_BY_USER = "Cancel by user"
    EXPIRE_GATEWAY_TOKEN = "Expire gateway token"
    EXPIRE_VERIFY_PAYMENT = "Expire verify payment"
    COMPLETE = "Complete"
    ERROR = "Unknown error acquired"
