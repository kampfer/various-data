// 交易金额计算工具（需求 6.1、6.5、6.6）
//
// 设计要点：
//   1. 交易金额 = 交易价格 × 交易数量 + 费用，纯前端展示，不落库、不传输、不写入 Redux 状态。
//   2. 使用 BigInt 进行精确的十进制运算，避免 JavaScript Number 的浮点误差
//      （项目约束：金额/比率不在前端使用浮点计算）。
//   3. 空值或非法十进制文本按 0 处理，保证展示始终有值（即使输入未完成）。
//   4. 仅作为展示辅助，不参与校验、不进入 TradeDraft 持久化字段、不进入网络请求体。

/** 十进制解析结果：value 为去掉小数点后的整数（保留符号），scale 为小数位数。 */
interface ParsedDecimal {
  readonly value: bigint;
  readonly scale: number;
}

/** 接受普通十进制文本；与 TradeDraftValidator.DECIMAL_PATTERN 一致。 */
const DECIMAL_PATTERN = /^[+-]?\d+(\.\d+)?$/;

/**
 * 把十进制字符串解析为整数与小数位数，用于精确的十进制运算。
 *
 * 空值、undefined 或非法文本返回 ``{ value: 0n, scale: 0 }``，
 * 使未完成的输入也能给出确定的展示值（按 0 处理）。
 */
function parseDecimal(value: string | null | undefined): ParsedDecimal {
  if (value === null || value === undefined || value === '') return { value: 0n, scale: 0 };
  const trimmed = value.trim();
  if (!DECIMAL_PATTERN.test(trimmed)) return { value: 0n, scale: 0 };
  const sign = trimmed.startsWith('-') ? -1n : 1n;
  const unsigned = trimmed.replace(/^[+-]/, '');
  const [intPart, fracPart = ''] = unsigned.split('.');
  const scale = fracPart.length;
  // 去掉前导 0 避免 BigInt 解析异常（'0' 本身合法）
  const digits = (intPart + fracPart).replace(/^0+/, '') || '0';
  return { value: sign * BigInt(digits), scale };
}

/**
 * 把整数与小数位数格式化为十进制字符串，固定保留两位小数。
 *
 * 不足两位时补 0，超过两位时四舍五入到两位；值为 0 时返回 ``"0.00"``。
 */
function formatDecimal(value: bigint, scale: number): string {
  const sign = value < 0n ? '-' : '';
  const unsigned = value < 0n ? -value : value;

  // 四舍五入到两位小数：若 scale > 2，按第 3 位小数四舍五入
  let roundedValue = unsigned;
  let roundedScale = scale;
  if (scale > 2) {
    const divisor = 10n ** BigInt(scale - 2);
    const quotient = roundedValue / divisor;
    const remainder = roundedValue % divisor;
    // 余数 >= 除数的一半则进位（四舍五入）
    if (remainder * 2n >= divisor) {
      roundedValue = quotient + 1n;
    } else {
      roundedValue = quotient;
    }
    roundedScale = 2;
  }

  // 补足到两位小数：整数部分 + 两位小数
  const padded = roundedValue.toString().padStart(roundedScale + 1, '0');
  const intPart = padded.slice(0, padded.length - roundedScale);
  const fracPart = padded.slice(padded.length - roundedScale).padEnd(2, '0');
  return `${sign}${intPart}.${fracPart}`;
}

/**
 * 计算交易金额 = 交易价格 × 交易数量 + 费用（需求 6.1、6.5）。
 *
 * 使用 BigInt 进行精确的十进制运算，全程不经过浮点数；空值按 0 处理。
 * 仅用于前端展示，不落库、不传输、不写入 Redux 状态或交易草稿（需求 6.6）。
 *
 * @param price 交易价格/净值或单价的原始十进制文本，空值按 0
 * @param quantity 交易数量/份额或数量的原始十进制文本，空值按 0
 * @param fee 费用的原始十进制文本，空值按 0
 * @returns 交易金额展示文本，如 ``"123.45"``；输入均为空时返回 ``"0"``
 */
export function computeTransactionAmount(
  price: string | null | undefined,
  quantity: string | null | undefined,
  fee: string | null | undefined,
): string {
  const priceDecimal = parseDecimal(price);
  const quantityDecimal = parseDecimal(quantity);
  const feeDecimal = parseDecimal(fee);

  // 乘法：price × quantity，value 相乘、scale 相加
  const productValue = priceDecimal.value * quantityDecimal.value;
  const productScale = priceDecimal.scale + quantityDecimal.scale;

  // 加法：product + fee，对齐小数位数后再相加
  const maxScale = Math.max(productScale, feeDecimal.scale);
  const productAdjusted = productValue * (10n ** BigInt(maxScale - productScale));
  const feeAdjusted = feeDecimal.value * (10n ** BigInt(maxScale - feeDecimal.scale));
  const sumValue = productAdjusted + feeAdjusted;

  return formatDecimal(sumValue, maxScale);
}

export default computeTransactionAmount;
