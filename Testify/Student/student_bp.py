from flask import Blueprint, render_template, session, request, redirect, url_for, jsonify
from Testify.Authentication.auth_bp import role_required
from Testify.__init__ import db_config
import mysql.connector
import random
from datetime import datetime, timedelta
import hashlib
import json


student = Blueprint('student', __name__, template_folder='templates',
                  static_folder='static', static_url_path='/student/static')


# ─────────────────────────── Anti-Cheating Helper Functions ────────────────

def get_device_fingerprint():
    """Generate a unique device fingerprint from user-agent and IP."""
    user_agent = request.headers.get('User-Agent', '')
    ip_address = request.remote_addr
    fingerprint = hashlib.sha256(f"{user_agent}:{ip_address}".encode()).hexdigest()
    return fingerprint, ip_address


def check_double_device(student_id, exam_id, current_device):
    """Check if student is attempting exam from multiple devices simultaneously."""
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True, buffered=True)
    
    # Check for active attempts with different device fingerprints
    cursor.execute("""
        SELECT DISTINCT eal.device_info, eal.ip_address, ea.attempt_id
        FROM exam_activity_logs eal
        JOIN exam_attempts ea ON eal.attempt_id = ea.attempt_id
        WHERE ea.student_id = %s AND ea.exam_id = %s 
        AND ea.status = 'In Progress'
        AND eal.activity IN ('STARTED_EXAM', 'ANSWERED_QUESTION', 'TAB_SWITCH_DETECTED')
        AND eal.created_at > DATE_SUB(NOW(), INTERVAL 5 MINUTE)
    """, (student_id, exam_id))
    
    active_devices = cursor.fetchall()
    cursor.close()
    connection.close()
    
    if active_devices:
        # Check if current device is different
        for device in active_devices:
            if device['device_info'] != current_device:
                return True, len(active_devices) + 1  # True = violation detected
    
    return False, 1


def check_exam_security_violations(attempt_id):
    """Get count of security violations for an attempt."""
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True, buffered=True)
    
    cursor.execute("""
        SELECT COUNT(*) as violation_count
        FROM exam_security_logs
        WHERE attempt_id = %s
    """, (attempt_id,))
    
    result = cursor.fetchone()
    cursor.close()
    connection.close()
    
    return result['violation_count'] if result else 0


def get_violation_details(attempt_id):
    """Get detailed violation information."""
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True, buffered=True)
    
    cursor.execute("""
        SELECT event_type, COUNT(*) as count
        FROM exam_security_logs
        WHERE attempt_id = %s
        GROUP BY event_type
    """, (attempt_id,))
    
    violations = cursor.fetchall()
    cursor.close()
    connection.close()
    
    return violations


