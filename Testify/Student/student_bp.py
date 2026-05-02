from flask import Blueprint, render_template, session
from Testify.Authentication.auth_bp import role_required
from Testify.__init__ import db_config
import mysql.connector


student = Blueprint('student', __name__, template_folder='templates',
                  static_folder='static', static_url_path='/student/static')

def get_student_context():
    """Helper function to get user_name and classes for all student routes."""
    user_id = session.get('user_id')
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)
    
    # Fetch user name
    cursor.execute("SELECT first_name, last_name FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    
    # Check if student_profile exists
    cursor.execute("SELECT student_id, block_id FROM student_profiles WHERE user_id = %s", (user_id,))
    student_profile = cursor.fetchone()
    
    if student_profile:
        # Fetch student's classes using block_id
        query = """
        SELECT ca.assignment_id, ca.course_code, ca.status,
               s.subject_id, s.subject_code, s.subject_name,
               b.block_id, b.block_name, b.section, b.year_level,
               p.program_id, p.program_name
        FROM course_assignments ca
        JOIN subjects s ON ca.subject_id = s.subject_id
        JOIN blocks b ON ca.block_id = b.block_id
        JOIN programs p ON b.program_id = p.program_id
        WHERE ca.block_id = %s
        ORDER BY s.subject_code
        """
        cursor.execute(query, (student_profile['block_id'],))
        classes = cursor.fetchall()
    else:
        classes = []
    
    cursor.close()
    connection.close()
    
    user_name = f"{user['first_name']} {user['last_name']}" if user else "Student"
    
    return {'user_name': user_name, 'classes': classes}

@student.route('/dashboard')
@role_required('STUDENT')
def dashboard():

    context = get_student_context()
    return render_template('student_dashboard.html', **context)


@student.route('/student_dashboard')
@role_required('STUDENT')
def display_student():
    context = get_student_context()
    return render_template('student_dashboard.html', **context)


@student.route('/exams')
@role_required('STUDENT')
def exams():
    context = get_student_context()
    return render_template('exams.html', **context)


@student.route('/quizzes')
@role_required('STUDENT')
def quizzes():
    context = get_student_context()
    return render_template('quizzes.html', **context)


@student.route('/my-classes')
@role_required('STUDENT')
def my_classes():
    context = get_student_context()
    
    user_id = session.get('user_id')
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)
    
    # Fetch student profile
    cursor.execute("SELECT student_id, block_id FROM student_profiles WHERE user_id = %s", (user_id,))
    student_profile = cursor.fetchone()
    
    if student_profile:
        block_id = student_profile['block_id']
        
        # Fetch detailed class information
        query = """
        SELECT 
            ca.assignment_id,
            ca.course_code,
            ca.status,
            s.subject_id,
            s.subject_code,
            s.subject_name,
            t.teacher_id,
            u.first_name,
            u.last_name,
            u.email,
            b.block_id,
            b.block_name,
            b.section,
            b.year_level
        FROM course_assignments ca
        JOIN subjects s ON ca.subject_id = s.subject_id
        JOIN users u ON ca.teacher_id = u.user_id
        JOIN teacher_profiles t ON u.user_id = t.user_id
        JOIN blocks b ON ca.block_id = b.block_id
        WHERE ca.block_id = %s AND ca.status = 'ACTIVE'
        ORDER BY s.subject_code
        """
        cursor.execute(query, (block_id,))
        classes = cursor.fetchall()
        
        # For each class, fetch exam statistics
        for cls in classes:
            exam_query = """
            SELECT 
                COUNT(DISTINCT ea.attempt_id) as total_exams,
                COALESCE(AVG(ea.score), 0) as average_score,
                COUNT(CASE WHEN ea.status = 'COMPLETED' THEN 1 END) as completed_exams
            FROM exam_attempts ea
            JOIN exams e ON ea.exam_id = e.exam_id
            WHERE e.assignment_id = %s AND ea.student_id = %s
            """
            cursor.execute(exam_query, (cls['assignment_id'], student_profile['student_id']))
            stats = cursor.fetchone()
            cls['exam_stats'] = stats if stats else {
                'total_exams': 0,
                'average_score': 0,
                'completed_exams': 0
            }
        
        context['classes_detail'] = classes
    else:
        context['classes_detail'] = []
    
    cursor.close()
    connection.close()
    
    return render_template('classes_student.html', **context)


@student.route('/schedule')
@role_required('STUDENT')
def schedule():
    context = get_student_context()
    return render_template('schedule.html', **context)


@student.route('/results')
@role_required('STUDENT')
def results():
    context = get_student_context()
    return render_template('results.html', **context)


@student.route('/profile')
@role_required('STUDENT')
def profile():
    context = get_student_context()
    return render_template('profile.html', **context)


