"""投资交易账本的纯计算组件。

本模块只处理内存中的领域值，不访问数据库、网络或文件系统。
"""

from __future__ import annotations

from typing import TypeVar

from app.investmentLedger.exceptions import PageOutOfRange


ItemT = TypeVar("ItemT")


class Paginator:
    """与条目类型无关的分页切片器（需求 2.11、2.24-2.31）。"""

    def slice(
        self, items: list[ItemT], page: int, pageSize: int
    ) -> tuple[list[ItemT], int]:
        """返回请求页的有序切片及总页数。

        空结果的总页数为 0；非空结果请求超过最后一页时抛出领域异常。
        """
        total = len(items)
        pageCount = (total + pageSize - 1) // pageSize if total else 0

        isIntegerPage = isinstance(page, int) and not isinstance(page, bool)
        if not isIntegerPage or page < 1 or (pageCount > 0 and page > pageCount):
            raise PageOutOfRange(page=page, pageCount=pageCount)

        start = (page - 1) * pageSize
        return items[start : start + pageSize], pageCount


class Paginator2:
    """分页参数工具（无状态，纯静态方法）。"""

    @staticmethod
    def get_limit_offset(page: int, page_size: int) -> tuple[int, int]:
        """将页码和页大小转换为数据库分页参数。"""
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20
        offset = (page - 1) * page_size
        return page_size, offset

    @staticmethod
    def get_page_count(total: int, page_size: int) -> int:
        """根据总记录数和每页条数计算总页数。"""
        if total <= 0 or page_size <= 0:
            return 0
        return (total + page_size - 1) // page_size
