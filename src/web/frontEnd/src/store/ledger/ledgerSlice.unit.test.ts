import dayjs from 'dayjs';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type {
  HoldingOut,
  Metric,
  PortfolioStatisticsOut,
  TransactionOut,
} from '../../api/types';
import LedgerQueryState from '../../domain/ledger/LedgerQueryState';
import type { LedgerQuerySnapshot } from '../../domain/ledger/LedgerQueryState';
import store from '../index';
import { SET_FILTERS } from '../actionTypes.js';
import ledgerReducer, {
  applyQuery,
  changePage,
  changePageSize,
  openHistoryScope,
} from './ledgerSlice';
import * as thunks from './thunks';

const availableMetric = (value: string): Metric => ({
  available: true,
  value,
  unavailableReason: null,
});

const transaction: TransactionOut = {
  id: 7,
  productType: 'FUND',
  productName: '测试基金',
  productCode: 'F001',
  transactionPrice: '1.25',
  transactionQuantity: '10',
  direction: 'BUY',
  tradeDate: '2024-01-02',
};

const holding: HoldingOut = {
  productType: 'FUND',
  productName: '测试基金',
  productCode: 'F001',
  position: availableMetric('12.50'),
  positionQuantity: availableMetric('10'),
  totalProfit: availableMetric('0.00'),
  totalProfitRate: availableMetric('0'),
  annualizedRate: availableMetric('0'),
};

const portfolio: PortfolioStatisticsOut = {
  totalPosition: availableMetric('12.50'),
  totalProfit: availableMetric('0.00'),
  totalProfitRate: availableMetric('0'),
  totalAnnualizedRate: availableMetric('0'),
};

const initialLedger = () => ledgerReducer(undefined, { type: 'test/init' });

const historyPage = {
  items: [transaction],
  total: 1,
  page: 4,
  pageSize: 50,
  pageCount: 1,
};

