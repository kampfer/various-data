// 交易草稿校验器：纯字符串/十进制文本语义，不改写用户草稿（需求 1.2）。
import { PRODUCT_TYPES, TRADE_DIRECTIONS } from './constants';
import { PRODUCT_TYPE_LABELS, TRADE_DIRECTION_LABELS } from './labels';
import type { TradeDraft } from '../../api/types';

/** 单个字段的校验错误，字段名始终为 canonical camelCase。 */
export interface FieldError { readonly field: string; readonly code: string; readonly message: string; }
/** 完整草稿的校验结果。 */
export interface ValidationResult { readonly valid: boolean; readonly fieldErrors: readonly FieldError[]; }
/** 放宽枚举和值字段，以便校验器能报告非法原始输入。 */
export interface TradeDraftLike extends Omit<TradeDraft, 'productType' | 'direction' | 'transactionPrice' | 'transactionQuantity'> {
  readonly productType?: string | null;
  readonly direction?: string | null;
  readonly transactionPrice?: string | null;
  readonly transactionQuantity?: string | null;
}

const MAX_PRODUCT_NAME_LENGTH = 100;
const MAX_PRODUCT_CODE_LENGTH = 32;
const DATE_PATTERN = /^(\d{4})-(\d{2})-(\d{2})$/;
/** 只接受普通十进制文本；不使用 Number/float 或科学计数法。 */
export const DECIMAL_PATTERN = /^[+-]?\d+(\.\d+)?$/;
const INTEGER_PATTERN = /^\+?\d+$/;
/** 校验器对外稳定错误码。 */
export const TRADE_ERROR_CODES = {
  REQUIRED: 'REQUIRED', NOT_IN_ENUM: 'NOT_IN_ENUM', TOO_LONG: 'TOO_LONG',
  NOT_A_NUMBER: 'NOT_A_NUMBER', NOT_INTEGER: 'NOT_INTEGER', OUT_OF_RANGE: 'OUT_OF_RANGE',
  INVALID_DATE: 'INVALID_DATE',
} as const;

/** 不依赖日期库地判断 YYYY-MM-DD 是否为真实公历日期。 */
export const isValidCalendarDate = (value: string): boolean => {
  const matched = DATE_PATTERN.exec(value);
  if (matched === null) return false;
  const year = Number(matched[1]); const month = Number(matched[2]); const day = Number(matched[3]);
  if (month < 1 || month > 12) return false;
  const leap = (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0;
  const limit = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1] ?? 0;
  return day >= 1 && day <= limit;
};
const charLength = (value: string): number => Array.from(value).length;
const joinLabels = (labels: readonly string[]): string => labels.length < 2 ? labels.join('') : `${labels.slice(0, -1).join('、')}或${labels[labels.length - 1] ?? ''}`;
const PRODUCT_TYPE_HINT = joinLabels(PRODUCT_TYPES.map((code) => PRODUCT_TYPE_LABELS[code]));
const TRADE_DIRECTION_HINT = joinLabels(TRADE_DIRECTIONS.map((code) => TRADE_DIRECTION_LABELS[code]));

/** 根据产品类型校验交易价格与交易数量，不格式化、不截断、不引入数值上界。 */
export default class TradeDraftValidator {
  public validate(draft: TradeDraftLike): ValidationResult {
    const fieldErrors: FieldError[] = [];
    const push = (error: FieldError | null): void => { if (error !== null) fieldErrors.push(error); };
    push(this.checkEnum('productType', draft.productType, PRODUCT_TYPES, `产品类型必须为${PRODUCT_TYPE_HINT}之一`));
    push(this.checkText('productName', draft.productName, MAX_PRODUCT_NAME_LENGTH, '产品名称'));
    push(this.checkText('productCode', draft.productCode, MAX_PRODUCT_CODE_LENGTH, '产品代码'));
    push(this.checkPositiveDecimal('transactionPrice', draft.transactionPrice, '交易价格'));
    push(this.checkQuantity(draft.productType, draft.transactionQuantity));
    push(this.checkEnum('direction', draft.direction, TRADE_DIRECTIONS, `交易方向必须为${TRADE_DIRECTION_HINT}之一`));
    push(this.checkTradeDate(draft.tradeDate));
    return { valid: fieldErrors.length === 0, fieldErrors };
  }

  private checkEnum(field: string, value: string | null | undefined, codes: readonly string[], message: string): FieldError | null {
    return typeof value === 'string' && codes.includes(value) ? null : { field, code: TRADE_ERROR_CODES.NOT_IN_ENUM, message };
  }
  private checkText(field: string, value: string | null | undefined, maxLength: number, label: string): FieldError | null {
    if (typeof value !== 'string' || value.length === 0) return { field, code: TRADE_ERROR_CODES.REQUIRED, message: `${label}不能为空` };
    return charLength(value) <= maxLength ? null : { field, code: TRADE_ERROR_CODES.TOO_LONG, message: `${label}不能超过 ${maxLength} 个字符` };
  }
  private checkPositiveDecimal(field: string, value: string | null | undefined, label: string): FieldError | null {
    if (value === null || value === undefined || value === '') return { field, code: TRADE_ERROR_CODES.REQUIRED, message: `${label}不能为空` };
    if (!DECIMAL_PATTERN.test(value)) return { field, code: TRADE_ERROR_CODES.NOT_A_NUMBER, message: `${label}必须是大于 0 的有限十进制数值` };
    const digits = value.replace(/^[+-]/, '').replace('.', '');
    return value.startsWith('-') || /^0*$/.test(digits) ? { field, code: TRADE_ERROR_CODES.OUT_OF_RANGE, message: `${label}必须大于 0` } : null;
  }
  private checkQuantity(productType: string | null | undefined, value: string | null | undefined): FieldError | null {
    const decimalError = this.checkPositiveDecimal('transactionQuantity', value, '交易数量');
    if (decimalError !== null) return decimalError;
    const decimalText = value ?? '';
    if (productType === 'STOCK') {
      if (!INTEGER_PATTERN.test(decimalText)) return { field: 'transactionQuantity', code: TRADE_ERROR_CODES.NOT_INTEGER, message: '股票数量必须为正整数' };
    }
    return null;
  }
  private checkTradeDate(value: string | null | undefined): FieldError | null {
    if (typeof value !== 'string' || value.length === 0) return { field: 'tradeDate', code: TRADE_ERROR_CODES.REQUIRED, message: '交易日期不能为空' };
    return isValidCalendarDate(value) ? null : { field: 'tradeDate', code: TRADE_ERROR_CODES.INVALID_DATE, message: '交易日期必须为有效日历日期，格式为 YYYY-MM-DD' };
  }
}
