from flask import Blueprint, render_template

teacher = Blueprint('teacher', __name__, template_folder='templates',
                  static_folder='static', static_url_path='/teacher/static')

@teacher.route('/teacher_dashboard')
def display_teacher():
    return render_template('teacher_dashboard.html')