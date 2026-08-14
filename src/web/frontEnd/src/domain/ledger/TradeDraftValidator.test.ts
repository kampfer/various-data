// Feature: investment-trade-ledger, Property 1: 交易草稿校验拒绝无效输入并保留原值
// 对任意「至少含一个无效字段」的交易草稿，断言：校验拒绝、每个无效字段恰好一条中文错误原因、草稿字段值不被改写。
// Validates: Requirements 1.2
import fc from 'fast-check';
import { describe, expect, it } from 'vitest';
import TradeDraftValidator, { TRADE_ERROR_CODES } from './TradeDraftValidator';
import type { TradeDraftLike } from './TradeDraftValidator';
import { PRODUCT_TYPES, TRADE_DIRECTIONS } from './constants';

/** 交易草稿的全部字段名，与 TradeDraft / 表单项一一对应（需求 1.1） */
const DRAFT_FIELDS = [
  'productType',
  'productName',
  'productCode',
  'unitPrice',
  'quantity',
  'direction',
  'tradeDate',
] as const;

/** 字段名联合类型 */
type DraftField = typeof DRAFT_FIELDS[number];

/** 单字段生成结果：value 为草稿取值，invalid 标记该取值按需求 1.2 是否无效 */
interface FieldCase<T> {
  readonly value: T;
  readonly invalid: boolean;
}

/** 本校验器可能产出的错误码全集，用于断言错误码不漂移 */
const ERROR_CODE_VALUES: readonly string[] = Object.values(TRADE_ERROR_CODES);

/** 至少含一个中日韩汉字，确保原因是面向用户的中文文案（labels.ts 为文案唯一来源） */
const CHINESE_PATTERN = /[\u4e00-\u9fa5]/;

/** 文本字符池：混入 ASCII、中文与 emoji，验证长度以码点计数而非 UTF-16 单元 */
const CHAR_POOL = ['a', 'Z', '3', '招', '银', '🚀', '-'] as const;

/** 生成码点长度恰为 length 的文本（length=0 时为空串） */
const textOfLength = (length: number): fc.Arbitrary<string> =>
  fc
    .array(fc.constantFrom(...CHAR_POOL), { minLength: length, maxLength: length })
    .map((chars) => chars.join(''));

/** 把「有效取值生成器」与「无效取值生成器」合成带标记的字段生成器；无效侧加权，提升命中前提的概率 */
const fieldCase = <T>(valid: fc.Arbitrary<T>, invalid: fc.Arbitrary<T>): fc.Arbitrary<FieldCase<T>> =>
  fc.oneof(
    { arbitrary: valid.map((value) => ({ value, invalid: false })), weight: 2 },
    { arbitrary: invalid.map((value) => ({ value, invalid: true })), weight: 3 },
  );

/** 有效产品类型：码全集内的英文码 */
const validProductTypeArb: fc.Arbitrary<string | null> = fc.constantFrom<string>(...PRODUCT_TYPES);

/** 无效产品类型：中文字面量、大小写不符的码、越集码、空串与 null（任务 10.5 要求覆盖） */
const invalidProductTypeArb: fc.Arbitrary<string | null> = fc.constantFrom<string | null>(
  '理财',
  '基金',
  '股票',
  'wealth',
  'Fund',
  'stock',
  'BOND',
  '',
  ' WEALTH',
  null,
);

/** 有效交易方向 */
const validDirectionArb: fc.Arbitrary<string | null> = fc.constantFrom<string>(...TRADE_DIRECTIONS);

/** 无效交易方向：中文字面量、大小写不符的码、空串与 null */
const invalidDirectionArb: fc.Arbitrary<string | null> = fc.constantFrom<string | null>(
  '买入',
  '卖出',
  'buy',
  'Sell',
  'BUYS',
  '',
  null,
);

/** 有效产品名称：长度取 1 / 100 两个边界与中间随机长度 */
const validProductNameArb: fc.Arbitrary<string | null> = fc
  .oneof(fc.constant(1), fc.constant(100), fc.integer({ min: 2, max: 99 }))
  .chain(textOfLength);

/** 无效产品名称：长度 0（空）与 101（超上界），另含 null */
const invalidProductNameArb: fc.Arbitrary<string | null> = fc.oneof(
  fc.constantFrom(0, 101).chain(textOfLength),
  fc.constant(null),
);

/** 有效产品代码：长度取 1 / 32 两个边界与中间随机长度 */
const validProductCodeArb: fc.Arbitrary<string | null> = fc
  .oneof(fc.constant(1), fc.constant(32), fc.integer({ min: 2, max: 31 }))
  .chain(textOfLength);

/** 无效产品代码：长度 0（空）与 33（超上界），另含 null */
const invalidProductCodeArb: fc.Arbitrary<string | null> = fc.oneof(
  fc.constantFrom(0, 33).chain(textOfLength),
  fc.constant(null),
);

