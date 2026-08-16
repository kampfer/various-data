// LedgerQueryState 的模块快照、范围和分页转换示例测试。
import { describe, expect, it } from 'vitest';
import LedgerQueryState from './LedgerQueryState';

describe('LedgerQueryState', () => {
  it('为两个模块分别创建独立默认快照，不携带 activeModule', () => {
    const history = LedgerQueryState.default('history').toSnapshot();
    const holdings = LedgerQueryState.default('holdings').toSnapshot();

    expect(history).toEqual(holdings);
    expect(history).not.toHaveProperty('activeModule');
    expect(history.page).toBe(1);
    expect(history.scopeProductType).toBeNull();
    expect(history.scopeProductCode).toBeNull();
  });

  it('仅允许历史模块通过范围入口生成成对范围参数', () => {
    const scoped = LedgerQueryState.defaultWithScope('history', {
      productType: 'STOCK',
      productCode: '600000',
    });

    expect(scoped.toSnapshot()).toMatchObject({
      scopeProductType: 'STOCK',
      scopeProductCode: '600000',
      page: 1,
    });
    expect(scoped.toParams()).toMatchObject({
      scopeProductType: 'STOCK',
      scopeProductCode: '600000',
    });
    expect(() => LedgerQueryState.defaultWithScope('holdings', {
      productType: 'STOCK',
      productCode: '600000',
    })).toThrow();
  });

  it('半范围快照不会被序列化为不完整的历史范围', () => {
    const partial = LedgerQueryState.from({
      ...LedgerQueryState.default('history').toSnapshot(),
      scopeProductType: 'FUND',
    });

    expect(partial.toSnapshot().scopeProductType).toBeNull();
    expect(partial.toSnapshot().scopeProductCode).toBeNull();
    expect(partial.toParams()).not.toHaveProperty('scopeProductType');
  });

  it('条件、排序或页大小变化将页码归一到第一页，范围不被普通筛选补丁修改', () => {
    const applied = LedgerQueryState.defaultWithScope('history', {
      productType: 'FUND', productCode: 'F001',
    }).withPage(4);

    const changed = applied.withFilters({ tradeDateOrder: 'desc', scopeProductCode: 'OTHER' });
    expect(changed.toSnapshot()).toMatchObject({ page: 1, tradeDateOrder: 'desc' });
    expect(changed.toSnapshot().scopeProductCode).toBe('F001');
    expect(changed.withPageSize(50).toSnapshot().page).toBe(1);
  });

  it('模块直接切换只读取另一模块快照，不改变原模块快照', () => {
    const history = LedgerQueryState.default('history').withFilters({ productName: '指数' }).withPage(3);
    const holdings = LedgerQueryState.default('holdings').withPageSize(50).withPage(2);

    expect(history.toSnapshot().page).toBe(3);
    expect(history.toSnapshot().productName).toBe('指数');
    expect(holdings.toSnapshot().pageSize).toBe(50);
    expect(holdings.toSnapshot().page).toBe(2);
  });
});