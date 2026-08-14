// domain/ledger/TradeDraftValidator.ts
// 交易草稿校验器（需求 1.2）：纯逻辑、无副作用，逐字段给出中文原因，绝不改写入参。
// 依赖仅限领域层自身的 constants（码全集）与 labels（中文文案唯一来源），不依赖 React / antd / axios / RTK。
import { PRODUCT_TYPES, TRADE_DIRECTIONS } from './constants';
import { PRODUCT_TYPE_LABELS, TRADE_DIRECTION_LABELS } from './labels';
import type { TradeDraft } from '../../api/types';

/** 单个字段的校验错误 */
export interface FieldError {
  /** 出错字段名，camelCase，与表单项 / DTO 字段一一对应（如 unitPrice） */
  readonly field: string;
  /** 机器可读错误码，英文常量，如 INVALID_SCALE / OUT_OF_RANGE / NOT_IN_ENUM */
  readonly code: string;
  /** 面向用户的中文原因，直接渲染到 antd Form.Item 的 help 上 */
  readonly message: string;
}

/** 校验结果：valid 与 fieldErrors 为空的关系恒等（valid === (fieldErrors.length === 0)） */
export interface ValidationResult {
  /** 是否全部字段有效 */
  readonly valid: boolean;
  /** 全部无效字段的错误列表；每个无效字段恰好产出一条（需求 1.2「指出每个无效信息项」） */
  readonly fieldErrors: readonly FieldError[];
}

/**
 * 校验器入参：在 `api/types.ts` 的 `TradeDraft` 之上把两个枚举字段放宽为 `string`、
 * 把单价放宽为 `string | number`，因为校验器的职责正是判定「取值是否落在码全集内 / 是否为合法十进制数」，
 * 而这些非法取值（中文字面量、小写码、数字类型）在收窄类型下无法表达。
 * `TradeDraft` 可直接赋给本类型（协变放宽），因此调用方无需额外转换。
 */
export interface TradeDraftLike extends Omit<TradeDraft, 'productType' | 'direction' | 'unitPrice'> {
  /** 产品类型：期望为 PRODUCT_TYPES 中的英文码，其它取值一律判为无效（需求 1.2） */
  readonly productType?: string | null;
  /** 交易方向：期望为 TRADE_DIRECTIONS 中的英文码 */
  readonly direction?: string | null;
  /** 交易单价：十进制字符串承载（避免浮点误差），要求 > 0 且小数位恰为 2 */
  readonly unitPrice?: string | number | null;
}

/** 产品名称长度上界（字符数，闭区间上界），需求 1.2 */
const MAX_PRODUCT_NAME_LENGTH = 100;

/** 产品代码长度上界（字符数，闭区间上界），需求 1.2 */
const MAX_PRODUCT_CODE_LENGTH = 32;

/** 交易日期格式：严格 YYYY-MM-DD，日历有效性另行判定 */
const DATE_PATTERN = /^(\d{4})-(\d{2})-(\d{2})$/;

/**
 * 十进制数字面量：可带负号、可带任意位小数；据此再判定小数位数与正负。
 * 由 `ValuationDraftValidator`（需求 3.2）复用，保证两处「什么算数值」的判定完全一致。
 */
export const DECIMAL_PATTERN = /^[+-]?\d+(\.\d+)?$/;

/** 无符号整数字面量：交易数量的唯一合法书写形式 */
const INTEGER_PATTERN = /^\+?\d+$/;

/** 本校验器使用的错误码全集，供状态层与测试引用，避免手写字符串漂移 */
export const TRADE_ERROR_CODES = {
  /** 必填字段缺失或为空串 */
  REQUIRED: 'REQUIRED',
  /** 取值不属于预定义码全集（含中文字面量、小写码、空值） */
  NOT_IN_ENUM: 'NOT_IN_ENUM',
  /** 超过字符数上界 */
  TOO_LONG: 'TOO_LONG',
  /** 不是合法的十进制数字面量 */
  NOT_A_NUMBER: 'NOT_A_NUMBER',
  /** 不是整数 */
  NOT_INTEGER: 'NOT_INTEGER',
  /** 数值超出定义域（如 <= 0） */
  OUT_OF_RANGE: 'OUT_OF_RANGE',
  /** 小数位数不符合要求（交易单价须恰为 2 位） */
  INVALID_SCALE: 'INVALID_SCALE',
  /** 不是有效日历日期 */
  INVALID_DATE: 'INVALID_DATE',
} as const;

