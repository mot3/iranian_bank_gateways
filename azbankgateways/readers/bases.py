import abc

import six

from ..models import BankType
from ..default_settings import settings


@six.add_metaclass(abc.ABCMeta)
class Reader:
    @abc.abstractmethod
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
        pass

    def klass(self, bank_type: BankType) -> dict:
        return settings.BANK_CLASS[bank_type]

    @abc.abstractmethod
    def get_bank_priorities(self) -> list:
        pass

    @abc.abstractmethod
    def default(self):
        pass

    @abc.abstractmethod
    def currency(self):
        pass
