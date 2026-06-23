"""调度引擎控制 API"""

from fastapi import APIRouter

from app.services.scheduler.engine import get_scheduler

router = APIRouter()


@router.get("/scheduler/status")
async def scheduler_status():
    """获取调度引擎状态"""
    scheduler = get_scheduler()
    return {
        "running": scheduler._running,
        "task_count": len(scheduler._tasks),
        "task_names": [t.get_name() for t in scheduler._tasks if not t.done()],
    }


@router.post("/scheduler/start")
async def scheduler_start():
    """启动调度引擎"""
    scheduler = get_scheduler()
    await scheduler.start()
    return {"status": "started"}


@router.post("/scheduler/stop")
async def scheduler_stop():
    """停止调度引擎"""
    scheduler = get_scheduler()
    await scheduler.stop()
    return {"status": "stopped"}