def get_student_context():
    """Helper function to get user_name and classes for all student routes."""
    user_id = session.get('user_id')
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True, buffered=True)

    # Fetch user name
    cursor.execute("SELECT first_name, last_name FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()

    # Check if student_profile exists
    cursor.execute("SELECT student_id, block_id FROM student_profiles WHERE user_id = %s", (user_id,))
    student_profile = cursor.fetchone()

    if student_profile:
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


# ─────────────────────────── Dashboard routes ────────────────────────────────

@student.route('/dashboard')
@role_required('STUDENT')
def dashboard():
    context = get_student_context()
    
    user_id = session.get('user_id')
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True, buffered=True)
    
    # Get student profile info
    cursor.execute("SELECT student_id, student_number, block_id FROM student_profiles WHERE user_id = %s", (user_id,))
    student_profile = cursor.fetchone()
    
    if student_profile:
        student_id = student_profile['student_id']
        student_number = student_profile['student_number']
        block_id = student_profile['block_id']
        
        # Get student full name
        cursor.execute("SELECT first_name, middle_name, last_name, email FROM users WHERE user_id = %s", (user_id,))
        user_info = cursor.fetchone()
        
        # Get block and program info
        cursor.execute("""
            SELECT b.year_level, b.section, p.program_code, p.program_name
            FROM blocks b
            JOIN programs p ON b.program_id = p.program_id
            WHERE b.block_id = %s
        """, (block_id,))
        block_info = cursor.fetchone()
        
        # Calculate statistics
        # Total quizzes/exams taken
        cursor.execute("""
            SELECT COUNT(*) as total_taken
            FROM exam_attempts ea
            JOIN exams e ON ea.exam_id = e.exam_id
            WHERE ea.student_id = %s AND ea.status IN ('Submitted', 'Auto Submitted')
        """, (student_id,))
        total_taken = cursor.fetchone()['total_taken']
        
        # Average score
        cursor.execute("""
            SELECT AVG(ea.score) as avg_score
            FROM exam_attempts ea
            JOIN exams e ON ea.exam_id = e.exam_id
            WHERE ea.student_id = %s AND ea.status IN ('Submitted', 'Auto Submitted')
        """, (student_id,))
        avg_score_result = cursor.fetchone()
        avg_score = round(avg_score_result['avg_score'], 1) if avg_score_result['avg_score'] else 0
        
        # Upcoming exams
        now = datetime.now()
        cursor.execute("""
            SELECT COUNT(*) as upcoming_count
            FROM exams e
            JOIN course_assignments ca ON e.assignment_id = ca.assignment_id
            WHERE ca.block_id = %s AND e.status = 'Published' 
            AND e.start_datetime > %s
        """, (block_id, now))
        upcoming_count = cursor.fetchone()['upcoming_count']
        
        # Completed tests
        cursor.execute("""
            SELECT COUNT(*) as completed_count
            FROM exam_attempts ea
            JOIN exams e ON ea.exam_id = e.exam_id
            WHERE ea.student_id = %s AND ea.status IN ('Submitted', 'Auto Submitted')
        """, (student_id,))
        completed_count = cursor.fetchone()['completed_count']
        
        # Active classes
        cursor.execute("""
            SELECT COUNT(DISTINCT ca.assignment_id) as active_classes
            FROM course_assignments ca
            WHERE ca.block_id = %s AND ca.status = 'Assigned'
        """, (block_id,))
        active_classes = cursor.fetchone()['active_classes']
        
        # Get leaderboard data (top 5 students in the same block)
        cursor.execute("""
            SELECT u.first_name, u.last_name, sp.student_number,
                   AVG(ea.score) as avg_score
            FROM exam_attempts ea
            JOIN student_profiles sp ON ea.student_id = sp.student_id
            JOIN users u ON sp.user_id = u.user_id
            WHERE sp.block_id = %s AND ea.status IN ('Submitted', 'Auto Submitted')
            GROUP BY sp.student_id, u.first_name, u.last_name, sp.student_number
            ORDER BY avg_score DESC
            LIMIT 5
        """, (block_id,))
        leaderboard = cursor.fetchall()
        
        # Get subject performance data
        cursor.execute("""
            SELECT s.subject_name, AVG(ea.score) as avg_score
            FROM exam_attempts ea
            JOIN exams e ON ea.exam_id = e.exam_id
            JOIN course_assignments ca ON e.assignment_id = ca.assignment_id
            JOIN subjects s ON ca.subject_id = s.subject_id
            WHERE ea.student_id = %s AND ea.status IN ('Submitted', 'Auto Submitted')
            GROUP BY s.subject_id, s.subject_name
        """, (student_id,))
        subject_performance = cursor.fetchall()
        
        # Get upcoming events (exams)
        cursor.execute("""
            SELECT e.exam_title, e.exam_type, e.start_datetime
            FROM exams e
            JOIN course_assignments ca ON e.assignment_id = ca.assignment_id
            WHERE ca.block_id = %s AND e.status = 'Published'
            AND e.start_datetime > %s
            ORDER BY e.start_datetime
            LIMIT 3
        """, (block_id, now))
        upcoming_events = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        # Build context with real data
        context.update({
            'student_name': f"{user_info['first_name']} {user_info['middle_name'][0] if user_info['middle_name'] else ''} {user_info['last_name']}".strip(),
            'student_number': student_number,
            'block_display': f"{block_info['program_code']} {block_info['year_level']}-{block_info['section']}" if block_info else 'N/A',
            'email': user_info['email'],
            'total_taken': total_taken,
            'avg_score': avg_score,
            'upcoming_count': upcoming_count,
            'completed_count': completed_count,
            'active_classes': active_classes,
            'leaderboard': leaderboard,
            'subject_performance': subject_performance,
            'upcoming_events': upcoming_events
        })
    else:
        cursor.close()
        connection.close()
    
    return render_template('student_dashboard.html', **context)


@student.route('/student_dashboard')
@role_required('STUDENT')
def display_student():
    context = get_student_context()
    return render_template('student_dashboard.html', **context)


# ─────────────────────────── Simple page routes ──────────────────────────────

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


@student.route('/schedule')
@role_required('STUDENT')
def schedule():
    context = get_student_context()
    return render_template('schedule.html', **context)


