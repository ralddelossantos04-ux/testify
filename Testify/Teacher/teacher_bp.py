from flask import Blueprint, render_template, session, url_for, redirect, request, jsonify
from Testify.Authentication.auth_bp import role_required
from Testify.__init__ import db_config
import mysql.connector
from datetime import datetime

teacher = Blueprint('teacher', __name__, template_folder='templates',
                  static_folder='static', static_url_path='/teacher/static')

def get_teacher_context():
    """Helper function to get user_name and classes for all teacher routes."""
    user_id = session.get('user_id')
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)
    
    # Fetch user name
    cursor.execute("SELECT first_name, last_name FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    
    # First, check if teacher_profile exists for this user
    cursor.execute("SELECT teacher_id FROM teacher_profiles WHERE user_id = %s", (user_id,))
    teacher_profile = cursor.fetchone()
    
    if teacher_profile:
        # Fetch teacher's classes using the teacher_id directly
        query = """
        SELECT ca.assignment_id, ca.course_code, ca.status,
               s.subject_id, s.subject_code, s.subject_name,
               b.block_id, b.block_name, b.section, b.year_level,
               p.program_id, p.program_name,
               d.department_id, d.department_name
        FROM course_assignments ca
        JOIN subjects s ON ca.subject_id = s.subject_id
        JOIN blocks b ON ca.block_id = b.block_id
        JOIN programs p ON b.program_id = p.program_id
        JOIN departments d ON p.department_id = d.department_id
        WHERE ca.teacher_id = %s
        ORDER BY p.program_name, b.year_level, b.section
        """
        cursor.execute(query, (teacher_profile['teacher_id'],))
        classes = cursor.fetchall()
    else:
        classes = []
    
    cursor.close()
    connection.close()
    
    user_name = f"{user['first_name']} {user['last_name']}" if user else "Teacher"
    
    return {'user_name': user_name, 'classes': classes}

@teacher.route('/teacher_dashboard')
@role_required('TEACHER')
def dashboard():
    context = get_teacher_context()
    return render_template('teacher_dashboard.html', **context)

@teacher.route('/exams')
@role_required('TEACHER')
def exams():
    context = get_teacher_context()
    return render_template('exams.html', **context)

@teacher.route('/quizzes')
@role_required('TEACHER')
def quizzes():
    context = get_teacher_context()
    return render_template('quizzes.html', **context)

@teacher.route('/schedule')
@role_required('TEACHER')
def schedule():
    context = get_teacher_context()
    return render_template('schedule.html', **context)

@teacher.route('/results')
@role_required('TEACHER')
def results():
    context = get_teacher_context()
    return render_template('results.html', **context)

@teacher.route('/reports')
@role_required('TEACHER')
def reports():
    context = get_teacher_context()
    return render_template('reports.html', **context)

@teacher.route('/announcements')
@role_required('TEACHER')
def announcements():
    context = get_teacher_context()
    return render_template('announcements.html', **context)

@teacher.route('/activity_logs')
@role_required('TEACHER')
def activity_logs():
    context = get_teacher_context()
    return render_template('activity_logs.html', **context)

@teacher.route('/profile')
@role_required('TEACHER')
def profile():
    context = get_teacher_context()
    return render_template('profile.html', **context)

@teacher.route('/class/<int:assignment_id>')
@role_required('TEACHER')
def class_detail(assignment_id):
    context = get_teacher_context()
    user_id = session.get('user_id')
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)
    
    # Fetch class details - join with teacher_profiles to match user_id
    query = """
    SELECT ca.assignment_id, ca.course_code, ca.status,
           s.subject_id, s.subject_code, s.subject_name,
           b.block_id, b.block_name, b.section, b.year_level,
           p.program_id, p.program_name,
           d.department_id, d.department_name
    FROM course_assignments ca
    JOIN subjects s ON ca.subject_id = s.subject_id
    JOIN blocks b ON ca.block_id = b.block_id
    JOIN programs p ON b.program_id = p.program_id
    JOIN departments d ON p.department_id = d.department_id
    JOIN teacher_profiles tp ON ca.teacher_id = tp.teacher_id
    WHERE ca.assignment_id = %s AND tp.user_id = %s
    """
    cursor.execute(query, (assignment_id, user_id))
    class_info = cursor.fetchone()
    
    if not class_info:
        cursor.close()
        connection.close()
        return redirect(url_for('teacher.dashboard'))
    
    # Fetch students in this class/block
    students_query = """
    SELECT sp.student_id, sp.student_number, sp.year_level,
           u.user_id, u.first_name, u.last_name, u.status
    FROM student_profiles sp
    JOIN users u ON sp.user_id = u.user_id
    WHERE sp.block_id = %s
    ORDER BY u.last_name, u.first_name
    """
    cursor.execute(students_query, (class_info['block_id'],))
    students = cursor.fetchall()
    
    # Fetch exams for this assignment
    exams_query = """
    SELECT e.exam_id, e.assignment_id, e.exam_title, e.exam_type, e.duration_minutes,
           e.total_questions, e.start_datetime, e.end_datetime, e.shuffle_questions,
           e.shuffle_answers, e.fullscreen_required, e.copy_paste_disabled, e.status,
           e.created_at
    FROM exams e
    WHERE e.assignment_id = %s
    ORDER BY e.created_at DESC
    """
    cursor.execute(exams_query, (assignment_id,))
    exams = cursor.fetchall()
    
    # Fetch questions and choices for each exam
    for exam in exams:
        questions_query = """
        SELECT eq.question_id, eq.question_text, eq.question_type, eq.points
        FROM exam_questions eq
        WHERE eq.exam_id = %s
        ORDER BY eq.question_id
        """
        cursor.execute(questions_query, (exam['exam_id'],))
        questions = cursor.fetchall()
        
        # Fetch choices for each question
        for question in questions:
            choices_query = """
            SELECT qc.choice_id, qc.choice_text, qc.is_correct
            FROM question_choices qc
            WHERE qc.question_id = %s
            ORDER BY qc.choice_id
            """
            cursor.execute(choices_query, (question['question_id'],))
            question['choices'] = cursor.fetchall()
        
        exam['questions'] = questions
    
    cursor.close()
    connection.close()
    
    return render_template('class_detail.html', **context, class_info=class_info, students=students, exams=exams)

