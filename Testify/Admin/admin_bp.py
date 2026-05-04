from flask import Blueprint, render_template, request, jsonify
from Testify.Authentication.auth_bp import role_required
from Testify.__init__ import db_config
import mysql.connector
import datetime
import random
import re
from werkzeug.security import generate_password_hash

# ============================================
# BLUEPRINT DEFINITION
# ============================================
admin = Blueprint('admin', __name__, template_folder='templates',
                  static_folder='static', static_url_path='/admin/static')


# ============================================
# DATABASE HELPER
# ============================================
def get_db_connection():
    return mysql.connector.connect(**db_config)


# ============================================
# ACTIVITY LOGGING HELPER
# ============================================
def log_activity(user_id, role, action, target_table, target_id, description, ip_address=None):
    """Helper function to log system activities to system_activity_logs table."""
    db = get_db_connection()
    cursor = db.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO system_activity_logs
                (user_id, role, action, target_table, target_id, description, ip_address, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """,
            (user_id, role, action, target_table, target_id, description, ip_address)
        )
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error logging activity: {e}")
    finally:
        cursor.close()
        db.close()


# ============================================
# BLOCK AUTO-GENERATION HELPERS
# ============================================
def get_next_section(program_id, year_level):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT section FROM blocks WHERE program_id = %s AND year_level = %s ORDER BY section DESC LIMIT 1",
        (program_id, year_level)
    )
    result = cursor.fetchone()
    cursor.close()
    db.close()

    if result and result['section']:
        last_section = result['section']
        return chr(ord(last_section) + 1)
    return 'A'


def generate_block_name(program_code, year_level, section, specialization_code=None):
    if specialization_code:
        return f"{program_code}-{specialization_code}{year_level}{section}"
    return f"{program_code}{year_level}{section}"


# ============================================
# EXISTING ADMIN DASHBOARD ROUTES
# ============================================

@admin.route('/admin_dashboard')
@role_required('ADMIN')
def dashboard():
    return render_template('admin_dashboard.html')


@admin.route('/students')
@role_required('ADMIN')
def students():
    return render_template('students.html')


@admin.route('/subjects')
@role_required('ADMIN')
def subjects():
    return render_template('subjects.html')

@admin.route('/programs')
@role_required('ADMIN')
def programs():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    # Fetch departments for dropdown
    cursor.execute("SELECT department_id, department_code, department_name FROM departments ORDER BY department_code")
    departments = cursor.fetchall()
    
    cursor.execute("""
        SELECT p.*, d.department_code, d.department_name, COUNT(b.block_id) as total_blocks
        FROM programs p
        LEFT JOIN departments d ON p.department_id = d.department_id
        LEFT JOIN blocks b ON p.program_id = b.program_id
        GROUP BY p.program_id
        ORDER BY p.program_code
    """)
    programs_list = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template('programs_blocks.html', programs=programs_list, departments=departments)


@admin.route('/assignments')
@role_required('ADMIN')
def assignments():
    return render_template('assignments.html')


@admin.route('/exams')
@role_required('ADMIN')
def exams():
    return render_template('exams.html')


@admin.route('/quizzes')
@role_required('ADMIN')
def quizzes():
    return render_template('quizzes.html')


@admin.route('/results')
@role_required('ADMIN')
def results():
    # Get filter parameters
    exam_type = request.args.get('exam_type', 'Exam')  # Default to Exam
    program_id = request.args.get('program_id', '')
    specialization_id = request.args.get('specialization_id', '')
    block_id = request.args.get('block_id', '')
    subject_id = request.args.get('subject_id', '')
    exam_id = request.args.get('exam_id', '')
    search = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 10

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Fetch programs for filter
    cursor.execute("SELECT program_id, program_code, program_name FROM programs ORDER BY program_code")
    programs = cursor.fetchall()

    # Build query with filters
    query = """
        SELECT
            ea.attempt_id,
            ea.score,
            ea.status as attempt_status,
            ea.started_at,
            ea.submitted_at,
            e.exam_id,
            e.exam_title,
            e.exam_type,
            e.total_questions,
            e.duration_minutes,
            u.user_id,
            u.first_name,
            u.middle_name,
            u.last_name,
            sp.student_number,
            p.program_id,
            p.program_code,
            p.program_name,
            b.block_id,
            b.block_name,
            b.year_level,
            b.section,
            s.subject_id,
            s.subject_code,
            s.subject_name,
            (SELECT COUNT(*) FROM exam_security_logs esl WHERE esl.attempt_id = ea.attempt_id) as violation_count
        FROM exam_attempts ea
        JOIN exams e ON ea.exam_id = e.exam_id
        JOIN course_assignments ca ON e.assignment_id = ca.assignment_id
        JOIN subjects s ON ca.subject_id = s.subject_id
        JOIN student_profiles sp ON ea.student_id = sp.student_id
        JOIN users u ON sp.user_id = u.user_id
        JOIN blocks b ON sp.block_id = b.block_id
        JOIN programs p ON sp.program_id = p.program_id
        WHERE ea.status IN ('Submitted', 'Auto Submitted')
        AND e.exam_type = %s
    """

    count_query = """
        SELECT COUNT(*) as total
        FROM exam_attempts ea
        JOIN exams e ON ea.exam_id = e.exam_id
        JOIN course_assignments ca ON e.assignment_id = ca.assignment_id
        JOIN subjects s ON ca.subject_id = s.subject_id
        JOIN student_profiles sp ON ea.student_id = sp.student_id
        JOIN users u ON sp.user_id = u.user_id
        JOIN blocks b ON sp.block_id = b.block_id
        JOIN programs p ON sp.program_id = p.program_id
        WHERE ea.status IN ('Submitted', 'Auto Submitted')
        AND e.exam_type = %s
    """

    params = [exam_type]

    # Add filters
    if program_id:
        query += " AND p.program_id = %s"
        count_query += " AND p.program_id = %s"
        params.append(program_id)

    if specialization_id:
        # Filter by block names that contain the specialization code
        cursor.execute("SELECT specialization_code FROM specializations WHERE specialization_id = %s", (specialization_id,))
        spec = cursor.fetchone()
        if spec and spec['specialization_code']:
            query += " AND b.block_name LIKE %s"
            count_query += " AND b.block_name LIKE %s"
            params.append(f"%{spec['specialization_code']}%")

    if block_id:
        query += " AND b.block_id = %s"
        count_query += " AND b.block_id = %s"
        params.append(block_id)

    if subject_id:
        query += " AND s.subject_id = %s"
        count_query += " AND s.subject_id = %s"
        params.append(subject_id)

    if exam_id:
        query += " AND e.exam_id = %s"
        count_query += " AND e.exam_id = %s"
        params.append(exam_id)

    if search:
        query += " AND (u.first_name LIKE %s OR u.last_name LIKE %s OR sp.student_number LIKE %s)"
        count_query += " AND (u.first_name LIKE %s OR u.last_name LIKE %s OR sp.student_number LIKE %s)"
        search_term = f"%{search}%"
        params.extend([search_term, search_term, search_term])

    query += " ORDER BY ea.submitted_at DESC LIMIT %s OFFSET %s"
    params.extend([per_page, (page - 1) * per_page])

    # Fetch exam results
    cursor.execute(query, params)
    results = cursor.fetchall()

    # Get total count for pagination
    cursor.execute(count_query, params[:-2])  # Exclude limit and offset
    total = cursor.fetchone()['total']

    cursor.close()
    db.close()

    # Format data for template
    for result in results:
        # Calculate percentage
        if result['total_questions'] and result['total_questions'] > 0:
            result['percentage'] = round((result['score'] / result['total_questions']) * 100, 1)
        else:
            result['percentage'] = 0

        # Calculate time spent in minutes (before formatting dates)
        if result['started_at'] and result['submitted_at']:
            time_spent = (result['submitted_at'] - result['started_at']).total_seconds() / 60
            result['time_spent'] = round(time_spent, 1)
        else:
            result['time_spent'] = 0

        # Format dates after calculating time spent
        if result['started_at']:
            result['started_at_date'] = result['started_at'].strftime('%B %d, %Y')
            result['started_at_time'] = result['started_at'].strftime('%I:%M %p')
        if result['submitted_at']:
            result['submitted_at_date'] = result['submitted_at'].strftime('%B %d, %Y')
            result['submitted_at_time'] = result['submitted_at'].strftime('%I:%M %p')

        # Determine pass/fail (assuming 60% is passing)
        result['passed'] = result['percentage'] >= 60

    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    showing_start = (page - 1) * per_page + 1 if total > 0 else 0
    showing_end = min(page * per_page, total) if total > 0 else 0

    return render_template('results_page.html',
                          results=results,
                          programs=programs,
                          exam_type=exam_type,
                          program_id=program_id,
                          specialization_id=specialization_id,
                          block_id=block_id,
                          subject_id=subject_id,
                          exam_id=exam_id,
                          search=search,
                          page=page,
                          per_page=per_page,
                          total=total,
                          total_pages=total_pages,
                          showing_start=showing_start,
                          showing_end=showing_end)


@admin.route('/api/results/blocks/<int:program_id>')
@role_required('ADMIN')
def api_results_blocks(program_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT block_id, block_name, year_level, section
        FROM blocks
        WHERE program_id = %s
        ORDER BY year_level, section
    """, (program_id,))
    blocks = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify({'success': True, 'blocks': blocks})


@admin.route('/api/results/subjects/<int:program_id>')
@role_required('ADMIN')
def api_results_subjects(program_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT subject_id, subject_code, subject_name
        FROM subjects
        WHERE program_id = %s
        ORDER BY subject_code
    """, (program_id,))
    subjects = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify({'success': True, 'subjects': subjects})


@admin.route('/api/results/exams')
@role_required('ADMIN')
def api_results_exams():
    exam_type = request.args.get('exam_type', 'Exam')
    subject_id = request.args.get('subject_id', '')
    
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    query = """
        SELECT e.exam_id, e.exam_title
        FROM exams e
        JOIN course_assignments ca ON e.assignment_id = ca.assignment_id
        WHERE e.exam_type = %s
    """
    params = [exam_type]
    
    if subject_id:
        query += " AND ca.subject_id = %s"
        params.append(subject_id)
    
    query += " ORDER BY e.exam_title"
    
    cursor.execute(query, params)
    exams = cursor.fetchall()
    cursor.close()
    db.close()
    
    return jsonify({'success': True, 'exams': exams})


@admin.route('/api/results/search-students')
@role_required('ADMIN')
def api_search_students():
    query = request.args.get('q', '').strip()
    exam_type = request.args.get('exam_type', 'Exam')
    
    if len(query) < 2:
        return jsonify({'success': True, 'students': []})
    
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT DISTINCT
            u.user_id,
            u.first_name,
            u.middle_name,
            u.last_name,
            sp.student_number,
            sp.student_id
        FROM users u
        JOIN student_profiles sp ON u.user_id = sp.user_id
        JOIN exam_attempts ea ON sp.student_id = ea.student_id
        JOIN exams e ON ea.exam_id = e.exam_id
        WHERE e.exam_type = %s
        AND (u.first_name LIKE %s OR u.last_name LIKE %s OR sp.student_number LIKE %s)
        ORDER BY u.last_name, u.first_name
        LIMIT 10
    """, (exam_type, f'%{query}%', f'%{query}%', f'%{query}%'))
    
    students = cursor.fetchall()
    cursor.close()
    db.close()
    
    return jsonify({'success': True, 'students': students})