@student.route('/results')
@role_required('STUDENT')
def results():
    context = get_student_context()

    user_id    = session.get('user_id')
    attempt_id = request.args.get('attempt_id', type=int)  # optional: specific attempt

    print(f"[DEBUG] user_id: {user_id}, attempt_id: {attempt_id}")

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True, buffered=True)

    # Get student_id
    cursor.execute("SELECT student_id FROM student_profiles WHERE user_id = %s", (user_id,))
    sp = cursor.fetchone()

    print(f"[DEBUG] student_profile: {sp}")

    result_data = None

    if sp:
        student_id = sp['student_id']
        print(f"[DEBUG] student_id: {student_id}")

        # Build base query — fetch a specific attempt or the most-recently submitted one
        if attempt_id:
            print(f"[DEBUG] Querying specific attempt_id: {attempt_id}")
            cursor.execute("""
                SELECT ea.attempt_id, ea.exam_id, ea.score, ea.started_at, ea.submitted_at,
                       e.exam_title, e.exam_type, e.duration_minutes, e.total_questions,
                       s.subject_name, s.subject_code
                FROM exam_attempts ea
                JOIN exams e ON ea.exam_id = e.exam_id
                JOIN course_assignments ca ON e.assignment_id = ca.assignment_id
                JOIN subjects s ON ca.subject_id = s.subject_id
                WHERE ea.attempt_id = %s AND ea.student_id = %s
                  AND ea.status IN ('Submitted', 'Auto Submitted')
            """, (attempt_id, student_id))
        else:
            print(f"[DEBUG] Querying most recent attempt for student")
            cursor.execute("""
                SELECT ea.attempt_id, ea.exam_id, ea.score, ea.started_at, ea.submitted_at,
                       e.exam_title, e.exam_type, e.duration_minutes, e.total_questions,
                       s.subject_name, s.subject_code
                FROM exam_attempts ea
                JOIN exams e ON ea.exam_id = e.exam_id
                JOIN course_assignments ca ON e.assignment_id = ca.assignment_id
                JOIN subjects s ON ca.subject_id = s.subject_id
                WHERE ea.student_id = %s AND ea.status IN ('Submitted', 'Auto Submitted')
                ORDER BY ea.submitted_at DESC
                LIMIT 1
            """, (student_id,))
        attempt = cursor.fetchone()
        print(f"[DEBUG] attempt found: {attempt}")
        
        if not attempt:
            print(f"[DEBUG] No attempt found - checking all attempts for student")
            cursor.execute("""
                SELECT ea.attempt_id, ea.exam_id, ea.score, ea.status
                FROM exam_attempts ea
                WHERE ea.student_id = %s
            """, (student_id,))
            all_attempts = cursor.fetchall()
            print(f"[DEBUG] All attempts for student: {all_attempts}")
        else:
            current_attempt_id = attempt['attempt_id']

            # Compute time used
            if attempt['started_at'] and attempt['submitted_at']:
                delta = attempt['submitted_at'] - attempt['started_at']
                mins  = int(delta.total_seconds() // 60)
                secs  = int(delta.total_seconds() % 60)
                time_used = f"{mins:02d}:{secs:02d}"
            else:
                time_used = "--:--"

            # Fetch all questions for this exam
            cursor.execute(
                "SELECT question_id, question_text, question_type, points "
                "FROM exam_questions WHERE exam_id = %s ORDER BY question_id",
                (attempt['exam_id'],)
            )
            questions_raw = cursor.fetchall()

            # Fetch all choices for these questions
            if questions_raw:
                q_ids        = [q['question_id'] for q in questions_raw]
                placeholders = ','.join(['%s'] * len(q_ids))
                cursor.execute(
                    f"SELECT choice_id, question_id, choice_text, is_correct "
                    f"FROM question_choices WHERE question_id IN ({placeholders})",
                    tuple(q_ids)
                )
                all_choices = cursor.fetchall()

                # Map choices by question_id
                choices_map = {}
                correct_map = {}   # question_id -> {id, text}
                for c in all_choices:
                    choices_map.setdefault(c['question_id'], []).append(c)
                    if c['is_correct']:
                        correct_map[c['question_id']] = {
                            'id':   c['choice_id'],
                            'text': c['choice_text']
                        }

                # Fetch student answers for this attempt
                cursor.execute(
                    "SELECT question_id, choice_id FROM student_answers WHERE attempt_id = %s",
                    (current_attempt_id,)
                )
                student_answers = {
                    row['question_id']: row['choice_id']
                    for row in cursor.fetchall()
                }
            else:
                choices_map, correct_map, student_answers = {}, {}, {}

            # Build questions list — schema matches new results.html JS
            total_points  = 0
            earned_points = 0
            questions_out = []

            for idx, q in enumerate(questions_raw):
                qid     = q['question_id']
                pts     = float(q['points'] or 1)
                correct = correct_map.get(qid)
                ans_id  = student_answers.get(qid)   # None = skipped

                ans_text = None
                if ans_id is not None:
                    for c in choices_map.get(qid, []):
                        if c['choice_id'] == ans_id:
                            ans_text = c['choice_text']
                            break

                is_correct_ans = (
                    ans_id is not None
                    and correct is not None
                    and ans_id == correct['id']
                )
                if is_correct_ans:
                    earned_points += pts
                total_points += pts

                # correct: True (right), False (wrong), None (skipped)
                correct_flag = None if ans_id is None else bool(is_correct_ans)

                questions_out.append({
                    'num':          idx + 1,
                    'text':         q['question_text'],
                    'type':         q['question_type'],
                    'points':       pts,
                    'correct':      correct_flag,
                    'your_answer':  ans_text,
                    'right_answer': correct['text'] if correct else None,
                })

            score_pct = round((earned_points / total_points) * 100) if total_points else 0

            # ── Student profile: student_number + block display ──────────────
            cursor.execute("""
                SELECT sp2.student_number,
                       b.year_level, b.section,
                       p.program_code
                FROM student_profiles sp2
                JOIN blocks   b ON sp2.block_id  = b.block_id
                JOIN programs p ON b.program_id  = p.program_id
                WHERE sp2.student_id = %s
            """, (student_id,))
            profile        = cursor.fetchone()
            block_display  = (
                f"{profile['program_code']} {profile['year_level']}-{profile['section']}"
                if profile else 'N/A'
            )
            student_number = profile['student_number'] if profile else 'N/A'

            # ── Full name (First MI. Last) ────────────────────────────────────
            cursor.execute(
                "SELECT first_name, middle_name, last_name FROM users WHERE user_id = %s",
                (user_id,)
            )
            u = cursor.fetchone()
            if u:
                mi        = (u['middle_name'][0] + '.') if u.get('middle_name') else ''
                full_name = ' '.join(filter(None, [u['first_name'], mi, u['last_name']]))
            else:
                full_name = context.get('user_name', 'Student')

            # ── ISO strings for JS fmtDate / fmtTime ─────────────────────────
            started_iso   = attempt['started_at'].isoformat()  if attempt['started_at']   else None
            submitted_iso = attempt['submitted_at'].isoformat() if attempt['submitted_at'] else None

            result_data = {
                'exam_title':      attempt['exam_title'],
                'exam_type':       attempt['exam_type'],
                'subject_name':    attempt['subject_name'],
                'subject_code':    attempt['subject_code'],
                'student_name':    full_name,
                'student_number':  student_number,
                'block':           block_display,
                'started_at':      started_iso,
                'submitted_at':    submitted_iso,
                'score':           int(earned_points),
                'total_points':    int(total_points),
                'total_questions': len(questions_out),
                'passing_score':   60,   # configurable pass mark (%)
                'time_used':       time_used,
                'questions':       questions_out,
            }
    else:
        print(f"[DEBUG] No student profile found for user_id: {user_id}")

    cursor.close()
    connection.close()

    context['result_data'] = result_data
    return render_template('student_results.html', **context)



@student.route('/profile')
@role_required('STUDENT')
def profile():
    context = get_student_context()
    return render_template('profile.html', **context)


# ─────────────────────────── My Classes ──────────────────────────────────────

@student.route('/my-classes')
@role_required('STUDENT')
def my_classes():
    context = get_student_context()

    user_id = session.get('user_id')
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True, buffered=True)

    cursor.execute("SELECT student_id, block_id FROM student_profiles WHERE user_id = %s", (user_id,))
    student_profile = cursor.fetchone()

    if student_profile:
        block_id = student_profile['block_id']
        student_id = student_profile['student_id']

        query = """
        SELECT
            ca.assignment_id, ca.course_code, ca.status,
            s.subject_id, s.subject_code, s.subject_name,
            t.teacher_id, u.first_name, u.middle_name, u.last_name, u.email,
            b.block_id, b.block_name, b.section, b.year_level
        FROM course_assignments ca
        JOIN subjects s ON ca.subject_id = s.subject_id
        JOIN teacher_profiles t ON ca.teacher_id = t.teacher_id
        JOIN users u ON t.user_id = u.user_id
        JOIN blocks b ON ca.block_id = b.block_id
        WHERE ca.block_id = %s AND ca.status = 'Assigned'
        ORDER BY s.subject_code
        """
        cursor.execute(query, (block_id,))
        classes = cursor.fetchall()

        for cls in classes:
            cursor.execute("""
                SELECT
                    COUNT(DISTINCT ea.attempt_id) AS total_exams,
                    COALESCE(AVG(ea.score), 0) AS average_score,
                    COUNT(CASE WHEN ea.status IN ('Submitted','Auto Submitted') THEN 1 END) AS completed_exams
                FROM exam_attempts ea
                JOIN exams e ON ea.exam_id = e.exam_id
                WHERE e.assignment_id = %s AND ea.student_id = %s
            """, (cls['assignment_id'], student_id))
            stats = cursor.fetchone()
            cls['exam_stats'] = stats or {'total_exams': 0, 'average_score': 0, 'completed_exams': 0}

        context['classes_detail'] = classes
        
        # Fetch exam data for the student
        cursor.execute("""
            SELECT e.exam_title, e.exam_type, ea.score, e.total_questions,
                   ea.attempt_id, e.exam_id
            FROM exam_attempts ea
            JOIN exams e ON ea.exam_id = e.exam_id
            JOIN course_assignments ca ON e.assignment_id = ca.assignment_id
            WHERE ea.student_id = %s AND ea.status IN ('Submitted', 'Auto Submitted')
            AND e.exam_type = 'Exam'
            ORDER BY ea.submitted_at DESC
        """, (student_id,))
        exams_data = cursor.fetchall()
        
        # Fetch quiz data for the student
        cursor.execute("""
            SELECT e.exam_title, e.exam_type, ea.score, e.total_questions,
                   ea.attempt_id, e.exam_id
            FROM exam_attempts ea
            JOIN exams e ON ea.exam_id = e.exam_id
            JOIN course_assignments ca ON e.assignment_id = ca.assignment_id
            WHERE ea.student_id = %s AND ea.status IN ('Submitted', 'Auto Submitted')
            AND e.exam_type = 'Quiz'
            ORDER BY ea.submitted_at DESC
        """, (student_id,))
        quizzes_data = cursor.fetchall()
        
        # Calculate violations for each attempt
        for exam in exams_data:
            cursor.execute("""
                SELECT COUNT(*) as violation_count
                FROM exam_security_logs
                WHERE attempt_id = %s
            """, (exam['attempt_id'],))
            violations = cursor.fetchone()
            exam['violations'] = violations['violation_count'] if violations else 0
            exam['percent'] = round((exam['score'] / exam['total_questions'] * 100) if exam['total_questions'] > 0 else 0, 0)
        
        for quiz in quizzes_data:
            cursor.execute("""
                SELECT COUNT(*) as violation_count
                FROM exam_security_logs
                WHERE attempt_id = %s
            """, (quiz['attempt_id'],))
            violations = cursor.fetchone()
            quiz['violations'] = violations['violation_count'] if violations else 0
            quiz['percent'] = round((quiz['score'] / quiz['total_questions'] * 100) if quiz['total_questions'] > 0 else 0, 0)
        
        context['exams'] = exams_data
        context['quizzes'] = quizzes_data
        
        # Fetch all published exams for tasks categorization
        cursor.execute("""
            SELECT e.exam_id, e.exam_title, e.exam_type, e.start_datetime, e.end_datetime,
                   s.subject_name,
                   (SELECT attempt_id FROM exam_attempts ea WHERE ea.exam_id = e.exam_id AND ea.student_id = %s AND ea.status IN ('Submitted', 'Auto Submitted') LIMIT 1) as attempt_id
            FROM exams e
            JOIN course_assignments ca ON e.assignment_id = ca.assignment_id
            JOIN subjects s ON ca.subject_id = s.subject_id
            WHERE ca.block_id = %s AND e.status = 'Published'
        """, (student_id, block_id))
        all_exams = cursor.fetchall()
        
        today_tasks = []
        upcoming_tasks = []
        missed_tasks = []
        now = datetime.now()
        
        for ex in all_exams:
            if not ex['attempt_id']:
                # Create a copy to serialize
                ex_copy = dict(ex)
                ex_copy['start_datetime'] = ex['start_datetime'].isoformat() if ex['start_datetime'] else None
                ex_copy['end_datetime'] = ex['end_datetime'].isoformat() if ex['end_datetime'] else None
                ex_copy['sidebar_date'] = ex['end_datetime'].strftime('%b %d, %Y') if ex['end_datetime'] else ''
                
                if ex['start_datetime'] <= now <= ex['end_datetime']:
                    today_tasks.append(ex_copy)
                elif now < ex['start_datetime']:
                    upcoming_tasks.append(ex_copy)
                elif now > ex['end_datetime']:
                    missed_tasks.append(ex_copy)
                    
        context['today_tasks'] = today_tasks
        context['upcoming_tasks'] = upcoming_tasks
        context['missed_tasks'] = missed_tasks
        
        # For the right sidebar, show only up to 5 upcoming/available tasks
        upcoming_sidebar_tasks = sorted(today_tasks + upcoming_tasks, key=lambda x: x['end_datetime'] if x['end_datetime'] else '')[:5]
        context['upcoming_sidebar_tasks'] = upcoming_sidebar_tasks
        
        # Get block and program info for display
        cursor.execute("""
            SELECT b.year_level, b.section, p.program_code, p.program_name
            FROM blocks b
            JOIN programs p ON b.program_id = p.program_id
            WHERE b.block_id = %s
        """, (block_id,))
        block_info = cursor.fetchone()
        context['block_display'] = f"{block_info['program_code']} {block_info['year_level']}-{block_info['section']}" if block_info else 'N/A'
        
    else:
        context['classes_detail'] = []
        context['exams'] = []
        context['quizzes'] = []
        context['block_display'] = 'N/A'

    cursor.close()
    connection.close()
    return render_template('classes_student.html', **context)


