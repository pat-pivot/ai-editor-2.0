"""
AI Editor 2.0 - Redis Queue Worker
Main entry point for background job processing

Usage:
    # Run worker only
    python worker.py

    # Run worker with scheduler (for cron jobs)
    python worker.py --with-scheduler

Schedule (ET → UTC):
    Step 1: Pre-filter      - 9:00 PM ET  = 2:00 AM UTC
    Step 2: Slot Selection  - 9:15 PM ET  = 2:15 AM UTC
    Step 3: Decoration      - 9:25 PM ET  = 2:25 AM UTC
    Step 3b: Images         - 9:30 PM ET  = 2:30 AM UTC
    Step 4: HTML Compile    - 10:00 PM ET = 3:00 AM UTC
    Step 4b: Mautic Send    - 5:00 AM ET  = 10:00 AM UTC
    Step 5: Social Sync     - 4:30 AM ET  = 9:30 AM UTC
    Step 5b: Social Sync 2  - 5:00 AM ET  = 10:00 AM UTC

    Scheduled Send Checker  - Every 5 minutes (checks for user-scheduled newsletters)
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from redis import Redis
from rq import Worker, Queue
from rq_scheduler import Scheduler

# Load environment variables
load_dotenv()

# Redis connection
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')


def get_redis_connection():
    """Get Redis connection from URL"""
    return Redis.from_url(REDIS_URL)


def setup_scheduled_jobs(scheduler: Scheduler):
    """
    Configure all scheduled jobs for the AI Editor 2.0 pipeline.

    Days: Tuesday-Saturday (newsletter is Mon-Fri delivery, prepared night before)
    All times in UTC
    """
    from jobs.prefilter import prefilter_stories
    from jobs.slot_selection import select_slots
    from jobs.decoration import decorate_stories
    from jobs.image_generation import generate_images
    from jobs.html_compile import compile_html
    from jobs.mautic_send import send_via_mautic
    from jobs.social_sync import sync_social_posts
    from jobs.scheduled_send_checker import check_scheduled_newsletters

    # Clear existing scheduled jobs
    for job in scheduler.get_jobs():
        scheduler.cancel(job)

    print("[Scheduler] Setting up scheduled jobs...")

    # Step 1: Pre-filter - 9:00 PM ET = 2:00 AM UTC (Tue-Sat)
    scheduler.cron(
        '0 2 * * 2-6',  # minute hour day month day_of_week
        func=prefilter_stories,
        queue_name='default',
        id='step1_prefilter',
        description='Step 1: Pre-filter stories by slot eligibility'
    )
    print("[Scheduler] Step 1 (prefilter) scheduled: 2:00 AM UTC Tue-Sat")

    # Step 2: Slot Selection - 9:15 PM ET = 2:15 AM UTC (Tue-Sat)
    scheduler.cron(
        '15 2 * * 2-6',
        func=select_slots,
        queue_name='high',
        id='step2_slot_selection',
        description='Step 2: Claude agents select 5 stories'
    )
    print("[Scheduler] Step 2 (slot_selection) scheduled: 2:15 AM UTC Tue-Sat")

    # Step 3: Decoration - 9:25 PM ET = 2:25 AM UTC (Tue-Sat)
    scheduler.cron(
        '25 2 * * 2-6',
        func=decorate_stories,
        queue_name='default',
        id='step3_decoration',
        description='Step 3: Generate headlines, deks, bullets'
    )
    print("[Scheduler] Step 3 (decoration) scheduled: 2:25 AM UTC Tue-Sat")

    # Step 3b: Image Generation - 9:30 PM ET = 2:30 AM UTC (Tue-Sat)
    scheduler.cron(
        '30 2 * * 2-6',
        func=generate_images,
        queue_name='default',
        id='step3b_images',
        description='Step 3b: Generate images via Gemini Imagen 3'
    )
    print("[Scheduler] Step 3b (images) scheduled: 2:30 AM UTC Tue-Sat")

    # Step 4: HTML Compile - 10:00 PM ET = 3:00 AM UTC (Tue-Sat)
    scheduler.cron(
        '0 3 * * 2-6',
        func=compile_html,
        queue_name='default',
        id='step4_html_compile',
        description='Step 4: Compile HTML email template'
    )
    print("[Scheduler] Step 4 (html_compile) scheduled: 3:00 AM UTC Tue-Sat")

    # Step 4b: Mautic Send - 5:00 AM ET = 10:00 AM UTC (Tue-Sat)
    scheduler.cron(
        '0 10 * * 2-6',
        func=send_via_mautic,
        queue_name='high',
        id='step4b_mautic_send',
        description='Step 4b: Send newsletter via Mautic'
    )
    print("[Scheduler] Step 4b (mautic_send) scheduled: 10:00 AM UTC Tue-Sat")

    # Step 5: Social Sync - 4:30 AM ET = 9:30 AM UTC (Tue-Sat)
    scheduler.cron(
        '30 9 * * 2-6',
        func=sync_social_posts,
        queue_name='low',
        id='step5_social_sync',
        description='Step 5: Syndicate to P5 Social Posts'
    )
    print("[Scheduler] Step 5 (social_sync) scheduled: 9:30 AM UTC Tue-Sat")

    # Step 5b: Social Sync (second run) - 5:00 AM ET = 10:00 AM UTC (Tue-Sat)
    scheduler.cron(
        '0 10 * * 2-6',
        func=sync_social_posts,
        queue_name='low',
        id='step5b_social_sync_2',
        description='Step 5b: Second social sync run'
    )
    print("[Scheduler] Step 5b (social_sync_2) scheduled: 10:00 AM UTC Tue-Sat")

    # Scheduled Send Checker - Every 5 minutes (all days)
    # Checks for newsletters with status='scheduled' and sends when their time arrives
    scheduler.cron(
        '*/5 * * * *',  # Every 5 minutes
        func=check_scheduled_newsletters,
        queue_name='high',
        id='scheduled_send_checker',
        description='Check for scheduled newsletters and trigger sends'
    )
    print("[Scheduler] Scheduled Send Checker: Every 5 minutes")

    print("[Scheduler] All jobs scheduled successfully")


def run_scheduler():
    """Run the RQ scheduler for cron jobs"""
    conn = get_redis_connection()
    scheduler = Scheduler(connection=conn)

    # Setup all scheduled jobs
    setup_scheduled_jobs(scheduler)

    print(f"[Scheduler] Starting scheduler at {datetime.utcnow().isoformat()}")
    scheduler.run()


def warmup_database():
    """
    Warm up database connection on startup.
    Render free tier PostgreSQL can be cold - this ensures it's ready before jobs run.
    """
    try:
        from utils.db import get_db
        db = get_db()
        # Simple query to wake up the database
        with db.get_cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        print("[Worker] Database connection warm-up successful")
        return True
    except Exception as e:
        print(f"[Worker] Database warm-up failed (will retry on first job): {e}")
        return False


def run_worker():
    """Run the RQ worker"""
    conn = get_redis_connection()

    # Define queues to listen to (in priority order)
    # Set default_timeout to 2 hours (7200s) for long-running jobs like prefilter
    # Default RQ timeout is 180s which is too short for batch Gemini API calls
    queues = [
        Queue('high', connection=conn, default_timeout=7200),
        Queue('default', connection=conn, default_timeout=7200),
        Queue('low', connection=conn, default_timeout=7200),
    ]

    print(f"[Worker] Starting worker at {datetime.utcnow().isoformat()}")
    print(f"[Worker] Listening on queues: high, default, low")
    print(f"[Worker] Default job timeout: 7200 seconds (2 hours)")

    # Warm up database connection before processing jobs
    warmup_database()

    worker = Worker(queues, connection=conn)
    worker.work()


def enqueue_job(job_func, queue_name: str = 'default', **kwargs):
    """
    Manually enqueue a job.

    Args:
        job_func: The function to run
        queue_name: Queue to add job to ('high', 'default', 'low')
        **kwargs: Arguments to pass to the job function

    Returns:
        RQ Job object
    """
    conn = get_redis_connection()
    queue = Queue(queue_name, connection=conn)
    return queue.enqueue(job_func, **kwargs)


if __name__ == '__main__':
    if '--with-scheduler' in sys.argv or '--scheduler' in sys.argv:
        # Run scheduler only (separate process)
        run_scheduler()
    else:
        # Run worker only
        run_worker()
