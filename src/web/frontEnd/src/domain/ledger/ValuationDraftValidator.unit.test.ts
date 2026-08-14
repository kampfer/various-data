// ValuationDraftValidator 示例单元测试：任务 10.6；属性测试由独立任务 10.7 覆盖。
// Validates: Requirements 3.1, 3.2
import { describe, expect, it } from 'vitest';
import ValuationDraftValidator, { MAX_VALUATION_UNIT_PRICE } from './ValuationDraftValidator';
import { TRADE_ERROR_CODES } from './TradeDraftValidator';
import type { ValuationDraftLike } from './ValuationDraftValidator';

/** 构造其余字段有效的估值草稿，便于只考察一个字段。 */
const validDraft = (unitPrice: string): ValuationDraftLike => ({
  productType: 'WEALTH',
  productCode: 'A'.repeat(32),
  valuationDate: '2024-02-29',
  unitPrice,
});

describe('ValuationDraftValidator', () => {
  it.each(['0', '0.1', '0.12', MAX_VALUATION_UNIT_PRICE])(
    '接受边界内且小数位不超过两位的估值单价 %s',
    (unitPrice) => {
      expect(new ValuationDraftValidator().validate(validDraft(unitPrice))).toEqual({
        valid: true,
        fieldErrors: [],
      });
    },
  );

  it('为每个无效字段返回一条中文原因并保持草稿原值', () => {
    const draft: ValuationDraftLike = {
      productType: '理财',
      productCode: '',
      valuationDate: '2024-02-30',
      unitPrice: '1000000000.00',
    };
    const before = { ...draft };

    const result = new ValuationDraftValidator().validate(draft);

    expect(result.valid).toBe(false);
    expect(result.fieldErrors.map(({ field }) => field)).toEqual([
      'productType',
      'productCode',
      'valuationDate',
      'unitPrice',
    ]);
    expect(new Set(result.fieldErrors.map(({ field }) => field)).size).toBe(4);
    result.fieldErrors.forEach(({ message }) => expect(message).toMatch(/[\u4e00-\u9fa5]/));
    expect(draft).toEqual(before);
  });

  it.each([
    ['-0.01', TRADE_ERROR_CODES.OUT_OF_RANGE],
    ['1000000000.00', TRADE_ERROR_CODES.OUT_OF_RANGE],
    ['1.001', TRADE_ERROR_CODES.INVALID_SCALE],
    ['非数字', TRADE_ERROR_CODES.NOT_A_NUMBER],
  ])('拒绝无效估值单价 %s', (unitPrice, expectedCode) => {
    const result = new ValuationDraftValidator().validate(validDraft(unitPrice));

    expect(result.valid).toBe(false);
    expect(result.fieldErrors).toHaveLength(1);
    expect(result.fieldErrors[0]).toMatchObject({
      field: 'unitPrice',
      code: expectedCode,
    });
  });

  it('产品代码按 Unicode 字符计数，超过 32 个字符时拒绝', () => {
    const draft: ValuationDraftLike = {
      ...validDraft('1'),
      productCode: '🚀'.repeat(33),
    };

    const result = new ValuationDraftValidator().validate(draft);

    expect(result.fieldErrors).toEqual([
      {
        field: 'productCode',
        code: TRADE_ERROR_CODES.TOO_LONG,
        message: '产品代码不能超过 32 个字符',
      },
    ]);
  });
});