# ─────────────────────────── Assessments list ────────────────────────────────

@student.route('/assessments')
@role_required('STUDENT')
def assessments():
    context = get_student_context()

    user_id = session.get('user_id')
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True, buffered=True)

    cursor.execute("SELECT student_id, block_id FROM student_profiles WHERE user_id = %s", (user_id,))
    student_profile = cursor.fetchone()

    exams_list = []

    if student_profile:
        block_id = student_profile['block_id']

        query = """
        SELECT e.exam_id, e.exam_title, e.exam_type, e.duration_minutes,
               e.total_questions, e.start_datetime, e.end_datetime, e.status,
               s.subject_name,
               (SELECT attempt_id FROM exam_attempts ea 
                WHERE ea.exam_id = e.exam_id AND ea.student_id = %s 
                AND ea.status IN ('Submitted', 'Auto Submitted') 
                ORDER BY ea.submitted_at DESC LIMIT 1) as completed_attempt_id
        FROM exams e
        JOIN course_assignments ca ON e.assignment_id = ca.assignment_id
        JOIN subjects s ON ca.subject_id = s.subject_id
        WHERE ca.block_id = %s AND e.status = 'Published'
        ORDER BY e.start_datetime DESC
        """
        cursor.execute(query, (student_profile['student_id'], block_id))
        exams_list = cursor.fetchall()

        now = datetime.now()
        for exam in exams_list:
            if exam.get('completed_attempt_id'):
                exam['status'] = 'completed'
            elif exam['start_datetime'] <= now <= exam['end_datetime']:
                exam['status'] = 'available'
            elif now < exam['start_datetime']:
                exam['status'] = 'upcoming'
            else:
                exam['status'] = 'expired'

    cursor.close()
    connection.close()

    context['exams_list'] = exams_list
    return render_template('assessments.html', **context)


