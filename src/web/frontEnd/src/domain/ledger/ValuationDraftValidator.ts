// domain/ledger/ValuationDraftValidator.ts
// 估值草稿校验器（需求 3.1、3.2）：纯逻辑、无副作用，逐字段给出中文原因，绝不改写入参。
// 与 TradeDraftValidator 同签名（草稿 → ValidationResult），并复用其导出的错误结构、错误码、
// 日历日期判定与数值字面量判定，避免同一规则出现两份实现而漂移。
import { PRODUCT_TYPES } from './constants';
import {
  DECIMAL_PATTERN,
  PRODUCT_TYPE_HINT,
  TRADE_ERROR_CODES,
  isValidCalendarDate,
} from './TradeDraftValidator';
import type { FieldError, ValidationResult } from './TradeDraftValidator';
import type { ValuationDraft } from '../../api/types';

/** 产品代码长度上界（字符数，闭区间上界），需求 3.2 */
const MAX_PRODUCT_CODE_LENGTH = 32;

/** 估值单价上界字面量，与后端 `MAX_VALUATION_UNIT_PRICE` 逐字符一致（需求 3.2） */
export const MAX_VALUATION_UNIT_PRICE = '999999999.99';

/**
 * 估值单价整数部分允许的最大位数。
 * 上界 999999999.99 的整数部分恰为 9 位，且小数位已被限制为 ≤ 2（故小数部分最大为 .99），
 * 因此「整数部分位数 ≤ 9」与「数值 ≤ 999999999.99」等价，可纯字符串判定、零浮点运算。
 */
const MAX_UNIT_PRICE_INTEGER_DIGITS = 9;

/** 估值单价允许的最大小数位数（需求 3.2 的「小数位不超过 2 位」） */
const MAX_UNIT_PRICE_SCALE = 2;

/**
 * 校验器入参：在 `api/types.ts` 的 `ValuationDraft` 之上把产品类型放宽为 `string`、
 * 把估值单价放宽为 `string | number`，因为校验器的职责正是判定「取值是否落在码全集内 /
 * 是否为合法十进制数」，而这些非法取值在收窄类型下无法表达。
 * `ValuationDraft` 可直接赋给本类型（协变放宽），调用方无需额外转换。
 */
export interface ValuationDraftLike extends Omit<ValuationDraft, 'productType' | 'unitPrice'> {
  /** 产品类型：期望为 PRODUCT_TYPES 中的英文码，其它取值一律判为无效（需求 3.2） */
  readonly productType?: string | null;
  /** 估值单价：十进制字符串承载（避免浮点误差），要求 0 ≤ v ≤ 999999999.99 且小数位 ≤ 2 */
  readonly unitPrice?: string | number | null;
}

/** 以字符（码点）为单位计数，与后端 Python `len(str)` 语义对齐，避免 emoji 被按 UTF-16 单元重复计数 */
const charLength = (value: string): number => Array.from(value).length;

/** 估值草稿校验器：无状态，可安全复用同一实例 */
export default class ValuationDraftValidator {
  /**
   * 校验草稿全部字段。
   * @param draft 待校验草稿；**不变量：方法内只读取 draft，不修改其任何字段**（需求 3.2 保留已提交值）
   * @returns 每个无效字段恰好一条 FieldError；产品类型以 PRODUCT_TYPES 的英文码为唯一合法集
   */
  validate(draft: ValuationDraftLike): ValidationResult {
    const fieldErrors: FieldError[] = [];
    const push = (error: FieldError | null): void => {
      if (error !== null) fieldErrors.push(error);
    };

    push(ValuationDraftValidator.checkProductType(draft.productType));
    push(ValuationDraftValidator.checkProductCode(draft.productCode));
    push(ValuationDraftValidator.checkValuationDate(draft.valuationDate));
    push(ValuationDraftValidator.checkUnitPrice(draft.unitPrice));

    return { valid: fieldErrors.length === 0, fieldErrors };
  }

