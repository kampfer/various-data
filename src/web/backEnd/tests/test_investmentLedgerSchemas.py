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
    # 费用校验（需求 6.3）：float/NaN/Infinity 被拒为 NOT_A_NUMBER；负数被拒为 OUT_OF_RANGE
    ('fee', 'NaN', ERROR_CODE_NOT_A_NUMBER), ('fee', 'Infinity', ERROR_CODE_NOT_A_NUMBER),
    ('fee', '-0.01', ERROR_CODE_OUT_OF_RANGE),
])
def testInvalidOrNonpositiveValuesAreRejectedOnCanonicalField(field, value, code):
    with pytest.raises(ValidationError) as caught:
        TransactionCreate(**payload(**{field: value}))
    assert errors(caught.value) == {field: code}


def testFeeIsOptionalAndDefaultsToNoneForServiceLayerNormalization():
    """未提供 fee 时透传 None，由服务层归一为 Decimal(0) 落库（需求 6.2）。"""
    model = TransactionCreate(**payload())
    assert model.fee is None


def testFeeAcceptsZeroAndPositiveFiniteDecimal():
    """费用接受 0 与任意精度的正有限十进制数值（需求 6.2、6.3）。"""
    assert TransactionCreate(**payload(fee='0')).fee == Decimal('0')
    assert TransactionCreate(**payload(fee='5.00')).fee == Decimal('5.00')
    assert TransactionCreate(**payload(fee='0.1234567890123456789')).fee == Decimal('0.1234567890123456789')


def testFeeRejectsFloatToPreventPrecisionLoss():
    """float 入参被拒绝，避免金额精度损失（与交易价格/数量同口径，需求 6.3）。"""
    with pytest.raises(ValidationError) as caught:
        TransactionCreate(**payload(fee=1.5))
    assert errors(caught.value) == {'fee': ERROR_CODE_NOT_A_NUMBER}


def testTransactionOutExposesFeeAsNonEmptyDecimalString():
    """出参 fee 为非空十进制字符串，未提供时归一为 '0'（需求 6.5）。"""
    from app.investmentLedger.schemas import TransactionOut
    assert TransactionOut.model_validate({
        'id': 1, 'product_type': 'FUND', 'product_name': '基金', 'product_code': 'F001',
        'transaction_price': '1.2345', 'transaction_quantity': '2.5', 'fee': '5.00',
        'direction': 'BUY', 'trade_date': '2024-02-29',
    }).model_dump(by_alias=True)['fee'] == '5.00'
    assert TransactionOut.model_validate({
        'id': 1, 'product_type': 'FUND', 'product_name': '基金', 'product_code': 'F001',
        'transaction_price': '1.2345', 'transaction_quantity': '2.5', 'fee': '0',
        'direction': 'BUY', 'trade_date': '2024-02-29',
    }).model_dump(by_alias=True)['fee'] == '0'
