import abc
import logging

from common.utiles import utctimestampnow
from db.mongo import Mongo, MongoCrud, create_objectid

import six

from ..default_settings import settings
from ..exceptions import (
    AmountDoesNotSupport,
    BankGatewayStateInvalid,
    BankGatewayTokenExpired,
    CurrencyDoesNotSupport, SettingDoesNotExist
)
from ..models import Bank, CurrencyEnum, PaymentStatus
from ..utils import append_querystring


# TODO: handle and expire record after 15 minutes
@six.add_metaclass(abc.ABCMeta)
class BaseBank:
    """Base bank for sending to gateway."""

    _gateway_currency: str = CurrencyEnum.IRR
    _currency: str = CurrencyEnum.IRR
    _amount: int = 0
    _gateway_amount: int = 0
    _mobile_number: str = None
    _tracking_code: str = None
    _reference_number: str = ""
    _transaction_status_text: str = ""
    _client_callback_url: str = ""
    _bank: Bank = None
    _request = None
    _db: Mongo = None

    def __init__(self, **kwargs):
        self.default_setting_kwargs = kwargs
        self.set_default_settings()

    @abc.abstractmethod
    def set_default_settings(self):
        """default setting, like fetch merchant code, terminal id and etc"""
        for item in ["db"]:
            if item not in self.default_setting_kwargs:
                raise SettingDoesNotExist()
            setattr(self, f"_{item.lower()}",
                    self.default_setting_kwargs[item])

    def prepare_amount(self):
        """prepare amount"""
        if self._currency == self._gateway_currency:
            self._gateway_amount = self._amount
        elif self._currency == CurrencyEnum.IRR and self._gateway_currency == CurrencyEnum.IRT:
            self._gateway_amount = CurrencyEnum.rial_to_toman(self._amount)
        elif self._currency == CurrencyEnum.IRT and self._gateway_currency == CurrencyEnum.IRR:
            self._gateway_amount = CurrencyEnum.toman_to_rial(self._amount)
        else:
            self._gateway_amount = self._amount

        if not self.check_amount():
            raise AmountDoesNotSupport()

    def check_amount(self):
        return self.get_gateway_amount() >= self.get_minimum_amount()

    @classmethod
    def get_minimum_amount(cls):
        return 1000

    @abc.abstractmethod
    def get_bank_type(self):
        pass

    def get_amount(self):
        """get the amount"""
        return self._amount

    def set_amount(self, amount):
        """set amount"""
        if int(amount) <= 0:
            raise AmountDoesNotSupport()
        self._amount = int(amount)

    @abc.abstractmethod
    def prepare_pay(self):
        logging.debug("Prepare pay method")
        self.prepare_amount()
        # tracking_code = int(str(uuid.uuid4().int)
        #                     [-1 * settings.TRACKING_CODE_LENGTH:])
        # self._set_tracking_code(tracking_code)
        self._set_tracking_code(str(create_objectid()))

    @abc.abstractmethod
    def get_pay_data(self):
        pass

    @abc.abstractmethod
    async def pay(self):
        logging.debug("Pay method")
        self.prepare_pay()

    @abc.abstractmethod
    def get_verify_data(self):
        pass

    @abc.abstractmethod
    async def prepare_verify(self, tracking_code):
        logging.debug("Prepare verify method")
        self._set_tracking_code(tracking_code)
        await self._set_bank_record()
        self.prepare_amount()

    @abc.abstractmethod
    async def verify(self, tracking_code):
        logging.debug("Verify method")
        await self.prepare_verify(tracking_code)

    async def ready(self, col_name, col_obj) -> Bank:
        await self.pay()
        bank = Bank(
            _id=self.get_tracking_code(),
            bank_type=self.get_bank_type(),
            amount=self.get_amount(),
            reference_number=self.get_reference_number(),
            response_result=self.get_transaction_status_text(),
            tracking_code=self.get_tracking_code(),
            phone=self.get_mobile_number(),
            col_name=col_name,
            col_obj=col_obj
        )
        self._bank = bank
        if self._client_callback_url:
            self._bank.callback_url = self._client_callback_url

        await self._set_payment_status(PaymentStatus.WAITING)

        return bank

    @abc.abstractmethod
    async def prepare_verify_from_gateway(self):
        pass

    async def verify_from_gateway(self, request):
        self.set_request(request)
        await self.prepare_verify_from_gateway()
        if not self._bank.status == PaymentStatus.CANCEL_BY_USER:
            await self._set_payment_status(PaymentStatus.RETURN_FROM_BANK)
            await self.verify(self.get_tracking_code())

    def get_client_callback_url(self):
        # return append_querystring(
        #     self._bank.callback_url,
        #     {settings.TRACKING_CODE_QUERY_PARAM: self.get_tracking_code()},
        # )
        return self._bank.callback_url

    def redirect_client_callback(self):
        logging.debug("Redirect to client")
        return self.get_client_callback_url()

    async def get_bank(self):

        return self._bank

    # def get_col_obj(self):
    #     return json.loads(self._bank.col_obj.decode("utf-8"))

    def set_mobile_number(self, mobile_number):
        self._mobile_number = mobile_number

    def get_mobile_number(self):
        return self._mobile_number

    def set_client_callback_url(self, callback_url):
        if not self._bank:
            self._client_callback_url = callback_url
        else:
            logging.critical(
                "You are change the call back url in invalid situation.",
                extra={
                    "bank_id": self._bank.pk,
                    "status": self._bank.status,
                },
            )
            raise BankGatewayStateInvalid(
                "Bank state not equal to waiting. Probably finish "
                f"or redirect to bank gateway. status is {self._bank.status}"
            )

    def _set_reference_number(self, reference_number):
        """reference number get from bank"""
        self._reference_number = reference_number

    async def _set_bank_record(self):
        try:
            self._bank = await MongoCrud.find_one(self._db, Bank, {
                Bank.tracking_code: self.get_tracking_code(),
            })
            logging.debug("Set reference find bank object.")
        except Bank.DoesNotExist:
            logging.debug("Cant find bank record object.")
            raise BankGatewayStateInvalid(
                "Cant find bank record with reference number reference number is {}".format(
                    self.get_reference_number()
                )
            )

   

        self.set_amount(self._bank.amount)

    def get_reference_number(self):
        return self._reference_number

    def _set_transaction_status_text(self, txt):
        self._transaction_status_text = txt

    def get_transaction_status_text(self):
        return self._transaction_status_text

    async def _set_payment_status(self, payment_status):
        if payment_status == PaymentStatus.RETURN_FROM_BANK and \
                self._bank.status != PaymentStatus.REDIRECT_TO_BANK:
            logging.debug(
                "Payment status is not status suitable.",
                extra={"status": self._bank.status},
            )
            raise BankGatewayStateInvalid(
                "You change the status bank record before/after this record change status from redirect to bank. "
                "current status is {}".format(self._bank.status)
            )

        self._bank.status = payment_status

        await MongoCrud.update_one_set(
            self._db, Bank, {Bank.id: self._bank.id},
            self._bank, upsert=True)

        logging.debug("Change bank payment status",
                      extra={"status": payment_status})

    def set_gateway_currency(self, currency: CurrencyEnum):
        if currency not in [CurrencyEnum.IRR, CurrencyEnum.IRT]:
            raise CurrencyDoesNotSupport()
        self._gateway_currency = currency

    # def get_gateway_currency(self):
    #     return self._gateway_currency

    def set_currency(self, currency: CurrencyEnum):
        if currency not in [CurrencyEnum.IRR, CurrencyEnum.IRT]:
            raise CurrencyDoesNotSupport()
        self._currency = currency

    def get_currency(self):
        return self._currency

    def get_gateway_amount(self):
        return self._gateway_amount

    def _set_tracking_code(self, tracking_code):
        self._tracking_code = tracking_code

    def get_tracking_code(self):
        return self._tracking_code

    # """ًRequest"""

    def set_request(self, request):
        self._request = request

    def get_request(self):
        return self._request

    # """gateway"""

    def _prepare_check_gateway(self, amount=None):
        if amount:
            self.set_amount(amount)
        else:
            self.set_amount(10000)
        self.set_client_callback_url("/")

    async def check_gateway(self, amount=None):
        self._prepare_check_gateway(amount)
        await self.pay()

    @abc.abstractmethod
    def _get_gateway_payment_url_parameter(self):
        """
        :return
        url: str
        """
        pass

    @abc.abstractmethod
    def _get_gateway_payment_parameter(self):
        """
        :return
        params: dict
        """
        pass

    @abc.abstractmethod
    def _get_gateway_payment_method_parameter(self):
        """
        :return
        method: POST, GET
        """
        pass

    async def redirect_gateway(self):
        if (utctimestampnow() - self._bank.created_at) > 120:
            await self._set_payment_status(PaymentStatus.EXPIRE_GATEWAY_TOKEN)
            logging.debug("Redirect to bank expire!")
            raise BankGatewayTokenExpired()
        logging.debug("Redirect to bank")
        await self._set_payment_status(PaymentStatus.REDIRECT_TO_BANK)
        return self.get_gateway_payment_url()

    def get_gateway_payment_url(self):
        url = self._get_gateway_payment_url_parameter()
        params = self._get_gateway_payment_parameter()

        return append_querystring(url, params)

    def _get_gateway_callback_url(self):
        return settings.CALLBACK_NAMESPACE
