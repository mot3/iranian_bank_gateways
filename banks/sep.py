import logging

import aiohttp
from aiohttp.client_exceptions import ServerTimeoutError, ClientConnectionError

from db.mongo import MongoCrud

from .banks import BaseBank, Bank
from ..exceptions import BankGatewayConnectionError, SettingDoesNotExist
from ..exceptions.exceptions import BankGatewayRejectPayment
from ..models import BankType, CurrencyEnum, PaymentStatus


class SEP(BaseBank):
    _merchant_code = None
    _terminal_code = None

    def __init__(self, **kwargs):
        super(SEP, self).__init__(**kwargs)
        self.set_gateway_currency(CurrencyEnum.IRR)
        self._token_api_url = "https://sep.shaparak.ir/MobilePG/MobilePayment"
        self._payment_url = "https://sep.shaparak.ir/OnlinePG/SendToken"
        self._verify_api_url = "https://sep.shaparak.ir/verifyTxnRandomSessionkey/ipg/VerifyTransaction"

    def get_bank_type(self):
        return BankType.SEP

    def set_default_settings(self):
        super(SEP, self).set_default_settings()
        for item in ["MERCHANT_CODE", "TERMINAL_CODE"]:
            if item not in self.default_setting_kwargs:
                raise SettingDoesNotExist()
            setattr(self, f"_{item.lower()}",
                    self.default_setting_kwargs[item])

    def get_pay_data(self):
        data = {
            "Action": "Token",
            "Amount": self.get_gateway_amount(),
            "Wage": 0,
            "TerminalId": self._merchant_code,
            "ResNum": self.get_tracking_code(),
            "RedirectURL": self._get_gateway_callback_url(),
            "CellNumber": self.get_mobile_number(),
        }
        return data

    def prepare_pay(self):
        super(SEP, self).prepare_pay()

    async def pay(self):
        await super(SEP, self).pay()
        data = self.get_pay_data()
        response_json = await self._send_data(self._token_api_url, data)
        if str(response_json["status"]) == "1":
            token = response_json["token"]
            self._set_reference_number(token)
        else:
            logging.critical("SEP gateway reject payment")
            raise BankGatewayRejectPayment(self.get_transaction_status_text())

    """
    : gateway
    """

    def _get_gateway_payment_url_parameter(self):
        return self._payment_url

    def _get_gateway_payment_method_parameter(self):
        return "POST"

    def _get_gateway_payment_parameter(self):
        params = {
            "Token": self.get_reference_number(),
            "GetMethod": "true",
        }
        return params

    """
    verify from gateway
    """

    async def prepare_verify_from_gateway(self):
        await super(SEP, self).prepare_verify_from_gateway()
        request = self.get_request()

        form = await request.form()

        tracking_code = form.get("ResNum", None)
        ref_num = form.get("RefNum", None)

        self._set_tracking_code(tracking_code)
        self._set_reference_number(ref_num)

        await self._set_bank_record()

        token = form.get("Token", None)
        trace_no = form.get('TraceNo', None)
        secure_pan = form.get('SecurePan', None)

        if form.get("State", "NOK") == "OK" and ref_num:
            self._bank.token = ref_num
            self._bank.trace_no = trace_no
            self._bank.secure_pan = secure_pan

    

            await MongoCrud.update_one_set(
                self._db, Bank,
                {Bank.id: self._bank.id},
                self._bank)
        else:
            await self._set_payment_status(PaymentStatus.CANCEL_BY_USER)

    async def verify_from_gateway(self, request):
        await super(SEP, self).verify_from_gateway(request)

    """
    verify
    """

    def get_verify_data(self):
        super(SEP, self).get_verify_data()
        data = {
            "RefNum": self.get_reference_number(),
            "TerminalNumber": self._merchant_code
        }
        return data

    async def prepare_verify(self, tracking_code):
        await super(SEP, self).prepare_verify(tracking_code)

    async def verify(self, transaction_code):
        await super(SEP, self).verify(transaction_code)
        data = self.get_verify_data()
        result = await self._send_data(self._verify_api_url, data)
        if result['ResultCode'] == 0:
            await self._set_payment_status(PaymentStatus.COMPLETE)
        else:
            await self._set_payment_status(PaymentStatus.CANCEL_BY_USER)
            logging.debug("SEP gateway unapprove payment")

    async def _send_data(self, api, data):
        try:
            async with aiohttp.ClientSession() as client:
                async with client.post(api, json=data, timeout=5) as response:
                    response_json = await response.json()

        except ServerTimeoutError:
            logging.exception("SEP time out gateway {}".format(data))
            raise BankGatewayConnectionError()
        except ClientConnectionError:
            logging.exception("SEP time out gateway {}".format(data))
            raise BankGatewayConnectionError()

        self._set_transaction_status_text(response_json.get("errorDesc"))
        return response_json
