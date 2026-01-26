"""
Flask blueprint for blocked and on-hold story overviews.
"""

from flask import Blueprint, render_template, jsonify

from core.overviews import get_blocked_stories, get_on_hold_stories

bp = Blueprint('overviews', __name__, url_prefix='/overviews')


@bp.route('/')
def index():
    """Overview index page."""
    return render_template('overviews/index.html')


@bp.route('/blocked')
def blocked():
    """Show blocked stories."""
    result = get_blocked_stories()

    if not result['success']:
        return render_template('overviews/error.html', error=result['error']), 500

    return render_template('overviews/blocked.html',
                           stories=result['stories'],
                           count=result['count'])


@bp.route('/on-hold')
def on_hold():
    """Show on-hold stories."""
    result = get_on_hold_stories()

    if not result['success']:
        return render_template('overviews/error.html', error=result['error']), 500

    return render_template('overviews/on_hold.html',
                           stories=result['stories'],
                           count=result['count'])


@bp.route('/api/blocked')
def api_blocked():
    """API endpoint for blocked stories (for AJAX calls)."""
    result = get_blocked_stories()
    return jsonify(result)


@bp.route('/api/on-hold')
def api_on_hold():
    """API endpoint for on-hold stories (for AJAX calls)."""
    result = get_on_hold_stories()
    return jsonify(result)