@admin.route('/api/results/specializations/<int:program_id>')
@role_required('ADMIN')
def api_results_specializations(program_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT specialization_id, specialization_name, specialization_code
        FROM specializations
        WHERE program_id = %s
        ORDER BY specialization_code
    """, (program_id,))
    specializations = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify({'success': True, 'specializations': specializations, 'has_specializations': len(specializations) > 0})


@admin.route('/reports')
@role_required('ADMIN')
def reports():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Fetch programs for dropdown
    cursor.execute("SELECT program_id, program_code, program_name FROM programs ORDER BY program_code")
    programs = cursor.fetchall()

    # Fetch summary statistics
    # Total students who have attempted exams
    cursor.execute("""
        SELECT COUNT(DISTINCT ea.student_id) as total_students
        FROM exam_attempts ea
        WHERE ea.status IN ('Submitted', 'Auto Submitted')
    """)
    total_students = cursor.fetchone()['total_students'] or 0

    # Average score (percentage)
    cursor.execute("""
        SELECT AVG((ea.score / e.total_questions) * 100) as avg_score
        FROM exam_attempts ea
        JOIN exams e ON ea.exam_id = e.exam_id
        WHERE ea.status IN ('Submitted', 'Auto Submitted')
        AND e.total_questions > 0
    """)
    avg_score = cursor.fetchone()['avg_score'] or 0

    # Highest score (percentage)
    cursor.execute("""
        SELECT MAX((ea.score / e.total_questions) * 100) as max_score
        FROM exam_attempts ea
        JOIN exams e ON ea.exam_id = e.exam_id
        WHERE ea.status IN ('Submitted', 'Auto Submitted')
        AND e.total_questions > 0
    """)
    highest_score = cursor.fetchone()['max_score'] or 0

    # Passing rate (percentage of students who scored >= 60%)
    cursor.execute("""
        SELECT 
            COUNT(CASE WHEN (ea.score / e.total_questions) * 100 >= 60 THEN 1 END) * 100.0 / COUNT(*) as passing_rate
        FROM exam_attempts ea
        JOIN exams e ON ea.exam_id = e.exam_id
        WHERE ea.status IN ('Submitted', 'Auto Submitted')
        AND e.total_questions > 0
    """)
    passing_rate = cursor.fetchone()['passing_rate'] or 0

    # Section performance data
    cursor.execute("""
        SELECT 
            b.block_name,
            b.year_level,
            b.section,
            p.program_code,
            COUNT(DISTINCT ea.student_id) as student_count,
            AVG((ea.score / e.total_questions) * 100) as avg_score,
            COUNT(CASE WHEN (ea.score / e.total_questions) * 100 >= 60 THEN 1 END) * 100.0 / COUNT(*) as pass_rate
        FROM exam_attempts ea
        JOIN exams e ON ea.exam_id = e.exam_id
        JOIN student_profiles sp ON ea.student_id = sp.student_id
        JOIN blocks b ON sp.block_id = b.block_id
        JOIN programs p ON sp.program_id = p.program_id
        WHERE ea.status IN ('Submitted', 'Auto Submitted')
        AND e.total_questions > 0
        GROUP BY b.block_id, b.block_name, b.year_level, b.section, p.program_code
        ORDER BY p.program_code, b.year_level, b.section
    """)
    section_performance = cursor.fetchall()

    cursor.close()
    db.close()

    # Format statistics
    summary_stats = {
        'total_students': total_students,
        'average_score': round(avg_score, 1),
        'highest_score': round(highest_score, 1),
        'passing_rate': round(passing_rate, 1)
    }

    # Format section performance
    for section in section_performance:
        section['avg_score'] = round(section['avg_score'], 1) if section['avg_score'] else 0
        section['pass_rate'] = round(section['pass_rate'], 1) if section['pass_rate'] else 0

    return render_template('reports.html',
                          programs=programs,
                          summary_stats=summary_stats,
                          section_performance=section_performance)


# ============================================
# REPORTS API ROUTES
# ============================================

@admin.route('/api/reports/year-levels/<int:program_id>')
@role_required('ADMIN')
def api_reports_year_levels(program_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT DISTINCT year_level
        FROM blocks
        WHERE program_id = %s
        ORDER BY year_level
    """, (program_id,))
    year_levels = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify({'success': True, 'year_levels': year_levels})


@admin.route('/api/reports/specializations/<int:program_id>')
@role_required('ADMIN')
def api_reports_specializations(program_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT specialization_id, specialization_name, specialization_code
        FROM specializations
        WHERE program_id = %s
        ORDER BY specialization_code
    """, (program_id,))
    specializations = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify({'success': True, 'specializations': specializations})


@admin.route('/api/reports/sections')
@role_required('ADMIN')
def api_reports_sections():
    program_id = request.args.get('program_id', '')
    year_level = request.args.get('year_level', '')
    
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    query = "SELECT block_id, block_name, section FROM blocks WHERE 1=1"
    params = []
    
    if program_id:
        query += " AND program_id = %s"
        params.append(program_id)
    
    if year_level:
        query += " AND year_level = %s"
        params.append(year_level)
    
    query += " ORDER BY section"
    
    cursor.execute(query, params)
    sections = cursor.fetchall()
    cursor.close()
    db.close()
    
    return jsonify({'success': True, 'sections': sections})


@admin.route('/api/reports/subjects/<int:program_id>')
@role_required('ADMIN')
def api_reports_subjects(program_id):
    year_level = request.args.get('year_level', '')
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    query = """
        SELECT s.subject_id, s.subject_code, s.subject_name
        FROM subjects s
        WHERE s.program_id = %s
    """
    params = [program_id]
    
    if year_level:
        query += " AND s.year_level = %s"
        params.append(year_level)
    
    query += " ORDER BY s.subject_code"
    
    cursor.execute(query, params)
    subjects = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify({'success': True, 'subjects': subjects})


@admin.route('/api/reports/exams')
@role_required('ADMIN')
def api_reports_exams():
    subject_id = request.args.get('subject_id', '')
    
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    query = """
        SELECT e.exam_id, e.exam_title
        FROM exams e
        JOIN course_assignments ca ON e.assignment_id = ca.assignment_id
        WHERE 1=1
    """
    params = []
    
    if subject_id:
        query += " AND ca.subject_id = %s"
        params.append(subject_id)
    
    query += " ORDER BY e.exam_title"
    
    cursor.execute(query, params)
    exams = cursor.fetchall()
    cursor.close()
    db.close()
    
    return jsonify({'success': True, 'exams': exams})


@admin.route('/api/reports/generate')
@role_required('ADMIN')
def api_reports_generate():
    program_id = request.args.get('program_id', '')
    specialization_id = request.args.get('specialization_id', '')
    year_level = request.args.get('year_level', '')
    section_id = request.args.get('section_id', '')
    subject_id = request.args.get('subject_id', '')
    exam_id = request.args.get('exam_id', '')
    
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    # Build summary statistics query with filters
    summary_query = """
        SELECT 
            COUNT(DISTINCT ea.student_id) as total_students,
            AVG((ea.score / e.total_questions) * 100) as avg_score,
            MAX((ea.score / e.total_questions) * 100) as max_score,
            COUNT(CASE WHEN (ea.score / e.total_questions) * 100 >= 60 THEN 1 END) * 100.0 / COUNT(*) as passing_rate
        FROM exam_attempts ea
        JOIN exams e ON ea.exam_id = e.exam_id
        JOIN student_profiles sp ON ea.student_id = sp.student_id
        JOIN blocks b ON sp.block_id = b.block_id
        JOIN programs p ON sp.program_id = p.program_id
        JOIN course_assignments ca ON e.assignment_id = ca.assignment_id
        WHERE ea.status IN ('Submitted', 'Auto Submitted')
        AND e.total_questions > 0
    """
    summary_params = []
    
    # Build section performance query with filters
    section_query = """
        SELECT 
            b.block_name,
            b.year_level,
            b.section,
            p.program_code,
            COUNT(DISTINCT ea.student_id) as student_count,
            AVG((ea.score / e.total_questions) * 100) as avg_score,
            COUNT(CASE WHEN (ea.score / e.total_questions) * 100 >= 60 THEN 1 END) * 100.0 / COUNT(*) as pass_rate
        FROM exam_attempts ea
        JOIN exams e ON ea.exam_id = e.exam_id
        JOIN student_profiles sp ON ea.student_id = sp.student_id
        JOIN blocks b ON sp.block_id = b.block_id
        JOIN programs p ON sp.program_id = p.program_id
        JOIN course_assignments ca ON e.assignment_id = ca.assignment_id
        WHERE ea.status IN ('Submitted', 'Auto Submitted')
        AND e.total_questions > 0
    """
    section_params = []
    
    # Apply filters
    if program_id:
        summary_query += " AND p.program_id = %s"
        section_query += " AND p.program_id = %s"
        summary_params.append(program_id)
        section_params.append(program_id)
    
    if specialization_id:
        spec_code = get_specialization_code(specialization_id)
        if spec_code:
            summary_query += " AND b.block_name LIKE %s"
            section_query += " AND b.block_name LIKE %s"
            summary_params.append(f"%{spec_code}%")
            section_params.append(f"%{spec_code}%")
    
    if year_level:
        summary_query += " AND b.year_level = %s"
        section_query += " AND b.year_level = %s"
        summary_params.append(year_level)
        section_params.append(year_level)
    
    if section_id:
        summary_query += " AND b.block_id = %s"
        section_query += " AND b.block_id = %s"
        summary_params.append(section_id)
        section_params.append(section_id)
    
    if subject_id:
        summary_query += " AND ca.subject_id = %s"
        section_query += " AND ca.subject_id = %s"
        summary_params.append(subject_id)
        section_params.append(subject_id)
    
    if exam_id:
        summary_query += " AND e.exam_id = %s"
        section_query += " AND e.exam_id = %s"
        summary_params.append(exam_id)
        section_params.append(exam_id)
    
    # Add grouping for section query
    section_query += " GROUP BY b.block_id, b.block_name, b.year_level, b.section, p.program_code ORDER BY p.program_code, b.year_level, b.section"
    
    # Fetch summary statistics
    cursor.execute(summary_query, summary_params)
    summary = cursor.fetchone()
    
    # Fetch section performance
    cursor.execute(section_query, section_params)
    section_performance = cursor.fetchall()
    
    cursor.close()
    db.close()
    
    # Format summary stats
    summary_stats = {
        'total_students': summary['total_students'] or 0,
        'average_score': round(summary['avg_score'] or 0, 1),
        'highest_score': round(summary['max_score'] or 0, 1),
        'passing_rate': round(summary['passing_rate'] or 0, 1)
    }
    
    # Format section performance
    for section in section_performance:
        section['avg_score'] = round(section['avg_score'] or 0, 1)
        section['pass_rate'] = round(section['pass_rate'] or 0, 1)
    
    return jsonify({
        'success': True,
        'summary_stats': summary_stats,
        'section_performance': section_performance
    })


@admin.route('/api/reports/chart-data')
@role_required('ADMIN')
def api_reports_chart_data():
    program_id = request.args.get('program_id', '')
    specialization_id = request.args.get('specialization_id', '')
    year_level = request.args.get('year_level', '')
    section_id = request.args.get('section_id', '')
    subject_id = request.args.get('subject_id', '')
    exam_id = request.args.get('exam_id', '')
    
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    # Build query for assessment volume by type
    query = """
        SELECT 
            e.exam_type,
            COUNT(*) as count
        FROM exam_attempts ea
        JOIN exams e ON ea.exam_id = e.exam_id
        JOIN student_profiles sp ON ea.student_id = sp.student_id
        JOIN blocks b ON sp.block_id = b.block_id
        JOIN programs p ON sp.program_id = p.program_id
        JOIN course_assignments ca ON e.assignment_id = ca.assignment_id
        WHERE ea.status IN ('Submitted', 'Auto Submitted')
    """
    params = []
    
    # Apply filters
    if program_id:
        query += " AND p.program_id = %s"
        params.append(program_id)
    
    if specialization_id:
        query += " AND b.block_name LIKE %s"
        params.append(f"%{get_specialization_code(specialization_id)}%")
    
    if year_level:
        query += " AND b.year_level = %s"
        params.append(year_level)
    
    if section_id:
        query += " AND b.block_id = %s"
        params.append(section_id)
    
    if subject_id:
        query += " AND ca.subject_id = %s"
        params.append(subject_id)
    
    if exam_id:
        query += " AND e.exam_id = %s"
        params.append(exam_id)
    
    query += " GROUP BY e.exam_type"
    
    cursor.execute(query, params)
    volume_data = cursor.fetchall()
    
    cursor.close()
    db.close()
    
    # Format data for chart
    quiz_count = 0
    exam_count = 0
    for item in volume_data:
        if item['exam_type'] == 'Quiz':
            quiz_count = item['count']
        elif item['exam_type'] == 'Exam':
            exam_count = item['count']
    
    return jsonify({
        'success': True,
        'volume_data': {
            'quiz': quiz_count,
            'exam': exam_count
        }
    })


def get_specialization_code(specialization_id):
    """Helper function to get specialization code from ID"""
    if not specialization_id:
        return ''
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT specialization_code FROM specializations WHERE specialization_id = %s", (specialization_id,))
    result = cursor.fetchone()
    cursor.close()
    db.close()
    return result['specialization_code'] if result else ''


@admin.route('/api/reports/subject-performance')
@role_required('ADMIN')
def api_reports_subject_performance():
    program_id = request.args.get('program_id', '')
    specialization_id = request.args.get('specialization_id', '')
    year_level = request.args.get('year_level', '')
    
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    # Build query for subject performance
    # This fetches subjects based on program, year level, and considers specialization
    query = """
        SELECT 
            s.subject_id,
            s.subject_code,
            s.subject_name,
            s.year_level,
            p.program_code,
            sp.specialization_name,
            COALESCE(AVG(CASE WHEN e.exam_type = 'Quiz' THEN (ea.score / e.total_questions) * 100 END), 0) as avg_quiz_score,
            COALESCE(AVG(CASE WHEN e.exam_type = 'Exam' THEN (ea.score / e.total_questions) * 100 END), 0) as avg_exam_score
        FROM subjects s
        LEFT JOIN programs p ON s.program_id = p.program_id
        LEFT JOIN specializations sp ON s.specialization_id = sp.specialization_id
        LEFT JOIN course_assignments ca ON s.subject_id = ca.subject_id
        LEFT JOIN exams e ON ca.assignment_id = e.assignment_id
        LEFT JOIN exam_attempts ea ON e.exam_id = ea.exam_id AND ea.status IN ('Submitted', 'Auto Submitted')
        WHERE 1=1
    """
    params = []
    
    # Apply filters
    if program_id:
        query += " AND s.program_id = %s"
        params.append(program_id)
    
    if specialization_id:
        query += " AND s.specialization_id = %s"
        params.append(specialization_id)
    
    if year_level:
        query += " AND s.year_level = %s"
        params.append(year_level)
    
    query += " GROUP BY s.subject_id, s.subject_code, s.subject_name, s.year_level, p.program_code, sp.specialization_name"
    query += " ORDER BY s.subject_code"
    
    cursor.execute(query, params)
    subject_data = cursor.fetchall()
    
    cursor.close()
    db.close()
    
    # Format data for chart
    labels = []
    quiz_scores = []
    exam_scores = []
    
    for subject in subject_data:
        label = f"{subject['subject_code']} ({subject['subject_name']})"
        labels.append(label)
        quiz_scores.append(round(subject['avg_quiz_score'], 1) if subject['avg_quiz_score'] else 0)
        exam_scores.append(round(subject['avg_exam_score'], 1) if subject['avg_exam_score'] else 0)
    
    return jsonify({
        'success': True,
        'subject_performance': {
            'labels': labels,
            'quiz_scores': quiz_scores,
            'exam_scores': exam_scores
        }
    })


@admin.route('/api/activity_logs/<int:log_id>')
@role_required('ADMIN')
def api_activity_log_details(log_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT
            sal.log_id,
            sal.user_id,
            sal.role,
            sal.action,
            sal.target_table,
            sal.target_id,
            sal.description,
            sal.ip_address,
            sal.created_at,
            u.first_name,
            u.middle_name,
            u.last_name,
            u.email,
            u.username,
            CONCAT(u.first_name, ' ', u.last_name) as full_name
        FROM system_activity_logs sal
        JOIN users u ON sal.user_id = u.user_id
        WHERE sal.log_id = %s
    """, (log_id,))
    
    log = cursor.fetchone()
    cursor.close()
    db.close()
    
    if not log:
        return jsonify({'success': False, 'message': 'Activity log not found'}), 404
    
    # Format timestamp
    if log['created_at']:
        log['created_at_formatted'] = log['created_at'].strftime('%B %d, %Y at %I:%M %p')
    
    return jsonify({'success': True, 'log': log})