  /**
   * 产品类型校验：取值必须严格等于码全集中的某一项（需求 3.2）。
   * 中文字面量（'理财'）、大小写不符的码（'stock'）、空串与 null / undefined 一律判为 NOT_IN_ENUM。
   */
  private static checkProductType(value: string | null | undefined): FieldError | null {
    // 放宽为 readonly string[] 后再 includes：码全集是字面量元组，直接 includes 无法接受任意字符串
    const codes: readonly string[] = PRODUCT_TYPES;
    if (typeof value === 'string' && codes.includes(value)) return null;
    return {
      field: 'productType',
      code: TRADE_ERROR_CODES.NOT_IN_ENUM,
      message: `产品类型必须为${PRODUCT_TYPE_HINT}之一`,
    };
  }

  /** 产品代码校验：非空且不超过 32 个字符（需求 3.2 的 1..32） */
  private static checkProductCode(value: string | null | undefined): FieldError | null {
    const field = 'productCode';
    if (typeof value !== 'string' || value.length === 0) {
      return { field, code: TRADE_ERROR_CODES.REQUIRED, message: '产品代码不能为空' };
    }
    if (charLength(value) > MAX_PRODUCT_CODE_LENGTH) {
      return {
        field,
        code: TRADE_ERROR_CODES.TOO_LONG,
        message: `产品代码不能超过 ${MAX_PRODUCT_CODE_LENGTH} 个字符`,
      };
    }
    return null;
  }

  /** 估值日期校验：必须为 YYYY-MM-DD 且是有效日历日期（需求 3.2），判定逻辑复用自交易校验器 */
  private static checkValuationDate(value: string | null | undefined): FieldError | null {
    const field = 'valuationDate';
    if (typeof value !== 'string' || value.length === 0) {
      return { field, code: TRADE_ERROR_CODES.REQUIRED, message: '估值日期不能为空' };
    }
    if (!isValidCalendarDate(value)) {
      return {
        field,
        code: TRADE_ERROR_CODES.INVALID_DATE,
        message: '估值日期必须为有效日历日期，格式为 YYYY-MM-DD',
      };
    }
    return null;
  }

  /**
   * 估值单价校验：0 ≤ v ≤ 999999999.99 且小数位 ≤ 2（需求 3.2）。
   * 与交易单价不同，0 是合法取值，且不要求恰有两位小数（整数写法同样合法）。
   * 全程以字符串判定大小与正负，不做任何浮点运算，避免精度失真。
   */
  private static checkUnitPrice(value: string | number | null | undefined): FieldError | null {
    const field = 'unitPrice';
    if (value === null || value === undefined || value === '') {
      return { field, code: TRADE_ERROR_CODES.REQUIRED, message: '估值单价不能为空' };
    }
    const text = typeof value === 'number' ? String(value) : value;
    if (!DECIMAL_PATTERN.test(text)) {
      return {
        field,
        code: TRADE_ERROR_CODES.NOT_A_NUMBER,
        message: `估值单价必须为 0 至 ${MAX_VALUATION_UNIT_PRICE} 之间、小数位不超过两位的数值`,
      };
    }
    const unsigned = text.replace(/^[+-]/, '');
    const [integerPart = '', fractionPart = ''] = unsigned.split('.');
    if (fractionPart.length > MAX_UNIT_PRICE_SCALE) {
      return {
        field,
        code: TRADE_ERROR_CODES.INVALID_SCALE,
        message: '估值单价的小数位不能超过两位',
      };
    }
    const outOfRange: FieldError = {
      field,
      code: TRADE_ERROR_CODES.OUT_OF_RANGE,
      message: `估值单价必须在 0 至 ${MAX_VALUATION_UNIT_PRICE} 之间`,
    };
    // 「-0」「-0.00」在十进制语义下等于 0，不算负数，与后端 Decimal 判定保持一致
    const isZero = /^0*$/.test(integerPart + fractionPart);
    if (text.startsWith('-') && !isZero) return outOfRange;
    // 去掉前导零后再计位数，使 '0000123.45' 这类写法不被误判为超上界
    const significantDigits = integerPart.replace(/^0+/, '');
    if (significantDigits.length > MAX_UNIT_PRICE_INTEGER_DIGITS) return outOfRange;
    return null;
  }
}
