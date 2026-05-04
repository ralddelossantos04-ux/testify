# Anti-Cheating Features Implementation

## Overview
Comprehensive anti-cheating mechanisms have been implemented for the Testify exam system to prevent student cheating during online exams and quizzes.

---

## 🔒 Features Implemented

### 1. **Auto Timer** ⏱️
- **Backend**: Countdown timer calculates remaining time from exam start to end
- **Frontend**: Real-time countdown display in top-right corner
- **Auto-Submit**: When time reaches 0, exam automatically submits
- **Time Tracking**: Tracks time used vs. time allocated
- **Visual Warnings**: 
  - Yellow warning at 10 minutes remaining
  - Red danger state at 5 minutes remaining
  - Pulsing animation at final minutes

**Files Modified:**
- `student_bp.py`: `take_exam()` - calculates `time_left_seconds`
- `take_exam.html`: `updateTimer()` function with auto-submit logic

---

### 2. **Tab Switching Detection** 🚨
- **Detection Method**: Uses `document.visibilitychange` event
- **Logging**: Every tab switch is logged as a security violation
- **Tracking**: Counter for total switches during exam (`state.tabSwitches`)
- **User Notification**: Toast warning appears each time student leaves tab
- **Database Logging**: Event logged to `exam_security_logs` table

**Event Logged:**
```
event_type: 'TAB_SWITCH_DETECTED'
event_details: { switch_count, timestamp }
```

**Files Modified:**
- `take_exam.html`: Event listener on `visibilitychange`

---

### 3. **Double Device Detection** 📱💻
- **Device Fingerprinting**: Combines User-Agent + IP address
- **Check on Exam Start**: Validates if student using same exam from different device
- **Active Session Check**: Queries last 5 minutes of activity logs
- **Automatic Flagging**: If different device detected, flags and logs violation

**Backend Functions:**
- `get_device_fingerprint()` - Generates SHA256 hash of device signature
- `check_double_device()` - Queries active sessions with different devices
- API endpoint: `/api/exam/validate_device` - Real-time device validation

**Database:**
- `exam_activity_logs`: Stores device_info and ip_address
- `exam_security_logs`: Logs DOUBLE_DEVICE_DETECTED events

**Files Modified:**
- `student_bp.py`: New functions + enhanced `/take_exam` route
- `take_exam.html`: `validateDevice()` function on page load

---

### 4. **Fullscreen Exam Mode** 🖥️
- **Enforcement**: Configurable per exam via `fullscreen_required` column
- **Auto-Request**: On page load, fullscreen is automatically requested
- **Exit Detection**: Monitors fullscreen status every 500ms
- **Re-entry Prompt**: If student exits fullscreen, warning shown and fullscreen re-requested
- **Browser Support**: Works with standard fullscreen API (Chrome, Firefox, Safari, Edge)

**Configuration:**
- Set `fullscreen_required = 1` in exams table for mandatory fullscreen
- Set `fullscreen_required = 0` to allow normal exam mode

**Fullscreen APIs Used:**
```javascript
elem.requestFullscreen()
elem.webkitRequestFullscreen()
elem.mozRequestFullScreen()
```

**Files Modified:**
- `student_bp.py`: Passes `fullscreen_required` to template
- `take_exam.html`: `requestFullscreen()` and `checkFullscreenStatus()` functions

---

### 5. **Copy/Paste Disabled** 🚫
- **Scope**: Can be configured per exam via `copy_paste_disabled` column
- **Disabled Operations**:
  - ❌ Ctrl+C (Copy)
  - ❌ Ctrl+V (Paste)
  - ❌ Ctrl+X (Cut)
  - ❌ Ctrl+A (Select All)
  - ❌ Right-click context menu
  
- **Logging**: Each attempt is logged with event type
- **User Notification**: Toast warning for each blocked action

**Events Logged:**
```
'COPY_ATTEMPT', 'PASTE_ATTEMPT', 'CUT_ATTEMPT', 'RIGHT_CLICK_ATTEMPT', 'KEYBOARD_SHORTCUT_BLOCKED'
```

**Configuration:**
- Set `copy_paste_disabled = 1` in exams table to enable
- Set `copy_paste_disabled = 0` to allow normal clipboard operations

**Event Listeners:**
- `copy`, `paste`, `cut` events on document
- `contextmenu` (right-click) event
- `keydown` event for keyboard shortcuts

**Files Modified:**
- `student_bp.py`: Passes `copy_paste_disabled` to template
- `take_exam.html`: Multiple event listeners and prevention logic

