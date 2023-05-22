from ..models import BankType

from .bases import Reader

from ..default_settings import settings


class DefaultReader(Reader):
    def read(self, bank_type: BankType) -> dict:
        """

        :param bank_type:
        :param identifier:
        :return:
        base on bank type for example for BMI:
        {
            'MERCHANT_CODE': '<YOUR INFO>',
            'TERMINAL_CODE': '<YOUR INFO>',
            'SECRET_KEY': '<YOUR INFO>',
        }
        """
        return settings.BANK_GATEWAYS[bank_type]

    def default(self):
        return settings.BANK_DEFAULT

    def currency(self):
        return settings.CURRENCY

    def get_bank_priorities(self,) -> list:
        priorities = [self.default()]
        priorities = list(dict.fromkeys(priorities + settings.BANK_PRIORITIES))
        return priorities
