// Feature: investment-trade-ledger, Property 7: 无效查询输入不改变已应用的浏览状态与结果
// Validates: Requirements 2.20, 2.21, 2.26, 2.30
import fc from 'fast-check';
import { describe, expect, it } from 'vitest';
import LedgerQueryState from './LedgerQueryState';
import type { LedgerQuerySnapshot } from './LedgerQueryState';
import QueryInputValidator from './QueryInputValidator';
import type { ValidationResult } from './TradeDraftValidator';
import { PRODUCT_TYPES, TRADE_DIRECTIONS } from './constants';

interface BrowsedResult {
  readonly productCode: string;
  readonly productName: string;
  readonly amount: number;
}

type InvalidQueryInput =
  | { readonly kind: 'search'; readonly value: string }
  | { readonly kind: 'dateRange'; readonly start: string | null; readonly end: string | null }
  | { readonly kind: 'pageSize'; readonly value: number }
  | { readonly kind: 'page'; readonly value: number; readonly pageCount: number };

interface Scenario {
  readonly snapshot: LedgerQuerySnapshot;
  readonly results: BrowsedResult[];
  readonly input: InvalidQueryInput;
}

const CHAR_POOL = ['A', '7', '招', '银', '🚀', '-'] as const;
const textOfLength = (length: number): fc.Arbitrary<string> =>
  fc.array(fc.constantFrom(...CHAR_POOL), { minLength: length, maxLength: length })
    .map((chars) => chars.join(''));
const optional = <T>(arb: fc.Arbitrary<T>): fc.Arbitrary<T | null> => fc.option(arb, { nil: null });
const validDateArb = fc.date({
  min: new Date('2000-01-01T00:00:00Z'),
  max: new Date('2035-12-31T00:00:00Z'),
}).map((date) => date.toISOString().slice(0, 10));
const validSearchArb = fc.integer({ min: 1, max: 100 }).chain(textOfLength);
const validSnapshotArb: fc.Arbitrary<LedgerQuerySnapshot> = fc.record({
  productType: optional(fc.constantFrom(...PRODUCT_TYPES)),
  direction: optional(fc.constantFrom(...TRADE_DIRECTIONS)),
  dateRange: optional(fc.tuple(validDateArb, validDateArb).map(([left, right]) =>
    left <= right ? [left, right] as const : [right, left] as const)),
  productName: optional(validSearchArb),
  productCode: optional(validSearchArb),
  tradeDateOrder: optional(fc.constantFrom('asc' as const, 'desc' as const)),
  holdingSort: optional(fc.tuple(
    fc.constantFrom('position' as const, 'totalProfit' as const),
    fc.constantFrom('asc' as const, 'desc' as const),
  )),
  page: fc.integer({ min: 1, max: 50 }),
  pageSize: fc.integer({ min: 1, max: 100 }),
  scope: optional(fc.tuple(fc.constantFrom(...PRODUCT_TYPES), textOfLength(8))),
}).map(({ dateRange, holdingSort, scope, ...snapshot }) => ({
  ...snapshot,
  startDate: dateRange?.[0] ?? null,
  endDate: dateRange?.[1] ?? null,
  holdingSortField: holdingSort?.[0] ?? null,
  holdingSortOrder: holdingSort?.[1] ?? null,
  scopeProductType: scope?.[0] ?? null,
  scopeProductCode: scope?.[1] ?? null,
}));

const resultArb = (pageSize: number): fc.Arbitrary<BrowsedResult[]> => fc.array(fc.record({
  productCode: textOfLength(8),
  productName: textOfLength(12),
  amount: fc.integer({ min: -1_000_000, max: 1_000_000 }),
}), { minLength: 1, maxLength: pageSize });

const invalidDateRangeArb: fc.Arbitrary<InvalidQueryInput> = fc.oneof(
  validDateArb.map((start) => ({ kind: 'dateRange' as const, start, end: null })),
  validDateArb.map((end) => ({ kind: 'dateRange' as const, start: null, end })),
  fc.constantFrom('2024-02-30', '2023-02-29', '2024-13-01', 'not-a-date')
    .map((start) => ({ kind: 'dateRange' as const, start, end: '2024-12-31' })),
  fc.tuple(validDateArb, validDateArb)
    .filter(([left, right]) => left !== right)
    .map(([left, right]) => ({
      kind: 'dateRange' as const,
      start: left > right ? left : right,
      end: left > right ? right : left,
    })),
);

