from pydantic import BaseModel, Field

from common.utiles import utctimestampnow
from db.mongo import Tables, SetEnum, PyObjectId, create_objectid
import json

from .enum import PaymentStatus


class Bank(BaseModel, metaclass=SetEnum):
    id: PyObjectId = Field(None, alias='_id')
    status: str = None
    bank_type: str = None
    tracking_code: str = None
    amount: str = None
    reference_number: str = None
    response_result: str = None
    callback_url: str = None
    phone: str = None
    trace_no: str = None
    secure_pan: str = None
    ref_num: str = None
    token: str = None
    col_name: str = None
    col_obj: dict = None
    created_at: int = Field(default_factory=utctimestampnow)

    class Config:
        collection = Tables.transaction

    @property
    def is_success(self):
        return self.status == PaymentStatus.COMPLETE
