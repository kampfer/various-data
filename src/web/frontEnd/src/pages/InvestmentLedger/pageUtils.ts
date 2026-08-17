import { message } from 'antd';
import QueryInputValidator from '../../domain/ledger/QueryInputValidator';
import type { LedgerQuerySnapshot } from '../../domain/ledger/LedgerQueryState';

/** 页面间共享的路由导航意图；产品历史交易范围改由 URL 查询参数承载。 */
export type LedgerNavigationState =
  | { readonly ledgerNavigation: 'module-switch' }
  | null;

/** 从未知异常提取用户可读中文消息。 */
export const rejectionMessage = (error: unknown, fallback = '网络异常，请稍后重试'): string => {
  if (typeof error === 'object' && error !== null && 'message' in error) {
    const value = (error as { readonly message?: unknown }).message;
    if (typeof value === 'string' && value.length > 0) return value;
  }
  return error instanceof Error && error.message.length > 0 ? error.message : fallback;
};

/** 校验查询补丁；失败时只提示，不改变 Redux 中已应用的快照。 */
export const validateQueryPatch = (
  query: LedgerQuerySnapshot,
  patch: Partial<LedgerQuerySnapshot>,
): boolean => {
  const validator = new QueryInputValidator();
  for (const value of [patch.productName, patch.productCode]) {
    if (value !== undefined && value !== null) {
      const result = validator.validateSearchValue(value);
      if (!result.valid) {
        void message.error(result.fieldErrors[0]?.message ?? '搜索值无效');
        return false;
      }
    }
  }

  if (patch.startDate !== undefined || patch.endDate !== undefined) {
    const startDate = patch.startDate === undefined ? query.startDate : patch.startDate;
    const endDate = patch.endDate === undefined ? query.endDate : patch.endDate;
    const result = validator.validateDateRange(startDate, endDate);
    if (!result.valid) {
      void message.error(result.fieldErrors[0]?.message ?? '交易日期范围无效');
      return false;
    }
  }
  return true;
};
