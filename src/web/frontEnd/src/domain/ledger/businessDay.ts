import type { Dayjs } from 'dayjs';

/**
 * 计算交易日期之后的下一个工作日。
 *
 * 当前账本未接入节假日交易日历，因此工作日按周一至周五计算；
 * 周五、周六、周日分别顺延到下周一。函数不修改传入的 Dayjs 实例。
 */
export const nextWorkingDay = (value: Dayjs): Dayjs => {
  let next = value.add(1, 'day');
  while (next.day() === 0 || next.day() === 6) {
    next = next.add(1, 'day');
  }
  return next;
};
