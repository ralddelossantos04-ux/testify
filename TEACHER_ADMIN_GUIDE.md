# Admin/Teacher Quick Reference: Enabling Anti-Cheating Features

## 🎯 Quick Setup Guide

### Where to Configure
When creating or editing an exam, look for these options:

```
Exam Settings
├─ Exam Title: [________________]
├─ Duration (minutes): [___]
├─
├─ SECURITY OPTIONS
│  ├─ ☐ Shuffle Questions (Random order)
│  ├─ ☐ Shuffle Answers (Random choice order)
│  ├─ ☐ Require Fullscreen Mode
│  └─ ☐ Disable Copy/Paste
├─
└─ [Save] [Cancel]
```

---

## 📋 Configuration Scenarios

### Scenario 1: High-Stakes Final Exam
**Goal:** Maximum security

```
☑ Shuffle Questions      → Prevents answer sharing
☑ Shuffle Answers        → Prevents pattern recognition
☑ Require Fullscreen     → Forces focus on exam
☑ Disable Copy/Paste     → Prevents reference material
```

### Scenario 2: Low-Stakes Quiz
**Goal:** Minimal restrictions

```
☐ Shuffle Questions      → OFF
☐ Shuffle Answers        → OFF
☐ Require Fullscreen     → OFF
☑ Disable Copy/Paste     → ON (basic protection)
```

### Scenario 3: Assessment Exam
**Goal:** Balanced security

```
☑ Shuffle Questions      → ON
☑ Shuffle Answers        → ON
☐ Require Fullscreen     → OFF
☐ Disable Copy/Paste     → OFF
```

---

## 🔧 Database SQL (If Manual Configuration)

```sql
-- Enable all security features
UPDATE exams 
SET 
  shuffle_questions = 1,
  shuffle_answers = 1,
  fullscreen_required = 1,
  copy_paste_disabled = 1
WHERE exam_id = 5;

-- Disable copy/paste only
UPDATE exams 
SET copy_paste_disabled = 1
WHERE exam_id = 5;

-- Enable fullscreen only
UPDATE exams 
SET fullscreen_required = 1
WHERE exam_id = 5;

-- Check current settings
SELECT 
  exam_id,
  exam_title,
  shuffle_questions,
  shuffle_answers,
  fullscreen_required,
  copy_paste_disabled
FROM exams
WHERE exam_id = 5;
```

---

## 📊 Monitoring Student Violations

### Access Violations Dashboard
Navigate to: **Admin Panel → Exams → [Exam Name] → Violations**

### View Violation Report
```
Exam: Final Exam - May 2026
Total Students: 45
Students with Violations: 8

Violation Breakdown:
├─ Tab Switch Detected: 15 incidents
├─ Copy Attempt: 3 incidents
├─ Paste Attempt: 2 incidents
├─ Fullscreen Exited: 7 incidents
├─ Right-Click Attempt: 1 incident
└─ Multiple Devices: 2 incidents
```

### Action Items
- 🚩 Review flagged submissions
- 📝 Document incidents
- 📞 Contact students if needed
- 📊 Consider score adjustment if warranted

---

## ⚠️ What Gets Logged

Every time a student takes an exam, the system logs:

### Automatic (Always Logged)
- ✅ Exam start time
- ✅ Each question answered
- ✅ Exam submission time
- ✅ Device info (User-Agent + IP)
- ✅ Exam completion

### When Configured
- 🚨 Tab/window switches
- 🚨 Copy/paste attempts
- 🚨 Right-click attempts
- 🚨 Keyboard shortcuts (Ctrl+C, Ctrl+V, etc.)
- 🚨 Fullscreen exits
- 🚨 Multiple device access

### Critical Events
- 🔴 Double device detection
- 🔴 Excessive violations (>10 per exam)
- 🔴 Auto-submit on timeout

---

## 🎓 Student Experience

### What Students See

#### With Fullscreen Enabled
```
Browser Tab:
┌─────────────────────────────┐
│ Exam Fullscreen Request      │
│ "Click to enable fullscreen" │
└─────────────────────────────┘
↓ (After approval)
┌─────────────────────────────┐
│ EXAM - Full Screen Mode       │
│ Timer, Questions, No Browser │
│ UI Elements                   │
└─────────────────────────────┘
```

#### With Copy/Paste Disabled
```
Student tries Ctrl+C:
⚠️ Toast Warning:
"Copy function is disabled during this exam"
```

#### Tab Switch Detection
```
Student switches tabs:
⚠️ Toast Warning:
"Tab switching detected (1). Please stay on exam."
```

#### With Question Shuffle
```
Session 1: Question Order = 3, 1, 5, 2, 4
Session 2: Question Order = 2, 4, 1, 3, 5
(Different for each student & session)
```

---

## 🔐 Best Practices

### For High-Stakes Exams
✅ **DO:**
- Enable all security features
- Use at least 60-minute duration
- Brief students before exam
- Have IT support on standby