const holdingsPage = {
  items: [holding],
  total: 1,
  page: 3,
  pageSize: 20,
  pageCount: 1,
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe('ledger slice 查询状态不变量', () => {
  it('路由切换不派发 reducer，因此已应用历史快照与结果保持不变', () => {
    let state = ledgerReducer(
      initialLedger(),
      applyQuery({
        module: 'history',
        patch: { productName: '旧条件', tradeDateOrder: 'desc' },
      }),
    );
    state = ledgerReducer(state, changePageSize({ module: 'history', size: 50 }));
    state = ledgerReducer(state, changePage({ module: 'history', page: 4 }));
    state = ledgerReducer(
      state,
      thunks.fetchHistory.fulfilled(historyPage, 'history-success', undefined),
    );
    const historyBeforeRouteSwitch = state.history;

    // 路由切换不 dispatch ledger action；即使其它状态观察器触发未知 action，两个快照也必须保持。
    const stateAfterRouteSwitch = ledgerReducer(state, { type: 'router/locationChanged' });
    expect(stateAfterRouteSwitch).toBe(state);
    expect(stateAfterRouteSwitch.history).toBe(historyBeforeRouteSwitch);
    expect(state.history.query).toMatchObject({
      productName: '旧条件', tradeDateOrder: 'desc', pageSize: 50, page: 4,
    });
    expect(state).not.toHaveProperty('activeModule');
    expect(state).not.toHaveProperty('bootstrapping');
  });


  it('从持仓入口进入历史时只保留产品范围并重置此前浏览状态', () => {
    let state = ledgerReducer(
      initialLedger(),
      applyQuery({
        module: 'history',
        patch: {
          productType: 'WEALTH',
          direction: 'SELL',
          productCode: '旧代码',
          holdingSortField: 'totalProfit',
          holdingSortOrder: 'desc',
        },
      }),
    );
    state = ledgerReducer(state, changePageSize({ module: 'history', size: 50 }));
    state = ledgerReducer(state, changePage({ module: 'history', page: 4 }));
    state = ledgerReducer(
      state,
      thunks.fetchHistory.fulfilled(historyPage, 'history-success', undefined),
    );

    const scope = { productCode: '600000', productName: '示例股票' };
    state = ledgerReducer(state, openHistoryScope(scope));

    expect(state).not.toHaveProperty('activeModule');
    expect(state.history.query).toEqual(
      LedgerQueryState.defaultWithScope('history', scope).toSnapshot(),
    );
    expect(state.history).toMatchObject({
      items: [], total: 0, page: 1, pageSize: 20, pageCount: 0, loading: false, error: null,
    });
  });

  it.each<Partial<LedgerQuerySnapshot>>([
    { productType: 'FUND' },
    { productName: '基金' },
    { startDate: '2024-01-01', endDate: '2024-12-31' },
    { tradeDateOrder: 'asc' },
    { holdingSortField: 'position', holdingSortOrder: 'desc' },
  ])('任一筛选、搜索或排序条件变更后页码归 1：%o', (patch) => {
    let state = ledgerReducer(initialLedger(), changePage({ module: 'holdings', page: 8 }));
    state = ledgerReducer(state, applyQuery({ module: 'holdings', patch }));

    expect(state.holdings.query.page).toBe(1);
  });

  it('页大小变更后页码归 1', () => {
    let state = ledgerReducer(initialLedger(), changePage({ module: 'history', page: 8 }));
    state = ledgerReducer(state, changePageSize({ module: 'history', size: 50 }));

    expect(state.history.query.page).toBe(1);
    expect(state.history.query.pageSize).toBe(50);
  });
});


describe('ledger slice 失败态', () => {
  it('列表与组合统计请求失败时保留既有数据和已应用查询', () => {
    let state = ledgerReducer(
      initialLedger(),
      applyQuery({ module: 'history', patch: { productCode: 'F001' } }),
    );
    state = ledgerReducer(
      state,
      thunks.fetchHistory.fulfilled(historyPage, 'history-success', undefined),
    );
    state = ledgerReducer(
      state,
      applyQuery({ module: 'holdings', patch: { productType: 'FUND' } }),
    );
    state = ledgerReducer(
      state,
      thunks.fetchHoldings.fulfilled(holdingsPage, 'holdings-success', undefined),
    );
    state = ledgerReducer(
      state,
      thunks.fetchPortfolioStatistics.fulfilled(portfolio, 'portfolio-success', undefined),
    );
    const historyBefore = state.history;
    const holdingsBefore = state.holdings;

    state = ledgerReducer(
      state,
      thunks.fetchHistory.rejected(null, 'history-failure', undefined, { message: '历史加载失败' }),
    );
    state = ledgerReducer(
      state,
      thunks.fetchHoldings.rejected(null, 'holdings-failure', undefined, { message: '持仓加载失败' }),
    );
    state = ledgerReducer(
      state,
      thunks.fetchPortfolioStatistics.rejected(
        null,
        'portfolio-failure',
        undefined,
        { message: '统计加载失败' },
      ),
    );

    expect(state.history.items).toBe(historyBefore.items);
    expect(state.history.query).toBe(historyBefore.query);
    expect(state.history.error).toBe('历史加载失败');
    expect(state.holdings.items).toBe(holdingsBefore.items);
    expect(state.holdings.query).toBe(holdingsBefore.query);
    expect(state.holdings.portfolio).toBe(holdingsBefore.portfolio);
    expect(state.holdings.error).toBe('统计加载失败');
  });
});


describe('根 store 迁移兼容性', () => {
  it('保留 news、stock、crawlers 分支及其迁移前初始值', () => {
    const state = store.getState() as {
      news: unknown;
      stock: unknown;
      crawlers: unknown;
    };

    expect(store.getState()).toHaveProperty('news');
    expect(store.getState()).toHaveProperty('stock');
    expect(store.getState()).toHaveProperty('crawlers');
    expect(state.news).toEqual({
      list: [],
      total: 0,
      filters: { filterWords: '', period: [], priority: 0, sortBy: 0, category: 0 },
      categories: [],
    });
    expect(state.stock).toEqual({
      zoomStart: expect.anything(),
      zoomEnd: expect.anything(),
      code: 'sh000001',
    });
    expect(state.crawlers).toEqual({
      list: [],
      fetchingCrawlers: false,
      exeingCrawler: false,
    });
  });

  it('派发账本及旧模块 action 时无 serializable 或 immutable 控制台告警', () => {
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => undefined);

    store.dispatch(applyQuery({ module: 'history', patch: { productCode: 'F001' } }));
    store.dispatch({
      type: SET_FILTERS,
      payload: {
        filterWords: '',
        period: [dayjs('2024-01-01'), dayjs('2024-01-31')],
        priority: 0,
        sortBy: 0,
        category: 0,
      },
    });

    const messages = [...errorSpy.mock.calls, ...warnSpy.mock.calls]
      .flat()
      .map(String)
      .join('\n');
    expect(messages).not.toMatch(/non-serializable|mutation detected|immutable/i);
  });
});