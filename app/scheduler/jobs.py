"""Persistent scheduler setup and job lifecycle management using APScheduler and SQLite."""

import logging
from datetime import datetime
from typing import Optional
from aiogram import Bot
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.scheduler.reminders import execute_reminder_job, execute_vague_clarification_job, set_bot_instance

logger = logging.getLogger(__name__)


class SchedulerService:
    """Encapsulates persistent APScheduler instance with SQLite jobstore."""

    def __init__(self, db_url: Optional[str] = None) -> None:
        self.db_url = db_url or settings.SCHEDULER_DATABASE_URL
        jobstores = {
            "default": SQLAlchemyJobStore(url=self.db_url),
        }
        job_defaults = {
            "coalesce": True,
            "max_instances": 3,
            "misfire_grace_time": 300,  # 5 minutes grace time for delayed executions after restart
        }
        self.scheduler = AsyncIOScheduler(jobstores=jobstores, job_defaults=job_defaults)

    def start(self, bot: Bot) -> None:
        """Start scheduler and bind active bot instance."""
        set_bot_instance(bot)
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info(f"Persistent APScheduler started with SQLite jobstore: {self.db_url}")

    def shutdown(self, wait: bool = False) -> None:
        """Safely shut down the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=wait)
            logger.info("Persistent APScheduler shutdown complete.")

    def schedule_reminder(self, reminder_id: int, run_date: datetime) -> str:
        """
        Schedule a persistent reminder job that triggers at run_date.
        Returns unique job ID.
        """
        job_id = f"rem_{reminder_id}"
        self.scheduler.add_job(
            execute_reminder_job,
            trigger="date",
            run_date=run_date,
            args=[reminder_id],
            id=job_id,
            replace_existing=True,
        )
        logger.info(f"Scheduled persistent reminder {reminder_id} at {run_date} (job_id: {job_id})")
        return job_id

    def schedule_vague_clarification(self, clarification_id: int, clarify_at: datetime) -> str:
        """
        Schedule a persistent vague-time clarification ping.
        Returns unique job ID.
        """
        job_id = f"clrf_{clarification_id}"
        self.scheduler.add_job(
            execute_vague_clarification_job,
            trigger="date",
            run_date=clarify_at,
            args=[clarification_id],
            id=job_id,
            replace_existing=True,
        )
        logger.info(f"Scheduled persistent clarification {clarification_id} at {clarify_at} (job_id: {job_id})")
        return job_id

    def reschedule_reminder(self, reminder_id: int, new_run_date: datetime) -> str:
        """Reschedule an existing reminder job (e.g. on snooze)."""
        job_id = f"rem_{reminder_id}"
        self.scheduler.add_job(
            execute_reminder_job,
            trigger="date",
            run_date=new_run_date,
            args=[reminder_id],
            id=job_id,
            replace_existing=True,
        )
        logger.info(f"Rescheduled reminder {reminder_id} to {new_run_date}")
        return job_id

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a scheduled job by its ID."""
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Cancelled scheduler job {job_id}")
            return True
        except Exception as e:
            logger.warning(f"Could not cancel job {job_id}: {e}")
            return False


# Global singleton instance
scheduler_service = SchedulerService()
