"""Default settings for messaging."""

from functools import lru_cache
from config import settings as psetting
from pydantic import BaseSettings

iranian_bank_gateways = "engines.iranian_bank_gateways"


# TODO: refactor configs
class BanksSettings(BaseSettings):
    BANK_CLASS: dict = {
        "SEP": f"{iranian_bank_gateways}.banks.SEP",
        "IDPAY": f"{iranian_bank_gateways}.banks.IDPay",
    }
    _AZ_IRANIAN_BANK_GATEWAYS = {}
    BANK_PRIORITIES = []
    BANK_GATEWAYS = {
        "SEP": {
            "MERCHANT_CODE": "",
            "TERMINAL_CODE": ""
        },
        "IDPAY": {},
    }

    BANK_DEFAULT = "SEP"
    SETTING_VALUE_READER_CLASS = f"{iranian_bank_gateways}.readers.DefaultReader"

    CURRENCY = "IRT"
    CALLBACK_NAMESPACE = f"{url}/payment/receive"


@lru_cache()
def get_settings() -> BanksSettings:
    return BanksSettings()


settings = get_settings()
