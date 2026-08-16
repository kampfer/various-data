"""受控估值摄取命令；不接受估值覆盖参数，也不注册 HTTP 路由。"""

from __future__ import annotations

import argparse
import json
import logging
from typing import NoReturn

from .orchestrator import IngestRunReport
from .tasks import IngestTaskRequest, OrchestratorIngestTask, ValuationIngestTask

logger = logging.getLogger(__name__)


def buildParser() -> argparse.ArgumentParser:
    """构造只允许受信采集器标识和产品键的运维命令参数。"""
    parser = argparse.ArgumentParser(description="运行受控估值采集任务")
    parser.add_argument(
        "--collector",
        action="append",
        dest="collectors",
        metavar="PLUGIN_ID",
        help="受信采集器标识；省略时运行全部已启用的受信采集器",
    )
    parser.add_argument(
        "--product",
        action="append",
        required=True,
        dest="products",
        metavar="TYPE:CODE",
        help="目标产品键；TYPE 仅允许 WEALTH、FUND 或 STOCK",
    )
    return parser


def parseProduct(value: str) -> tuple[str, str]:
    """解析严格的 TYPE:CODE 产品键，不允许 URL、单价或来源等覆盖字段。"""
    productType, separator, productCode = value.partition(":")
    if not separator or not productType or not productCode or ":" in productCode:
        raise ValueError("产品键必须使用 TYPE:CODE 格式")
    return productType, productCode


def createDefaultTask() -> OrchestratorIngestTask:
    """构造本地命令使用的任务适配器；后台运行器可替换为同一协议实现。"""
    return OrchestratorIngestTask()


def _reportPayload(report: IngestRunReport) -> dict[str, object]:
    """把内部运行报告转换为不含原始载荷的可审计 JSON 输出。"""
    failed = sum(result.error is not None for result in report.results)
    skipped = sum(result.skipped for result in report.results)
    return {
        "accepted": report.accepted,
        "skipped": skipped,
        "failed": failed,
        "collectors": [
            {
                "pluginId": result.plugin_id,
                "accepted": result.accepted,
                "skipped": result.skipped,
                "error": result.error,
                "attempts": result.attempts,
                "durationSeconds": result.duration_seconds,
            }
            for result in report.results
        ],
    }


def _argumentError(parser: argparse.ArgumentParser, error: Exception) -> NoReturn:
    """将受控参数校验错误统一交给 argparse，以固定状态码 2 退出。"""
    parser.error(str(error))


def main(argv: list[str] | None = None, *, task: ValuationIngestTask | None = None) -> int:
    """执行一次内部摄取，输出审计结果，并用退出状态标记隔离失败。"""
    parser = buildParser()
    args = parser.parse_args(argv)
    try:
        request = IngestTaskRequest(
            product_keys=tuple(parseProduct(item) for item in args.products),
            collector_ids=tuple(args.collectors) if args.collectors else None,
        )
    except ValueError as error:
        _argumentError(parser, error)
    try:
        report = (task or createDefaultTask()).run(request)
    except Exception:
        logger.exception("valuation_ingest_failed phase=task")
        print(json.dumps({"accepted": 0, "skipped": 0, "failed": 1, "collectors": []}, ensure_ascii=False))
        return 1
    payload = _reportPayload(report)
    logger.info(
        "valuation_ingest_completed accepted=%s skipped=%s failed=%s collector_count=%s",
        payload["accepted"],
        payload["skipped"],
        payload["failed"],
        len(report.results),
    )
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if payload["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
