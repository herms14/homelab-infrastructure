"""
Sentinel Bot Webhook Server
Quart-based async HTTP server for webhooks and APIs.
"""

import logging
from functools import wraps
from typing import TYPE_CHECKING

from quart import Quart, request, jsonify

if TYPE_CHECKING:
    from core import SentinelBot
    from config import Config

logger = logging.getLogger('sentinel.webhooks')


def require_api_key(f):
    """Decorator to require API key for endpoints."""
    @wraps(f)
    async def decorated(*args, **kwargs):
        app = args[0] if args else None
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')

        if not api_key or api_key != app.config.get('API_KEY'):
            return jsonify({'error': 'Unauthorized'}), 401

        return await f(*args, **kwargs)
    return decorated


def create_app(bot: 'SentinelBot', config: 'Config') -> Quart:
    """Create and configure the Quart application."""
    app = Quart(__name__)
    app.config['API_KEY'] = config.webhook.api_key
    app.bot = bot
    app.sentinel_config = config

    # ==================== Health Check ====================

    @app.route('/health', methods=['GET'])
    async def health():
        """Health check endpoint."""
        return jsonify({
            'status': 'healthy',
            'bot_ready': bot.is_ready() if bot else False,
            'guilds': len(bot.guilds) if bot else 0,
        })

    # ==================== Watchtower Webhook ====================

    @app.route('/webhook/watchtower', methods=['POST'])
    async def watchtower_webhook():
        """Handle Watchtower container update notifications."""
        try:
            data = await request.get_json()
            logger.info(f"Watchtower webhook received: {data}")

            # Parse Watchtower notification
            # Format varies by Watchtower version
            entries = data if isinstance(data, list) else [data]

            for entry in entries:
                container = entry.get('name') or entry.get('container')
                status = entry.get('status', 'updated')
                image = entry.get('image', 'unknown')

                if container and bot.channel_router:
                    await bot.channel_router.send_update_notification(
                        container_name=container,
                        host_ip='watchtower',
                        status='success' if status == 'updated' else status,
                        details=f"Image: {image}"
                    )

            return jsonify({'status': 'ok'})
        except Exception as e:
            logger.error(f"Watchtower webhook error: {e}")
            return jsonify({'error': str(e)}), 500

    # ==================== Jellyseerr Webhook ====================

    @app.route('/webhook/jellyseerr', methods=['POST'])
    async def jellyseerr_webhook():
        """Handle Jellyseerr media request notifications."""
        try:
            data = await request.get_json()
            logger.info(f"Jellyseerr webhook received: {data}")

            notification_type = data.get('notification_type', '')
            media = data.get('media', {})
            request_info = data.get('request', {})

            title = media.get('tmdbTitle') or media.get('tvdbTitle') or 'Unknown'
            media_type = media.get('media_type', 'media')
            poster = media.get('posterPath')

            # Map Jellyseerr notification types to our events
            event_map = {
                'MEDIA_PENDING': 'requested',
                'MEDIA_APPROVED': 'approved',
                'MEDIA_AVAILABLE': 'completed',
                'MEDIA_FAILED': 'failed',
                'MEDIA_DECLINED': 'declined',
            }
            event = event_map.get(notification_type, notification_type)

            if bot.channel_router:
                await bot.channel_router.send_media_notification(
                    title=title,
                    media_type=media_type,
                    event=event,
                    poster_url=f"https://image.tmdb.org/t/p/w500{poster}" if poster else None,
                    details={
                        'Requested By': request_info.get('requestedBy', {}).get('username', 'Unknown'),
                        'Status': event.title(),
                    }
                )

            return jsonify({'status': 'ok'})
        except Exception as e:
            logger.error(f"Jellyseerr webhook error: {e}")
            return jsonify({'error': str(e)}), 500

    # ==================== Claude Task API ====================

    @app.route('/api/tasks', methods=['GET'])
    async def list_tasks():
        """List pending tasks."""
        try:
            if not bot.db:
                return jsonify({'error': 'Database not available'}), 503

            tasks = await bot.db.get_pending_tasks(limit=50)
            return jsonify({'tasks': tasks})
        except Exception as e:
            logger.error(f"List tasks error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/tasks', methods=['POST'])
    async def create_task():
        """Create a new task."""
        try:
            if not bot.db:
                return jsonify({'error': 'Database not available'}), 503

            data = await request.get_json()
            description = data.get('description')
            priority = data.get('priority', 'medium')
            submitted_by = data.get('submitted_by', 'api')

            if not description:
                return jsonify({'error': 'description required'}), 400

            task_id = await bot.db.create_task(
                description=description,
                priority=priority,
                submitted_by=submitted_by
            )

            # Notify via Discord
            if bot.channel_router:
                await bot.channel_router.send_task_notification(
                    task_id=task_id,
                    description=description,
                    event='created'
                )

            return jsonify({'task_id': task_id, 'status': 'created'}), 201
        except Exception as e:
            logger.error(f"Create task error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/tasks/next', methods=['GET'])
    async def get_next_task():
        """Get the next available task."""
        try:
            if not bot.db:
                return jsonify({'error': 'Database not available'}), 503

            task = await bot.db.get_next_task()
            if task:
                return jsonify({'task': task})
            return jsonify({'task': None, 'message': 'No pending tasks'})
        except Exception as e:
            logger.error(f"Get next task error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/tasks/<int:task_id>/claim', methods=['POST'])
    async def claim_task(task_id: int):
        """Claim a task for processing."""
        try:
            if not bot.db:
                return jsonify({'error': 'Database not available'}), 503

            data = await request.get_json()
            instance_id = data.get('instance_id')
            instance_name = data.get('instance_name')

            if not instance_id:
                return jsonify({'error': 'instance_id required'}), 400

            success = await bot.db.claim_task(task_id, instance_id, instance_name)

            if success:
                # Update instance heartbeat
                await bot.db.update_instance_heartbeat(instance_id, instance_name or instance_id, 'working')

                # Notify via Discord
                if bot.channel_router:
                    task = await bot.db.get_pending_tasks(limit=100)
                    task_desc = next((t['description'] for t in task if t['id'] == task_id), 'Unknown')
                    await bot.channel_router.send_task_notification(
                        task_id=task_id,
                        description=task_desc,
                        event='claimed',
                        instance_name=instance_name
                    )

                return jsonify({'status': 'claimed'})
            return jsonify({'error': 'Task not available'}), 409
        except Exception as e:
            logger.error(f"Claim task error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/tasks/<int:task_id>/complete', methods=['POST'])
    async def complete_task(task_id: int):
        """Mark a task as completed."""
        try:
            if not bot.db:
                return jsonify({'error': 'Database not available'}), 503

            data = await request.get_json()
            instance_id = data.get('instance_id')
            notes = data.get('notes')

            if not instance_id:
                return jsonify({'error': 'instance_id required'}), 400

            success = await bot.db.complete_task(task_id, instance_id, notes)

            if success:
                # Update instance heartbeat
                await bot.db.update_instance_heartbeat(instance_id, instance_id, 'idle')

                # Notify via Discord
                if bot.channel_router:
                    await bot.channel_router.send_task_notification(
                        task_id=task_id,
                        description=notes or 'Task completed',
                        event='completed',
                        instance_name=instance_id
                    )

                return jsonify({'status': 'completed'})
            return jsonify({'error': 'Task not found or not claimed by this instance'}), 404
        except Exception as e:
            logger.error(f"Complete task error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/instances', methods=['GET'])
    async def list_instances():
        """List active Claude instances."""
        try:
            if not bot.db:
                return jsonify({'error': 'Database not available'}), 503

            instances = await bot.db.get_active_instances(minutes=10)
            return jsonify({'instances': instances})
        except Exception as e:
            logger.error(f"List instances error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/instances/heartbeat', methods=['POST'])
    async def instance_heartbeat():
        """Record instance heartbeat."""
        try:
            if not bot.db:
                return jsonify({'error': 'Database not available'}), 503

            data = await request.get_json()
            instance_id = data.get('instance_id')
            instance_name = data.get('instance_name')
            status = data.get('status', 'idle')

            if not instance_id:
                return jsonify({'error': 'instance_id required'}), 400

            await bot.db.update_instance_heartbeat(instance_id, instance_name or instance_id, status)
            return jsonify({'status': 'ok'})
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
            return jsonify({'error': str(e)}), 500

    # ==================== Stats Endpoint ====================

    @app.route('/api/stats', methods=['GET'])
    async def get_stats():
        """Get task queue statistics."""
        try:
            if not bot.db:
                return jsonify({'error': 'Database not available'}), 503

            task_stats = await bot.db.get_task_stats()
            instances = await bot.db.get_active_instances(minutes=10)

            return jsonify({
                'tasks': task_stats,
                'active_instances': len(instances),
            })
        except Exception as e:
            logger.error(f"Stats error: {e}")
            return jsonify({'error': str(e)}), 500

    return app
