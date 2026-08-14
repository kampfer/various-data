// QueryInputValidator 示例单元测试：任务 10.8；属性测试由独立任务 10.9 覆盖。
// Validates: Requirements 2.20, 2.21, 2.25, 2.26, 2.30, 2.31
import { describe, expect, it } from 'vitest';
import QueryInputValidator from './QueryInputValidator';

const validator = new QueryInputValidator();
const expectValid = (result: ReturnType<QueryInputValidator['validatePage']>): void => {
  expect(result).toEqual({ valid: true, fieldErrors: [] });
};

const expectChineseError = (
  result: ReturnType<QueryInputValidator['validatePage']>,
  field: string,
): void => {
  expect(result.valid).toBe(false);
  expect(result.fieldErrors).toHaveLength(1);
  expect(result.fieldErrors[0]?.field).toBe(field);
  expect(result.fieldErrors[0]?.message).toMatch(/[\u4e00-\u9fa5]/);
  expect(Object.keys(result).sort()).toEqual(['fieldErrors', 'valid']);
};

describe('QueryInputValidator', () => {
  it('接受 1..100 个 Unicode 字符的搜索值并拒绝空值或超长值', () => {
    expectValid(validator.validateSearchValue('基金'));
    expectValid(validator.validateSearchValue('🚀'.repeat(100)));
    expectChineseError(validator.validateSearchValue(''), 'searchValue');
    expectChineseError(validator.validateSearchValue('🚀'.repeat(101)), 'searchValue');
  });

  it('接受未启用或成对、有效且有序的日期范围', () => {
    expectValid(validator.validateDateRange(null, null));
    expectValid(validator.validateDateRange('2024-02-29', '2024-02-29'));
    expectValid(validator.validateDateRange('2023-12-31', '2024-01-01'));
  });

  it.each([
    ['2024-01-01', null],
    [null, '2024-01-01'],
    ['2024-02-30', '2024-03-01'],
    ['2024-03-02', '2024-03-01'],
  ] as const)('拒绝缺项、无效日历日期或倒置的日期范围 %s..%s', (start, end) => {
    expectChineseError(validator.validateDateRange(start, end), 'startDate');
  });

  it.each([1, 100])('接受边界内整数页大小 %s', (size) => {
    expectValid(validator.validatePageSize(size));
  });

  it.each([0, 101, 1.5, '20', null, Number.NaN])('拒绝非 1..100 整数页大小 %s', (size) => {
    const result = validator.validatePageSize(size);
    expectChineseError(result, 'pageSize');
    expect(result.fieldErrors[0]?.message).toBe('自定义页大小必须为 1 至 100 的整数');
  });

  it('仅接受 1..总页数内的整数页码', () => {
    expectValid(validator.validatePage(1, 3));
    expectValid(validator.validatePage(3, 3));
    expectChineseError(validator.validatePage(0, 3), 'page');
    expectChineseError(validator.validatePage(4, 3), 'page');
    expectChineseError(validator.validatePage(1.5, 3), 'page');
    expect(validator.validatePage(4, 3).fieldErrors[0]?.message).toContain('有效页码为 1 至 3');
  });

  it('总页数为 0 时任何页码均无效，并返回无可浏览页提示', () => {
    const result = validator.validatePage(1, 0);

    expectChineseError(result, 'page');
    expect(result.fieldErrors[0]?.message).toBe('当前结果没有可浏览的页');
  });
});