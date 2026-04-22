from flask import Blueprint, render_template

admin = Blueprint('admin', __name__, template_folder='templates',
                  static_folder='static', static_url_path='/admin/static')

@admin.route('/admin_dashboard')
def display_admin():
    return render_template('admin_dashboard.html')