@admin.route('/activity_logs')
@role_required('ADMIN')
def activity_logs():
    # Get filter parameters
    search = request.args.get('search', '').strip()
    role_filter = request.args.get('role', '')
    module_filter = request.args.get('module', '')
    page = request.args.get('page', 1, type=int)
    per_page = 15

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Build query for system activity logs
    query = """
        SELECT
            sal.log_id,
            sal.user_id,
            sal.role,
            sal.action,
            sal.target_table,
            sal.target_id,
            sal.description,
            sal.ip_address,
            sal.created_at,
            u.first_name,
            u.middle_name,
            u.last_name,
            CONCAT(u.first_name, ' ', u.last_name) as full_name
        FROM system_activity_logs sal
        JOIN users u ON sal.user_id = u.user_id
        WHERE 1=1
    """
    count_query = """
        SELECT COUNT(*) as total
        FROM system_activity_logs sal
        JOIN users u ON sal.user_id = u.user_id
        WHERE 1=1
    """
    params = []

    # Apply search filter
    if search:
        query += " AND (u.first_name LIKE %s OR u.last_name LIKE %s OR sal.action LIKE %s OR sal.description LIKE %s)"
        count_query += " AND (u.first_name LIKE %s OR u.last_name LIKE %s OR sal.action LIKE %s OR sal.description LIKE %s)"
        search_term = f"%{search}%"
        params.extend([search_term, search_term, search_term, search_term])

    # Apply role filter
    if role_filter:
        query += " AND sal.role = %s"
        count_query += " AND sal.role = %s"
        params.append(role_filter)

    # Apply module filter based on target_table
    if module_filter == 'users':
        query += " AND sal.target_table IN ('users', 'student_profiles', 'teacher_profiles')"
        count_query += " AND sal.target_table IN ('users', 'student_profiles', 'teacher_profiles')"
    elif module_filter == 'programs':
        query += " AND sal.target_table IN ('programs', 'subjects', 'blocks')"
        count_query += " AND sal.target_table IN ('programs', 'subjects', 'blocks')"
    elif module_filter == 'exams':
        query += " AND sal.target_table IN ('exams', 'exam_questions')"
        count_query += " AND sal.target_table IN ('exams', 'exam_questions')"
    elif module_filter == 'assignments':
        query += " AND sal.target_table = 'course_assignments'"
        count_query += " AND sal.target_table = 'course_assignments'"

    query += " ORDER BY sal.created_at DESC LIMIT %s OFFSET %s"
    params.extend([per_page, (page - 1) * per_page])

    # Fetch activity logs
    cursor.execute(query, params)
    logs = cursor.fetchall()

    # Get total count for pagination
    cursor.execute(count_query, params[:-2])
    total = cursor.fetchone()['total']

    cursor.close()
    db.close()

    # Format data for template
    for log in logs:
        # Format timestamp
        if log['created_at']:
            log['date_display'] = log['created_at'].strftime('%B %d, %Y')
            log['time_display'] = log['created_at'].strftime('%I:%M %p')
        
        # Generate initials for avatar
        initials = ''.join([word[0].upper() for word in log['full_name'].split() if word])[:2]
        log['initials'] = initials if initials else 'UN'
        
        # Determine action type and badge color
        action_lower = log['action'].lower()
        if 'add' in action_lower or 'create' in action_lower:
            log['action_type'] = 'Created'
            log['badge_class'] = 'bg-green-100 text-green-700 border-green-200'
        elif 'update' in action_lower or 'edit' in action_lower:
            log['action_type'] = 'Updated'
            log['badge_class'] = 'bg-blue-100 text-blue-700 border-blue-200'
        elif 'publish' in action_lower:
            log['action_type'] = 'Published'
            log['badge_class'] = 'bg-purple-100 text-purple-700 border-purple-200'
        elif 'close' in action_lower or 'deactivate' in action_lower:
            log['action_type'] = 'Closed'
            log['badge_class'] = 'bg-red-100 text-red-700 border-red-200'
        elif 'assign' in action_lower:
            log['action_type'] = 'Assigned'
            log['badge_class'] = 'bg-orange-100 text-orange-700 border-orange-200'
        else:
            log['action_type'] = log['action']
            log['badge_class'] = 'bg-gray-100 text-gray-700 border-gray-200'
        
        # Determine icon based on target_table
        target_table = log['target_table']
        if target_table in ['users', 'student_profiles', 'teacher_profiles']:
            log['icon'] = 'ph-user-plus'
        elif target_table == 'programs':
            log['icon'] = 'ph-buildings'
        elif target_table == 'subjects':
            log['icon'] = 'ph-books'
        elif target_table == 'blocks':
            log['icon'] = 'ph-users-three'
        elif target_table in ['exams', 'exam_questions']:
            log['icon'] = 'ph-file-text'
        elif target_table == 'course_assignments':
            log['icon'] = 'ph-chalkboard-teacher'
        else:
            log['icon'] = 'ph-list-magnifying-glass'

    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    showing_start = (page - 1) * per_page + 1 if total > 0 else 0
    showing_end = min(page * per_page, total) if total > 0 else 0

    return render_template('activity_logs.html',
                          logs=logs,
                          search=search,
                          role_filter=role_filter,
                          module_filter=module_filter,
                          page=page,
                          per_page=per_page,
                          total=total,
                          total_pages=total_pages,
                          showing_start=showing_start,
                          showing_end=showing_end)


@admin.route('/announcements')
@role_required('ADMIN')
def announcements():
    return render_template('announcements.html')


@admin.route('/teachers')
@role_required('ADMIN')
def teachers():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    # Fetch departments for dropdown
    cursor.execute("SELECT department_id, department_code, department_name FROM departments ORDER BY department_code")
    departments = cursor.fetchall()
    
    # Fetch teachers with their data
    cursor.execute("""
        SELECT u.user_id, u.status, u.first_name, u.middle_name, u.last_name, u.email, u.gender,
               tp.teacher_id, tp.employee_id, tp.department_id,
               d.department_code, d.department_name
        FROM users u
        JOIN teacher_profiles tp ON u.user_id = tp.user_id
        LEFT JOIN departments d ON tp.department_id = d.department_id
        WHERE u.role = 'TEACHER'
        ORDER BY tp.employee_id
    """)
    teachers_list = cursor.fetchall()
    
    # Fetch stats
    cursor.execute("SELECT COUNT(*) as total FROM users WHERE role = 'TEACHER'")
    total = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as male FROM users u JOIN teacher_profiles tp ON u.user_id = tp.user_id WHERE u.role = 'TEACHER' AND u.gender = 'Male'")
    male = cursor.fetchone()['male']
    
    cursor.execute("SELECT COUNT(*) as female FROM users u JOIN teacher_profiles tp ON u.user_id = tp.user_id WHERE u.role = 'TEACHER' AND u.gender = 'Female'")
    female = cursor.fetchone()['female']
    
    stats = {'total': total, 'male': male, 'female': female}
    
    cursor.close()
    db.close()
    
    return render_template('teachers.html', teachers=teachers_list, departments=departments, stats=stats)


# ============================================
# TEACHERS API ROUTES
# ============================================

@admin.route('/api/teachers/counts', methods=['GET'])
@role_required('ADMIN')
def api_teachers_counts():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) as total FROM users WHERE role = 'TEACHER'")
    total = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) as male FROM users u JOIN teacher_profiles tp ON u.user_id = tp.user_id WHERE u.role = 'TEACHER' AND u.gender = 'Male'")
    male = cursor.fetchone()['male']

    cursor.execute("SELECT COUNT(*) as female FROM users u JOIN teacher_profiles tp ON u.user_id = tp.user_id WHERE u.role = 'TEACHER' AND u.gender = 'Female'")
    female = cursor.fetchone()['female']

    cursor.close()
    db.close()

    return jsonify({'success': True, 'total': total, 'male': male, 'female': female})