@teacher.route('/create_exam/<int:assignment_id>')
@role_required('TEACHER')
def create_exam(assignment_id):
    context = get_teacher_context()
    
    # Fetch course code for this assignment
    user_id = session.get('user_id')
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor(dictionary=True)
    
    try:
        query = """
        SELECT ca.course_code, ca.assignment_id, s.subject_name
        FROM course_assignments ca
        JOIN subjects s ON ca.subject_id = s.subject_id
        JOIN teacher_profiles tp ON ca.teacher_id = tp.teacher_id
        WHERE ca.assignment_id = %s AND tp.user_id = %s
        """
        cursor.execute(query, (assignment_id, user_id))
        assignment = cursor.fetchone()
        
        if not assignment:
            return redirect(url_for('teacher.dashboard'))
        
        context['assignment_id'] = assignment_id
        context['course_code'] = assignment['course_code']
        context['subject_name'] = assignment['subject_name']
        
    finally:
        cursor.close()
        connection.close()
    
    return render_template('create_exam.html', **context)


@teacher.route('/save_exam', methods=['POST'])
@role_required('TEACHER')
def save_exam():
    """
    Save exam with questions and choices to database.
    Expected JSON structure from frontend:
    {
        assignment_id: int,
        exam_title: string,
        exam_type: 'Quiz' or 'Exam',
        duration_minutes: int,
        start_datetime: datetime string (ISO format from datetime-local input),
        end_datetime: datetime string (ISO format from datetime-local input),
        status: 'Draft' or 'Published',
        questions: [
            {
                question_text: string,
                question_type: 'MCQ' or 'TrueFalse',
                points: int,
                choices: [
                    { choice_text: string, is_correct: boolean },
                    ...
                ]
            },
            ...
        ]
    }
    """
    try:
        data = request.get_json()
        
        # Validate required data
        if not data:
            return jsonify({"success": False, "message": "No data received"}), 400
        
        required_fields = ['assignment_id', 'exam_title', 'exam_type', 'duration_minutes', 
                          'start_datetime', 'end_datetime', 'status', 'questions']
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "message": f"Missing required field: {field}"}), 400
        
        if not data['questions']:
            return jsonify({"success": False, "message": "At least one question is required"}), 400
        
        # Validate that all questions have at least one choice
        for q in data['questions']:
            if not q.get('choices') or len(q['choices']) == 0:
                return jsonify({"success": False, "message": "All questions must have at least one choice"}), 400
            
            # Validate that at least one choice is marked as correct
            if not any(c.get('is_correct', False) for c in q['choices']):
                return jsonify({"success": False, "message": "Each question must have at least one correct choice"}), 400
        
        user_id = session.get('user_id')
        connection = mysql.connector.connect(**db_config)
        connection.autocommit = False
        cursor = connection.cursor(dictionary=True)
        
        try:
            # Verify that the teacher owns this assignment
            verify_query = """
            SELECT ca.assignment_id, tp.teacher_id
            FROM course_assignments ca
            JOIN teacher_profiles tp ON ca.teacher_id = tp.teacher_id
            WHERE ca.assignment_id = %s AND tp.user_id = %s
            """
            cursor.execute(verify_query, (data['assignment_id'], user_id))
            assignment = cursor.fetchone()
            
            if not assignment:
                cursor.close()
                connection.close()
                return jsonify({"success": False, "message": "Unauthorized: Assignment not found or you don't have access"}), 403
            
            # Map exam_type from frontend to database enum
            exam_type_map = {
                'Quiz': 'Quiz',
                'Exam': 'Exam',
                'quiz': 'Quiz',
                'exam': 'Exam'
            }
            db_exam_type = exam_type_map.get(data['exam_type'], 'Exam')
            
            # Map status from frontend to database enum
            status_map = {
                'Draft': 'draft',
                'Published': 'published',
                'draft': 'draft',
                'published': 'published'
            }
            db_status = status_map.get(data['status'], 'draft')
            
            # Convert datetime strings from HTML datetime-local input
            try:
                start_time = datetime.fromisoformat(data['start_datetime'].replace('T', ' '))
                end_time = datetime.fromisoformat(data['end_datetime'].replace('T', ' '))
            except (ValueError, AttributeError):
                return jsonify({"success": False, "message": "Invalid datetime format"}), 400
                
            if end_time <= start_time:
                return jsonify({"success": False, "message": "End date and time must be after start date and time"}), 400
            
            # Insert into exams table
            exam_query = """
            INSERT INTO exams (
                assignment_id, exam_title, exam_type, duration_minutes, 
                total_questions, start_datetime, end_datetime, 
                shuffle_questions, shuffle_answers, fullscreen_required, copy_paste_disabled,
                status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            exam_values = (
                data['assignment_id'],
                data['exam_title'],
                db_exam_type,
                int(data['duration_minutes']),
                len(data['questions']),
                start_time,
                end_time,
                True,  # shuffle_questions
                True,  # shuffle_answers
                True,  # fullscreen_required
                True,  # copy_paste_disabled
                db_status
            )
            
            cursor.execute(exam_query, exam_values)
            exam_id = cursor.lastrowid
            
            if not exam_id:
                raise Exception("Failed to insert exam")
            
            # Loop through each question
            for q_index, q in enumerate(data['questions']):
                # Validate question data
                if not q.get('question_text') or not q.get('question_type'):
                    raise ValueError(f"Question {q_index + 1} is missing required fields")
                
                # Map question_type from frontend to database enum
                q_type_map = {
                    'MCQ': 'MCQ',
                    'TrueFalse': 'TrueFalse',
                    'MTQ': 'MTQ'
                }
                db_q_type = q_type_map.get(q['question_type'], 'MCQ')
                
                # Insert question into exam_questions table
                q_query = """
                INSERT INTO exam_questions (exam_id, question_text, question_type, points)
                VALUES (%s, %s, %s, %s)
                """
                
                question_points = int(q.get('points', 1))
                cursor.execute(q_query, (exam_id, q['question_text'], db_q_type, question_points))
                question_id = cursor.lastrowid
                
                if not question_id:
                    raise Exception(f"Failed to insert question {q_index + 1}")
                
                # Insert choices for this question into question_choices table
                for c_index, choice in enumerate(q['choices']):
                    if not choice.get('choice_text'):
                        raise ValueError(f"Question {q_index + 1}, Choice {c_index + 1} is missing text")
                    
                    choice_query = """
                    INSERT INTO question_choices (question_id, choice_text, is_correct)
                    VALUES (%s, %s, %s)
                    """
                    
                    is_correct = bool(choice.get('is_correct', False))
                    cursor.execute(choice_query, (question_id, choice['choice_text'], is_correct))
            
            # Commit all changes
            connection.commit()
            
            return jsonify({
                "success": True,
                "message": "Assessment created successfully!",
                "exam_id": exam_id
            }), 201
        
        except ValueError as ve:
            connection.rollback()
            return jsonify({"success": False, "message": f"Validation error: {str(ve)}"}), 400
        
        except Exception as e:
            connection.rollback()
            print(f"Error saving exam: {str(e)}")
            return jsonify({"success": False, "message": f"Database error: {str(e)}"}), 500
        
        finally:
            cursor.close()
            connection.close()
    
    except Exception as e:
        print(f"Unexpected error in save_exam: {str(e)}")
        return jsonify({"success": False, "message": "An unexpected error occurred"}), 500


@teacher.route('/delete_exam/<int:exam_id>', methods=['POST'])
@role_required('TEACHER')
def delete_exam(exam_id):
    """Delete an exam and all its related data (questions, choices, attempts)."""
    user_id = session.get('user_id')
    connection = mysql.connector.connect(**db_config)
    connection.autocommit = False
    cursor = connection.cursor(dictionary=True)
    
    try:
        # First verify that the teacher owns the assignment for this exam
        verify_query = """
        SELECT ca.assignment_id, tp.teacher_id
        FROM exams e
        JOIN course_assignments ca ON e.assignment_id = ca.assignment_id
        JOIN teacher_profiles tp ON ca.teacher_id = tp.teacher_id
        WHERE e.exam_id = %s AND tp.user_id = %s
        """
        cursor.execute(verify_query, (exam_id, user_id))
        assignment = cursor.fetchone()
        
        if not assignment:
            return jsonify({"success": False, "message": "Unauthorized: Exam not found or you don't have access"}), 403
        
        # Get all attempt_ids for this exam
        cursor.execute("SELECT attempt_id FROM exam_attempts WHERE exam_id = %s", (exam_id,))
        attempts = cursor.fetchall()
        
        # Delete student_answers for all attempts
        for attempt in attempts:
            cursor.execute("DELETE FROM student_answers WHERE attempt_id = %s", (attempt['attempt_id'],))
        
        # Delete exam_security_logs for all attempts
        for attempt in attempts:
            cursor.execute("DELETE FROM exam_security_logs WHERE attempt_id = %s", (attempt['attempt_id'],))
        
        # Delete exam_attempts for this exam
        cursor.execute("DELETE FROM exam_attempts WHERE exam_id = %s", (exam_id,))
        
        # Delete exam_activity_logs for this exam
        cursor.execute("DELETE FROM exam_activity_logs WHERE exam_id = %s", (exam_id,))
        
        # Get all question_ids for this exam
        cursor.execute("SELECT question_id FROM exam_questions WHERE exam_id = %s", (exam_id,))
        questions = cursor.fetchall()
        
        # Delete question_choices for all questions
        for q in questions:
            cursor.execute("DELETE FROM question_choices WHERE question_id = %s", (q['question_id'],))
        
        # Delete exam_questions for this exam
        cursor.execute("DELETE FROM exam_questions WHERE exam_id = %s", (exam_id,))
        
        # Delete the exam itself
        cursor.execute("DELETE FROM exams WHERE exam_id = %s", (exam_id,))
        
        # Commit all changes
        connection.commit()
        
        return jsonify({
            "success": True,
            "message": "Exam deleted successfully!"
        }), 200
        
    except Exception as e:
        connection.rollback()
        return jsonify({"success": False, "message": f"Error deleting exam: {str(e)}"}), 500
    finally:
        cursor.close()
        connection.close()
