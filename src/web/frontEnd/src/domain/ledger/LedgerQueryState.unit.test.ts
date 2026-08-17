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
    expect(history.scopeProductCode).toBeNull();
  });

  it('仅允许历史模块通过范围入口生成范围参数', () => {
    const scoped = LedgerQueryState.defaultWithScope('history', {
      productCode: '600000',
      productName: '示例股票',
    });

    expect(scoped.toSnapshot()).toMatchObject({
      scopeProductCode: '600000',
      page: 1,
    });
    expect(scoped.toParams()).toMatchObject({
      scopeProductCode: '600000',
    });
    expect(scoped.toParams()).not.toHaveProperty('productName');
    expect(() => LedgerQueryState.defaultWithScope('holdings', {
      productCode: '600000',
      productName: '示例股票',
    })).toThrow();
  });

  it('条件、排序或页大小变化将页码归一到第一页，范围不被普通筛选补丁修改', () => {
    const applied = LedgerQueryState.defaultWithScope('history', {
      productCode: 'F001', productName: '示例基金',
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