@admin.route('/api/teachers', methods=['GET'])
@role_required('ADMIN')
def api_teachers():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    department_id = request.args.get('department_id', '').strip()
    status = request.args.get('status', '').strip()
    search = request.args.get('search', '').strip()

    offset = (page - 1) * per_page

    query = """
        SELECT u.user_id, u.status, u.created_at, u.first_name, u.middle_name, u.last_name, u.email, u.gender,
               tp.teacher_id, tp.employee_id, d.department_code, d.department_id
        FROM users u
        JOIN teacher_profiles tp ON u.user_id = tp.user_id
        LEFT JOIN departments d ON tp.department_id = d.department_id
        WHERE u.role = 'TEACHER'
    """
    
    count_query = """
        SELECT COUNT(*) as total FROM users u
        JOIN teacher_profiles tp ON u.user_id = tp.user_id
        WHERE u.role = 'TEACHER'
    """
    
    params = []
    conditions = []

    if department_id:
        conditions.append("tp.department_id = %s")
        params.append(department_id)
    if status:
        conditions.append("u.status = %s")
        params.append(status)
    if search:
        conditions.append("(u.first_name LIKE %s OR u.last_name LIKE %s OR u.email LIKE %s OR tp.employee_id LIKE %s)")
        like_term = f"%{search}%"
        params.extend([like_term, like_term, like_term, like_term])

    if conditions:
        where_clause = " AND " + " AND ".join(conditions)
        query += where_clause
        count_query += " AND " + " AND ".join(conditions)

    query += " ORDER BY tp.employee_id LIMIT %s OFFSET %s"
    params.extend([per_page, offset])

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute(count_query, params[:-2] if conditions else [])
    total = cursor.fetchone()['total']

    cursor.execute(query, params)
    teachers = cursor.fetchall()

    cursor.close()
    db.close()

    for t in teachers:
        if t.get('created_at'):
            t['created_at'] = t['created_at'].strftime('%Y-%m-%d %H:%M:%S')

    total_pages = (total + per_page - 1) // per_page if total > 0 else 1

    return jsonify({
        'success': True,
        'teachers': teachers,
        'total': total,
        'total_pages': total_pages,
        'page': page,
        'per_page': per_page
    })


