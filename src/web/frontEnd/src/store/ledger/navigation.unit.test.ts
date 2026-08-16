import { describe, expect, it } from 'vitest';
import LedgerQueryState from '../../domain/ledger/LedgerQueryState';
import ledgerReducer, {
  applyQuery,
  changePage,
  changePageSize,
  openHistoryScope,
  resetHistory,
} from './ledgerSlice';

const initialLedger = () => ledgerReducer(undefined, { type: 'test/init' });

describe('账本路由导航状态', () => {
  it('module-switch 不派发重置 action 时保留目标模块快照与结果', () => {
    let state = ledgerReducer(initialLedger(), applyQuery({
      module: 'holdings',
      patch: { productName: '指数', holdingSortField: 'totalProfit', holdingSortOrder: 'desc' },
    }));
    state = ledgerReducer(state, changePageSize({ module: 'holdings', size: 50 }));
    state = ledgerReducer(state, changePage({ module: 'holdings', page: 2 }));
    const before = state.holdings;

    // URL 导航由 LedgerLayout 处理，目标快照不经过任何状态重置。
    expect(state.holdings).toBe(before);
    expect(state.holdings.query).toMatchObject({
      productName: '指数', holdingSortField: 'totalProfit', holdingSortOrder: 'desc',
      pageSize: 50, page: 2,
    });
  });

  it('holding-scope 只保留成对产品范围并恢复历史默认状态', () => {
    let state = ledgerReducer(initialLedger(), applyQuery({
      module: 'history',
      patch: { productName: '旧搜索', direction: 'SELL', tradeDateOrder: 'desc' },
    }));
    state = ledgerReducer(state, changePageSize({ module: 'history', size: 50 }));
    state = ledgerReducer(state, openHistoryScope({ productType: 'FUND', productCode: 'F001' }));

    expect(state.history.query).toEqual(LedgerQueryState.defaultWithScope('history', {
      productType: 'FUND', productCode: 'F001',
    }).toSnapshot());
    expect(state.history.query.productName).toBeNull();
    expect(state.history.query.direction).toBeNull();
    expect(state.history.query.pageSize).toBe(20);
  });

  it('无上下文 history 深链重置为全部交易默认状态且不产生不完整 scope', () => {
    let state = ledgerReducer(initialLedger(), openHistoryScope({
      productType: 'STOCK', productCode: '600000',
    }));
    state = ledgerReducer(state, resetHistory());

    expect(state.history.query).toEqual(LedgerQueryState.default('history').toSnapshot());
    expect(state.history.query.scopeProductType).toBeNull();
    expect(state.history.query.scopeProductCode).toBeNull();
  });
});
