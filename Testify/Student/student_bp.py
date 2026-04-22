from flask import Blueprint, render_template

student = Blueprint('student', __name__, template_folder='templates',
                  static_folder='static', static_url_path='/student/static')

@student.route('/student_dashboard')
def display_student():
    return render_template('student_dashboard.html')