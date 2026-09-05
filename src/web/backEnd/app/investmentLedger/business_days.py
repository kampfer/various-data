"""投资账本中的工作日计算工具。"""

from datetime import date, timedelta


def next_working_day(value: date) -> date:
    """返回日期之后的下一个工作日。

    当前项目没有接入节假日交易日历，因此工作日按周一至周五计算；
    周五、周六、周日分别顺延到下周一。函数不会修改传入的日期对象。
    """
    next_day = value + timedelta(days=1)
    while next_day.weekday() >= 5:
        next_day += timedelta(days=1)
    return next_day
