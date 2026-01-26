"""
Flask blueprint for PowerPoint generation.
"""

from flask import Blueprint, render_template, request, send_file, redirect, url_for, jsonify
from pathlib import Path
import logging

from webapp.tasks import task_manager

bp = Blueprint('powerpoint', __name__, url_prefix='/powerpoint')
logger = logging.getLogger(__name__)


@bp.route('/', methods=['GET', 'POST'])
def generate():
    """PowerPoint generation form and submission handler."""
    if request.method == 'GET':
        return render_template('powerpoint/form.html')

    # POST: Create background task
    sprint_id = request.form.get('sprint_id', '').strip()

    # Convert empty string to None for "active sprint" behavior
    if not sprint_id:
        sprint_id = None
    else:
        try:
            sprint_id = int(sprint_id)
        except ValueError:
            return render_template('powerpoint/form.html',
                                   error="Invalid sprint ID. Please enter a number."), 400

    task_id = task_manager.create_task('powerpoint', {
        'sprint_id': sprint_id
    })

    return redirect(url_for('powerpoint.status', task_id=task_id))


@bp.route('/status/<task_id>')
def status(task_id):
    """Task status page with progress tracking."""
    task = task_manager.get_task(task_id)
    if not task:
        return "Task not found", 404
    return render_template('powerpoint/status.html', task=task)


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
            'powerpoint.download',
            task_id=task_id,
            filename=file_path.name
        )
        response['sprint_name'] = result.get('sprint_name')
        response['issue_count'] = result.get('issue_count')
        response['epic_count'] = result.get('epic_count')

    return jsonify(response)


@bp.route('/download/<task_id>/<filename>')
def download(task_id, filename):
    """Download generated PowerPoint file."""
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
