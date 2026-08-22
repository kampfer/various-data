// 交易金额计算工具的定向测试（需求 6.1、6.5、6.6）
//
// 覆盖：
//   1. 基本公式：交易金额 = 价格 × 数量 + 费用
//   2. 空值按 0 处理，保证未完成输入也能给出确定展示值
//   3. 高精度十进制运算，不经过浮点数（与项目「金额不使用浮点」约束一致）
//   4. 非法文本按 0 处理，展示始终有值
//   5. 固定保留两位小数（四舍五入）
import { describe, expect, it } from 'vitest';
import computeTransactionAmount from './transactionAmount';

describe('computeTransactionAmount', () => {
  it('计算 交易金额 = 价格 × 数量 + 费用，固定两位小数', () => {
    // 1.2345 × 2.5 + 0 = 3.08625 → 四舍五入到 3.09
    expect(computeTransactionAmount('1.2345', '2.5', '0')).toBe('3.09');
    // 10.123 × 100 + 5.00 = 1017.3 → 1017.30
    expect(computeTransactionAmount('10.123', '100', '5.00')).toBe('1017.30');
    // 整数场景：100 × 10 + 15 = 1015 → 1015.00
    expect(computeTransactionAmount('100', '10', '15')).toBe('1015.00');
  });

  it('费用为 0 或未提供时结果相同（空值按 0 处理）', () => {
    expect(computeTransactionAmount('1.5', '10', '0')).toBe('15.00');
    expect(computeTransactionAmount('1.5', '10', null)).toBe('15.00');
    expect(computeTransactionAmount('1.5', '10', undefined)).toBe('15.00');
    expect(computeTransactionAmount('1.5', '10', '')).toBe('15.00');
  });

  it('价格为空或数量为空时按 0 计算，仅展示费用', () => {
    expect(computeTransactionAmount(null, null, '5.00')).toBe('5.00');
    expect(computeTransactionAmount('', '', '5.00')).toBe('5.00');
    expect(computeTransactionAmount(null, null, '5.50')).toBe('5.50');
  });

  it('全部输入为空时返回 0.00', () => {
    expect(computeTransactionAmount(null, null, null)).toBe('0.00');
    expect(computeTransactionAmount(undefined, undefined, undefined)).toBe('0.00');
  });

  it('使用 BigInt 精确运算高精度十进制，不产生浮点误差', () => {
    // 0.1 × 0.2 + 0 = 0.02（浮点会得到 0.020000000000000004）
    expect(computeTransactionAmount('0.1', '0.2', '0')).toBe('0.02');
    // 任意精度四舍五入：1.000000000000000001 × 2 + 0 = 2.000000000000000002 → 2.00
    expect(computeTransactionAmount('1.000000000000000001', '2', '0')).toBe('2.00');
  });

  it('非法十进制文本按 0 处理，展示始终有值', () => {
    expect(computeTransactionAmount('NaN', '2', '5')).toBe('5.00');
    expect(computeTransactionAmount('abc', '2', '5')).toBe('5.00');
    expect(computeTransactionAmount('1.5', 'NaN', '5')).toBe('5.00');
  });

  it('固定保留两位小数，不足补 0', () => {
    // 1.5 × 2 + 0 = 3 → 3.00
    expect(computeTransactionAmount('1.5', '2', '0')).toBe('3.00');
    // 1.25 × 4 + 0 = 5 → 5.00
    expect(computeTransactionAmount('1.25', '4', '0')).toBe('5.00');
    // 1.1 × 1.1 + 0 = 1.21
    expect(computeTransactionAmount('1.1', '1.1', '0')).toBe('1.21');
  });

  it('第三位小数四舍五入', () => {
    // 1.005 × 1 + 0 = 1.005 → 1.01（四舍五入）
    expect(computeTransactionAmount('1.005', '1', '0')).toBe('1.01');
    // 1.004 × 1 + 0 = 1.004 → 1.00
    expect(computeTransactionAmount('1.004', '1', '0')).toBe('1.00');
    // 1.234 × 1 + 0 = 1.234 → 1.23
    expect(computeTransactionAmount('1.234', '1', '0')).toBe('1.23');
    // 1.235 × 1 + 0 = 1.235 → 1.24
    expect(computeTransactionAmount('1.235', '1', '0')).toBe('1.24');
  });
});
