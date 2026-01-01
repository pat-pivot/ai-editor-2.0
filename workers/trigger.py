"""
AI Editor 2.0 - HTTP Trigger Service
Flask app for triggering RQ jobs from Next.js dashboard

Endpoints:
    POST /jobs/<step_name>  - Trigger a specific pipeline step
    GET /jobs/<job_id>      - Get job status
    GET /health             - Health check

Environment:
    REDIS_URL: Redis connection string
    TRIGGER_SECRET: Shared secret for authentication (optional)
"""

import os
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from redis import Redis
from rq import Queue
from rq.job import Job
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Redis connection
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
TRIGGER_SECRET = os.environ.get('TRIGGER_SECRET', '')


def get_redis_connection():
    """Get Redis connection from URL"""
    return Redis.from_url(REDIS_URL)


def verify_auth():
    """Verify request authentication if TRIGGER_SECRET is set"""
    if not TRIGGER_SECRET:
        return True

    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
        return token == TRIGGER_SECRET
    return False


# Job function mapping
JOB_FUNCTIONS = {}


def get_job_function(step_name: str):
    """
    Lazy load job functions to avoid import errors at startup.
    Maps step names to their handler functions.
    """
    if step_name in JOB_FUNCTIONS:
        return JOB_FUNCTIONS[step_name]

    try:
        if step_name == 'ingest':
            from jobs.ingest import ingest_articles
            JOB_FUNCTIONS[step_name] = ingest_articles
        elif step_name == 'ai_scoring':
            from jobs.ai_scoring import run_ai_scoring
            JOB_FUNCTIONS[step_name] = run_ai_scoring
        elif step_name == 'prefilter':
            from jobs.prefilter import prefilter_stories
            JOB_FUNCTIONS[step_name] = prefilter_stories
        elif step_name == 'slot_selection':
            from jobs.slot_selection import select_slots
            JOB_FUNCTIONS[step_name] = select_slots
        elif step_name == 'decoration':
            from jobs.decoration import decorate_stories
            JOB_FUNCTIONS[step_name] = decorate_stories
        elif step_name == 'images':
            from jobs.image_generation import generate_images
            JOB_FUNCTIONS[step_name] = generate_images
        elif step_name == 'html_compile':
            from jobs.html_compile import compile_html
            JOB_FUNCTIONS[step_name] = compile_html
        elif step_name == 'mautic_send':
            from jobs.mautic_send import send_via_mautic
            JOB_FUNCTIONS[step_name] = send_via_mautic
        elif step_name == 'social_sync':
            from jobs.social_sync import sync_social_posts
            JOB_FUNCTIONS[step_name] = sync_social_posts
        # Sandbox jobs (FreshRSS-based pipeline)
        elif step_name == 'ingest_sandbox':
            from jobs.ingest_sandbox import ingest_articles_sandbox
            JOB_FUNCTIONS[step_name] = ingest_articles_sandbox
        elif step_name == 'ai_scoring_sandbox':
            from jobs.ai_scoring_sandbox import run_ai_scoring_sandbox
            JOB_FUNCTIONS[step_name] = run_ai_scoring_sandbox
        elif step_name == 'repair_google_news':
            from repair_google_news import repair_google_news_job
            JOB_FUNCTIONS[step_name] = repair_google_news_job
        else:
            return None

        return JOB_FUNCTIONS.get(step_name)
    except ImportError as e:
        logger.error(f"Failed to import job function for {step_name}: {e}")
        return None


# Queue name mapping (matches worker.py priority)
QUEUE_MAPPING = {
    'ingest': 'default',
    'ai_scoring': 'default',
    'prefilter': 'default',
    'slot_selection': 'high',
    'decoration': 'default',
    'images': 'default',
    'html_compile': 'default',
    'mautic_send': 'high',
    'social_sync': 'low',
    # Sandbox jobs (FreshRSS-based pipeline)
    'ingest_sandbox': 'default',
    'ai_scoring_sandbox': 'default',
    # Repair/maintenance jobs
    'repair_google_news': 'low',
}


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        conn = get_redis_connection()
        conn.ping()
        redis_status = 'connected'
    except Exception as e:
        redis_status = f'error: {str(e)}'

    return jsonify({
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat(),
        'redis': redis_status,
        'available_jobs': list(QUEUE_MAPPING.keys())
    })


