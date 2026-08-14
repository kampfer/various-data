import { describe, expect, it } from 'vitest';
import LedgerQueryState from '../../domain/ledger/LedgerQueryState';
import type { HoldingOut, Metric, PortfolioStatisticsOut, TransactionOut } from '../../api/types';
import ledgerReducer from './ledgerSlice';
import {
  selectActiveModule,
  selectCurrentModule,
  selectCurrentPageRows,
  selectCurrentPagination,
  selectHasScope,
  selectHistoryPagination,
  selectHistoryQuery,
  selectHistoryRows,
  selectHoldingsPagination,
  selectHoldingsQuery,
  selectHoldingsRows,
  selectLedger,
  selectPortfolioStatistics,
  selectTradeFieldErrorMap,
  selectValuationFieldErrorMap,
} from './selectors';
import type { LedgerRootState, LedgerState } from './types';

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
  unitPrice: '1.25',
  quantity: 10,
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

const initialLedger = ledgerReducer(undefined, { type: 'selectors/init' });
const rootState = (ledger: LedgerState): LedgerRootState => ({ ledger });

describe('ledger selectors', () => {
  it('按当前模块派生对应当前页行数据', () => {
    const historyState = rootState({
      ...initialLedger,
      activeModule: 'history',
      history: { ...initialLedger.history, items: [transaction] },
      holdings: { ...initialLedger.holdings, items: [holding] },
    });

    expect(selectLedger(historyState)).toBe(historyState.ledger);
    expect(selectCurrentModule(historyState)).toBe('history');
    expect(selectActiveModule(historyState)).toBe('history');
    expect(selectHistoryRows(historyState)).toEqual([transaction]);
    expect(selectHoldingsRows(historyState)).toEqual([holding]);
    expect(selectCurrentPageRows(historyState)).toEqual([transaction]);

    const holdingsState = rootState({ ...historyState.ledger, activeModule: 'holdings' });
    expect(selectCurrentPageRows(holdingsState)).toEqual([holding]);
    const pendingState = rootState({ ...historyState.ledger, activeModule: null });
    expect(selectCurrentPageRows(pendingState)).toEqual([]);
  });

  it('分页为零时不产生有效页码，非空时回显当前有效页', () => {
    const state = rootState({
      ...initialLedger,
      activeModule: 'history',
      history: { ...initialLedger.history, page: 1, pageCount: 0, total: 0 },
      holdings: { ...initialLedger.holdings, page: 2, pageCount: 3, total: 45 },
    });

    expect(selectHistoryPagination(state)).toEqual({
      page: 1,
      pageSize: initialLedger.history.pageSize,
      pageCount: 0,
      total: 0,
      hasPages: false,
      validPage: null,
    });
    expect(selectHoldingsPagination(state)).toMatchObject({
      page: 2,
      pageCount: 3,
      total: 45,
      hasPages: true,
      validPage: 2,
    });
    expect(selectCurrentPagination(state)).toBe(selectHistoryPagination(state));
  });

  it('记忆化派生查询对象并识别产品历史范围', () => {
    const scopedQuery = LedgerQueryState.defaultWithScope('history', {
      productType: 'STOCK',
      productCode: '600000',
    }).toSnapshot();
    const state = rootState({
      ...initialLedger,
      history: { ...initialLedger.history, query: scopedQuery },
    });

    expect(selectHistoryQuery(state)).toBe(selectHistoryQuery(state));
    expect(selectHoldingsQuery(state)).toBe(selectHoldingsQuery(state));
    expect(selectHasScope(state)).toBe(true);
  });

  it('派生组合统计并将字段错误按字段映射', () => {
    const portfolio: PortfolioStatisticsOut = {
      totalPosition: availableMetric('100.00'),
      totalProfit: availableMetric('5.00'),
      totalProfitRate: availableMetric('0.05'),
      totalAnnualizedRate: availableMetric('0.08'),
    };
    const state = rootState({
      ...initialLedger,
      holdings: { ...initialLedger.holdings, portfolio },
      tradeForm: {
        ...initialLedger.tradeForm,
        fieldErrors: [
          { field: 'unitPrice', code: 'INVALID_SCALE', message: '单价格式错误' },
          { field: 'unitPrice', code: 'OUT_OF_RANGE', message: '后续重复错误' },
        ],
      },
      valuationForm: {
        ...initialLedger.valuationForm,
        fieldErrors: [{ field: 'valuationDate', code: 'INVALID_DATE', message: '估值日期无效' }],
      },
    });

    expect(selectPortfolioStatistics(state)).toBe(portfolio);
    expect(selectTradeFieldErrorMap(state)).toEqual({ unitPrice: '单价格式错误' });
    expect(selectTradeFieldErrorMap(state)).toBe(selectTradeFieldErrorMap(state));
    expect(selectValuationFieldErrorMap(state)).toEqual({ valuationDate: '估值日期无效' });
  });
});
