"""交易 canonical DTO 与产品类型数值规则的定向测试。"""
from decimal import Decimal
import pytest
from pydantic import ValidationError
from app.investmentLedger.schemas import (
    ERROR_CODE_NOT_A_NUMBER, ERROR_CODE_NOT_INTEGER, ERROR_CODE_OUT_OF_RANGE, TransactionCreate,
)

BASE = {"productType": "FUND", "productName": "测试基金", "productCode": "F001", "transactionPrice": "1.234567890123456789", "transactionQuantity": "10.123456789", "direction": "BUY", "tradeDate": "2024-02-29"}
def payload(**values): return BASE | values
def errors(error): return {str(item['loc'][0]): item['type'] for item in error.errors()}

def testWealthAndFundAcceptUnlimitedPositiveDecimalTextWithoutFormatting():
    for product_type in ('WEALTH', 'FUND'):
        model = TransactionCreate(**payload(productType=product_type))
        assert model.transaction_price == Decimal('1.234567890123456789')
        assert model.transaction_quantity == Decimal('10.123456789')
        assert model.model_dump(by_alias=True)['transactionPrice'] == Decimal('1.234567890123456789')

def testStockUsesPositiveIntegerQuantityButKeepsArbitraryPricePrecision():
    model = TransactionCreate(**payload(productType='STOCK', transactionPrice='999999999999999999999.0000000000001', transactionQuantity='12345678901234567890'))
    assert model.transaction_quantity == Decimal('12345678901234567890')
    with pytest.raises(ValidationError) as caught:
        TransactionCreate(**payload(productType='STOCK', transactionQuantity='1.5'))
    assert errors(caught.value) == {'transactionQuantity': ERROR_CODE_NOT_INTEGER}

@pytest.mark.parametrize(('field', 'value', 'code'), [
    ('transactionPrice', 'NaN', ERROR_CODE_NOT_A_NUMBER), ('transactionPrice', 'Infinity', ERROR_CODE_NOT_A_NUMBER),
    ('transactionPrice', '0', ERROR_CODE_OUT_OF_RANGE), ('transactionQuantity', '-1', ERROR_CODE_OUT_OF_RANGE),
    ('transactionQuantity', 'abc', ERROR_CODE_NOT_A_NUMBER),
])
def testInvalidOrNonpositiveValuesAreRejectedOnCanonicalField(field, value, code):
    with pytest.raises(ValidationError) as caught:
        TransactionCreate(**payload(**{field: value}))
    assert errors(caught.value) == {field: code}