const invalidInputArb = (currentPage: number): fc.Arbitrary<InvalidQueryInput> => fc.oneof(
  fc.constant({ kind: 'search' as const, value: '' }),
  fc.integer({ min: 101, max: 150 }).chain(textOfLength)
    .map((value) => ({ kind: 'search' as const, value })),
  invalidDateRangeArb,
  fc.oneof(
    fc.integer({ min: -1_000, max: 0 }),
    fc.integer({ min: 101, max: 1_000 }),
    fc.integer({ min: 1, max: 100 }).map((value) => value + 0.5),
  ).map((value) => ({ kind: 'pageSize' as const, value })),
  fc.integer({ min: currentPage, max: 100 }).chain((pageCount) => fc.oneof(
    fc.integer({ min: -1_000, max: 0 }),
    fc.integer({ min: pageCount + 1, max: pageCount + 1_000 }),
  ).map((value) => ({ kind: 'page' as const, value, pageCount }))),
);
const scenarioArb: fc.Arbitrary<Scenario> = validSnapshotArb.chain((snapshot) =>
  fc.tuple(resultArb(snapshot.pageSize), invalidInputArb(snapshot.page))
    .map(([results, input]) => ({ snapshot, results, input })),
);

const validateInput = (validator: QueryInputValidator, input: InvalidQueryInput): ValidationResult => {
  switch (input.kind) {
    case 'search':
      return validator.validateSearchValue(input.value);
    case 'dateRange':
      return validator.validateDateRange(input.start, input.end);
    case 'pageSize':
      return validator.validatePageSize(input.value);
    case 'page':
      return validator.validatePage(input.value, input.pageCount);
  }
};

const FIXED_SNAPSHOT: LedgerQuerySnapshot = {
  productType: 'FUND', direction: 'BUY', startDate: '2024-01-01', endDate: '2024-12-31',
  productName: '指数', productCode: '510300', tradeDateOrder: 'desc',
  holdingSortField: 'totalProfit', holdingSortOrder: 'asc', page: 2, pageSize: 20,
  scopeProductCode: null,
};
const FIXED_RESULTS: BrowsedResult[] = [{ productCode: '510300', productName: '沪深300ETF', amount: 100 }];
const example = (input: InvalidQueryInput): [Scenario] => [{
  snapshot: FIXED_SNAPSHOT,
  results: FIXED_RESULTS,
  input,
}];
const REQUIRED_EXAMPLES: [Scenario][] = [
  example({ kind: 'search', value: '' }),
  example({ kind: 'search', value: '🚀'.repeat(101) }),
  example({ kind: 'dateRange', start: '2024-01-01', end: null }),
  example({ kind: 'dateRange', start: null, end: '2024-01-01' }),
  example({ kind: 'dateRange', start: '2024-02-30', end: '2024-03-01' }),
  example({ kind: 'dateRange', start: '2024-03-02', end: '2024-03-01' }),
  example({ kind: 'pageSize', value: 0 }),
  example({ kind: 'pageSize', value: 101 }),
  example({ kind: 'pageSize', value: 20.5 }),
  example({ kind: 'page', value: 0, pageCount: 3 }),
  example({ kind: 'page', value: 4, pageCount: 3 }),
];

describe('Property 7: 无效查询输入不改变已应用的浏览状态与结果', () => {
  it('任意无效搜索、日期范围、页大小或页码只返回错误，调用方不应用时状态与结果保持原引用和内容', () => {
    fc.assert(
      fc.property(scenarioArb, ({ snapshot, results, input }) => {
        const appliedState = LedgerQueryState.from(snapshot).toSnapshot();
        let currentState = appliedState;
        let currentResults = results;
        const stateBefore = { ...appliedState };
        const resultsBefore = results.map((row) => ({ ...row }));

        const validation = validateInput(new QueryInputValidator(), input);
        let didApply = false;
        if (validation.valid) {
          didApply = true;
          currentState = { ...currentState, page: 1 };
          currentResults = [...currentResults];
        }

        expect(validation.valid).toBe(false);
        expect(validation.fieldErrors.length).toBeGreaterThan(0);
        validation.fieldErrors.forEach((error) => expect(error.message).toMatch(/[\u4e00-\u9fa5]/));
        expect(Object.keys(validation).sort()).toEqual(['fieldErrors', 'valid']);
        expect(didApply).toBe(false);
        expect(currentState).toBe(appliedState);
        expect(currentState).toEqual(stateBefore);
        expect(currentResults).toBe(results);
        expect(currentResults).toEqual(resultsBefore);
      }),
      { numRuns: 100, examples: REQUIRED_EXAMPLES },
    );
  });
});
