// Feature: investment-trade-ledger, Property 10: 估值草稿校验拒绝无效输入并保留原值
// Validates: Requirements 3.2
import fc from 'fast-check';
import { describe, expect, it } from 'vitest';
import { PRODUCT_TYPES } from './constants';
import { TRADE_ERROR_CODES } from './TradeDraftValidator';
import ValuationDraftValidator from './ValuationDraftValidator';
import type { ValuationDraftLike } from './ValuationDraftValidator';

const DRAFT_FIELDS = ['productType', 'productCode', 'valuationDate', 'unitPrice'] as const;
type DraftField = typeof DRAFT_FIELDS[number];

interface FieldCase<T> {
  readonly value: T;
  readonly invalid: boolean;
}

interface DraftCases {
  readonly productType: FieldCase<string | null>;
  readonly productCode: FieldCase<string | null>;
  readonly valuationDate: FieldCase<string | null>;
  readonly unitPrice: FieldCase<string | number | null>;
}

const ERROR_CODES: readonly string[] = Object.values(TRADE_ERROR_CODES);
const CHINESE_PATTERN = /[\u4e00-\u9fa5]/;
const CHAR_POOL = ['A', '7', '招', '银', '🚀', '-'] as const;

const textOfLength = (length: number): fc.Arbitrary<string> =>
  fc.array(fc.constantFrom(...CHAR_POOL), { minLength: length, maxLength: length })
    .map((chars) => chars.join(''));

const fieldCase = <T>(
  valid: fc.Arbitrary<T>,
  invalid: fc.Arbitrary<T>,
): fc.Arbitrary<FieldCase<T>> => fc.oneof(
  { arbitrary: valid.map((value) => ({ value, invalid: false })), weight: 2 },
  { arbitrary: invalid.map((value) => ({ value, invalid: true })), weight: 3 },
);

const validProductTypeArb = fc.constantFrom<string>(...PRODUCT_TYPES);
const invalidProductTypeArb = fc.constantFrom<string | null>(
  '理财', '基金', '股票', 'wealth', 'Fund', 'stock', 'BOND', '', null,
);

const validProductCodeArb = fc.oneof(
  fc.constantFrom(1, 32).chain(textOfLength),
  fc.integer({ min: 2, max: 31 }).chain(textOfLength),
);
const invalidProductCodeArb = fc.oneof(
  fc.constantFrom(0, 33).chain(textOfLength),
  fc.constant(null),
);

const validDateArb = fc.oneof(
  fc.constantFrom('2024-02-29', '2000-02-29', '2023-12-31'),
  fc.date({ min: new Date('1990-01-01T00:00:00Z'), max: new Date('2035-12-31T00:00:00Z') })
    .map((date) => date.toISOString().slice(0, 10)),
);
const invalidDateArb = fc.constantFrom<string | null>(
  '2024-02-30', '2023-02-29', '2024-13-01', '2024-04-31',
  '2024-1-01', '2024/01/01', 'not-a-date', '', null,
);

const validUnitPriceArb = fc.oneof(
  fc.constantFrom<string | number>('0', '999999999.99', '0.01', '123456789.9'),
  fc.tuple(fc.integer({ min: 0, max: 999_999_999 }), fc.integer({ min: 0, max: 99 }))
    .map(([integerPart, fraction]) => `${integerPart}.${String(fraction).padStart(2, '0')}`),
);
const invalidUnitPriceArb = fc.constantFrom<string | number | null>(
  '1000000000.00', '1.001', '0.001', '-1', '-0.01', '', null,
);

const draftCasesArb: fc.Arbitrary<DraftCases> = fc.record({
  productType: fieldCase(validProductTypeArb, invalidProductTypeArb),
  productCode: fieldCase(validProductCodeArb, invalidProductCodeArb),
  valuationDate: fieldCase(validDateArb, invalidDateArb),
  unitPrice: fieldCase(validUnitPriceArb, invalidUnitPriceArb),
}).filter((cases) => DRAFT_FIELDS.some((field) => cases[field].invalid));

const valid = <T>(value: T): FieldCase<T> => ({ value, invalid: false });
const invalid = <T>(value: T): FieldCase<T> => ({ value, invalid: true });
const example = (
  productType: FieldCase<string | null>,
  productCode: FieldCase<string | null>,
  valuationDate: FieldCase<string | null>,
  unitPrice: FieldCase<string | number | null>,
): [DraftCases] => [{ productType, productCode, valuationDate, unitPrice }];

const REQUIRED_EXAMPLES: [DraftCases][] = [
  example(invalid('理财'), valid('510300'), valid('2024-02-29'), valid('0')),
  example(valid('FUND'), invalid(''), valid('2024-02-29'), valid('999999999.99')),
  example(valid('STOCK'), valid('AAPL'), invalid('2024-02-30'), valid('1')),
  example(valid('WEALTH'), valid('W001'), valid('2024-01-01'), invalid('1000000000.00')),
  example(valid('FUND'), valid('F001'), valid('2024-01-01'), invalid('1.001')),
  example(valid('STOCK'), valid('600000'), valid('2024-01-01'), invalid('-0.01')),
];

describe('Property 10: 估值草稿校验拒绝无效输入并保留原值', () => {
  it('对任意至少含一个无效字段的草稿，拒绝保存、逐字段提示且不修改原值', () => {
    fc.assert(
      fc.property(draftCasesArb, (cases) => {
        const draft: ValuationDraftLike = {
          productType: cases.productType.value,
          productCode: cases.productCode.value,
          valuationDate: cases.valuationDate.value,
          unitPrice: cases.unitPrice.value,
        };
        const before = { ...draft };
        const expectedInvalidFields = DRAFT_FIELDS.filter((field) => cases[field].invalid);

        const result = new ValuationDraftValidator().validate(draft);

        expect(result.valid).toBe(false);
        const errorFields = result.fieldErrors.map(({ field }) => field);
        expect([...errorFields].sort()).toEqual([...expectedInvalidFields].sort());
        expect(new Set(errorFields).size).toBe(errorFields.length);
        result.fieldErrors.forEach(({ code, message }) => {
          expect(ERROR_CODES).toContain(code);
          expect(message.length).toBeGreaterThan(0);
          expect(CHINESE_PATTERN.test(message)).toBe(true);
        });
        expect(Object.keys(draft).sort()).toEqual(Object.keys(before).sort());
        DRAFT_FIELDS.forEach((field: DraftField) => {
          expect(draft[field]).toEqual(before[field]);
        });
      }),
      { numRuns: 100, examples: REQUIRED_EXAMPLES },
    );
  });
});