# ─────────────────────────── Take Exam ───────────────────────────────────────

@student.route('/take_exam/<int:exam_id>')
@role_required('STUDENT')
def take_exam(exam_id):
    user_id = session.get('user_id')
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True, buffered=True)

    # Get student profile
    cursor.execute("SELECT student_id FROM student_profiles WHERE user_id = %s", (user_id,))
    student_profile = cursor.fetchone()
    if not student_profile:
        cursor.close()
        connection.close()
        return redirect(url_for('student.assessments'))
    student_id = student_profile['student_id']

    # Get exam details (only published)
    cursor.execute("""
        SELECT e.*, s.subject_name
        FROM exams e
        JOIN course_assignments ca ON e.assignment_id = ca.assignment_id
        JOIN subjects s ON ca.subject_id = s.subject_id
        WHERE e.exam_id = %s AND e.status = 'Published'
    """, (exam_id,))
    exam = cursor.fetchone()

    if not exam:
        cursor.close()
        connection.close()
        return redirect(url_for('student.assessments'))

    # Check time window
    now = datetime.now()
    if now < exam['start_datetime'] or now > exam['end_datetime']:
        cursor.close()
        connection.close()
        return redirect(url_for('student.assessments'))

    # Get device fingerprint for double-device detection
    device_fingerprint, ip_address = get_device_fingerprint()
    
    # Check for double device attempt
    is_double_device, device_count = check_double_device(student_id, exam_id, device_fingerprint)
    if is_double_device:
        cursor.execute("""
            INSERT INTO exam_security_logs (attempt_id, event_type, event_details)
            SELECT attempt_id, %s, %s
            FROM exam_attempts 
            WHERE exam_id = %s AND student_id = %s AND status = 'In Progress'
            LIMIT 1
        """, ('DOUBLE_DEVICE_DETECTED', f'Multiple devices detected. Device count: {device_count}', exam_id))
        connection.commit()

    # Check existing attempt
    cursor.execute(
        "SELECT * FROM exam_attempts WHERE exam_id = %s AND student_id = %s",
        (exam_id, student_id)
    )
    attempt = cursor.fetchone()

    if attempt and attempt['status'] in ('Submitted', 'Auto Submitted'):
        submitted_attempt_id = attempt['attempt_id']
        cursor.close()
        connection.close()
        return redirect(url_for('student.results', attempt_id=submitted_attempt_id))

    if not attempt:
        cursor.execute("""
            INSERT INTO exam_attempts (exam_id, student_id, started_at, status)
            VALUES (%s, %s, %s, 'In Progress')
        """, (exam_id, student_id, now))
        connection.commit()
        attempt_id = cursor.lastrowid
        started_at = now
    else:
        attempt_id = attempt['attempt_id']
        started_at = attempt['started_at']

    # Log activity with device info
    cursor.execute("""
        INSERT INTO exam_activity_logs (student_id, exam_id, attempt_id, activity, device_info, ip_address)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (student_id, exam_id, attempt_id, 'STARTED_EXAM',
          device_fingerprint, ip_address))
    connection.commit()

    # Fetch questions
    cursor.execute("SELECT * FROM exam_questions WHERE exam_id = %s", (exam_id,))
    questions = cursor.fetchall()

    if exam['shuffle_questions']:
        random.shuffle(questions)

    # Fetch choices
    choices = {}
    if questions:
        ids = [q['question_id'] for q in questions]
        placeholders = ','.join(['%s'] * len(ids))
        cursor.execute(
            f"SELECT * FROM question_choices WHERE question_id IN ({placeholders})",
            tuple(ids)
        )
        for c in cursor.fetchall():
            choices.setdefault(c['question_id'], []).append(c)

    if exam['shuffle_answers']:
        for qid in choices:
            random.shuffle(choices[qid])

    cursor.close()
    connection.close()

    # Compute time remaining
    attempt_end = started_at + timedelta(minutes=exam['duration_minutes'])
    if attempt_end > exam['end_datetime']:
        attempt_end = exam['end_datetime']
    time_left = max(int((attempt_end - datetime.now()).total_seconds()), 0)

    # Pass security settings to frontend
    security_settings = {
        'fullscreen_required': exam.get('fullscreen_required', False),
        'copy_paste_disabled': exam.get('copy_paste_disabled', False),
        'device_fingerprint': device_fingerprint,
        'ip_address': ip_address,
        'is_double_device': is_double_device
    }

    return render_template('take_exam.html',
                           exam=exam,
                           questions=questions,
                           choices=choices,
                           attempt_id=attempt_id,
                           time_left_seconds=time_left,
                           security_settings=security_settings)


# ─────────────────────────── API: Validate Device & Access ──────────────────

@student.route('/api/exam/validate_device', methods=['POST'])
@role_required('STUDENT')
def validate_device():
    """Validate device and check for multiple device access."""
    data = request.json
    attempt_id = data.get('attempt_id')
    current_device = data.get('device_fingerprint')

    user_id = session.get('user_id')
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True, buffered=True)

    # Get attempt and student details
    cursor.execute("""
        SELECT ea.exam_id, ea.student_id, ea.status
        FROM exam_attempts ea
        JOIN student_profiles sp ON ea.student_id = sp.student_id
        WHERE ea.attempt_id = %s AND sp.user_id = %s
    """, (attempt_id, user_id))
    attempt = cursor.fetchone()

    if not attempt or attempt['status'] != 'In Progress':
        cursor.close()
        connection.close()
        return jsonify({'status': 'error', 'valid': False})

    # Check for multiple devices
    is_double_device, device_count = check_double_device(
        attempt['student_id'], 
        attempt['exam_id'], 
        current_device
    )

    if is_double_device:
        # Log the violation
        cursor.execute("""
            INSERT INTO exam_security_logs (attempt_id, event_type, event_details)
            VALUES (%s, %s, %s)
        """, (attempt_id, 'DOUBLE_DEVICE_DETECTED', 
              json.dumps({'device_count': device_count, 'timestamp': datetime.now().isoformat()})))
        connection.commit()

    cursor.close()
    connection.close()

    return jsonify({
        'status': 'success',
        'valid': True,
        'double_device': is_double_device,
        'device_count': device_count
    })


# ─────────────────────────── API: Log Security ───────────────────────────────

@student.route('/api/exam/log_security', methods=['POST'])
@role_required('STUDENT')
def log_security():
    data = request.json
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(buffered=True)
    cursor.execute("""
        INSERT INTO exam_security_logs (attempt_id, event_type, event_details)
        VALUES (%s, %s, %s)
    """, (data.get('attempt_id'), data.get('event_type'), data.get('event_details')))
    connection.commit()
    cursor.close()
    connection.close()
    return jsonify({'status': 'success'})


# ─────────────────────────── API: Submit Exam ────────────────────────────────

@student.route('/api/exam/submit', methods=['POST'])
@role_required('STUDENT')
def submit_exam():
    data = request.json
    attempt_id = data.get('attempt_id')
    answers = data.get('answers', {})  # { "question_id": choice_id, ... }

    user_id = session.get('user_id')
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True, buffered=True)

    # Verify ownership & in-progress status
    cursor.execute("""
        SELECT ea.exam_id, ea.student_id
        FROM exam_attempts ea
        JOIN student_profiles sp ON ea.student_id = sp.student_id
        WHERE ea.attempt_id = %s AND sp.user_id = %s AND ea.status = 'In Progress'
    """, (attempt_id, user_id))
    attempt = cursor.fetchone()

    if not attempt:
        cursor.close()
        connection.close()
        return jsonify({'status': 'error', 'message': 'Invalid attempt or already submitted'})

    # Check for critical violations (multiple devices, excessive tab switches)
    violation_count = check_exam_security_violations(attempt_id)
    
    # Get violation details
    violation_details = get_violation_details(attempt_id)
    critical_violations = sum(v['count'] for v in violation_details if v['event_type'] in ['DOUBLE_DEVICE_DETECTED', 'COPY_ATTEMPT', 'PASTE_ATTEMPT', 'TAB_SWITCH_DETECTED'])
    
    # If too many violations, still allow submit but flag it
    # (Admins/teachers can review the submission later)

    score = 0.0

    for q_id_str, choice_id in (answers or {}).items():
        if not choice_id:
            continue
        q_id = int(q_id_str)
        choice_id = int(choice_id)

        # Upsert answer
        cursor.execute(
            "DELETE FROM student_answers WHERE attempt_id = %s AND question_id = %s",
            (attempt_id, q_id)
        )
        cursor.execute(
            "INSERT INTO student_answers (attempt_id, question_id, choice_id) VALUES (%s, %s, %s)",
            (attempt_id, q_id, choice_id)
        )

        # Score
        cursor.execute(
            "SELECT is_correct FROM question_choices WHERE choice_id = %s AND question_id = %s",
            (choice_id, q_id)
        )
        ci = cursor.fetchone()
        if ci and ci['is_correct']:
            cursor.execute(
                "SELECT points FROM exam_questions WHERE question_id = %s",
                (q_id,)
            )
            qi = cursor.fetchone()
            if qi:
                score += float(qi['points'] or 1.0)

    # Finalise attempt
    cursor.execute("""
        UPDATE exam_attempts
        SET submitted_at = %s, score = %s, status = 'Submitted'
        WHERE attempt_id = %s
    """, (datetime.now(), score, attempt_id))

    connection.commit()
    cursor.close()
    connection.close()

    # Pass the attempt_id so the results page loads this specific attempt
    redirect_url = url_for('student.results', attempt_id=attempt_id)
    return jsonify({'status': 'success', 'redirect_url': redirect_url})
