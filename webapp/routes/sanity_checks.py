"""
Flask blueprint for sanity checks.
"""

from flask import Blueprint, render_template, jsonify

from core.sanity_checks import get_to_refine_stories, get_ready_stories

bp = Blueprint('sanity_checks', __name__, url_prefix='/sanity-checks')


@bp.route('/')
def index():
    """Sanity checks index page."""
    return render_template('sanity_checks/index.html')


@bp.route('/to-refine')
def to_refine():
    """Check 'To Refine' stories."""
    result = get_to_refine_stories()

    if not result['success']:
        return render_template('sanity_checks/error.html', error=result['error']), 500

    return render_template('sanity_checks/to_refine.html',
                           total_stories=result['total_stories'],
                           issues_with_problems=result['issues_with_problems'],
                           problem_count=len(result['issues_with_problems']))


@bp.route('/ready')
def ready():
    """Check 'Ready' stories."""
    result = get_ready_stories()

    if not result['success']:
        return render_template('sanity_checks/error.html', error=result['error']), 500

    return render_template('sanity_checks/ready.html',
                           total_stories=result['total_stories'],
                           issues_with_problems=result['issues_with_problems'],
                           problem_count=len(result['issues_with_problems']))


@bp.route('/api/to-refine')
def api_to_refine():
    """API endpoint for 'To Refine' checks (for AJAX calls)."""
    result = get_to_refine_stories()
    return jsonify(result)


@bp.route('/api/ready')
def api_ready():
    """API endpoint for 'Ready' checks (for AJAX calls)."""
    result = get_ready_stories()
    return jsonify(result)
