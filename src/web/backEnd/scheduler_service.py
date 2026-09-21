"""定时任务调度器独立服务入口。

将原本随 FastAPI Web 服务一起启动的调度器提取为独立进程运行，
便于将 Web 服务与定时任务解耦、单独部署与重启。

调度器实际执行的任务及其数据依赖（见 app/tasks/）：
    - crawlSinaNews：每小时抓取新浪财经快讯，写入 sinaFinanceNews 相关表
    - crawlOMO：每天抓取央行公开市场操作，写入 omo 相关表（含 app_state）
    - backupDatabase：每月拷贝数据库文件，无需任何 model
    - pickStock：未注册定时任务，仅供调试，无数据库依赖

因此本服务只初始化上述任务真正用到的表（新浪快讯、OMO），
不涉及 Web 端投资台账（investmentLedger）的表结构。

启动方式（在 backEnd 目录下）：
    python scheduler_service.py
"""

from app.database import engine
from app.sinaFinanceNews.models import Base as SinaNewsBase
from app.omo.models import Base as OMOBase
from app.scheduler import initScheduler


def initSchedulerModels() -> None:
    """仅创建定时任务所依赖的表：新浪财经快讯与央行公开市场操作。"""
    SinaNewsBase.metadata.create_all(bind=engine)
    OMOBase.metadata.create_all(bind=engine)


def main() -> None:
    # 确保定时任务依赖的表已创建（仅新浪快讯与 OMO，不含投资台账）
    initSchedulerModels()

    # 独立服务使用阻塞式调度器，占用主线程持续运行
    scheduler = initScheduler(blocking=True)
    print("定时任务调度器独立服务启动中……（按 Ctrl+C 退出）")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        # 收到中断信号时优雅关闭，等待正在执行的任务结束
        scheduler.shutdown(wait=True)
        print("定时任务调度器已关闭")


if __name__ == "__main__":
    main()
