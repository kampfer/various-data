// 数值展示格式化工具
//
// 设计要点：
//   1. 全程不使用浮点数（parseFloat / Number / Math.*），仅基于字符串和 BigInt 的数位操作，
//      避免金融数值出现 0.1+0.2=0.30000000000000004 这类误差；
//   2. 支持按产品类型差异化精度（基金/理财净值 4 位，股票数量无限制）；
//   3. 空值或非法十进制文本按原值返回，不破坏用户输入。

import type { ProductType } from './constants';

/** 接受普通十进制文本；与 TradeDraftValidator.DECIMAL_PATTERN 一致。 */
const DECIMAL_PATTERN = /^[+-]?\d+(\.\d+)?$/;

/**
 * 把十进制字符串按固定小数位格式化。
 *
 * @param value 原始十进制字符串；空值或非法文本原样返回（避免破坏输入）
 * @param scale 目标小数位数，非负整数
 * @returns 格式化后的字符串；如 ``scale=4`` 则 ``"1.23"`` → ``"1.2300"``，
 *          ``"1.23456"`` → ``"1.2346"``（四舍五入）
 */
export function formatDecimalScale(value: string | null | undefined, scale: number): string {
  if (value === null || value === undefined || value === '') return value ?? '';
  const trimmed = value.trim();
  if (!DECIMAL_PATTERN.test(trimmed)) return value;
  if (scale < 0) return value;

  const sign = trimmed.startsWith('-') ? '-' : '';
  const unsigned = trimmed.replace(/^[+-]/, '');
  const dotIndex = unsigned.indexOf('.');
  const intPart = dotIndex >= 0 ? unsigned.slice(0, dotIndex) : unsigned;
  const fracPart = dotIndex >= 0 ? unsigned.slice(dotIndex + 1) : '';
  // 去掉整数部分前导 0，至少保留一个 0 保证纯 0 场景正确
  const normalizedInt = intPart.replace(/^0+/, '') || '0';

  if (scale === 0) {
    // 按个位四舍五入
    if (fracPart.length === 0 || Number(fracPart[0]) < 5) return `${sign}${normalizedInt}`;
    return `${sign}${(BigInt(normalizedInt) + 1n).toString()}`;
  }

  // fracPart 长度 < scale：右侧补 0
  // fracPart 长度 = scale：直接使用
  // fracPart 长度 > scale：按第 scale+1 位四舍五入
  if (fracPart.length <= scale) {
    const padded = fracPart.padEnd(scale, '0');
    return `${sign}${normalizedInt}.${padded}`;
  }

  const kept = fracPart.slice(0, scale);
  const roundDigit = fracPart[scale];
  let fracValue = BigInt(kept);
  const intValue = BigInt(normalizedInt);
  if (Number(roundDigit) >= 5) {
    fracValue += 1n;
    const fracMax = 10n ** BigInt(scale);
    if (fracValue >= fracMax) {
      fracValue = fracValue - fracMax;
      const newInt = (intValue + 1n).toString();
      const newFrac = fracValue.toString().padStart(scale, '0');
      return `${sign}${newInt}.${newFrac}`;
    }
  }
  const newFrac = fracValue.toString().padStart(scale, '0');
  return `${sign}${normalizedInt}.${newFrac}`;
}

/**
 * 按产品类型格式化净值/单价：基金/理财固定 4 位小数，股票保持原样。
 *
 * 用于历史记录表格净值/单价列（render）与新建表单净值输入的失焦展示。
 */
export function formatPriceByProductType(
  value: string | null | undefined,
  productType: ProductType | null | undefined,
): string {
  if (productType === 'FUND' || productType === 'WEALTH') {
    return formatDecimalScale(value, 4);
  }
  // 股票单价：不施加精度限制，原样返回
  return value ?? '';
}

/**
 * 按产品类型格式化份额/数量：股票数量整数校验由 validator 保证，
 * 理财/基金份额展示不固定精度，原样返回。
 *
 * 目前未对数量列施加展示精度限制，本函数保留为未来扩展入口。
 */
export function formatQuantityByProductType(
  value: string | null | undefined,
  _productType: ProductType | null | undefined,
): string {
  return value ?? '';
}

export default formatDecimalScale;