@admin.route('/api/teachers/add', methods=['POST'])
@role_required('ADMIN')
def create_teacher():
    """Create a new teacher with full server-side validation."""
    data = request.get_json() or request.form

    # --- Normalise text helpers ---
    def normalise_name(val):
        """Trim, collapse internal spaces, title-case each word."""
        cleaned = re.sub(r'\s+', ' ', (val or '').strip())
        return ' '.join(w.capitalize() for w in cleaned.split())

    NAME_PATTERN = re.compile(r'^[A-Za-z]+(\s[A-Za-z]+)*\.?$')
    EMAIL_PATTERN = re.compile(r'^[a-z0-9._%+\-]+@(gmail\.com|.*\.edu\.ph)$')
    CONTACT_PATTERN = re.compile(r'^(09|\+63)\d{9}$')
    CONSECUTIVE_RE = re.compile(r'(.)\1\1')  # 3+ same consecutive digits

    first_name  = normalise_name(data.get('first_name', ''))
    last_name   = normalise_name(data.get('last_name', ''))
    middle_name = normalise_name(data.get('middle_name', ''))
    email       = (data.get('email', '') or '').strip().lower()
    gender      = (data.get('gender', '') or '').strip()
    birthdate   = (data.get('birthdate', '') or '').strip()
    contact_number = (data.get('contact_number', '') or '').strip()
    province    = (data.get('province', '') or '').strip()
    municipal   = (data.get('municipal', '') or '').strip()
    barangay    = (data.get('barangay', '') or '').strip()
    department_id = data.get('department_id')

    errors = {}

    # First name
    if not first_name:
        errors['first_name'] = 'First name is required.'
    elif not NAME_PATTERN.match(first_name):
        errors['first_name'] = 'First name must contain letters only (single spaces allowed between words).'

    # Last name
    if not last_name:
        errors['last_name'] = 'Last name is required.'
    elif not NAME_PATTERN.match(last_name):
        errors['last_name'] = 'Last name must contain letters only (single spaces allowed between words).'

    # Middle name (optional)
    if middle_name and not NAME_PATTERN.match(middle_name):
        errors['middle_name'] = 'Middle name must contain letters only (single spaces allowed between words).'

    # Email
    if not email:
        errors['email'] = 'Email is required.'
    elif not EMAIL_PATTERN.match(email):
        errors['email'] = 'Email must be a valid lowercase Gmail or .edu.ph address.'

    # Gender
    if not gender or gender not in ('Male', 'Female'):
        errors['gender'] = 'Please select a valid gender.'

    # Birthdate
    if not birthdate:
        errors['birthdate'] = 'Birthdate is required.'
    else:
        try:
            datetime.datetime.strptime(birthdate, '%Y-%m-%d')
        except ValueError:
            errors['birthdate'] = 'Birthdate must be in YYYY-MM-DD format.'

    # Contact number
    if not contact_number:
        errors['contact_number'] = 'Contact number is required.'
    else:
        digits_only = re.sub(r'[^\d]', '', contact_number)
        if not CONTACT_PATTERN.match(contact_number):
            errors['contact_number'] = 'Contact number must start with 09 or +63 and be 11 digits total.'
        elif CONSECUTIVE_RE.search(digits_only):
            errors['contact_number'] = 'Contact number cannot have more than 3 consecutive identical digits.'

    # Address fields
    if not province:
        errors['province'] = 'Province is required.'
    if not municipal:
        errors['municipal'] = 'Municipality is required.'
    if not barangay:
        errors['barangay'] = 'Barangay is required.'

    # Department
    if not department_id:
        errors['department_id'] = 'Department is required.'

    if errors:
        return jsonify({'success': False, 'message': 'Validation failed.', 'errors': errors}), 422

    try:
        department_id = int(department_id)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Invalid department ID.'}), 400

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Duplicate email check
    cursor.execute("SELECT 1 FROM users WHERE email = %s", (email,))
    if cursor.fetchone():
        cursor.close()
        db.close()
        return jsonify({'success': False, 'message': 'This email address is already registered.', 'errors': {'email': 'Email already exists.'}}), 409

    # Department lookup
    cursor.execute("SELECT department_code FROM departments WHERE department_id = %s", (department_id,))
    department = cursor.fetchone()
    if not department:
        cursor.close()
        db.close()
        return jsonify({'success': False, 'message': 'Department not found.'}), 404

    department_code = department['department_code']

    # Auto-generate employee_id
    cursor.execute(
        "SELECT employee_id FROM teacher_profiles WHERE employee_id LIKE %s ORDER BY employee_id DESC LIMIT 1",
        (f"{department_code}%",)
    )
    result = cursor.fetchone()
    if result:
        last_num = int(result['employee_id'].replace(department_code, ''))
        employee_id = f"{department_code}{last_num + 1:04d}"
    else:
        employee_id = f"{department_code}0001"

    # Compose full address
    address = ', '.join(filter(None, [barangay, municipal, province]))

    try:
        cursor.execute(
            """
            INSERT INTO users
                (username, password, email, first_name, middle_name, last_name,
                 gender, role, status, created_at, birthdate, contact_number, address)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'TEACHER', 'Active', NOW(), %s, %s, %s)
            """,
            (employee_id, employee_id, email, first_name, middle_name, last_name, gender, birthdate or None, contact_number or None, address or None)
        )
        user_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO teacher_profiles
                (user_id, department_id, employee_id, created_at)
            VALUES (%s, %s, %s, NOW())
            """,
            (user_id, department_id, employee_id)
        )

        db.commit()
        cursor.close()
        db.close()

        # Log the activity
        from flask import session
        admin_user_id = session.get('user_id')
        admin_ip = request.remote_addr
        log_activity(
            user_id=admin_user_id,
            role='admin',
            action='Add teacher',
            target_table='teacher_profiles',
            target_id=user_id,
            description=f'Created new teacher: {first_name} {last_name} (Employee ID: {employee_id})',
            ip_address=admin_ip
        )

        return jsonify({
            'success': True,
            'message': 'Teacher added successfully.',
            'user_id': user_id,
            'employee_id': employee_id
        })
    except Exception as e:
        db.rollback()
        cursor.close()
        db.close()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin.route('/api/teachers/update-status/<int:user_id>', methods=['POST'])
@role_required('ADMIN')
def update_teacher_status(user_id):
    data = request.get_json() or request.form
    status = data.get('status', '').strip()

    if not status or status not in ['Active', 'Inactive']:
        return jsonify({'success': False, 'message': 'Invalid status'}), 400

    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute("UPDATE users SET status = %s WHERE user_id = %s AND role = 'TEACHER'", (status, user_id))
        db.commit()

        if cursor.rowcount == 0:
            cursor.close()
            db.close()
            return jsonify({'success': False, 'message': 'Teacher not found'}), 404

        cursor.close()
        db.close()
        
        # Log the activity
        from flask import session
        admin_user_id = session.get('user_id')
        admin_ip = request.remote_addr
        action_type = 'Deactivate user' if status == 'Inactive' else 'Update user'
        log_activity(
            user_id=admin_user_id,
            role='admin',
            action=action_type,
            target_table='users',
            target_id=user_id,
            description=f'{action_type}: Teacher ID {user_id} status changed to {status}',
            ip_address=admin_ip
        )
        
        return jsonify({'success': True, 'message': 'Status updated successfully'})
    except Exception as e:
        cursor.close()
        db.close()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin.route('/api/teachers/delete/<int:user_id>', methods=['POST'])
@role_required('ADMIN')
def delete_teacher_api(user_id):
    db = get_db_connection()
    cursor = db.cursor()

    try:
        # Delete teacher profile first
        cursor.execute("DELETE FROM teacher_profiles WHERE user_id = %s", (user_id,))
        # Then delete user
        cursor.execute("DELETE FROM users WHERE user_id = %s AND role = 'TEACHER'", (user_id,))
        db.commit()

        if cursor.rowcount == 0:
            cursor.close()
            db.close()
            return jsonify({'success': False, 'message': 'Teacher not found'}), 404

        cursor.close()
        db.close()
        return jsonify({'success': True, 'message': 'Teacher deleted successfully'})
    except Exception as e:
        cursor.close()
        db.close()
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================
# PROGRAMS API ROUTES
# ============================================

@admin.route('/api/programs', methods=['GET'])
@role_required('ADMIN')
def api_programs():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT p.*, d.department_code, d.department_name, COUNT(DISTINCT b.block_id) as total_blocks, 
               GROUP_CONCAT(DISTINCT s.specialization_name ORDER BY s.specialization_code SEPARATOR ', ') as specialization_names
        FROM programs p
        LEFT JOIN departments d ON p.department_id = d.department_id
        LEFT JOIN blocks b ON p.program_id = b.program_id
        LEFT JOIN specializations s ON p.program_id = s.program_id
        GROUP BY p.program_id
        ORDER BY p.program_code
    """)
    programs_list = cursor.fetchall()
    cursor.close()
    db.close()

    for p in programs_list:
        if p['created_at']:
            p['created_at'] = p['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        p['total_blocks'] = int(p['total_blocks'] or 0)
        p['specialization_names'] = p['specialization_names'] or ''

    return jsonify({'success': True, 'programs': programs_list})


@admin.route('/api/programs/search', methods=['GET'])
@role_required('ADMIN')
def search_programs():
    query = request.args.get('q', '').strip()
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    if query:
        search_term = f"%{query}%"
        cursor.execute("""
            SELECT p.*, d.department_code, d.department_name, COUNT(DISTINCT b.block_id) as total_blocks, 
                   GROUP_CONCAT(DISTINCT s.specialization_name ORDER BY s.specialization_code SEPARATOR ', ') as specialization_names
            FROM programs p
            LEFT JOIN departments d ON p.department_id = d.department_id
            LEFT JOIN blocks b ON p.program_id = b.program_id
            LEFT JOIN specializations s ON p.program_id = s.program_id
            WHERE p.program_code LIKE %s OR p.program_name LIKE %s
            GROUP BY p.program_id
            ORDER BY p.program_code
        """, (search_term, search_term))
    else:
        cursor.execute("""
            SELECT p.*, d.department_code, d.department_name, COUNT(DISTINCT b.block_id) as total_blocks, 
                   GROUP_CONCAT(DISTINCT s.specialization_name ORDER BY s.specialization_code SEPARATOR ', ') as specialization_names
            FROM programs p
            LEFT JOIN departments d ON p.department_id = d.department_id
            LEFT JOIN blocks b ON p.program_id = b.program_id
            LEFT JOIN specializations s ON p.program_id = s.program_id
            GROUP BY p.program_id
            ORDER BY p.program_code
        """)

    programs_list = cursor.fetchall()
    cursor.close()
    db.close()

    for p in programs_list:
        if p['created_at']:
            p['created_at'] = p['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        p['total_blocks'] = int(p['total_blocks'] or 0)
        p['specialization_names'] = p['specialization_names'] or ''

    return jsonify({'success': True, 'programs': programs_list})



@admin.route('/api/program/<int:program_id>', methods=['GET'])
@role_required('ADMIN')
def get_program(program_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT p.*, d.department_code, d.department_name 
        FROM programs p 
        LEFT JOIN departments d ON p.department_id = d.department_id 
        WHERE p.program_id = %s
    """, (program_id,))
    program = cursor.fetchone()

    if not program:
        cursor.close()
        db.close()
        return jsonify({'success': False, 'message': 'Program not found'}), 404

    cursor.execute("""
        SELECT b.* FROM blocks b WHERE b.program_id = %s ORDER BY b.year_level, b.section
    """, (program_id,))

    blocks = cursor.fetchall()

    cursor.execute("""
        SELECT specialization_id, specialization_name, specialization_code, created_at 
        FROM specializations 
        WHERE program_id = %s 
        ORDER BY specialization_code
    """, (program_id,))
    specializations = cursor.fetchall()

    cursor.close()
    db.close()

    if program['created_at']:
        program['created_at'] = program['created_at'].strftime('%Y-%m-%d %H:%M:%S')

    for b in blocks:
        if b['created_at']:
            b['created_at'] = b['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        b['total_students'] = None

    for s in specializations:
        if s['created_at']:
            s['created_at'] = s['created_at'].strftime('%Y-%m-%d %H:%M:%S')

    return jsonify({
        'success': True,
        'program': program,
        'blocks': blocks,
        'specializations': specializations
    })


@admin.route('/api/all-specializations', methods=['GET'])
@role_required('ADMIN')
def get_all_specializations():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT s.specialization_id, s.program_id, s.specialization_name, s.specialization_code, p.program_code
        FROM specializations s
        JOIN programs p ON s.program_id = p.program_id
        ORDER BY p.program_code, s.specialization_code
    """)
    specializations = cursor.fetchall()
    cursor.close()
    db.close()
    
    for s in specializations:
        if s.get('created_at'):
            s['created_at'] = s['created_at'].strftime('%Y-%m-%d %H:%M:%S')
    
    return jsonify({'success': True, 'specializations': specializations})




@admin.route('/program/add', methods=['POST'])
@role_required('ADMIN')
def add_program():
    data = request.get_json() or request.form
    program_code = data.get('program_code', '').strip().upper()
    program_name = data.get('program_name', '').strip()
    department_id = data.get('department_id')

    if not program_code or not program_name or not department_id:
        return jsonify({'success': False, 'message': 'Program code, name, and department are required'}), 400

    try:
        department_id = int(department_id)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Invalid department ID'}), 400

    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute(
            "INSERT INTO programs (program_code, program_name, department_id) VALUES (%s, %s, %s)",
            (program_code, program_name, department_id)
        )
        db.commit()
        new_id = cursor.lastrowid

        # Insert specializations if provided
        specializations = data.get('specializations', [])
        if specializations and isinstance(specializations, list):
            for spec in specializations:
                spec_name = spec.get('specialization_name', '').strip()
                spec_code = spec.get('specialization_code', '').strip().upper()
                if spec_name and spec_code:
                    cursor.execute(
                        "INSERT INTO specializations (program_id, specialization_name, specialization_code) VALUES (%s, %s, %s)",
                        (new_id, spec_name, spec_code)
                    )
            db.commit()

        cursor.close()
        db.close()

        # Log the activity
        from flask import session
        admin_user_id = session.get('user_id')
        admin_ip = request.remote_addr
        log_activity(
            user_id=admin_user_id,
            role='admin',
            action='Add program',
            target_table='programs',
            target_id=new_id,
            description=f'Created new program: {program_name} ({program_code})',
            ip_address=admin_ip
        )

        return jsonify({
            'success': True,
            'message': 'Program added successfully',
            'program_id': new_id
        })

    except mysql.connector.IntegrityError:
        cursor.close()
        db.close()
        return jsonify({'success': False, 'message': 'Program code already exists'}), 409
    except Exception as e:
        cursor.close()
        db.close()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin.route('/program/edit/<int:program_id>', methods=['POST'])
@role_required('ADMIN')
def edit_program(program_id):
    data = request.get_json() or request.form
    program_code = data.get('program_code', '').strip().upper()
    program_name = data.get('program_name', '').strip()
    department_id = data.get('department_id')

    if not program_code or not program_name or not department_id:
        return jsonify({'success': False, 'message': 'Program code, name, and department are required'}), 400

    try:
        department_id = int(department_id)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Invalid department ID'}), 400

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute(
            "UPDATE programs SET program_code = %s, program_name = %s, department_id = %s WHERE program_id = %s",
            (program_code, program_name, department_id, program_id)
        )

        # Check if program exists (rowcount may be 0 if values unchanged)
        cursor.execute("SELECT 1 FROM programs WHERE program_id = %s", (program_id,))
        if not cursor.fetchone():
            cursor.close()
            db.close()
            return jsonify({'success': False, 'message': 'Program not found'}), 404

        # Handle specializations
        specializations = data.get('specializations', [])
        if specializations is not None and isinstance(specializations, list):
            # Get existing specializations
            cursor.execute(
                "SELECT specialization_id FROM specializations WHERE program_id = %s",
                (program_id,)
            )
            existing_ids = {row['specialization_id'] for row in cursor.fetchall()}

            incoming_ids = set()
            for spec in specializations:
                spec_id = spec.get('specialization_id')
                spec_name = spec.get('specialization_name', '').strip()
                spec_code = spec.get('specialization_code', '').strip().upper()

                if not spec_name or not spec_code:
                    continue

                if spec_id:
                    # Update existing
                    cursor.execute(
                        "UPDATE specializations SET specialization_name = %s, specialization_code = %s WHERE specialization_id = %s AND program_id = %s",
                        (spec_name, spec_code, spec_id, program_id)
                    )
                    incoming_ids.add(int(spec_id))
                else:
                    # Insert new
                    cursor.execute(
                        "INSERT INTO specializations (program_id, specialization_name, specialization_code) VALUES (%s, %s, %s)",
                        (program_id, spec_name, spec_code)
                    )

            # Delete removed specializations
            to_delete = existing_ids - incoming_ids
            for sid in to_delete:
                cursor.execute(
                    "DELETE FROM specializations WHERE specialization_id = %s AND program_id = %s",
                    (sid, program_id)
                )

        db.commit()
        cursor.close()
        db.close()
        return jsonify({'success': True, 'message': 'Program updated successfully'})
    except mysql.connector.IntegrityError:
        cursor.close()
        db.close()
        return jsonify({'success': False, 'message': 'Program code or specialization code already exists'}), 409
    except Exception as e:
        cursor.close()
        db.close()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin.route('/program/delete/<int:program_id>', methods=['POST'])
@role_required('ADMIN')
def delete_program(program_id):
    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute("DELETE FROM blocks WHERE program_id = %s", (program_id,))
        cursor.execute("DELETE FROM specializations WHERE program_id = %s", (program_id,))
        cursor.execute("DELETE FROM programs WHERE program_id = %s", (program_id,))
        db.commit()

        if cursor.rowcount == 0:
            cursor.close()
            db.close()
            return jsonify({'success': False, 'message': 'Program not found'}), 404

        cursor.close()
        db.close()
        return jsonify({'success': True, 'message': 'Program deleted successfully'})
    except Exception as e:
        cursor.close()
        db.close()
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================
# DEPARTMENTS API ROUTES
# ============================================

@admin.route('/api/departments', methods=['GET'])
@role_required('ADMIN')
def api_departments():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM departments ORDER BY department_code")
    departments_list = cursor.fetchall()
    cursor.close()
    db.close()
    
    for d in departments_list:
        if d.get('created_at'):
            d['created_at'] = d['created_at'].strftime('%Y-%m-%d %H:%M:%S')
    
    return jsonify({'success': True, 'departments': departments_list})


@admin.route('/api/department/add', methods=['POST'])
@role_required('ADMIN')
def add_department():
    data = request.get_json() or request.form
    department_name = data.get('department_name', '').strip()
    department_code = data.get('department_code', '').strip().upper()

    if not department_code or not department_name:
        return jsonify({'success': False, 'message': 'Department code and name are required'}), 400

    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute(
            "INSERT INTO departments (department_code, department_name) VALUES (%s, %s)",
            (department_code, department_name)
        )
        db.commit()
        new_id = cursor.lastrowid

        cursor.close()
        db.close()

        return jsonify({
            'success': True,
            'message': 'Department added successfully',
            'department_id': new_id
        })

    except mysql.connector.IntegrityError:
        cursor.close()
        db.close()
        return jsonify({'success': False, 'message': 'Department code already exists'}), 409
    except Exception as e:
        cursor.close()
        db.close()
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================
# BLOCKS API ROUTES
# ============================================

@admin.route('/block/add', methods=['POST'])
@role_required('ADMIN')
def add_block():
    data = request.get_json() or request.form
    program_id = data.get('program_id')
    year_level = data.get('year_level')
    specialization_id = data.get('specialization_id')

    if not program_id or not year_level:
        return jsonify({'success': False, 'message': 'Program and year level are required'}), 400

    try:
        program_id = int(program_id)
        year_level = int(year_level)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Invalid program or year level'}), 400

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT program_code FROM programs WHERE program_id = %s", (program_id,))
    program = cursor.fetchone()

    if not program:
        cursor.close()
        db.close()
        return jsonify({'success': False, 'message': 'Program not found'}), 404

    program_code = program['program_code']

    # Get specialization code if provided
    specialization_code = None
    if specialization_id:
        try:
            specialization_id = int(specialization_id)
            cursor.execute(
                "SELECT specialization_code FROM specializations WHERE specialization_id = %s AND program_id = %s",
                (specialization_id, program_id)
            )
            spec = cursor.fetchone()
            if spec:
                specialization_code = spec['specialization_code']
        except (ValueError, TypeError):
            pass

    section = get_next_section(program_id, year_level)
    block_name = generate_block_name(program_code, year_level, section, specialization_code)

    try:
        cursor.execute(
            "INSERT INTO blocks (program_id, year_level, section, block_name) VALUES (%s, %s, %s, %s)",
            (program_id, year_level, section, block_name)
        )
        db.commit()
        new_id = cursor.lastrowid
        cursor.close()
        db.close()

        # Log the activity
        from flask import session
        admin_user_id = session.get('user_id')
        admin_ip = request.remote_addr
        log_activity(
            user_id=admin_user_id,
            role='admin',
            action='Create block',
            target_table='blocks',
            target_id=new_id,
            description=f'Created new block: {block_name} (Year {year_level}, Section {section})',
            ip_address=admin_ip
        )

        return jsonify({
            'success': True,
            'message': 'Block added successfully',
            'block_id': new_id,
            'block_name': block_name,
            'section': section
        })
    except Exception as e:
        cursor.close()
        db.close()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin.route('/block/edit/<int:block_id>', methods=['POST'])
@role_required('ADMIN')
def edit_block(block_id):
    data = request.get_json() or request.form
    year_level = data.get('year_level')

    if not year_level:
        return jsonify({'success': False, 'message': 'Year level is required'}), 400

    try:
        year_level = int(year_level)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Invalid year level'}), 400

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT b.*, p.program_code FROM blocks b JOIN programs p ON b.program_id = p.program_id WHERE b.block_id = %s", (block_id,))
    block = cursor.fetchone()

    if not block:
        cursor.close()
        db.close()
        return jsonify({'success': False, 'message': 'Block not found'}), 404

    program_code = block['program_code']
    section = block['section']

    # Preserve specialization code in block name if present
    specialization_code = None
    current_name = block['block_name']
    if current_name.startswith(program_code + '-'):
        remainder = current_name[len(program_code) + 1:]
        if len(remainder) >= 3:
            specialization_code = remainder[:-2]

    new_block_name = generate_block_name(program_code, year_level, section, specialization_code)

    try:
        cursor.execute(
            "UPDATE blocks SET year_level = %s, block_name = %s WHERE block_id = %s",
            (year_level, new_block_name, block_id)
        )
        db.commit()
        cursor.close()
        db.close()

        return jsonify({
            'success': True,
            'message': 'Block updated successfully',
            'block_name': new_block_name
        })
    except Exception as e:
        cursor.close()
        db.close()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin.route('/block/delete/<int:block_id>', methods=['POST'])
@role_required('ADMIN')
def delete_block(block_id):
    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute("DELETE FROM blocks WHERE block_id = %s", (block_id,))
        db.commit()

        if cursor.rowcount == 0:
            cursor.close()
            db.close()
            return jsonify({'success': False, 'message': 'Block not found'}), 404

        cursor.close()
        db.close()

        return jsonify({
            'success': True,
            'message': 'Block deleted successfully'
        })
    except Exception as e:
        cursor.close()
        db.close()
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================
# STUDENTS API ROUTES
# ============================================

@admin.route('/api/students/counts', methods=['GET'])
@role_required('ADMIN')
def api_students_counts():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) as total FROM users u JOIN student_profiles sp ON u.user_id = sp.student_id WHERE u.role = 'STUDENT'")
    total = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) as male FROM users u JOIN student_profiles sp ON u.user_id = sp.student_id WHERE u.role = 'STUDENT' AND u.gender = 'Male'")
    male = cursor.fetchone()['male']

    cursor.execute("SELECT COUNT(*) as female FROM users u JOIN student_profiles sp ON u.user_id = sp.student_id WHERE u.role = 'STUDENT' AND u.gender = 'Female'")
    female = cursor.fetchone()['female']

    cursor.close()
    db.close()

    return jsonify({'success': True, 'total': total, 'male': male, 'female': female})


