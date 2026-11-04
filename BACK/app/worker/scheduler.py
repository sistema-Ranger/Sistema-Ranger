# BACK/app/worker/scheduler.py
"""Proceso del worker: `python -m app.worker.scheduler`."""

import logging
from datetime import UTC, datetime

from apscheduler.schedulers.blocking import BlockingScheduler

from app.config import get_settings
from app.worker.jobs import Analyzer, cleanup


def main() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=logging.DEBUG if settings.is_development else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    analyzer = Analyzer(settings)
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        analyzer.run_cycle,
        "interval",
        seconds=settings.analysis_interval_seconds,
        id="analyze_all_hosts",
        next_run_time=datetime.now(UTC),
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(cleanup, "cron", hour=3, id="cleanup")
    logging.getLogger(__name__).info(
        "Worker iniciado: análisis cada %ss", settings.analysis_interval_seconds
    )
    scheduler.start()


if __name__ == "__main__":
    main()
