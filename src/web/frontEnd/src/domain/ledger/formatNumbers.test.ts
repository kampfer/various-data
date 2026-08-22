// 数值展示格式化工具的定向测试
//
// 覆盖：
//   1. formatDecimalScale：四舍五入到指定小数位，全程不使用浮点
//   2. formatPriceByProductType：基金/理财净值 4 位小数，股票原样
import { describe, expect, it } from 'vitest';
import { formatDecimalScale, formatPriceByProductType } from './formatNumbers';

describe('formatDecimalScale', () => {
  it('不足小数位补 0', () => {
    expect(formatDecimalScale('1.23', 4)).toBe('1.2300');
    expect(formatDecimalScale('5', 4)).toBe('5.0000');
    expect(formatDecimalScale('0', 4)).toBe('0.0000');
    expect(formatDecimalScale('0.5', 4)).toBe('0.5000');
  });

  it('超过小数位按四舍五入处理', () => {
    expect(formatDecimalScale('1.23454', 4)).toBe('1.2345');
    expect(formatDecimalScale('1.23455', 4)).toBe('1.2346');
    expect(formatDecimalScale('0.99999', 4)).toBe('1.0000');
    expect(formatDecimalScale('9.99995', 4)).toBe('10.0000');
    expect(formatDecimalScale('0.00001', 4)).toBe('0.0000');
    expect(formatDecimalScale('0.00005', 4)).toBe('0.0001');
  });

  it('scale=0 四舍五入到整数', () => {
    expect(formatDecimalScale('3.4', 0)).toBe('3');
    expect(formatDecimalScale('3.5', 0)).toBe('4');
    expect(formatDecimalScale('999.999', 0)).toBe('1000');
  });

  it('空值与非法文本原样返回，不破坏用户输入', () => {
    expect(formatDecimalScale('', 4)).toBe('');
    expect(formatDecimalScale(null, 4)).toBe('');
    expect(formatDecimalScale(undefined, 4)).toBe('');
    expect(formatDecimalScale('NaN', 4)).toBe('NaN');
    expect(formatDecimalScale('abc', 4)).toBe('abc');
  });

  it('处理整数与纯小数边界', () => {
    expect(formatDecimalScale('0001.23', 4)).toBe('1.2300');
    expect(formatDecimalScale('0.0000', 4)).toBe('0.0000');
  });
});

describe('formatPriceByProductType', () => {
  it('基金净值固定 4 位小数', () => {
    expect(formatPriceByProductType('1.23', 'FUND')).toBe('1.2300');
    expect(formatPriceByProductType('1.23456', 'FUND')).toBe('1.2346');
  });

  it('理财净值固定 4 位小数', () => {
    expect(formatPriceByProductType('2.5', 'WEALTH')).toBe('2.5000');
    expect(formatPriceByProductType('0.99999', 'WEALTH')).toBe('1.0000');
  });

  it('股票单价保持原样，不施加精度限制', () => {
    expect(formatPriceByProductType('10.123', 'STOCK')).toBe('10.123');
    expect(formatPriceByProductType('999.99', 'STOCK')).toBe('999.99');
    expect(formatPriceByProductType('12345.6789012345', 'STOCK')).toBe('12345.6789012345');
  });

  it('产品类型为空时原样返回（股票默认口径）', () => {
    expect(formatPriceByProductType('1.23', null)).toBe('1.23');
    expect(formatPriceByProductType('1.23', undefined)).toBe('1.23');
  });
});