@admin.route('/api/students', methods=['GET'])
@role_required('ADMIN')
def api_students():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    program_id = request.args.get('program_id', '').strip()
    year_level = request.args.get('year_level', '').strip()
    search = request.args.get('search', '').strip()

    offset = (page - 1) * per_page

    query = """
        SELECT u.user_id, u.status, u.first_name, u.middle_name, u.last_name, u.email, u.gender,
               sp.student_id, sp.student_number, sp.year_level,
               p.program_code, p.program_name,
               b.block_name
        FROM users u
        JOIN student_profiles sp ON u.user_id = sp.student_id
        LEFT JOIN programs p ON sp.program_id = p.program_id
        LEFT JOIN blocks b ON sp.block_id = b.block_id
        WHERE u.role = 'STUDENT'
    """
    
    count_query = """
        SELECT COUNT(*) as total FROM users u
        JOIN student_profiles sp ON u.user_id = sp.student_id
        WHERE u.role = 'STUDENT'
    """
    
    params = []
    conditions = []

    if program_id:
        conditions.append("sp.program_id = %s")
        params.append(program_id)
    if year_level:
        conditions.append("sp.year_level = %s")
        params.append(year_level)
    if search:
        conditions.append("(u.first_name LIKE %s OR u.last_name LIKE %s OR sp.student_number LIKE %s)")
        like_term = f"%{search}%"
        params.extend([like_term, like_term, like_term])

    if conditions:
        where_clause = " AND " + " AND ".join(conditions)
        query += where_clause
        count_query += " AND " + " AND ".join(conditions)

    query += " ORDER BY sp.student_number LIMIT %s OFFSET %s"
    params.extend([per_page, offset])

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute(count_query, params[:-2] if conditions else [])
    total = cursor.fetchone()['total']

    cursor.execute(query, params)
    students = cursor.fetchall()

    cursor.close()
    db.close()

    total_pages = (total + per_page - 1) // per_page if total > 0 else 1

    return jsonify({
        'success': True,
        'students': students,
        'total': total,
        'total_pages': total_pages,
        'page': page,
        'per_page': per_page
    })


