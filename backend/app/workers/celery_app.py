from celery import Celery
from app.core.config import settings

# 创建Celery应用实例
celery_app = Celery(
    "invoice_system",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.workers.ocr_tasks",
        "app.workers.email_tasks",
        "app.workers.monitoring_tasks"
    ]
)

# 配置Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    # 暂时移除队列路由，让所有任务都使用默认队列
    # task_routes={
    #     "app.workers.ocr_tasks.*": {"queue": "ocr"},
    #     "app.workers.email_tasks.*": {"queue": "email"},
    # },
    beat_schedule={
        # 每30分钟扫描一次邮箱
        "scan-emails-every-30-minutes": {
            "task": "app.workers.email_tasks.scan_emails_task",
            "schedule": 30.0 * 60,
        },
        # 监控类周期任务
        "collect-system-metrics-every-5-minutes": {
            "task": "app.workers.monitoring_tasks.collect_system_metrics",
            "schedule": 5.0 * 60,
        },
        "check-performance-alerts-every-10-minutes": {
            "task": "app.workers.monitoring_tasks.check_performance_alerts",
            "schedule": 10.0 * 60,
        },
        "analyze-task-performance-every-hour": {
            "task": "app.workers.monitoring_tasks.analyze_task_performance",
            "schedule": 60.0 * 60,
            "args": [1],
        },
    },
)

# 自动发现任务
celery_app.autodiscover_tasks(['app.workers'])