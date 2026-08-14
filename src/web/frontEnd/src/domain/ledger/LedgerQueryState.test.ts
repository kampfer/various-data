// Feature: investment-trade-ledger, Property 2: 浏览状态转换遵守重置不变量
// 断言浏览状态值对象的三条重置不变量（模块导航重置、持仓入口重置并附加范围、条件变更页码归 1）。
import fc from 'fast-check';
import { describe, expect, it } from 'vitest';
import LedgerQueryState from './LedgerQueryState';
import type { LedgerQuerySnapshot, ProductScope } from './LedgerQueryState';
import {
  MAX_PAGE_SIZE,
  MIN_PAGE_SIZE,
  PRODUCT_TYPES,
  TRADE_DIRECTIONS,
  type LedgerModule,
} from './constants';

/** 两个界面模块（需求 2.1、2.13） */
const MODULES: readonly LedgerModule[] = ['history', 'holdings'];

/** 产品范围字段：只应由「持仓条目入口」注入，不参与默认状态比较（需求 2.9） */
const SCOPE_KEYS = ['scopeProductType', 'scopeProductCode'] as const;

/** 需求 2.27 列举的「可变更条件」字段：改动其中任一项都必须把页码重置为 1 */
const CONDITION_KEYS = [
  'productType',
  'direction',
  'startDate',
  'endDate',
  'productName',
  'productCode',
  'tradeDateOrder',
  'holdingSortField',
  'holdingSortOrder',
] as const;

/** 可选值生成器：null 代表该条件未启用 */
const optional = <T>(arb: fc.Arbitrary<T>): fc.Arbitrary<T | null> => fc.option(arb, { nil: null });

/** YYYY-MM-DD 形式的有效日历日期 */
const dateArb = fc
  .date({ min: new Date('2000-01-01T00:00:00Z'), max: new Date('2030-12-31T00:00:00Z') })
  .map((d) => d.toISOString().slice(0, 10));

/** 搜索值：覆盖中文、emoji 与长度边界 1..100（需求 2.17、2.18、2.20） */
const searchArb = fc.oneof(
  fc.string({ minLength: 1, maxLength: 100 }),
  fc.constantFrom('招银', '沪深300ETF', '🚀基金', 'a'.repeat(100)),
);

/** 产品代码：长度 1..32（需求 2.9、2.10） */
const productCodeArb = fc.oneof(
  fc.string({ minLength: 1, maxLength: 32 }),
  fc.constantFrom('510300', 'A'.repeat(32), '沪深300'),
);

/** 任意「已应用的浏览状态」快照：条件任意启用、页大小 1..100、页码为任意有效值 */
const snapshotArb: fc.Arbitrary<LedgerQuerySnapshot> = fc.record({
  productType: optional(fc.constantFrom(...PRODUCT_TYPES)),
  direction: optional(fc.constantFrom(...TRADE_DIRECTIONS)),
  startDate: optional(dateArb),
  endDate: optional(dateArb),
  productName: optional(searchArb),
  productCode: optional(searchArb),
  tradeDateOrder: optional(fc.constantFrom('asc' as const, 'desc' as const)),
  holdingSortField: optional(fc.constantFrom('position' as const, 'totalProfit' as const)),
  holdingSortOrder: optional(fc.constantFrom('asc' as const, 'desc' as const)),
  page: fc.integer({ min: 1, max: 500 }),
  pageSize: fc.integer({ min: MIN_PAGE_SIZE, max: MAX_PAGE_SIZE }),
  scopeProductType: optional(fc.constantFrom(...PRODUCT_TYPES)),
  scopeProductCode: optional(productCodeArb),
});

/** 持仓条目产品键 */
const scopeArb: fc.Arbitrary<ProductScope> = fc.record({
  productType: fc.constantFrom(...PRODUCT_TYPES),
  productCode: productCodeArb,
});

/** 非空的条件变更补丁：至少改动 CONDITION_KEYS 中的一个字段（需求 2.27） */
const conditionPatchArb = fc
  .uniqueArray(fc.constantFrom(...CONDITION_KEYS), { minLength: 1, maxLength: CONDITION_KEYS.length })
  .chain((keys) =>
    fc.tuple(...keys.map((key) => conditionValueArb(key))).map((values) => {
      const patch: Partial<LedgerQuerySnapshot> = {};
      keys.forEach((key, index) => {
        Object.assign(patch, { [key]: values[index] });
      });
      return patch;
    }),
  );

/** 按字段生成合法的条件取值（含 null，代表「取消该条件」也属于一次变更） */
function conditionValueArb(key: typeof CONDITION_KEYS[number]): fc.Arbitrary<unknown> {
  switch (key) {
    case 'productType':
      return optional(fc.constantFrom(...PRODUCT_TYPES));
    case 'direction':
      return optional(fc.constantFrom(...TRADE_DIRECTIONS));
    case 'startDate':
    case 'endDate':
      return optional(dateArb);
    case 'productName':
    case 'productCode':
      return optional(searchArb);
    case 'holdingSortField':
      return optional(fc.constantFrom('position' as const, 'totalProfit' as const));
    default:
      return optional(fc.constantFrom('asc' as const, 'desc' as const));
  }
}

