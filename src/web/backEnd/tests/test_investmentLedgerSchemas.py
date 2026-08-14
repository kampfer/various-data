"""投资交易账本 Pydantic 契约的示例单元测试（任务 2.2）。

覆盖范围（需求 1.2、2.20、2.21、2.26、3.2）：

- 枚举字段的非法取值：中文字面量（如「理财」）与小写码（如 ``wealth``）一律拒绝；
- 文本长度边界：产品名称 0 / 1 / 100 / 101 字符，产品代码 1 / 32 / 33 字符，
  搜索值 1 / 100 / 101 字符；
- 交易单价小数位 1 / 2 / 3 位（仅 2 位合法）与估值单价小数位 ≤ 2 的差异；
- 非法日历日期（2 月 30 日）在解析阶段即失败；
- 交易日期范围必须成对出现且 ``start <= end``；
- 页大小闭区间边界 0 / 1 / 100 / 101。

所有断言都要求错误项**能定位到具体字段**：字段级错误直接检查 Pydantic
的 camelCase ``loc``；日期范围等模型级错误则复用既有统一错误翻译函数，
断言最终 ``FieldErrorItem.field`` 可精确回填到对应表单项（需求 1.2、3.2）。
本文件只做纯契约校验，不涉及任何数据库或网络 I/O。
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from pydantic import ValidationError

from app.investmentLedger.constants import (
    MAX_PAGE_SIZE,
    MAX_PRODUCT_CODE_LENGTH,
    MAX_PRODUCT_NAME_LENGTH,
    MAX_SEARCH_VALUE_LENGTH,
    MIN_PAGE_SIZE,
)
from app.investmentLedger.schemas import (
    ERROR_CODE_INVALID_SCALE,
    ERROR_CODE_OUT_OF_RANGE,
    TransactionCreate,
    TransactionQuery,
    ValuationUpsert,
)

#: 一份全字段合法的创建交易入参，作为各用例的基线（键名为对外 camelCase 别名）
VALID_TRANSACTION_PAYLOAD: dict[str, Any] = {
    "productType": "FUND",
    "productName": "测试基金",
    "productCode": "000001",
    "unitPrice": "1.23",
    "quantity": 100,
    "direction": "BUY",
    "tradeDate": "2024-01-02",
}

#: 一份全字段合法的估值写入入参，作为估值相关用例的基线
VALID_VALUATION_PAYLOAD: dict[str, Any] = {
    "productType": "STOCK",
    "productCode": "600519",
    "valuationDate": "2024-03-31",
    "unitPrice": "1234.5",
}


def buildTransactionPayload(**overrides: Any) -> dict[str, Any]:
    """在合法基线上覆盖指定字段，构造单点异常的交易入参。"""
    payload = dict(VALID_TRANSACTION_PAYLOAD)
    payload.update(overrides)
    return payload


def buildValuationPayload(**overrides: Any) -> dict[str, Any]:
    """在合法基线上覆盖指定字段，构造单点异常的估值入参。"""
    payload = dict(VALID_VALUATION_PAYLOAD)
    payload.update(overrides)
    return payload


def collectFieldErrors(error: ValidationError) -> dict[str, list[str]]:
    """把 ``ValidationError`` 折叠为「字段名 → 错误类型列表」。

    :param error: Pydantic 抛出的校验异常。
    :returns: 键为 camelCase 字段名（模型级校验器的错误归入 ``__model__``），
        值为该字段上出现的错误类型（自定义校验器为 ``ERROR_CODE_*``）。
    """
    fieldErrors: dict[str, list[str]] = {}
    for item in error.errors():
        location = item["loc"]
        fieldName = str(location[0]) if location else "__model__"
        fieldErrors.setdefault(fieldName, []).append(item["type"])
    return fieldErrors


def collectFieldMessages(error: ValidationError) -> dict[str, list[str]]:
    """把 ``ValidationError`` 折叠为「字段名 → 提示语列表」，用于断言中文原因。"""
    fieldMessages: dict[str, list[str]] = {}
    for item in error.errors():
        location = item["loc"]
        fieldName = str(location[0]) if location else "__model__"
        fieldMessages.setdefault(fieldName, []).append(item["msg"])
    return fieldMessages


class TestEnumRejection:
    """枚举字段只接受英文码，中文字面量与小写码一律拒绝（需求 1.1、1.2、3.2）。"""

    @pytest.mark.parametrize(
        "illegalProductType",
        ["理财", "基金", "股票", "wealth", "Fund", "STOCKS", ""],
    )
    def testIllegalProductTypeIsLocatedOnProductTypeField(
        self, illegalProductType: str
    ) -> None:
        """非法产品类型只在 ``productType`` 上报错，其余字段不受牵连。"""
        with pytest.raises(ValidationError) as caught:
            TransactionCreate(**buildTransactionPayload(productType=illegalProductType))

        fieldErrors = collectFieldErrors(caught.value)
        assert list(fieldErrors) == ["productType"]
        assert fieldErrors["productType"] == ["enum"]

    @pytest.mark.parametrize("illegalDirection", ["买入", "卖出", "buy", "Sell"])
    def testIllegalDirectionIsLocatedOnDirectionField(
        self, illegalDirection: str
    ) -> None:
        """非法交易方向只在 ``direction`` 上报错。"""
        with pytest.raises(ValidationError) as caught:
            TransactionCreate(**buildTransactionPayload(direction=illegalDirection))

        fieldErrors = collectFieldErrors(caught.value)
        assert list(fieldErrors) == ["direction"]
        assert fieldErrors["direction"] == ["enum"]

    def testMultipleIllegalEnumsAreReportedPerField(self) -> None:
        """两个枚举同时非法时，两条错误分别定位到各自字段。"""
        with pytest.raises(ValidationError) as caught:
            TransactionCreate(
                **buildTransactionPayload(productType="理财", direction="买入")
            )

        fieldErrors = collectFieldErrors(caught.value)
        assert set(fieldErrors) == {"productType", "direction"}

    @pytest.mark.parametrize("illegalProductType", ["理财", "stock"])
    def testValuationIllegalProductTypeIsLocatedOnProductTypeField(
        self, illegalProductType: str
    ) -> None:
        """估值入参的产品类型同样只接受英文码（需求 3.2）。"""
        with pytest.raises(ValidationError) as caught:
            ValuationUpsert(**buildValuationPayload(productType=illegalProductType))

        assert list(collectFieldErrors(caught.value)) == ["productType"]


class TestTextLengthBoundaries:
    """文本长度边界：名称 1..100、代码 1..32、搜索值 1..100（需求 1.2、2.20、3.2）。"""

    @pytest.mark.parametrize("nameLength", [1, MAX_PRODUCT_NAME_LENGTH])
    def testProductNameAtInclusiveBoundsIsAccepted(self, nameLength: int) -> None:
        """产品名称长度 1 与 100 均合法。"""
        model = TransactionCreate(
            **buildTransactionPayload(productName="名" * nameLength)
        )
        assert len(model.product_name) == nameLength

    @pytest.mark.parametrize(
        ("nameLength", "expectedType"),
        [(0, "string_too_short"), (MAX_PRODUCT_NAME_LENGTH + 1, "string_too_long")],
    )
    def testProductNameOutOfBoundsIsLocatedOnProductNameField(
        self, nameLength: int, expectedType: str
    ) -> None:
        """产品名称长度 0 与 101 被拒绝，错误定位到 ``productName``。"""
        with pytest.raises(ValidationError) as caught:
            TransactionCreate(**buildTransactionPayload(productName="名" * nameLength))

        fieldErrors = collectFieldErrors(caught.value)
        assert list(fieldErrors) == ["productName"]
        assert fieldErrors["productName"] == [expectedType]

    @pytest.mark.parametrize("codeLength", [1, MAX_PRODUCT_CODE_LENGTH])
    def testProductCodeAtInclusiveBoundsIsAccepted(self, codeLength: int) -> None:
        """产品代码长度 1 与 32 均合法。"""
        model = TransactionCreate(
            **buildTransactionPayload(productCode="C" * codeLength)
        )
        assert len(model.product_code) == codeLength

    @pytest.mark.parametrize(
        ("codeLength", "expectedType"),
        [(0, "string_too_short"), (MAX_PRODUCT_CODE_LENGTH + 1, "string_too_long")],
    )
    def testProductCodeOutOfBoundsIsLocatedOnProductCodeField(
        self, codeLength: int, expectedType: str
    ) -> None:
        """产品代码长度 0 与 33 被拒绝，错误定位到 ``productCode``。"""
        with pytest.raises(ValidationError) as caught:
            TransactionCreate(**buildTransactionPayload(productCode="C" * codeLength))

        fieldErrors = collectFieldErrors(caught.value)
        assert list(fieldErrors) == ["productCode"]
        assert fieldErrors["productCode"] == [expectedType]

    def testValuationProductCodeUpperBoundIsEnforced(self) -> None:
        """估值入参的产品代码同样限长 32（需求 3.2）。"""
        ValuationUpsert(
            **buildValuationPayload(productCode="C" * MAX_PRODUCT_CODE_LENGTH)
        )

        with pytest.raises(ValidationError) as caught:
            ValuationUpsert(
                **buildValuationPayload(
                    productCode="C" * (MAX_PRODUCT_CODE_LENGTH + 1)
                )
            )

        assert list(collectFieldErrors(caught.value)) == ["productCode"]

    @pytest.mark.parametrize("searchLength", [1, MAX_SEARCH_VALUE_LENGTH])
    def testSearchValueAtInclusiveBoundsIsAccepted(self, searchLength: int) -> None:
        """搜索值长度 1 与 100 均合法（需求 2.20）。"""
        query = TransactionQuery(productName="值" * searchLength)
        assert query.product_name is not None
        assert len(query.product_name) == searchLength

    @pytest.mark.parametrize(
        ("searchLength", "expectedType"),
        [(0, "string_too_short"), (MAX_SEARCH_VALUE_LENGTH + 1, "string_too_long")],
    )
    def testSearchValueOutOfBoundsIsLocatedOnSearchField(
        self, searchLength: int, expectedType: str
    ) -> None:
        """搜索值长度 0 与 101 被拒绝，错误定位到 ``productCode``（需求 2.20）。"""
        with pytest.raises(ValidationError) as caught:
            TransactionQuery(productCode="值" * searchLength)

        fieldErrors = collectFieldErrors(caught.value)
        assert list(fieldErrors) == ["productCode"]
        assert fieldErrors["productCode"] == [expectedType]


class TestUnitPriceScale:
    """单价小数位：交易单价恰 2 位、估值单价 ≤ 2 位（需求 1.2、3.2）。"""

    def testTwoDecimalPlacesTradePriceIsAccepted(self) -> None:
        """交易单价恰两位小数合法，且以 ``Decimal`` 精确承载。"""
        model = TransactionCreate(**buildTransactionPayload(unitPrice="12.30"))
        assert model.unit_price == Decimal("12.30")
        assert str(model.unit_price) == "12.30"

    @pytest.mark.parametrize("illegalPrice", ["10", "10.5", "10.123", "0.001"])
    def testNonTwoDecimalPlacesTradePriceIsRejectedWithScaleCode(
        self, illegalPrice: str
    ) -> None:
        """交易单价 0 位、1 位、3 位小数一律以 ``INVALID_SCALE`` 拒绝。"""
        with pytest.raises(ValidationError) as caught:
            TransactionCreate(**buildTransactionPayload(unitPrice=illegalPrice))

        fieldErrors = collectFieldErrors(caught.value)
        assert list(fieldErrors) == ["unitPrice"]
        assert fieldErrors["unitPrice"] == [ERROR_CODE_INVALID_SCALE]

    @pytest.mark.parametrize("nonPositivePrice", ["0.00", "-1.00"])
    def testNonPositiveTradePriceIsRejectedWithRangeCode(
        self, nonPositivePrice: str
    ) -> None:
        """交易单价必须 > 0，非正数以 ``OUT_OF_RANGE`` 拒绝并给出中文原因。"""
        with pytest.raises(ValidationError) as caught:
            TransactionCreate(**buildTransactionPayload(unitPrice=nonPositivePrice))

        fieldErrors = collectFieldErrors(caught.value)
        assert list(fieldErrors) == ["unitPrice"]
        assert fieldErrors["unitPrice"] == [ERROR_CODE_OUT_OF_RANGE]
        assert "交易单价必须大于 0" in collectFieldMessages(caught.value)["unitPrice"][0]

    @pytest.mark.parametrize("validPrice", ["0", "0.0", "1234.5", "999999999.99"])
    def testValuationPriceWithAtMostTwoDecimalPlacesIsAccepted(
        self, validPrice: str
    ) -> None:
        """估值单价允许 0..2 位小数，且下界 0 与上界 999999999.99 均合法。"""
        model = ValuationUpsert(**buildValuationPayload(unitPrice=validPrice))
        assert model.unit_price == Decimal(validPrice)

    @pytest.mark.parametrize("illegalPrice", ["1.234", "0.001"])
    def testValuationPriceWithThreeDecimalPlacesIsRejected(
        self, illegalPrice: str
    ) -> None:
        """估值单价三位小数以 ``INVALID_SCALE`` 拒绝，错误定位到 ``unitPrice``。"""
        with pytest.raises(ValidationError) as caught:
            ValuationUpsert(**buildValuationPayload(unitPrice=illegalPrice))

        fieldErrors = collectFieldErrors(caught.value)
        assert list(fieldErrors) == ["unitPrice"]
        assert fieldErrors["unitPrice"] == [ERROR_CODE_INVALID_SCALE]

    @pytest.mark.parametrize("illegalPrice", ["-0.01", "1000000000.00"])
    def testValuationPriceOutOfClosedIntervalIsRejected(
        self, illegalPrice: str
    ) -> None:
        """估值单价越出 0..999999999.99 闭区间以 ``OUT_OF_RANGE`` 拒绝（需求 3.2）。"""
        with pytest.raises(ValidationError) as caught:
            ValuationUpsert(**buildValuationPayload(unitPrice=illegalPrice))

        fieldErrors = collectFieldErrors(caught.value)
        assert list(fieldErrors) == ["unitPrice"]
        assert fieldErrors["unitPrice"] == [ERROR_CODE_OUT_OF_RANGE]


class TestCalendarDate:
    """日期必须是有效公历日期（需求 1.2、2.21、3.2）。"""

    @pytest.mark.parametrize(
        "illegalDate", ["2024-02-30", "2023-02-29", "2024-13-01", "2024-04-31"]
    )
    def testIllegalCalendarTradeDateIsLocatedOnTradeDateField(
        self, illegalDate: str
    ) -> None:
        """2 月 30 日等非法日历日期在解析阶段失败，错误定位到 ``tradeDate``。"""
        with pytest.raises(ValidationError) as caught:
            TransactionCreate(**buildTransactionPayload(tradeDate=illegalDate))

        assert list(collectFieldErrors(caught.value)) == ["tradeDate"]

    def testIllegalCalendarQueryDateIsLocatedOnStartDateField(self) -> None:
        """查询范围中的 2 月 30 日被拒绝，错误定位到 ``startDate``（需求 2.21）。"""
        with pytest.raises(ValidationError) as caught:
            TransactionQuery(startDate="2024-02-30", endDate="2024-03-01")

        assert list(collectFieldErrors(caught.value)) == ["startDate"]

    def testLeapDayIsAccepted(self) -> None:
        """闰年 2 月 29 日是有效日期，必须接受。"""
        model = TransactionCreate(**buildTransactionPayload(tradeDate="2024-02-29"))
        assert model.trade_date == date(2024, 2, 29)

    def testIllegalCalendarValuationDateIsLocatedOnValuationDateField(self) -> None:
        """估值日期同样拒绝非法日历日期（需求 3.2）。"""
        with pytest.raises(ValidationError) as caught:
            ValuationUpsert(**buildValuationPayload(valuationDate="2024-02-30"))

        assert list(collectFieldErrors(caught.value)) == ["valuationDate"]


class TestDateRange:
    """交易日期范围必须成对出现且起始不晚于结束（需求 2.21）。"""

    @staticmethod
    def collectTranslatedFields(error: ValidationError) -> list[str]:
        """经既有统一错误翻译器取得模型级错误最终对应的具体表单字段。"""
        from app.investmentLedger.exceptions import translateValidationErrors

        return [item.field for item in translateValidationErrors(error.errors())]

    def testEqualStartAndEndIsAccepted(self) -> None:
        """起止同一天是合法的闭区间。"""
        query = TransactionQuery(startDate="2024-01-02", endDate="2024-01-02")
        assert query.start_date == query.end_date == date(2024, 1, 2)

    def testStartLaterThanEndIsRejectedWithRangeCode(self) -> None:
        """``start > end`` 以 ``OUT_OF_RANGE`` 拒绝并定位到 ``startDate``。"""
        with pytest.raises(ValidationError) as caught:
            TransactionQuery(startDate="2024-02-01", endDate="2024-01-31")

        errorItems = caught.value.errors()
        assert len(errorItems) == 1
        assert errorItems[0]["type"] == ERROR_CODE_OUT_OF_RANGE
        assert "起始日期不能晚于结束日期" in errorItems[0]["msg"]
        assert self.collectTranslatedFields(caught.value) == ["startDate"]

    @pytest.mark.parametrize(
        "partialRange",
        [{"startDate": "2024-01-02"}, {"endDate": "2024-01-02"}],
    )
    def testPartialDateRangeIsRejected(self, partialRange: dict[str, Any]) -> None:
        """只给起始或结束日期被拒绝，并定位到 ``startDate`` 日期范围控件。"""
        with pytest.raises(ValidationError) as caught:
            TransactionQuery(**partialRange)

        errorItems = caught.value.errors()
        assert len(errorItems) == 1
        assert errorItems[0]["type"] == ERROR_CODE_OUT_OF_RANGE
        assert "同时提供起始日期与结束日期" in errorItems[0]["msg"]
        assert self.collectTranslatedFields(caught.value) == ["startDate"]


class TestPageBoundaries:
    """页码与页大小边界（需求 2.25、2.26、2.30）。"""

    @pytest.mark.parametrize("pageSize", [MIN_PAGE_SIZE, 10, 20, 50, MAX_PAGE_SIZE])
    def testPageSizeInsideClosedIntervalIsAccepted(self, pageSize: int) -> None:
        """页大小 1 与 100 及预设选项均合法。"""
        query = TransactionQuery(pageSize=pageSize)
        assert query.page_size == pageSize

    @pytest.mark.parametrize(
        ("pageSize", "expectedType"),
        [
            (0, "greater_than_equal"),
            (-1, "greater_than_equal"),
            (MAX_PAGE_SIZE + 1, "less_than_equal"),
        ],
    )
    def testPageSizeOutsideClosedIntervalIsLocatedOnPageSizeField(
        self, pageSize: int, expectedType: str
    ) -> None:
        """页大小 0 与 101 被拒绝，错误定位到 ``pageSize``（需求 2.26）。"""
        with pytest.raises(ValidationError) as caught:
            TransactionQuery(pageSize=pageSize)

        fieldErrors = collectFieldErrors(caught.value)
        assert list(fieldErrors) == ["pageSize"]
        assert fieldErrors["pageSize"] == [expectedType]

    @pytest.mark.parametrize("page", [0, -3])
    def testNonPositivePageIsLocatedOnPageField(self, page: int) -> None:
        """页码必须 >= 1，非正页码错误定位到 ``page``（需求 2.30）。"""
        with pytest.raises(ValidationError) as caught:
            TransactionQuery(page=page)

        fieldErrors = collectFieldErrors(caught.value)
        assert list(fieldErrors) == ["page"]
        assert fieldErrors["page"] == ["greater_than_equal"]

    def testDefaultQueryUsesModulePresetPageSize(self) -> None:
        """未指定分页参数时取默认页码 1 与模块预设页大小。"""
        query = TransactionQuery()
        assert query.page == 1
        assert query.page_size == 20