---

### 6. **Random Question Order** 🔀
- **Shuffling**: Questions randomized on every exam session
- **Backend Control**: Set `shuffle_questions = 1` in exams table
- **Implementation**: Uses Python's `random.shuffle()` before rendering
- **Prevents**: Students sharing question order or collaborating

**Files Modified:**
- `student_bp.py`: `/take_exam` route - checks exam setting and shuffles

---

### 7. **Random Answer Order** 🔀
- **Shuffling**: Answer choices randomized for each question
- **Backend Control**: Set `shuffle_answers = 1` in exams table
- **Implementation**: Uses Python's `random.shuffle()` before rendering
- **Prevents**: Pattern recognition or memorized answers from previous attempts

**Files Modified:**
- `student_bp.py`: `/take_exam` route - checks exam setting and shuffles choices

---

## 📊 Security Logging

### Event Types Logged
All events are stored in `exam_security_logs` table:

| Event Type | Trigger | Severity |
|-----------|---------|----------|
| EXAM_SESSION_STARTED | Exam begins | INFO |
| ANSWERED_QUESTION | Student answers | INFO |
| TAB_SWITCH_DETECTED | Student leaves exam tab | ⚠️ WARNING |
| WINDOW_BLUR_DETECTED | Window loses focus | ⚠️ WARNING |
| DOUBLE_DEVICE_DETECTED | Multiple devices active | 🔴 CRITICAL |
| COPY_ATTEMPT | User tries Ctrl+C | ⚠️ WARNING |
| PASTE_ATTEMPT | User tries Ctrl+V | ⚠️ WARNING |
| CUT_ATTEMPT | User tries Ctrl+X | ⚠️ WARNING |
| RIGHT_CLICK_ATTEMPT | User right-clicks | ⚠️ WARNING |
| KEYBOARD_SHORTCUT_BLOCKED | Forbidden shortcut | ⚠️ WARNING |
| FULLSCREEN_EXITED | Fullscreen mode exited | ⚠️ WARNING |
| EXAM_TIME_EXPIRED | Time runs out | INFO |