/** 断言 actual 除 scope 两字段外与目标模块默认浏览状态逐字段相等 */
function expectDefaultExceptScope(actual: LedgerQuerySnapshot, module: LedgerModule): void {
  const expected = LedgerQueryState.default(module).toSnapshot();
  (Object.keys(expected) as (keyof LedgerQuerySnapshot)[])
    .filter((key) => !SCOPE_KEYS.includes(key as typeof SCOPE_KEYS[number]))
    .forEach((key) => {
      expect(actual[key]).toEqual(expected[key]);
    });
}

describe('Property 2: 浏览状态转换遵守重置不变量', () => {
  it('模块间导航后目标模块的浏览状态等于该模块的默认浏览状态', () => {
    fc.assert(
      fc.property(snapshotArb, fc.constantFrom(...MODULES), (snapshot, target) => {
        const applied = LedgerQueryState.from(snapshot);
        // 模块导航语义：丢弃全部已应用条件，重新构造目标模块的默认浏览状态（需求 2.13）
        const navigated = LedgerQueryState.default(target);

        expect(navigated.isDefault(target)).toBe(true);
        expectDefaultExceptScope(navigated.toSnapshot(), target);
        // 导航后不携带任何产品历史交易范围
        expect(navigated.toSnapshot().scopeProductType).toBeNull();
        expect(navigated.toSnapshot().scopeProductCode).toBeNull();
        // 原状态未被改变（值对象不可变）
        expect(applied.toSnapshot()).toEqual(snapshot);
      }),
      { numRuns: 100 },
    );
  });

  it('从持仓条目进入历史交易记录模块后等于默认浏览状态且仅附加该条目的产品历史交易范围', () => {
    fc.assert(
      fc.property(snapshotArb, scopeArb, (snapshot, scope) => {
        const applied = LedgerQueryState.from(snapshot);
        const scoped = LedgerQueryState.defaultWithScope('history', scope);
        const result = scoped.toSnapshot();

        expect(scoped.isDefault('history')).toBe(true);
        expectDefaultExceptScope(result, 'history');
        // 仅附加范围：scope 两字段恰为该持仓条目的产品键
        expect(result.scopeProductType).toBe(scope.productType);
        expect(result.scopeProductCode).toBe(scope.productCode);
        // 范围会随请求下发，其余未启用条件仍被省略
        const params = scoped.toParams();
        expect(params.scopeProductType).toBe(scope.productType);
        expect(params.scopeProductCode).toBe(scope.productCode);
        expect(params.productType).toBeUndefined();
        expect(params.tradeDateOrder).toBeUndefined();
        expect(applied.toSnapshot()).toEqual(snapshot);
      }),
      { numRuns: 100 },
    );
  });

  it('更改任一筛选条件、搜索条件或排序后页码恒等于 1，其余字段仅按补丁变化', () => {
    fc.assert(
      fc.property(snapshotArb, conditionPatchArb, (snapshot, patch) => {
        const applied = LedgerQueryState.from(snapshot);
        const next = applied.withFilters(patch).toSnapshot();

        expect(next.page).toBe(1);
        // 补丁字段取补丁值，其它字段（含 pageSize 与范围）保持原值
        (Object.keys(snapshot) as (keyof LedgerQuerySnapshot)[])
          .filter((key) => key !== 'page')
          .forEach((key) => {
            const expected = key in patch ? patch[key] : snapshot[key];
            expect(next[key]).toEqual(expected);
          });
        expect(applied.toSnapshot()).toEqual(snapshot);
      }),
      { numRuns: 100 },
    );
  });

  it('更改页大小后页码恒等于 1，且其余字段保持不变', () => {
    fc.assert(
      fc.property(
        snapshotArb,
        fc.integer({ min: MIN_PAGE_SIZE, max: MAX_PAGE_SIZE }),
        (snapshot, size) => {
          const applied = LedgerQueryState.from(snapshot);
          const next = applied.withPageSize(size).toSnapshot();

          expect(next.page).toBe(1);
          expect(next.pageSize).toBe(size);
          (Object.keys(snapshot) as (keyof LedgerQuerySnapshot)[])
            .filter((key) => key !== 'page' && key !== 'pageSize')
            .forEach((key) => {
              expect(next[key]).toEqual(snapshot[key]);
            });
          expect(applied.toSnapshot()).toEqual(snapshot);
        },
      ),
      { numRuns: 100 },
    );
  });

  it('仅翻页不改变任何条件字段（重置不变量不误伤纯翻页）', () => {
    fc.assert(
      fc.property(snapshotArb, fc.integer({ min: 1, max: 500 }), (snapshot, page) => {
        const applied = LedgerQueryState.from(snapshot);
        const next = applied.withPage(page).toSnapshot();

        expect(next.page).toBe(page);
        (Object.keys(snapshot) as (keyof LedgerQuerySnapshot)[])
          .filter((key) => key !== 'page')
          .forEach((key) => {
            expect(next[key]).toEqual(snapshot[key]);
          });
        expect(applied.toSnapshot()).toEqual(snapshot);
      }),
      { numRuns: 100 },
    );
  });
});