@app.route('/jobs/<step_name>', methods=['POST'])
def trigger_job(step_name: str):
    """
    Trigger a specific pipeline step.

    Args:
        step_name: One of prefilter, slot_selection, decoration, images,
                   html_compile, mautic_send, social_sync

    Request Body (optional):
        {
            "issue_date": "2024-12-24",  // Override issue date
            "dry_run": false,             // Preview without changes
            ...other job-specific params
        }

    Returns:
        {
            "success": true,
            "job_id": "abc123",
            "step": "prefilter",
            "queue": "default",
            "enqueued_at": "2024-12-24T10:00:00Z"
        }
    """
    # Verify authentication
    if not verify_auth():
        return jsonify({
            'success': False,
            'error': 'Unauthorized'
        }), 401

    # Validate step name
    if step_name not in QUEUE_MAPPING:
        return jsonify({
            'success': False,
            'error': f'Invalid step: {step_name}',
            'valid_steps': list(QUEUE_MAPPING.keys())
        }), 400

    # Get job function
    job_func = get_job_function(step_name)
    if not job_func:
        return jsonify({
            'success': False,
            'error': f'Job function not found for {step_name}'
        }), 500

    # Get optional parameters from request body
    params = request.get_json() or {}

    try:
        # Connect to Redis and enqueue job
        conn = get_redis_connection()
        queue_name = QUEUE_MAPPING[step_name]
        queue = Queue(queue_name, connection=conn)

        # Enqueue the job with optional parameters
        job = queue.enqueue(
            job_func,
            job_timeout='30m',  # 30 minute timeout
            **params
        )

        logger.info(f"Triggered job {step_name} with ID {job.id}")

        return jsonify({
            'success': True,
            'job_id': job.id,
            'step': step_name,
            'queue': queue_name,
            'enqueued_at': datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error(f"Failed to enqueue job {step_name}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/jobs/status/<job_id>', methods=['GET'])
def get_job_status(job_id: str):
    """
    Get status of a job by ID.

    Returns:
        {
            "job_id": "abc123",
            "status": "finished",  // queued, started, finished, failed
            "result": {...},       // Job result if finished
            "error": "...",        // Error message if failed
            "started_at": "...",
            "ended_at": "..."
        }
    """
    try:
        conn = get_redis_connection()
        job = Job.fetch(job_id, connection=conn)

        response = {
            'job_id': job_id,
            'status': job.get_status(),
            'created_at': job.created_at.isoformat() if job.created_at else None,
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'ended_at': job.ended_at.isoformat() if job.ended_at else None,
        }

        if job.is_finished:
            response['result'] = job.result
        elif job.is_failed:
            response['error'] = str(job.exc_info) if job.exc_info else 'Unknown error'

        return jsonify(response)

    except Exception as e:
        return jsonify({
            'job_id': job_id,
            'status': 'not_found',
            'error': str(e)
        }), 404


@app.route('/jobs/cancel/<job_id>', methods=['POST'])
def cancel_job(job_id: str):
    """
    Cancel a job by ID.

    Returns:
        {
            "success": true,
            "job_id": "abc123",
            "message": "Job cancelled"
        }
    """
    # Verify authentication
    if not verify_auth():
        return jsonify({
            'success': False,
            'error': 'Unauthorized'
        }), 401

    try:
        conn = get_redis_connection()
        job = Job.fetch(job_id, connection=conn)

        status = job.get_status()
        if status in ['finished', 'failed']:
            return jsonify({
                'success': False,
                'job_id': job_id,
                'error': f'Job already {status}'
            }), 400

        # Cancel the job
        job.cancel()

        logger.info(f"Cancelled job {job_id}")

        return jsonify({
            'success': True,
            'job_id': job_id,
            'message': 'Job cancelled',
            'previous_status': status
        })

    except Exception as e:
        logger.error(f"Failed to cancel job {job_id}: {e}")
        return jsonify({
            'success': False,
            'job_id': job_id,
            'error': str(e)
        }), 404


@app.route('/jobs/cancel-all', methods=['POST'])
def cancel_all_jobs():
    """
    Cancel all jobs in all queues.

    Returns:
        {
            "success": true,
            "cancelled": 5,
            "details": {...}
        }
    """
    # Verify authentication
    if not verify_auth():
        return jsonify({
            'success': False,
            'error': 'Unauthorized'
        }), 401

    try:
        conn = get_redis_connection()
        cancelled = 0
        details = {}

        for queue_name in ['high', 'default', 'low']:
            queue = Queue(queue_name, connection=conn)
            queue_cancelled = 0

            # Cancel all jobs in the queue
            for job in queue.jobs:
                try:
                    job.cancel()
                    queue_cancelled += 1
                except Exception as e:
                    logger.warning(f"Failed to cancel job {job.id}: {e}")

            details[queue_name] = queue_cancelled
            cancelled += queue_cancelled

        logger.info(f"Cancelled {cancelled} jobs across all queues")

        return jsonify({
            'success': True,
            'cancelled': cancelled,
            'details': details
        })

    except Exception as e:
        logger.error(f"Failed to cancel all jobs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/jobs/queue', methods=['GET'])
def get_queue_status():
    """
    Get status of all queues.

    Returns:
        {
            "queues": {
                "high": {"count": 2, "jobs": [...]},
                "default": {"count": 5, "jobs": [...]},
                "low": {"count": 0, "jobs": []}
            }
        }
    """
    try:
        conn = get_redis_connection()
        queues = {}

        for queue_name in ['high', 'default', 'low']:
            queue = Queue(queue_name, connection=conn)
            jobs = []

            for job in queue.jobs[:10]:  # Limit to 10 jobs per queue
                jobs.append({
                    'id': job.id,
                    'func_name': job.func_name,
                    'status': job.get_status(),
                    'created_at': job.created_at.isoformat() if job.created_at else None
                })

            queues[queue_name] = {
                'count': len(queue),
                'jobs': jobs
            }

        return jsonify({'queues': queues})

    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500


if __name__ == '__main__':
    port = int(os.environ.get('TRIGGER_PORT', 5001))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'

    logger.info(f"Starting HTTP Trigger Service on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