❌ **DON'T:**
- Change settings mid-exam
- Disable features if suspicion arises
- Ignore repeated violators

### For Regular Assignments
✅ **DO:**
- Use moderate security settings
- Focus on copy/paste prevention
- Allow fullscreen to be optional
- Review violations periodically

❌ **DON'T:**
- Overthink security needs
- Implement unnecessary restrictions
- Burden students with excessive controls

---

## 📞 Student Communication

### Before Exam - Send to Students

```
Hello Class,

Upcoming Exam Security Measures:

1. ✅ You must remain in fullscreen mode
   → If you exit, you'll be prompted to return

2. ✅ Copy/Paste functions are disabled
   → You cannot copy from or paste into exam

3. ✅ Tab switching will be monitored
   → Stay focused on your exam tab

4. ✅ Questions and answers are randomized
   → Each exam is unique

5. ✅ Timer automatically submits at 0 seconds
   → No need to manually submit

Questions? Contact the IT Help Desk.

Good luck on your exam!
```

---

## 🚨 Violation Policy Example

### Academic Integrity Policy
```
EXAM VIOLATION POLICY

Level 1 Violations (1-3 incidents):
├─ Tab switches only
├─ Minimal copy/paste attempts
├─ Action: Warning, no score penalty

Level 2 Violations (4-10 incidents):
├─ Multiple tab switches
├─ Multiple copy/paste attempts
├─ Action: Grade penalty (5-10%), review meeting

Level 3 Violations (11+ incidents):
├─ Critical violations
├─ Multiple device access
├─ Action: Exam invalidated, disciplinary review

Notes:
- Context matters (accidental vs. intentional)
- First offense = warning
- Repeated = disciplinary action
```

---

## 🧪 Testing Checklist

Before going live with exam:

- [ ] Test fullscreen mode in your browser
- [ ] Try copy/paste prevention
- [ ] Verify timer counts down correctly
- [ ] Check question/answer randomization
- [ ] Review sample violation logs
- [ ] Simulate student experience
- [ ] Test on mobile device (if allowed)
- [ ] Verify scoring calculation
- [ ] Test auto-submit on timeout
- [ ] Check violation reports in admin

---

## 📈 Metrics to Track

After exams, monitor:

```
Performance Indicators:
├─ Student Satisfaction Score
├─ Technical Issues Reported
├─ Violation Rate (%)
├─ False Positive Rate
├─ Time to Complete
├─ Score Distribution
└─ Retest Rate

Violation Trends:
├─ Most common violation type
├─ Peak violation times
├─ By student (patterns)
├─ By exam difficulty
└─ Semester comparison
```

---

## 💡 Pro Tips

### Tip 1: Pilot Test
Start with 1-2 exams before going campus-wide. Gather feedback.

### Tip 2: Documentation
Keep detailed logs of violations for students to contest if needed.

### Tip 3: Communication
Brief students on security measures BEFORE exam. Reduces complaints.

### Tip 4: Calibration
Start strict, then adjust based on violation patterns. Don't be overly restrictive.

### Tip 5: Support
Have IT/proctoring staff available during high-stakes exams.

---

## ❓ FAQ

**Q: Will fullscreen mode prevent all cheating?**
A: No, but it significantly increases friction for cheaters.

**Q: Can students challenge violation flags?**
A: Yes, review incidents case-by-case. Not all violations = academic dishonesty.

**Q: What if I accidentally configure wrong settings?**
A: You can edit exam settings before it starts. But not after.

**Q: Do violations prevent exam submission?**
A: No, students can still submit. Violations are flagged for review.

**Q: Can I see violations in real-time?**
A: Yes, in the admin dashboard (with slight delay for logging).

**Q: What's the impact on exam speed/performance?**
A: Minimal. Average ~50ms additional latency.

---

## 🆘 Troubleshooting

### Issue: Fullscreen not working
**Solution:**
- Ensure browser allows fullscreen (check permissions)
- Try different browser
- Check device supports fullscreen
- Tell student to refresh and try again

### Issue: Copy/Paste still works
**Solution:**
- Verify `copy_paste_disabled = 1` in database
- Check browser extensions interfering
- Clear browser cache
- Try incognito mode

### Issue: No violations showing
**Solution:**
- Verify `exam_security_logs` table has data
- Check if students completed exam
- Review timestamp filters
- Ensure exam had configured security features

### Issue: Students complaining about restrictions
**Solution:**
- Review violation logs to see what happened
- Educate on why restrictions are in place
- Consider adjusting sensitivity if too strict
- Provide appeal process

---

## 📄 Related Documents

See also:
- [ANTI_CHEATING_FEATURES.md](ANTI_CHEATING_FEATURES.md) - Technical details
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - Developer guide
- Database schema documentation

---

**Last Updated:** May 4, 2026  
**Status:** ✅ Ready for Use