/**
 * 判定字符串是否为有效公历日期（YYYY-MM-DD），拒绝 2 月 30 日、13 月、0 日等。
 * 不借助 dayjs：领域层保持零框架依赖；`Date` 构造在跨时区下有歧义，故手工核算天数。
 * 由 `ValuationDraftValidator`（需求 3.2）与 `QueryInputValidator`（需求 2.21）复用。
 * @param value 待判定文本
 * @returns 是否为有效日历日期
 */
export const isValidCalendarDate = (value: string): boolean => {
  const matched = DATE_PATTERN.exec(value);
  if (matched === null) return false;
  const year = Number(matched[1]);
  const month = Number(matched[2]);
  const day = Number(matched[3]);
  if (month < 1 || month > 12) return false;
  const isLeap = (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0;
  const daysInMonth = [31, isLeap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  // month 已限定在 1..12，故索引必然命中；?? 分支仅为满足 noUncheckedIndexedAccess
  const limit = daysInMonth[month - 1] ?? 0;
  return day >= 1 && day <= limit;
};

/** 以字符（码点）为单位计数，与后端 Python `len(str)` 的语义对齐，避免 emoji 被按 UTF-16 单元重复计数 */
const charLength = (value: string): number => Array.from(value).length;

/** 把码全集的中文标签拼成「A、B或C」形式，保证提示文案与码全集同步演进 */
const joinLabels = (labels: readonly string[]): string =>
  labels.length <= 1
    ? labels.join('')
    : `${labels.slice(0, -1).join('、')}或${labels[labels.length - 1]}`;

/**
 * 产品类型提示语中的中文枚举串，顺序与 PRODUCT_TYPES 声明一致。
 * 由 `ValuationDraftValidator`（需求 3.2）复用，使两张表单的产品类型提示文案永不分叉。
 */
export const PRODUCT_TYPE_HINT = joinLabels(PRODUCT_TYPES.map((code) => PRODUCT_TYPE_LABELS[code]));

/** 交易方向提示语中的中文枚举串 */
const TRADE_DIRECTION_HINT = joinLabels(TRADE_DIRECTIONS.map((code) => TRADE_DIRECTION_LABELS[code]));

/** 交易草稿校验器：无状态，可安全复用同一实例 */
export default class TradeDraftValidator {
  /**
   * 校验草稿全部字段。
   * @param draft 待校验草稿；**不变量：方法内不读写以外的任何操作，不修改 draft 的任何字段**（需求 1.2 保留已提交值）
   * @returns 每个无效字段恰好一条 FieldError；枚举字段以 PRODUCT_TYPES / TRADE_DIRECTIONS 的英文码为唯一合法集
   */
  validate(draft: TradeDraftLike): ValidationResult {
    const fieldErrors: FieldError[] = [];
    const push = (error: FieldError | null): void => {
      if (error !== null) fieldErrors.push(error);
    };

    push(TradeDraftValidator.checkEnum('productType', draft.productType, PRODUCT_TYPES, `产品类型必须为${PRODUCT_TYPE_HINT}之一`));
    push(TradeDraftValidator.checkText('productName', draft.productName, MAX_PRODUCT_NAME_LENGTH, '产品名称'));
    push(TradeDraftValidator.checkText('productCode', draft.productCode, MAX_PRODUCT_CODE_LENGTH, '产品代码'));
    push(TradeDraftValidator.checkUnitPrice(draft.unitPrice));
    push(TradeDraftValidator.checkQuantity(draft.quantity));
    push(TradeDraftValidator.checkEnum('direction', draft.direction, TRADE_DIRECTIONS, `交易方向必须为${TRADE_DIRECTION_HINT}之一`));
    push(TradeDraftValidator.checkTradeDate(draft.tradeDate));

    return { valid: fieldErrors.length === 0, fieldErrors };
  }

  /**
   * 枚举字段校验：取值必须严格等于码全集中的某一项。
   * 中文字面量（'理财'）、大小写不符的码（'buy'）、空串与 null / undefined 一律判为 NOT_IN_ENUM。
   */
  private static checkEnum(
    field: string,
    value: string | null | undefined,
    codes: readonly string[],
    message: string,
  ): FieldError | null {
    if (typeof value === 'string' && codes.includes(value)) return null;
    return { field, code: TRADE_ERROR_CODES.NOT_IN_ENUM, message };
  }

  /** 文本字段校验：非空（字符数 >= 1）且不超过上界（需求 1.2 的 1..100 / 1..32） */
  private static checkText(
    field: string,
    value: string | null | undefined,
    maxLength: number,
    label: string,
  ): FieldError | null {
    if (typeof value !== 'string' || value.length === 0) {
      return { field, code: TRADE_ERROR_CODES.REQUIRED, message: `${label}不能为空` };
    }
    if (charLength(value) > maxLength) {
      return { field, code: TRADE_ERROR_CODES.TOO_LONG, message: `${label}不能超过 ${maxLength} 个字符` };
    }
    return null;
  }

  /** 交易单价校验：必须为大于 0 且小数位恰为 2 位的十进制数（需求 1.2） */
  private static checkUnitPrice(value: string | number | null | undefined): FieldError | null {
    const field = 'unitPrice';
    const invalid = '交易单价必须为大于 0 且恰有两位小数的数值';
    if (value === null || value === undefined || value === '') {
      return { field, code: TRADE_ERROR_CODES.REQUIRED, message: '交易单价不能为空' };
    }
    const text = typeof value === 'number' ? String(value) : value;
    if (!DECIMAL_PATTERN.test(text)) {
      return { field, code: TRADE_ERROR_CODES.NOT_A_NUMBER, message: invalid };
    }
    const unsigned = text.replace(/^[+-]/, '');
    const [integerPart = '', fractionPart = ''] = unsigned.split('.');
    if (fractionPart.length !== 2) {
      return { field, code: TRADE_ERROR_CODES.INVALID_SCALE, message: invalid };
    }
    // 以字符串判定正负与是否为零，避免任何浮点运算带来的判定失真
    const isZero = /^0*$/.test(integerPart + fractionPart);
    if (text.startsWith('-') || isZero) {
      return { field, code: TRADE_ERROR_CODES.OUT_OF_RANGE, message: invalid };
    }
    return null;
  }

  /** 交易数量校验：必须为大于 0 的整数（需求 1.2） */
  private static checkQuantity(value: string | number | null | undefined): FieldError | null {
    const field = 'quantity';
    const invalid = '交易数量必须为大于 0 的整数';
    if (value === null || value === undefined || value === '') {
      return { field, code: TRADE_ERROR_CODES.REQUIRED, message: '交易数量不能为空' };
    }
    if (typeof value === 'number') {
      if (!Number.isInteger(value)) return { field, code: TRADE_ERROR_CODES.NOT_INTEGER, message: invalid };
      if (value <= 0) return { field, code: TRADE_ERROR_CODES.OUT_OF_RANGE, message: invalid };
      return null;
    }
    if (!DECIMAL_PATTERN.test(value)) {
      return { field, code: TRADE_ERROR_CODES.NOT_A_NUMBER, message: invalid };
    }
    if (!INTEGER_PATTERN.test(value)) {
      // 含小数点或负号：小数一律非整数，负数以 NOT_INTEGER 之外的 OUT_OF_RANGE 表达更贴切
      return value.includes('.')
        ? { field, code: TRADE_ERROR_CODES.NOT_INTEGER, message: invalid }
        : { field, code: TRADE_ERROR_CODES.OUT_OF_RANGE, message: invalid };
    }
    if (/^\+?0*$/.test(value)) {
      return { field, code: TRADE_ERROR_CODES.OUT_OF_RANGE, message: invalid };
    }
    return null;
  }

  /** 交易日期校验：必须为 YYYY-MM-DD 且是有效日历日期（需求 1.2） */
  private static checkTradeDate(value: string | null | undefined): FieldError | null {
    const field = 'tradeDate';
    if (typeof value !== 'string' || value.length === 0) {
      return { field, code: TRADE_ERROR_CODES.REQUIRED, message: '交易日期不能为空' };
    }
    if (!isValidCalendarDate(value)) {
      return {
        field,
        code: TRADE_ERROR_CODES.INVALID_DATE,
        message: '交易日期必须为有效日历日期，格式为 YYYY-MM-DD',
      };
    }
    return null;
  }
}