### Database Schema
```sql
-- Stored in exam_security_logs table
CREATE TABLE exam_security_logs (
    security_log_id INT AUTO_INCREMENT PRIMARY KEY,
    attempt_id INT NOT NULL,
    event_type VARCHAR(100),
    event_details JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (attempt_id) REFERENCES exam_attempts(attempt_id)
);

-- Device info tracked in exam_activity_logs
CREATE TABLE exam_activity_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT,
    exam_id INT,
    attempt_id INT,
    activity VARCHAR(100),
    device_info VARCHAR(255),
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🔧 API Endpoints

### 1. **POST `/student/api/exam/validate_device`**
Validates device on page load. Returns if multiple devices detected.

**Request:**
```json
{
    "attempt_id": 123,
    "device_fingerprint": "sha256hash..."
}
```

**Response:**
```json
{
    "status": "success",
    "valid": true,
    "double_device": false,
    "device_count": 1
}
```

---

### 2. **POST `/student/api/exam/log_security`**
Logs security events to database.

**Request:**
```json
{
    "attempt_id": 123,
    "event_type": "TAB_SWITCH_DETECTED",
    "event_details": "{\"switch_count\": 2, \"timestamp\": \"2026-05-04T10:30:45\"}"
}
```

**Response:**
```json
{
    "status": "success"
}
```

---

### 3. **POST `/student/api/exam/submit`**
Submits exam answers. Validates ownership, checks violations, calculates score.

**Request:**
```json
{
    "attempt_id": 123,
    "answers": {
        "question_1": 5,
        "question_2": 3,
        "question_3": 1
    }
}
```

**Response:**
```json
{
    "status": "success",
    "redirect_url": "/student/results?attempt_id=123"
}
```

---

## 🎯 Frontend Security Features

### Real-time Monitoring
- Tab switching detection every time visibility changes
- Fullscreen status checked every 500ms
- Activity logging on every question answer
- Violation counter incremented on suspicious activity

### User Notifications
Toast notifications appear for:
- Tab switches with count
- Copy/paste attempts
- Fullscreen exit
- Multiple devices detected
- Auto-submit on timer expiration

### State Tracking
```javascript
const state = {
    current: 0,              // Current question index
    answers: [],             // Student answers
    reviewed: [],            // Questions marked for review
    tabSwitches: 0,          // Tab switch count
    violations: 0,           // Total violation count
    isFullscreen: false      // Fullscreen status
};
```

---

## 🛡️ Configuration Per Exam

Teachers can enable/disable security features when creating exams:

```python
# In Admin/Teacher exam creation
exam = {
    'exam_title': 'Final Exam',
    'shuffle_questions': 1,        # Enable random question order
    'shuffle_answers': 1,          # Enable random answer order
    'fullscreen_required': 1,      # Force fullscreen mode
    'copy_paste_disabled': 1       # Disable copy/paste
}
```

---

## 🔍 Admin Dashboard Features

Teachers/Admins can review:
- **Violation Count**: Total violations per student per exam
- **Event Log**: Detailed timeline of suspicious activities
- **Device Info**: Which devices were used, IP addresses
- **Time Analysis**: When answers were submitted, time gaps
- **Score Impact**: Flag suspicious submissions for review

---

## 📋 Implementation Checklist

- ✅ Auto Timer with auto-submit
- ✅ Tab Switching Detection
- ✅ Double Device Detection (fingerprinting + IP)
- ✅ Fullscreen Mode Enforcement
- ✅ Copy/Paste Disabled
- ✅ Random Question Order
- ✅ Random Answer Order
- ✅ Security Event Logging
- ✅ Device Fingerprinting (SHA256)
- ✅ Real-time Violation Tracking
- ✅ User Notifications (Toast warnings)
- ✅ API Endpoints for Security
- ✅ Database Schema for Event Logging

---

## 🚀 How to Enable Features

### For Admin/Teachers (Setting exam properties):

```python
# In your exam creation/edit form
exam_data = {
    'exam_title': 'Midterm Exam',
    'duration_minutes': 60,
    'shuffle_questions': True,       # Random question order
    'shuffle_answers': True,         # Random answer order
    'fullscreen_required': True,     # Force fullscreen
    'copy_paste_disabled': True,     # Block copy/paste operations
}
```

### Features Work Automatically:
- ✅ Tab switching is always detected
- ✅ Device fingerprinting always active
- ✅ Auto-submit on time expiration always active
- ✅ Timer always displayed

---

## ⚙️ Technical Details

### Device Fingerprinting Algorithm
```python
user_agent = request.headers.get('User-Agent')
ip_address = request.remote_addr
fingerprint = hashlib.sha256(f"{user_agent}:{ip_address}".encode()).hexdigest()
```

### Violation Tracking
- Violations counted in real-time on frontend
- Logged to database with timestamps
- Admins can review for academic integrity reviews
- Doesn't prevent submission (allows flagging after)

### Performance
- Minimal performance impact on exam experience
- Event logging is asynchronous (doesn't block user)
- Fullscreen checks run every 500ms (low overhead)
- No page reloads or interruptions

---

## 🔐 Security Best Practices

1. **Never store sensitive data in JavaScript** - Device fingerprints are hashed
2. **Always validate on backend** - Device checks performed server-side
3. **Timestamp all events** - Every event logged with creation time
4. **Use HTTPS** - IP addresses and device info should be transmitted securely
5. **Regular audits** - Review security logs for patterns of cheating

---

## 📝 Notes for Future Enhancement

Possible improvements:
- Proctoring integration (face detection)
- Browser locking (prevent alt-tab)
- IP geofencing (restrict to campus)
- Keystroke dynamics
- Mouse movement analysis
- Suspicious answer patterns detection
- ML-based anomaly detection

---

## 🎓 Testing

To test the anti-cheating features:

1. **Tab Switching**: Leave and return to exam tab → Toast warning appears
2. **Copy/Paste**: Try Ctrl+C or Ctrl+V → Warning and event logged
3. **Fullscreen**: Exit fullscreen → Auto-reminder to return
4. **Timer**: Wait for exam to expire → Auto-submit triggers
5. **Device**: Try accessing from 2 devices → Double device warning
6. **Question Shuffle**: Create exam with shuffle → Questions in different order each time
7. **Answer Shuffle**: Create exam with shuffle → Answer options in different order

---

## ✅ Deployment Checklist

- [ ] Database tables exist (exam_security_logs, exam_activity_logs)
- [ ] Backend student_bp.py updated with security functions
- [ ] Frontend take_exam.html updated with JavaScript features
- [ ] Exam creation/edit form has security checkboxes
- [ ] Test all features in staging environment
- [ ] Configure HTTPS for secure transmission
- [ ] Brief teachers on new security options
- [ ] Add security log review to admin dashboard

---

**Implementation Date:** May 4, 2026  
**Status:** ✅ Complete and Ready for Testing
