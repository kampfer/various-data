// domain/ledger/QueryInputValidator.ts
// 查询输入校验器（需求 2.20、2.21、2.25、2.26、2.30、2.31）：纯 TypeScript、无状态、无副作用。
import { MAX_PAGE_SIZE, MIN_PAGE_SIZE } from './constants';
import { TRADE_ERROR_CODES, isValidCalendarDate } from './TradeDraftValidator';
import type { FieldError, ValidationResult } from './TradeDraftValidator';

/** 产品名称或产品代码搜索值的字符数上界（需求 2.20）。 */
const MAX_SEARCH_VALUE_LENGTH = 100;

/** 按 Unicode 码点计数，与后端 Python `len(str)` 的字符语义一致。 */
const charLength = (value: string): number => Array.from(value).length;

/** 从单个可选错误构造统一校验结果，不携带任何状态变更或 dispatch 建议。 */
const resultOf = (error: FieldError | null): ValidationResult => ({
  valid: error === null,
  fieldErrors: error === null ? [] : [error],
});

/** 查询输入校验器：所有方法只读取参数并返回校验结果，可安全复用同一实例。 */
export default class QueryInputValidator {
  /** 校验搜索值为 1..100 个字符（需求 2.20）。 */
  validateSearchValue(value: string): ValidationResult {
    if (typeof value !== 'string' || value.length === 0) {
      return resultOf({
        field: 'searchValue',
        code: TRADE_ERROR_CODES.REQUIRED,
        message: `搜索值不能为空，且不能超过 ${MAX_SEARCH_VALUE_LENGTH} 个字符`,
      });
    }
    if (charLength(value) > MAX_SEARCH_VALUE_LENGTH) {
      return resultOf({
        field: 'searchValue',
        code: TRADE_ERROR_CODES.TOO_LONG,
        message: `搜索值不能为空，且不能超过 ${MAX_SEARCH_VALUE_LENGTH} 个字符`,
      });
    }
    return resultOf(null);
  }

  /**
   * 校验交易日期范围：两端同时为空表示未启用筛选；否则必须成对、日历有效且 start <= end。
   * 日期比较可直接使用字典序，因为有效输入均为固定宽度 YYYY-MM-DD。
   */
  validateDateRange(start: string | null, end: string | null): ValidationResult {
    const message = '交易日期范围必须同时提供有效的起始日期与结束日期，且起始日期不能晚于结束日期';
    if (start === null && end === null) return resultOf(null);
    if (start === null || end === null) {
      return resultOf({ field: 'startDate', code: TRADE_ERROR_CODES.OUT_OF_RANGE, message });
    }
    if (!isValidCalendarDate(start) || !isValidCalendarDate(end)) {
      return resultOf({ field: 'startDate', code: TRADE_ERROR_CODES.INVALID_DATE, message });
    }
    if (start > end) {
      return resultOf({ field: 'startDate', code: TRADE_ERROR_CODES.OUT_OF_RANGE, message });
    }
    return resultOf(null);
  }

  /** 校验自定义页大小为闭区间 1..100 内的 number 整数（需求 2.25、2.26）。 */
  validatePageSize(size: unknown): ValidationResult {
    if (!Number.isInteger(size) || (size as number) < MIN_PAGE_SIZE || (size as number) > MAX_PAGE_SIZE) {
      return resultOf({
        field: 'pageSize',
        code: Number.isInteger(size) ? TRADE_ERROR_CODES.OUT_OF_RANGE : TRADE_ERROR_CODES.NOT_INTEGER,
        message: `自定义页大小必须为 ${MIN_PAGE_SIZE} 至 ${MAX_PAGE_SIZE} 的整数`,
      });
    }
    return resultOf(null);
  }

  /** 校验请求页码；总页数为 0 时不存在任何有效页码（需求 2.30、2.31）。 */
  validatePage(page: number, pageCount: number): ValidationResult {
    if (pageCount === 0) {
      return resultOf({
        field: 'page',
        code: TRADE_ERROR_CODES.OUT_OF_RANGE,
        message: '当前结果没有可浏览的页',
      });
    }
    if (!Number.isInteger(page) || page < 1 || page > pageCount) {
      return resultOf({
        field: 'page',
        code: Number.isInteger(page) ? TRADE_ERROR_CODES.OUT_OF_RANGE : TRADE_ERROR_CODES.NOT_INTEGER,
        message: `请求的页码无效，有效页码为 1 至 ${pageCount}`,
      });
    }
    return resultOf(null);
  }
}