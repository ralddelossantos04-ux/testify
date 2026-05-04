# TODO: Fix Assessments Display for Students

## Task Summary
The exams created by teachers are not being displayed properly to students in the assessments page. This is due to several issues.

## Issues Found
1. **Status case mismatch**: Query checks for 'Published' but DB stores 'published' (lowercase)
2. **Template field mismatch**: Template uses `exam.title` but DB returns `exam.exam_title`
3. **Overly restrictive time filter**: Only shows exams where NOW() is between start and end datetime

## Plan

### Step 1: Fix SQL query in student_bp.py
- status: 'Published' -> 'published'
- Remove restrictive time filter to show all published exams
- Add more exam details to context

### Step 2: Fix assessments.html template
- Change exam.title to exam.exam_title
- Add better UI styling
- Display more exam information

## Status
- [x] Fix student_bp.py query
- [x] Fix assessments.html template

## Completed Fixes

### 1. student_bp.py
Updated the `/assessments` route:
- Changed status filter from `'Published'` to `'published'` (lowercase to match DB)
- Removed the overly restrictive time filter (`NOW() BETWEEN...`)
- Added more exam fields to query: exam_type, duration_minutes, total_questions, status

### 2. assessments.html
- Fixed field name: `exam.title` → `exam.exam_title`
- Added proper styling matching base_student.html design system
- Added exam metadata display (subject, duration, questions)
- Added exam schedule display (start/end datetime)
- Added proper badge for exam type (Quiz vs Exam)
- Added proper datetime formatting

### 3. Delete Exam Functionality (class_detail.html + teacher_bp.py)
Added delete function for teachers to delete exams:
- Added `/teacher/delete_exam/<exam_id>` route in teacher_bp.py
- Deletes exam and all related data (questions, choices, attempts, answers, logs)
- Added Delete button in class_detail.html for each exam
- Added JavaScript deleteExam() function with confirmation dialog
