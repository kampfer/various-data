// store/ledger/selectors.ts
// 账本派生选择器：集中完成视图所需的记忆化投影，不修改 Redux 状态。
import { createSelector } from '@reduxjs/toolkit';
import LedgerQueryState from '../../domain/ledger/LedgerQueryState';
import type { FieldError } from '../../domain/ledger/TradeDraftValidator';
import type { HoldingOut, TransactionOut } from '../../api/types';
import type { LedgerModule } from '../../domain/ledger/constants';
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

/** 由路由容器传入目标模块，以读取对应模块的行数据。 */
const selectTargetModule = (_state: LedgerRootState, module: LedgerModule): LedgerModule => module;

/** 路由目标模块的当前页行数据；模块值由 URL 派生，不存入 Redux。 */
export const selectModuleRows = createSelector(
  [selectLedger, selectTargetModule],
  (ledger, module): readonly CurrentPageRow[] => ledger[module].items,
);

/** 路由目标模块的浏览状态领域对象；模块值由 URL 派生。 */
export const selectModuleQuery = createSelector(
  [selectLedger, selectTargetModule],
  (ledger, module) => LedgerQueryState.from(ledger[module].query),
);

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

/** 由路由容器传入目标模块，以读取对应模块的分页信息。 */
export const selectModulePagination = createSelector(
  [selectLedger, selectTargetModule],
  (ledger, module) => toPaginationInfo(ledger[module]),
);

/** 是否正在浏览单个产品的历史交易范围。 */
export const selectHasScope = createSelector(
  [selectHistoryQuery],
  (query) => query.toSnapshot().scopeProductCode !== null,
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