/** 有效交易单价：> 0 且小数位恰为 2 位，含下界 0.01 与上界量级 */
const validUnitPriceArb: fc.Arbitrary<string | number | null> = fc.oneof(
  fc.constantFrom('0.01', '1.00', '12.34', '999999999.99'),
  fc
    .tuple(fc.integer({ min: 0, max: 999999 }), fc.integer({ min: 0, max: 99 }))
    .map(([integerPart, fraction]) => `${integerPart}.${String(fraction).padStart(2, '0')}`)
    .filter((text) => text !== '0.00'),
);

/** 无效交易单价：0.00、三位小数、少于两位小数、负数、非数字、空与 null（任务 10.5 要求覆盖） */
const invalidUnitPriceArb: fc.Arbitrary<string | number | null> = fc.constantFrom<string | number | null>(
  '0.00',
  '0',
  '1.0',
  '1.234',
  '0.001',
  '-1.00',
  '-0.01',
  'abc',
  '1.2.3',
  '',
  null,
);

/** 有效交易数量：> 0 的整数，允许 number 与十进制字符串两种承载形式 */
const validQuantityArb: fc.Arbitrary<string | number | null> = fc.oneof(
  fc.integer({ min: 1, max: 1_000_000 }),
  fc.integer({ min: 1, max: 1_000_000 }).map((value) => String(value)),
);

/** 无效交易数量：0、负数、小数、非数字、空与 null */
const invalidQuantityArb: fc.Arbitrary<string | number | null> = fc.constantFrom<string | number | null>(
  0,
  -1,
  1.5,
  '0',
  '-3',
  '1.5',
  'abc',
  '',
  null,
);

/** 有效交易日期：YYYY-MM-DD 的有效公历日期（含闰日） */
const validTradeDateArb: fc.Arbitrary<string | null> = fc.oneof(
  fc.constantFrom('2024-02-29', '2000-02-29', '2023-12-31', '1999-01-01'),
  fc
    .date({ min: new Date('1990-01-01T00:00:00Z'), max: new Date('2035-12-31T00:00:00Z') })
    .map((date) => date.toISOString().slice(0, 10)),
);

/** 无效交易日期：非法日历日、非法月日、格式不合规、空与 null */
const invalidTradeDateArb: fc.Arbitrary<string | null> = fc.constantFrom<string | null>(
  '2024-02-30',
  '2023-02-29',
  '2024-13-01',
  '2024-00-10',
  '2024-04-31',
  '2024-1-01',
  '2024/01/01',
  'not-a-date',
  '',
  null,
);

/** 各字段的带标记生成器集合 */
const draftCasesArb = fc.record({
  productType: fieldCase(validProductTypeArb, invalidProductTypeArb),
  productName: fieldCase(validProductNameArb, invalidProductNameArb),
  productCode: fieldCase(validProductCodeArb, invalidProductCodeArb),
  unitPrice: fieldCase(validUnitPriceArb, invalidUnitPriceArb),
  quantity: fieldCase(validQuantityArb, invalidQuantityArb),
  direction: fieldCase(validDirectionArb, invalidDirectionArb),
  tradeDate: fieldCase(validTradeDateArb, invalidTradeDateArb),
});

/** 前提：草稿至少含一个无效字段（属性只约束无效草稿） */
const invalidDraftCasesArb = draftCasesArb.filter((cases) =>
  DRAFT_FIELDS.some((field) => cases[field].invalid),
);

describe('Property 1: 交易草稿校验拒绝无效输入并保留原值', () => {
  it('对任意至少含一个无效字段的草稿：拒绝创建、每个无效字段一条中文原因、字段值保持不变', () => {
    fc.assert(
      fc.property(invalidDraftCasesArb, (cases) => {
        const draft: TradeDraftLike = {
          productType: cases.productType.value,
          productName: cases.productName.value,
          productCode: cases.productCode.value,
          unitPrice: cases.unitPrice.value,
          quantity: cases.quantity.value,
          direction: cases.direction.value,
          tradeDate: cases.tradeDate.value,
        };
        // 校验前的字段快照：用于断言「保留已提交的值以供更正」
        const before = { ...draft };
        const expectedInvalidFields = DRAFT_FIELDS.filter((field) => cases[field].invalid);

        const result = new TradeDraftValidator().validate(draft);

        // 1) 拒绝创建
        expect(result.valid).toBe(false);
        // 2) 无效字段与错误项一一对应：每个无效字段恰好一条，有效字段一条都没有
        const errorFields = result.fieldErrors.map((error) => error.field);
        expect([...errorFields].sort()).toEqual([...expectedInvalidFields].sort());
        expect(new Set(errorFields).size).toBe(errorFields.length);
        // 每条错误都带已定义的错误码与中文原因
        result.fieldErrors.forEach((error) => {
          expect(ERROR_CODE_VALUES).toContain(error.code);
          expect(error.message.length).toBeGreaterThan(0);
          expect(CHINESE_PATTERN.test(error.message)).toBe(true);
        });
        // 3) 草稿所有字段值保持不变（键集合与逐字段取值均不变）
        expect(Object.keys(draft).sort()).toEqual(Object.keys(before).sort());
        DRAFT_FIELDS.forEach((field) => {
          expect(draft[field]).toEqual(before[field]);
        });
      }),
      { numRuns: 100 },
    );
  });
});
