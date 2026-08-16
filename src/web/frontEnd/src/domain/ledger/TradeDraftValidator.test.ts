// Feature: investment-trade-ledger, Property 1: 差异化交易数值校验拒绝无效输入并保留原值
// **Validates: Requirements 1.2**
import fc from 'fast-check';
import { describe, expect, it } from 'vitest';
import TradeDraftValidator from './TradeDraftValidator';
import type { TradeDraftLike } from './TradeDraftValidator';

const validDecimal = fc.tuple(fc.integer({ min: 1, max: 10 ** 12 }), fc.integer({ min: 0, max: 10 ** 12 })).map(([whole, fraction]) => `${whole}.${String(fraction).padStart(12, '0')}`);
const invalidDecimal = fc.constantFrom('NaN', 'Infinity', '-1', '0', 'abc', '');
const base = (productType: string, transactionPrice: string, transactionQuantity: string): TradeDraftLike => ({ productType, productName: '产品', productCode: 'P001', transactionPrice, transactionQuantity, direction: 'BUY', tradeDate: '2024-02-29' });
describe('Property 1: 差异化交易数值校验', () => {
  it('对至少 100 个任意精度数值，保留输入并按产品类型拒绝无效值', () => {
    fc.assert(fc.property(fc.constantFrom('WEALTH', 'FUND', 'STOCK'), validDecimal, validDecimal, invalidDecimal, (productType, price, quantity, invalid) => {
      const validator = new TradeDraftValidator();
      const wealthOrFund = base(productType, price, quantity); const before = { ...wealthOrFund };
      const expectedValid = productType !== 'STOCK' || !quantity.includes('.');
      expect(validator.validate(wealthOrFund).valid).toBe(expectedValid);
      expect(wealthOrFund).toEqual(before);
      const invalidDraft = base(productType, invalid, quantity); const invalidBefore = { ...invalidDraft };
      const result = validator.validate(invalidDraft);
      expect(result.valid).toBe(false);
      expect(result.fieldErrors.some((error) => error.field === 'transactionPrice')).toBe(true);
      expect(invalidDraft).toEqual(invalidBefore);
    }), { numRuns: 100 });
  });
  it('股票仅拒绝小数数量，理财和基金允许相同输入', () => {
    const validator = new TradeDraftValidator();
    expect(validator.validate(base('FUND', '1.000000000000000001', '2.500000000000000003')).valid).toBe(true);
    expect(validator.validate(base('WEALTH', '999999999999999999.1', '2.5')).valid).toBe(true);
    const stock = validator.validate(base('STOCK', '1.1', '2.5'));
    expect(stock.fieldErrors).toMatchObject([{ field: 'transactionQuantity', code: 'NOT_INTEGER' }]);
  });
});
