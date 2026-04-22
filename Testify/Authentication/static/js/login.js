    const themes = {
    STUDENT: {
      light: '#6dda7b', mid: '#3cb84a', dark: '#27a037', btn: '#2dc653',
      btnShadow: 'rgba(45,198,83,.45)', btnShadowHover: 'rgba(45,198,83,.55)',
      grad: 'radial-gradient(ellipse at 70% 30%, #6dda7b 0%, #3cb84a 40%, #27a037 100%)',
      label: 'STUDENT'
    },
    TEACHER: {
      light: '#72b0f0', mid: '#4a90d9', dark: '#2770b8', btn: '#4a90d9',
      btnShadow: 'rgba(74,144,217,.45)', btnShadowHover: 'rgba(74,144,217,.6)',
      grad: 'radial-gradient(ellipse at 70% 30%, #72b0f0 0%, #4a90d9 40%, #2770b8 100%)',
      label: 'TEACHER'
    },
    ADMIN: {
    light: '#9b7cff',
    mid: '#6c5ce7',
    dark: '#4834d4',
    btn: '#6c5ce7',
    btnShadow: 'rgba(108,92,231,.45)',
    btnShadowHover: 'rgba(108,92,231,.6)',
    grad: 'radial-gradient(ellipse at 70% 30%, #9b7cff 0%, #6c5ce7 40%, #4834d4 100%)',
    label: 'ADMIN'
    }
  };

  function applyTheme(role) {
    const t = themes[role];
    const r = document.documentElement.style;
    r.setProperty('--theme-light',  t.light);
    r.setProperty('--theme-mid',    t.mid);
    r.setProperty('--theme-dark',   t.dark);
    r.setProperty('--theme-btn',    t.btn);
    r.setProperty('--theme-btn-shadow',       t.btnShadow);
    r.setProperty('--theme-btn-shadow-hover', t.btnShadowHover);
    // Background gradient
    document.body.style.background = t.grad;
    // Role tab label
    roleTab.textContent = t.label;
    // Swap input label
    document.getElementById('studentNumLabel').textContent =
      role === 'STUDENT' ? 'Student Number' : 'Username';
    // Show recover row only for Student
    document.getElementById('recoverRow').style.display =
      role === 'STUDENT' ? 'flex' : 'none';
  }

  /* ── Switch panel ── */
  const switchBtn  = document.getElementById('switchBtn');
  const switchOpts = document.getElementById('switchOptions');
  const roleTab    = document.getElementById('roleTab');

  switchBtn.addEventListener('click', () => {
    const open = switchOpts.classList.toggle('open');
    switchBtn.classList.toggle('open', open);
    switchBtn.setAttribute('aria-expanded', open);
  });

  document.querySelectorAll('.role-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      applyTheme(btn.dataset.role);
      switchOpts.classList.remove('open');
      switchBtn.classList.remove('open');
    });
  });

  /* Close on outside click */
  document.addEventListener('click', e => {
    if (!e.target.closest('.switch-panel')) {
      switchOpts.classList.remove('open');
      switchBtn.classList.remove('open');
    }
  });

  /* ── Eye toggle ── */
  const pwdInput = document.getElementById('password');
  const eyeToggle = document.getElementById('eyeToggle');
  const eyeIcon  = document.getElementById('eyeIcon');

  const eyeOpen  = `<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>`;
  const eyeClose = `<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/>`;

  eyeToggle.addEventListener('click', () => {
    const show = pwdInput.type === 'password';
    pwdInput.type = show ? 'text' : 'password';
    eyeIcon.innerHTML = show ? eyeClose : eyeOpen;
  });

  /* ── Logo flip – 3s auto-return ── */
  const logoWrapper = document.querySelector('.logo-wrapper');
  const logoInner   = document.querySelector('.logo-inner');
  let flipTimer  = null;
  let canFlip    = true;

  logoWrapper.addEventListener('mouseenter', () => {
    if (!canFlip) return;          // still in "used" state – do nothing
    canFlip = false;

    // Flip to wave side
    logoInner.classList.add('flipped');

    // After 3 s, flip back to logo (cursor may still be here)
    flipTimer = setTimeout(() => {
      logoInner.classList.remove('flipped');
      // canFlip stays false → hover won't retrigger while cursor is still on logo
    }, 3000);
  });

  logoWrapper.addEventListener('mouseleave', () => {
    // Cursor left – cancel any pending timer, snap back if still flipped, unlock
    clearTimeout(flipTimer);
    flipTimer = null;
    logoInner.classList.remove('flipped');

    // Wait for flip-back transition then re-enable
    setTimeout(() => { canFlip = true; }, 720);
  });

  /* ── Login ripple ── */
  document.getElementById('loginBtn').addEventListener('click', function(e) {
    const btn = this;
    const ripple = document.createElement('span');
    const size = Math.max(btn.offsetWidth, btn.offsetHeight);
    const rect = btn.getBoundingClientRect();
    ripple.className = 'ripple';
    ripple.style.cssText = `width:${size}px;height:${size}px;left:${e.clientX-rect.left-size/2}px;top:${e.clientY-rect.top-size/2}px`;
    btn.appendChild(ripple);
    setTimeout(() => ripple.remove(), 600);
  });
  
  /* Read role from URL parameter */
const params = new URLSearchParams(window.location.search);
const role = params.get("role") || "STUDENT";

applyTheme(role);
