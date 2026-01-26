"""
Flask blueprint for sprint forecast generation.
"""

from flask import Blueprint, render_template, request, send_file, redirect, url_for, jsonify
from pathlib import Path
import logging

from core.forecast import get_sprint_history
from webapp.tasks import task_manager

bp = Blueprint('forecast', __name__, url_prefix='/forecast')
logger = logging.getLogger(__name__)


@bp.route('/', methods=['GET', 'POST'])
def generate():
    """Forecast generation form and submission handler."""
    if request.method == 'GET':
        # Fetch sprint history to get team members
        try:
            results, all_members = get_sprint_history(max_sprints=10)
            return render_template('forecast/form.html',
                                   members=all_members,
                                   sprint_count=len(results))
        except Exception as e:
            logger.exception("Failed to fetch sprint history")
            return render_template('forecast/form.html',
                                   error=f"Failed to fetch team members: {str(e)}",
                                   members=[],
                                   sprint_count=0)

    # POST: Parse team availability and create task
    team_availability = {}
    for key, value in request.form.items():
        if key.startswith('member_'):
            member_name = key[7:]  # Remove 'member_' prefix
            try:
                days = float(value)
                if days >= 0:
                    team_availability[member_name] = days
            except ValueError:
                continue

    if not team_availability:
        return render_template('forecast/form.html',
                               error="Please enter availability for at least one team member.",
                               members=request.form.getlist('all_members'),
                               sprint_count=0), 400

    task_id = task_manager.create_task('forecast', {
        'team_availability': team_availability,
        'max_sprints': 10
    })

    return redirect(url_for('forecast.status', task_id=task_id))


@bp.route('/status/<task_id>')
def status(task_id):
    """Task status page with progress tracking."""
    task = task_manager.get_task(task_id)
    if not task:
        return "Task not found", 404
    return render_template('forecast/status.html', task=task)


@bp.route('/api/status/<task_id>')
def api_status(task_id):
    """AJAX endpoint for status polling."""
    task = task_manager.get_task(task_id)
    if not task:
        return jsonify({'error': 'Not found'}), 404

    response = {
        'status': task['status'],
        'progress': task['progress'],
        'error': task.get('error')
    }

    if task['status'] == 'completed' and task['result']:
        result = task['result']
        file_path = Path(result.get('file_path', ''))
        response['download_url'] = url_for(
            'forecast.download',
            task_id=task_id,
            filename=file_path.name
        )
        response['forecast_windows'] = result.get('forecast_windows', {})
        response['sprint_count'] = result.get('sprint_count')

    return jsonify(response)


@bp.route('/download/<task_id>/<filename>')
def download(task_id, filename):
    """Download generated forecast Excel file."""
    task = task_manager.get_task(task_id)
    if not task or task['status'] != 'completed':
        return "Not found", 404

    result = task.get('result')
    if not result:
        return "No result available", 404

    file_path = Path(result.get('file_path', ''))
    if not file_path.exists():
        return "File not found", 404

    return send_file(file_path, as_attachment=True, download_name=filename)
