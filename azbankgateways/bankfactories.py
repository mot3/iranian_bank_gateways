from __future__ import absolute_import, unicode_literals

import importlib
import logging

from .default_settings import settings
from .banks import BaseBank
from .exceptions.exceptions import BankGatewayAutoConnectionFailed
from .models import BankType


class BankFactory:
    def __init__(self):
        logging.debug("Create bank factory")
        self._secret_value_reader = self._import(
            settings.SETTING_VALUE_READER_CLASS)()

    @staticmethod
    def _import(path):
        package, attr = path.rsplit(".", 1)
        klass = getattr(importlib.import_module(package), attr)
        return klass

    def _import_bank(self, bank_type: BankType):
        """
        helper to import bank aliases from string paths.

        raises an AttributeError if a bank can't be found by it's alias
        """
        bank_class = self._import(self._secret_value_reader.klass(
            bank_type=bank_type))
        logging.debug("Import bank class")

        return bank_class, self._secret_value_reader.read(bank_type=bank_type)

    def create(self, db, bank_type: BankType = None) -> BaseBank:
        """Build bank class"""
        if not bank_type:
            bank_type = self._secret_value_reader.default()
        logging.debug("Request create bank", extra={"bank_type": bank_type})

        bank_klass, bank_settings = self._import_bank(bank_type)
        bank_settings.update({'db': db})
        bank = bank_klass(**bank_settings)
        bank.set_currency(self._secret_value_reader.currency())

        logging.debug("Create bank")
        return bank

    def create_default(self, db) -> BaseBank:
        """Build default class"""
        return self.create(db=db, bank_type=settings.BANK_DEFAULT)

    # def auto_create(self, identifier: str = "1", amount=None) -> BaseBank:
    #     logging.debug("Request create bank automatically")
    #     bank_list = self._secret_value_reader.get_bank_priorities(identifier)
    #     errors = []
    #     for bank_type in bank_list:
    #         try:
    #             bank = self.create(bank_type, identifier)
    #             bank.check_gateway(amount)
    #             return bank
    #         except Exception as e:
    #             logging.debug(str(e))
    #             logging.debug("Try to connect another bank...")
    #             errors.append(e)
    #             continue
    #     logging.debug("All banks failed to connect")
    #     errors_msg = "\n".join([str(e) for e in errors])
    #     raise BankGatewayAutoConnectionFailed(errors_msg)