@admin.route('/api/students/add', methods=['POST'])
@role_required('ADMIN')
def add_student():
    """Create a new student with full server-side validation."""
    data = request.get_json() or request.form

    # --- Normalise text helpers ---
    def normalise_name(val):
        """Trim, collapse internal spaces, title-case each word."""
        cleaned = re.sub(r'\s+', ' ', (val or '').strip())
        return ' '.join(w.capitalize() for w in cleaned.split())

    NAME_PATTERN = re.compile(r'^[A-Za-z]+(\s[A-Za-z]+)*\.?$')
    EMAIL_PATTERN = re.compile(r'^[a-z0-9._%+\-]+@gmail\.com$')
    CONTACT_PATTERN = re.compile(r'^(09|\+63)\d{9}$')
    CONSECUTIVE_RE = re.compile(r'(.)\1\1')  # 3+ same consecutive digits

    first_name  = normalise_name(data.get('first_name', ''))
    last_name   = normalise_name(data.get('last_name', ''))
    middle_name = normalise_name(data.get('middle_name', ''))
    email       = (data.get('email', '') or '').strip().lower()
    gender      = (data.get('gender', '') or '').strip()
    birthdate   = (data.get('birthdate', '') or '').strip()
    contact_number = (data.get('contact_number', '') or '').strip()
    province    = (data.get('province', '') or '').strip()
    municipal   = (data.get('municipal', '') or '').strip()
    barangay    = (data.get('barangay', '') or '').strip()
    program_id  = data.get('program_id')
    specialization_id = data.get('specialization_id', None)
    year_level  = data.get('year_level')

    errors = {}

    # First name
    if not first_name:
        errors['first_name'] = 'First name is required.'
    elif not NAME_PATTERN.match(first_name):
        errors['first_name'] = 'First name must contain letters only (single spaces allowed between words).'

    # Last name
    if not last_name:
        errors['last_name'] = 'Last name is required.'
    elif not NAME_PATTERN.match(last_name):
        errors['last_name'] = 'Last name must contain letters only (single spaces allowed between words).'

    # Middle name (optional)
    if middle_name and not NAME_PATTERN.match(middle_name):
        errors['middle_name'] = 'Middle name must contain letters only (single spaces allowed between words).'

    # Email
    if not email:
        errors['email'] = 'Email is required.'
    elif not EMAIL_PATTERN.match(email):
        errors['email'] = 'Email must be a valid lowercase Gmail address (e.g. name@gmail.com).'

    # Gender
    if not gender or gender not in ('Male', 'Female'):
        errors['gender'] = 'Please select a valid gender.'

    # Birthdate
    if not birthdate:
        errors['birthdate'] = 'Birthdate is required.'
    else:
        try:
            datetime.datetime.strptime(birthdate, '%Y-%m-%d')
        except ValueError:
            errors['birthdate'] = 'Birthdate must be in YYYY-MM-DD format.'

    # Contact number
    if not contact_number:
        errors['contact_number'] = 'Contact number is required.'
    else:
        digits_only = re.sub(r'[^\d]', '', contact_number)
        if not CONTACT_PATTERN.match(contact_number):
            errors['contact_number'] = 'Contact number must start with 09 or +63 and be 11 digits total.'
        elif CONSECUTIVE_RE.search(digits_only):
            errors['contact_number'] = 'Contact number cannot have more than 3 consecutive identical digits.'

    # Address fields
    if not province:
        errors['province'] = 'Province is required.'
    if not municipal:
        errors['municipal'] = 'Municipality is required.'
    if not barangay:
        errors['barangay'] = 'Barangay is required.'

    # Program / year level
    if not program_id:
        errors['program_id'] = 'Program is required.'
    if not year_level:
        errors['year_level'] = 'Year level is required.'

    if errors:
        return jsonify({'success': False, 'message': 'Validation failed.', 'errors': errors}), 422

    try:
        program_id = int(program_id)
        year_level = int(year_level)
        if specialization_id:
            specialization_id = int(specialization_id)
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Invalid program, year level, or specialization ID.'}), 400

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    # Duplicate email check
    cursor.execute("SELECT 1 FROM users WHERE email = %s", (email,))
    if cursor.fetchone():
        cursor.close()
        db.close()
        return jsonify({'success': False, 'message': 'This email address is already registered.', 'errors': {'email': 'Email already exists.'}}), 409

    # Program lookup
    cursor.execute("SELECT program_code FROM programs WHERE program_id = %s", (program_id,))
    program = cursor.fetchone()
    if not program:
        cursor.close()
        db.close()
        return jsonify({'success': False, 'message': 'Program not found.'}), 404

    program_code = program['program_code']

    # Specialization lookup
    specialization_code = None
    if specialization_id:
        cursor.execute(
            "SELECT specialization_code FROM specializations WHERE specialization_id = %s AND program_id = %s",
            (specialization_id, program_id)
        )
        spec = cursor.fetchone()
        if spec:
            specialization_code = spec['specialization_code']

    # Compose full address
    address = ', '.join(filter(None, [barangay, municipal, province]))

    try:
        # Create user account (username/password will be updated after we get the user_id)
        cursor.execute(
            """
            INSERT INTO users
                (username, password, email, first_name, middle_name, last_name,
                 gender, role, status, birthdate, contact_number, address)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'STUDENT', 'Active', %s, %s, %s)
            """,
            (email, email, email, first_name, middle_name or None, last_name, gender, birthdate or None, contact_number or None, address or None)
        )
        user_id = cursor.lastrowid

        # Generate student number: YYYearLevel-UserID
        current_year = datetime.datetime.now().year % 100
        student_number = f"{current_year}{year_level}-{user_id:04d}"

        hashed_password = generate_password_hash(student_number)
        cursor.execute(
            "UPDATE users SET username = %s, password = %s WHERE user_id = %s",
            (student_number, hashed_password, user_id)
        )

        block_id = assign_student_to_block(cursor, program_id, year_level, program_code, specialization_code)

        cursor.execute(
            """
            INSERT INTO student_profiles
                (user_id, student_number, program_id, block_id, year_level)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (user_id, student_number, program_id, block_id, year_level)
        )

        db.commit()
        cursor.close()
        db.close()

        # Log the activity
        from flask import session
        admin_user_id = session.get('user_id')
        admin_ip = request.remote_addr
        log_activity(
            user_id=admin_user_id,
            role='admin',
            action='Add student',
            target_table='student_profiles',
            target_id=user_id,
            description=f'Created new student: {first_name} {last_name} (Student Number: {student_number})',
            ip_address=admin_ip
        )

        return jsonify({
            'success': True,
            'message': 'Student added successfully.',
            'user_id': user_id,
            'student_number': student_number
        })
    except Exception as e:
        db.rollback()
        cursor.close()
        db.close()
        return jsonify({'success': False, 'message': str(e)}), 500


def assign_student_to_block(cursor, program_id, year_level, program_code, specialization_code=None):
    """
    Assign student to a block. If existing block has < 50 students, add to it.
    Otherwise, create a new block section.
    """
    # Find existing blocks matching program, year level, and specialization
    if specialization_code:
        cursor.execute("""
            SELECT b.block_id, b.section, COUNT(sp.student_id) as student_count
            FROM blocks b
            LEFT JOIN student_profiles sp ON b.block_id = sp.block_id
            WHERE b.program_id = %s AND b.year_level = %s AND b.block_name LIKE %s
            GROUP BY b.block_id, b.section
            ORDER BY b.section
        """, (program_id, year_level, f"{program_code}-{specialization_code}{year_level}%"))
    else:
        cursor.execute("""
            SELECT b.block_id, b.section, COUNT(sp.student_id) as student_count
            FROM blocks b
            LEFT JOIN student_profiles sp ON b.block_id = sp.block_id
            WHERE b.program_id = %s AND b.year_level = %s AND b.block_name LIKE %s
            GROUP BY b.block_id, b.section
            ORDER BY b.section
        """, (program_id, year_level, f"{program_code}{year_level}%"))

    blocks = cursor.fetchall()

    # Find first block with less than 50 students
    for block in blocks:
        if block['student_count'] < 50:
            return block['block_id']

    # If all blocks are full or no blocks exist, create new section
    last_section = 'A'
    if blocks:
        last_section = blocks[-1]['section']
        # Increment section letter
        last_section = chr(ord(last_section) + 1)

    # Generate block name
    if specialization_code:
        block_name = f"{program_code}-{specialization_code}{year_level}{last_section}"
    else:
        block_name = f"{program_code}{year_level}{last_section}"

    # Create new block
    cursor.execute(
        "INSERT INTO blocks (program_id, year_level, section, block_name) VALUES (%s, %s, %s, %s)",
        (program_id, year_level, last_section, block_name)
    )
    block_id = cursor.lastrowid

    return block_id


@admin.route('/api/students/update-status/<int:user_id>', methods=['POST'])
@role_required('ADMIN')
def update_student_status(user_id):
    data = request.get_json() or request.form
    status = data.get('status', '').strip()

    if not status or status not in ['Active', 'Inactive']:
        return jsonify({'success': False, 'message': 'Invalid status'}), 400

    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute("UPDATE users SET status = %s WHERE user_id = %s AND role = 'STUDENT'", (status, user_id))
        db.commit()

        if cursor.rowcount == 0:
            cursor.close()
            db.close()
            return jsonify({'success': False, 'message': 'Student not found'}), 404

        cursor.close()
        db.close()
        
        # Log the activity
        from flask import session
        admin_user_id = session.get('user_id')
        admin_ip = request.remote_addr
        action_type = 'Deactivate user' if status == 'Inactive' else 'Update user'
        log_activity(
            user_id=admin_user_id,
            role='admin',
            action=action_type,
            target_table='users',
            target_id=user_id,
            description=f'{action_type}: Student ID {user_id} status changed to {status}',
            ip_address=admin_ip
        )
        
        return jsonify({'success': True, 'message': 'Status updated successfully'})
    except Exception as e:
        cursor.close()
        db.close()
        return jsonify({'success': False, 'message': str(e)}), 500




# ============================================
# STUDENT VIEW API ROUTE
# ============================================

@admin.route('/api/students/view/<int:user_id>', methods=['GET'])
@role_required('ADMIN')
def api_view_student(user_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    try:
        print(f"DEBUG: Fetching student with user_id={user_id}")
        
        cursor.execute("""
            SELECT u.user_id, u.first_name, u.middle_name, u.last_name, u.email, u.gender, 
                   u.birthdate, u.contact_number, u.status, u.created_at,
                   sp.student_id, sp.student_number, sp.year_level,
                   p.program_id, p.program_code, p.program_name,
                   b.block_id, b.block_name
            FROM users u
            JOIN student_profiles sp ON u.user_id = sp.student_id
            LEFT JOIN programs p ON sp.program_id = p.program_id
            LEFT JOIN blocks b ON sp.block_id = b.block_id
            WHERE u.user_id = %s AND u.role = 'STUDENT'
        """, (user_id,))
        student = cursor.fetchone()
        
        print(f"DEBUG: Query result: {student}")
        
        if not student:
            cursor.close()
            db.close()
            print(f"DEBUG: Student not found for user_id={user_id}")
            return jsonify({'success': False, 'message': 'Student not found'}), 404
        
        # Extract specialization from block_name if it exists
        specialization_name = None
        specialization_code = None
        if student['block_name'] and '-' in student['block_name']:
            # Block name format: {program_code}-{specialization_code}{year_level}{section}
            parts = student['block_name'].split('-')
            if len(parts) > 1:
                # Get specialization code from the second part (remove year_level and section)
                spec_part = parts[1]
                if spec_part and len(spec_part) > 2:
                    # Extract just the specialization code (before year_level digit)
                    spec_code = ''
                    for char in spec_part:
                        if char.isdigit():
                            break
                        spec_code += char
                    if spec_code:
                        specialization_code = spec_code
                        # Try to get specialization name from database
                        cursor.execute("""
                            SELECT specialization_name FROM specializations 
                            WHERE program_id = %s AND specialization_code = %s
                        """, (student['program_id'], specialization_code))
                        spec_result = cursor.fetchone()
                        if spec_result:
                            specialization_name = spec_result['specialization_name']
        
        # Add specialization info to student dict
        student['specialization_code'] = specialization_code
        student['specialization_name'] = specialization_name
        
        # Format date fields properly
        if student['birthdate']:
            if hasattr(student['birthdate'], 'isoformat'):
                student['birthdate'] = student['birthdate'].isoformat()
        else:
            student['birthdate'] = None
        
        if student['created_at']:
            if hasattr(student['created_at'], 'isoformat'):
                student['created_at'] = student['created_at'].isoformat()
        else:
            student['created_at'] = None
        
        cursor.close()
        db.close()
        
        print(f"DEBUG: Returning student data successfully")
        return jsonify({'success': True, 'student': student})
    except Exception as e:
        print(f"ERROR in api_view_student: {str(e)}")
        import traceback
        traceback.print_exc()
        cursor.close()
        db.close()
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================
# TEACHER VIEW AND EDIT API ROUTES
# ============================================

@admin.route('/api/teachers/view/<int:user_id>', methods=['GET'])
@role_required('ADMIN')
def api_view_teacher(user_id):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    try:
        cursor.execute("""
            SELECT u.user_id, u.first_name, u.middle_name, u.last_name, u.email, u.gender, 
                   u.birthdate, u.address, u.contact_number, u.status, u.username,
                   tp.teacher_id, tp.employee_id, tp.department_id,
                   d.department_code, d.department_name
            FROM users u
            JOIN teacher_profiles tp ON u.user_id = tp.user_id
            LEFT JOIN departments d ON tp.department_id = d.department_id
            WHERE u.user_id = %s AND u.role = 'TEACHER'
        """, (user_id,))
        teacher = cursor.fetchone()
        
        if not teacher:
            cursor.close()
            db.close()
            return jsonify({'success': False, 'message': 'Teacher not found'}), 404
        
        # Ensure gender is properly formatted
        if teacher['gender']:
            teacher['gender'] = str(teacher['gender']).strip()
        else:
            teacher['gender'] = None
        
        # Format date fields properly for the form
        if teacher['birthdate']:
            if hasattr(teacher['birthdate'], 'isoformat'):
                teacher['birthdate'] = teacher['birthdate'].isoformat()
        else:
            teacher['birthdate'] = None
        
        cursor.close()
        db.close()
        
        return jsonify({'success': True, 'teacher': teacher})
    except Exception as e:
        cursor.close()
        db.close()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin.route('/api/teachers/edit/<int:user_id>', methods=['POST'])
@role_required('ADMIN')
def api_edit_teacher(user_id):
    data = request.get_json() or request.form
    first_name = data.get('first_name', '').strip()
    middle_name = data.get('middle_name', '').strip()
    last_name = data.get('last_name', '').strip()
    gender = data.get('gender', '').strip()
    birthdate = data.get('birthdate', '').strip() or None
    address = data.get('address', '').strip() or None
    contact_number = data.get('contact_number', '').strip() or None
    
    if not all([first_name, last_name, gender]):
        return jsonify({'success': False, 'message': 'First name, last name, and gender are required'}), 400
    
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    try:
        # First verify the teacher exists
        cursor.execute("SELECT user_id FROM users WHERE user_id = %s AND role = 'TEACHER'", (user_id,))
        teacher = cursor.fetchone()
        
        if not teacher:
            cursor.close()
            db.close()
            return jsonify({'success': False, 'message': 'Teacher not found'}), 404
        
        # Now update the teacher
        cursor.execute("""
            UPDATE users 
            SET first_name = %s, middle_name = %s, last_name = %s, 
                gender = %s, birthdate = %s, address = %s, contact_number = %s
            WHERE user_id = %s
        """, (first_name, middle_name, last_name, gender, birthdate, address, contact_number, user_id))
        
        db.commit()
        cursor.close()
        db.close()
        return jsonify({'success': True, 'message': 'Teacher profile updated successfully'})
    except Exception as e:
        cursor.close()
        db.close()
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================
# SUBJECTS ROUTES
# ============================================

@admin.route('/subjects_manage')
@role_required('ADMIN')
def admin_subjects():
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT program_id, program_code, program_name FROM programs ORDER BY program_code")
    programs = cursor.fetchall()
    cursor.execute("""
        SELECT s.specialization_id, s.program_id, s.specialization_name, s.specialization_code
        FROM specializations s
        ORDER BY s.specialization_code
    """)
    specializations = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template('subjects.html', programs=programs, specializations=specializations)



@admin.route('/subjects/list', methods=['GET'])
@role_required('ADMIN')
def api_subjects_list():
    program_filter = request.args.get('program_id', '').strip()
    year_filter = request.args.get('year_level', '').strip()
    specialization_filter = request.args.get('specialization_id', '').strip()
    search = request.args.get('search', '').strip()

    query = """
        SELECT s.*, p.program_code, p.program_name,
               sp.specialization_id as spec_id, sp.specialization_code, sp.specialization_name
        FROM subjects s 
        JOIN programs p ON s.program_id = p.program_id
        LEFT JOIN specializations sp ON s.specialization_id = sp.specialization_id
    """
    params = []
    conditions = []

    if program_filter:
        conditions.append("s.program_id = %s")
        params.append(program_filter)
    if year_filter:
        conditions.append("s.year_level = %s")
        params.append(year_filter)
    if specialization_filter:
        conditions.append("s.specialization_id = %s")
        params.append(specialization_filter)
    if search:
        conditions.append("(s.subject_code LIKE %s OR s.subject_name LIKE %s)")
        params.extend([f"%{search}%", f"%{search}%"])

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY p.program_code, s.year_level, s.subject_code"

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    
    try:
        cursor.execute(query, params)
        subjects = cursor.fetchall()
    except mysql.connector.ProgrammingError as e:
        if "Unknown column 's.specialization_id'" in str(e):
            # Fallback query without specialization join
            fallback_query = """
                SELECT s.*, p.program_code, p.program_name,
                       NULL as spec_id, NULL as specialization_code, NULL as specialization_name
                FROM subjects s 
                JOIN programs p ON s.program_id = p.program_id
            """
            fallback_conditions = []
            fallback_params = []
            if program_filter:
                fallback_conditions.append("s.program_id = %s")
                fallback_params.append(program_filter)
            if year_filter:
                fallback_conditions.append("s.year_level = %s")
                fallback_params.append(year_filter)
            if search:
                fallback_conditions.append("(s.subject_code LIKE %s OR s.subject_name LIKE %s)")
                fallback_params.extend([f"%{search}%", f"%{search}%"])
            if fallback_conditions:
                fallback_query += " WHERE " + " AND ".join(fallback_conditions)
            fallback_query += " ORDER BY p.program_code, s.year_level, s.subject_code"
            cursor.execute(fallback_query, fallback_params)
            subjects = cursor.fetchall()
        else:
            raise
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            db.close()
        except Exception:
            pass

    for subject in subjects:
        if subject['created_at']:
            subject['created_at'] = subject['created_at'].strftime('%Y-%m-%d %H:%M:%S')

    return jsonify({'success': True, 'subjects': subjects})



@admin.route('/subjects/add', methods=['POST'])
@role_required('ADMIN')
def add_subject():
    data = request.get_json() or request.form
    subject_code = data.get('subject_code', '').strip().upper()
    subject_name = data.get('subject_name', '').strip()
    program_id = data.get('program_id')
    year_level = data.get('year_level')
    specialization_id = data.get('specialization_id', None)

    if not all([subject_code, subject_name, program_id, year_level]):
        return jsonify({'success': False, 'message': 'All fields are required'}), 400

    try:
        program_id = int(program_id)
        year_level = int(year_level)
        if specialization_id:
            specialization_id = int(specialization_id)
        else:
            specialization_id = None
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Invalid program or year level'}), 400

    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute("""
            INSERT INTO subjects (subject_code, subject_name, program_id, year_level, specialization_id) 
            VALUES (%s, %s, %s, %s, %s)
        """, (subject_code, subject_name, program_id, year_level, specialization_id))
        db.commit()
        new_id = cursor.lastrowid
        
        # Log the activity
        from flask import session
        admin_user_id = session.get('user_id')
        admin_ip = request.remote_addr
        log_activity(
            user_id=admin_user_id,
            role='admin',
            action='Add subject',
            target_table='subjects',
            target_id=new_id,
            description=f'Created new subject: {subject_name} ({subject_code})',
            ip_address=admin_ip
        )
        
        return jsonify({
            'success': True,
            'message': 'Subject added successfully',
            'subject_id': new_id
        })
    except mysql.connector.ProgrammingError as e:
        if "Unknown column 'specialization_id'" in str(e):
            return jsonify({
                'success': False,
                'message': 'Database migration required: Please run ALTER TABLE subjects ADD COLUMN specialization_id INT NULL'
            }), 500
        raise
    except mysql.connector.IntegrityError:
        return jsonify({'success': False, 'message': 'Subject code already exists'}), 409
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            db.close()
        except Exception:
            pass



@admin.route('/subjects/edit/<int:subject_id>', methods=['POST'])
@role_required('ADMIN')
def edit_subject(subject_id):
    data = request.get_json() or request.form
    subject_code = data.get('subject_code', '').strip().upper()
    subject_name = data.get('subject_name', '').strip()
    program_id = data.get('program_id')
    year_level = data.get('year_level')
    specialization_id = data.get('specialization_id', None)

    if not all([subject_code, subject_name, program_id, year_level]):
        return jsonify({'success': False, 'message': 'All fields are required'}), 400

    try:
        program_id = int(program_id)
        year_level = int(year_level)
        if specialization_id:
            specialization_id = int(specialization_id)
        else:
            specialization_id = None
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Invalid program or year level'}), 400

    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute("""
            UPDATE subjects 
            SET subject_code = %s, subject_name = %s, program_id = %s, year_level = %s, specialization_id = %s 
            WHERE subject_id = %s
        """, (subject_code, subject_name, program_id, year_level, specialization_id, subject_id))
        db.commit()

        if cursor.rowcount == 0:
            return jsonify({'success': False, 'message': 'Subject not found'}), 404

        return jsonify({'success': True, 'message': 'Subject updated successfully'})
    except mysql.connector.ProgrammingError as e:
        if "Unknown column 'specialization_id'" in str(e):
            return jsonify({
                'success': False,
                'message': 'Database migration required: Please run ALTER TABLE subjects ADD COLUMN specialization_id INT NULL'
            }), 500
        raise
    except mysql.connector.IntegrityError:
        return jsonify({'success': False, 'message': 'Subject code already exists'}), 409
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            db.close()
        except Exception:
            pass



@admin.route('/subjects/delete/<int:subject_id>', methods=['POST'])
@role_required('ADMIN')
def delete_subject(subject_id):
    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute("DELETE FROM subjects WHERE subject_id = %s", (subject_id,))
        db.commit()

        if cursor.rowcount == 0:
            cursor.close()
            db.close()
            return jsonify({'success': False, 'message': 'Subject not found'}), 404

        return jsonify({'success': True, 'message': 'Subject deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            db.close()
        except Exception:
            pass


# ============================================
# ASSIGNMENTS ROUTES
# ============================================


def ensure_course_assignments_table():
    """Create the course_assignments table if it does not exist.
    Also ensures the course_code column is present."""
    db = get_db_connection()
    cursor = db.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS course_assignments (
            assignment_id INT AUTO_INCREMENT PRIMARY KEY,
            course_code VARCHAR(3) NOT NULL,
            subject_id INT NOT NULL,
            block_id INT NOT NULL,
            teacher_id INT DEFAULT NULL,
            status ENUM('Pending','Assigned') DEFAULT 'Pending',
            assigned_at DATETIME DEFAULT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY unique_course_code (course_code)
        )
    """)
    # If table already existed without course_code, add the column
    try:
        cursor.execute("SELECT course_code FROM course_assignments LIMIT 1")
        cursor.fetchall()
    except mysql.connector.errors.ProgrammingError:
        cursor.execute("ALTER TABLE course_assignments ADD COLUMN course_code VARCHAR(3) DEFAULT NULL AFTER assignment_id")
        # Backfill existing rows with unique codes
        cursor.execute("SELECT assignment_id FROM course_assignments WHERE course_code IS NULL")
        rows = cursor.fetchall()
        for row in rows:
            code = _generate_unique_course_code(cursor)
            cursor.execute("UPDATE course_assignments SET course_code = %s WHERE assignment_id = %s", (code, row[0]))
        # Drop old unique key if it exists and add new one
        try:
            cursor.execute("ALTER TABLE course_assignments DROP INDEX unique_subject_block")
        except Exception:
            pass
        try:
            cursor.execute("ALTER TABLE course_assignments ADD UNIQUE KEY unique_course_code (course_code)")
        except Exception:
            pass
    db.commit()
    cursor.close()
    db.close()


