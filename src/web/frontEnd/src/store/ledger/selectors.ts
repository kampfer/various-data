// store/ledger/selectors.ts
// 账本派生选择器：集中完成视图所需的记忆化投影，不修改 Redux 状态。
import { createSelector } from '@reduxjs/toolkit';
import LedgerQueryState from '../../domain/ledger/LedgerQueryState';
import type { FieldError } from '../../domain/ledger/TradeDraftValidator';
import type { HoldingOut, TransactionOut } from '../../api/types';
import type { LedgerRootState } from './types';

/** 当前页可能包含的行 DTO；具体类型由当前模块决定。 */
export type CurrentPageRow = TransactionOut | HoldingOut;

/** 分页组件所需的只读派生信息。 */
export interface PaginationInfo {
  /** 后端回显页码；pageCount 为 0 时不代表有效页码。 */
  readonly page: number;
  /** 当前应用页大小。 */
  readonly pageSize: number;
  /** 总页数；0 表示没有可浏览页。 */
  readonly pageCount: number;
  /** 分页前结果总数。 */
  readonly total: number;
  /** 是否存在有效页码；显式承载 pageCount === 0 的界面分支。 */
  readonly hasPages: boolean;
  /** 当前有效页码；空结果时为 null，避免把 state 中的 page=1 标记为有效。 */
  readonly validPage: number | null;
}

/** 字段名到首条中文错误信息的映射，供表单项直接消费。 */
export type FieldErrorMap = Readonly<Record<string, string>>;

/** 根选择器：复用任务 12.1 的最小根状态契约，未来 RootState 与其结构兼容。 */
export const selectLedger = (state: LedgerRootState) => state.ledger;

/** 当前模块；null 表示初始模块尚未决定。 */
export const selectCurrentModule = createSelector(
  [selectLedger],
  (ledger) => ledger.activeModule,
);

/** 与设计文档命名保持兼容。 */
export const selectActiveModule = selectCurrentModule;

/** 历史交易查询领域对象；仅在快照引用变化时重建。 */
export const selectHistoryQuery = createSelector(
  [selectLedger],
  (ledger) => LedgerQueryState.from(ledger.history.query),
);
/** 持仓查询领域对象；仅在快照引用变化时重建。 */
export const selectHoldingsQuery = createSelector(
  [selectLedger],
  (ledger) => LedgerQueryState.from(ledger.holdings.query),
);

/** 历史交易当前页行数据；空结果仍返回空数组以保留表格列头。 */
export const selectHistoryRows = createSelector(
  [selectLedger],
  (ledger) => ledger.history.items,
);

/** 持仓当前页行数据。 */
export const selectHoldingsRows = createSelector(
  [selectLedger],
  (ledger) => ledger.holdings.items,
);

const EMPTY_ROWS: readonly CurrentPageRow[] = Object.freeze([]);

/** 当前激活模块的页行数据；模块未决定时返回稳定的只读空数组。 */
export const selectCurrentPageRows = createSelector(
  [selectCurrentModule, selectHistoryRows, selectHoldingsRows],
  (module, historyRows, holdingsRows): readonly CurrentPageRow[] => {
    if (module === 'history') return historyRows;
    if (module === 'holdings') return holdingsRows;
    return EMPTY_ROWS;
  },
);

interface PaginationSource {
  readonly page: number;
  readonly pageSize: number;
  readonly pageCount: number;
  readonly total: number;
}

/** 从列表状态派生统一分页契约；纯函数便于两个模块复用。 */
const toPaginationInfo = (source: PaginationSource): PaginationInfo => {
  const hasPages = source.pageCount !== 0;
  return {
    page: source.page,
    pageSize: source.pageSize,
    pageCount: source.pageCount,
    total: source.total,
    hasPages,
    validPage: hasPages ? source.page : null,
  };
};

/** 历史交易分页信息。 */
export const selectHistoryPagination = createSelector(
  [selectLedger],
  (ledger) => toPaginationInfo(ledger.history),
);

/** 持仓分页信息。 */
export const selectHoldingsPagination = createSelector(
  [selectLedger],
  (ledger) => toPaginationInfo(ledger.holdings),
);

/** 当前模块分页信息；模块未决定时为 null。 */
export const selectCurrentPagination = createSelector(
  [selectCurrentModule, selectHistoryPagination, selectHoldingsPagination],
  (module, history, holdings): PaginationInfo | null => {
    if (module === 'history') return history;
    if (module === 'holdings') return holdings;
    return null;
  },
);

/** 是否正在浏览单个产品的历史交易范围。 */
export const selectHasScope = createSelector(
  [selectHistoryQuery],
  (query) => query.toSnapshot().scopeProductCode !== null,
);

/** 当前持仓查询对应的组合统计；尚未取得时为 null。 */
export const selectPortfolioStatistics = createSelector(
  [selectLedger],
  (ledger) => ledger.holdings.portfolio,
);

/** 把错误数组转换为字段映射；同字段重复时保留首条，确保展示稳定。 */
const toFieldErrorMap = (errors: readonly FieldError[]): FieldErrorMap => {
  const result: Record<string, string> = {};
  for (const error of errors) {
    if (!Object.prototype.hasOwnProperty.call(result, error.field)) {
      result[error.field] = error.message;
    }
  }
  return result;
};

/** 新建交易表单字段错误映射。 */
export const selectTradeFieldErrorMap = createSelector(
  [selectLedger],
  (ledger) => toFieldErrorMap(ledger.tradeForm.fieldErrors),
);

/** 估值表单字段错误映射。 */
export const selectValuationFieldErrorMap = createSelector(
  [selectLedger],
  (ledger) => toFieldErrorMap(ledger.valuationForm.fieldErrors),
);