def _generate_unique_course_code(cursor):
    """Generate a unique random 3-digit course code (100–999)."""
    for _ in range(500):
        code = str(random.randint(100, 999))
        cursor.execute("SELECT 1 FROM course_assignments WHERE course_code = %s", (code,))
        if not cursor.fetchone():
            return code
    raise Exception('Could not generate a unique course code after 500 attempts')


@admin.route('/course-assignments')
@role_required('ADMIN')
def course_assignments():
    return render_template('assignments.html')


@admin.route('/get-all-blocks', methods=['GET'])
@role_required('ADMIN')
def get_all_blocks():
    """Return every block with its program info for the global search bar."""
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT b.block_id, b.block_name, b.section, b.year_level,
                   b.program_id, p.program_code, p.program_name
            FROM blocks b
            JOIN programs p ON b.program_id = p.program_id
            ORDER BY b.block_name
        """)
        blocks = cursor.fetchall()
        cursor.close()
        db.close()
        return jsonify({'success': True, 'blocks': blocks})
    except Exception as e:
        cursor.close()
        db.close()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin.route('/get-assignments', methods=['GET'])
@role_required('ADMIN')
def get_assignments():
    """Return assignment rows for a given program + year_level + block.
    Each subject that matches the filter becomes a row.  If a
    course_assignments record exists the teacher info is attached;
    otherwise the row shows Pending."""
    program_id = request.args.get('program_id', '').strip()
    year_level = request.args.get('year_level', '').strip()
    block_id = request.args.get('block_id', '').strip()
    specialization_id = request.args.get('specialization_id', '').strip()

    if not program_id or not year_level or not block_id:
        return jsonify({'success': False, 'message': 'Program, year level, and block are required'}), 400

    ensure_course_assignments_table()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        # Build subject filter
        subject_query = """
            SELECT s.subject_id, s.subject_code, s.subject_name,
                   b.block_id, b.block_name,
                   ca.assignment_id, ca.course_code, ca.teacher_id, ca.status,
                   ca.assigned_at,
                   u.first_name AS teacher_first_name,
                   u.last_name  AS teacher_last_name,
                   tp.employee_id AS teacher_employee_id
            FROM subjects s
            CROSS JOIN blocks b
            LEFT JOIN course_assignments ca
                ON ca.subject_id = s.subject_id AND ca.block_id = b.block_id
            LEFT JOIN teacher_profiles tp ON ca.teacher_id = tp.teacher_id
            LEFT JOIN users u ON tp.user_id = u.user_id
            WHERE s.program_id = %s
              AND s.year_level = %s
              AND b.block_id   = %s
        """
        params = [program_id, year_level, block_id]

        if specialization_id:
            subject_query += " AND s.specialization_id = %s"
            params.append(specialization_id)

        subject_query += " ORDER BY s.subject_code"

        cursor.execute(subject_query, params)
        rows = cursor.fetchall()

        # Build result — rows without a course_assignments record are Pending
        assignments = []
        for row in rows:
            assigned_at = row.get('assigned_at')
            if assigned_at and hasattr(assigned_at, 'strftime'):
                assigned_at = assigned_at.strftime('%Y-%m-%d %H:%M:%S')
            assignments.append({
                'subject_id': row['subject_id'],
                'subject_code': row['subject_code'],
                'subject_name': row['subject_name'],
                'block_id': row['block_id'],
                'block_name': row['block_name'],
                'assignment_id': row['assignment_id'],
                'course_code': row.get('course_code', None),
                'teacher_id': row['teacher_id'],
                'teacher_first_name': row['teacher_first_name'],
                'teacher_last_name': row['teacher_last_name'],
                'teacher_employee_id': row['teacher_employee_id'],
                'status': row['status'] if row['status'] else 'Pending',
                'assigned_at': assigned_at
            })

        cursor.close()
        db.close()
        return jsonify({'success': True, 'assignments': assignments})
    except Exception as e:
        cursor.close()
        db.close()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin.route('/get-teachers', methods=['GET'])
@role_required('ADMIN')
def get_teachers_for_assignment():
    """Return all active teachers with department + program info,
    plus a departments list for the modal filter."""
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT tp.teacher_id, tp.employee_id, tp.department_id,
                   u.first_name, u.last_name,
                   d.department_code, d.department_name,
                   p.program_code
            FROM teacher_profiles tp
            JOIN users u ON tp.user_id = u.user_id
            LEFT JOIN departments d ON tp.department_id = d.department_id
            LEFT JOIN programs p ON tp.program_id = p.program_id
            WHERE u.role = 'TEACHER' AND u.status = 'Active'
            ORDER BY tp.employee_id
        """)
        teachers = cursor.fetchall()

        cursor.execute("SELECT department_id, department_code, department_name FROM departments ORDER BY department_code")
        departments = cursor.fetchall()

        cursor.close()
        db.close()
        return jsonify({'success': True, 'teachers': teachers, 'departments': departments})
    except Exception as e:
        cursor.close()
        db.close()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin.route('/assign-teacher', methods=['POST'])
@role_required('ADMIN')
def assign_teacher():
    """Assign a teacher to a subject+block.  Creates or updates the
    course_assignments record with a unique 3-digit course_code."""
    data = request.get_json() or request.form
    subject_id = data.get('subject_id')
    block_id = data.get('block_id')
    teacher_id = data.get('teacher_id')

    if not subject_id or not block_id or not teacher_id:
        return jsonify({'success': False, 'message': 'subject_id, block_id, and teacher_id are required'}), 400

    ensure_course_assignments_table()

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    try:
        # Check if an assignment already exists for this subject+block
        cursor.execute(
            "SELECT assignment_id, course_code FROM course_assignments WHERE subject_id = %s AND block_id = %s",
            (subject_id, block_id)
        )
        existing = cursor.fetchone()

        if existing:
            # Update existing assignment
            cursor.execute("""
                UPDATE course_assignments
                SET teacher_id = %s, status = 'Assigned', assigned_at = NOW()
                WHERE assignment_id = %s
            """, (teacher_id, existing['assignment_id']))
        else:
            # Generate a unique 3-digit course code
            course_code = _generate_unique_course_code(cursor)
            cursor.execute("""
                INSERT INTO course_assignments (course_code, subject_id, block_id, teacher_id, status, assigned_at)
                VALUES (%s, %s, %s, %s, 'Assigned', NOW())
            """, (course_code, subject_id, block_id, teacher_id))

        db.commit()
        cursor.close()
        db.close()
        
        # Log the activity
        from flask import session
        admin_user_id = session.get('user_id')
        admin_ip = request.remote_addr
        log_activity(
            user_id=admin_user_id,
            role='admin',
            action='Assign teacher',
            target_table='course_assignments',
            target_id=teacher_id,
            description=f'Assigned teacher ID {teacher_id} to subject ID {subject_id}, block ID {block_id}',
            ip_address=admin_ip
        )
        
        return jsonify({'success': True, 'message': 'Teacher assigned successfully'})
    except Exception as e:
        cursor.close()
        db.close()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin.route('/unassign-teacher', methods=['POST'])
@role_required('ADMIN')
def unassign_teacher():
    """Remove the teacher from a subject+block assignment."""
    data = request.get_json() or request.form
    subject_id = data.get('subject_id')
    block_id = data.get('block_id')

    if not subject_id or not block_id:
        return jsonify({'success': False, 'message': 'subject_id and block_id are required'}), 400

    ensure_course_assignments_table()

    db = get_db_connection()
    cursor = db.cursor()

    try:
        cursor.execute("""
            UPDATE course_assignments
            SET teacher_id = NULL, status = 'Pending', assigned_at = NULL
            WHERE subject_id = %s AND block_id = %s
        """, (subject_id, block_id))
        db.commit()
        cursor.close()
        db.close()
        return jsonify({'success': True, 'message': 'Teacher unassigned successfully'})
    except Exception as e:
        cursor.close()
        db.close()
        return jsonify({'success': False, 'message': str(e)}), 500

