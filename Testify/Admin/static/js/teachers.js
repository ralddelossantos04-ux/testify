// ============================================
// TEACHERS MANAGEMENT MODULE
// ============================================

let currentPage = 1;
let perPage = 10;
let totalPages = 1;
let currentSearch = '';
let currentDepartment = '';
let currentStatus = '';
let activeMenuId = null;

// ============================================
// CUSTOM MODAL SYSTEM
// ============================================

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    const backdrop = document.getElementById('modalBackdrop');
    if (modal && backdrop) {
        closeAllModals();
        backdrop.classList.add('active');
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    const backdrop = document.getElementById('modalBackdrop');
    if (modal) modal.classList.remove('active');
    const anyModalOpen = document.querySelector('.modal.active');
    if (!anyModalOpen && backdrop) {
        backdrop.classList.remove('active');
        document.body.style.overflow = '';
    }
}

function closeAllModals() {
    document.querySelectorAll('.modal.active').forEach(m => m.classList.remove('active'));
    const backdrop = document.getElementById('modalBackdrop');
    if (backdrop) backdrop.classList.remove('active');
    document.body.style.overflow = '';
}

document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeAllModals();
        closeAllActionMenus();
    }
});

// ============================================
// LOADING STATES
// ============================================

function showSkeleton() {
    const skeleton = document.getElementById('skeletonLoader');
    const table = document.getElementById('tableContainer');
    const empty = document.getElementById('emptyState');
    const pagination = document.getElementById('paginationContainer');
    if (skeleton) skeleton.style.display = 'block';
    if (table) table.style.display = 'none';
    if (empty) empty.style.display = 'none';
    if (pagination) pagination.style.display = 'none';
}

function hideSkeleton() {
    const skeleton = document.getElementById('skeletonLoader');
    if (skeleton) skeleton.style.display = 'none';
}

// ============================================
// STATS
// ============================================

function loadStats() {
    fetch('/admin/api/teachers/counts')
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                const statTotal = document.getElementById('statTotalTeachers');
                const statMale = document.getElementById('statMaleTeachers');
                const statFemale = document.getElementById('statFemaleTeachers');
                if (statTotal) statTotal.textContent = data.total;
                if (statMale) statMale.textContent = data.male;
                if (statFemale) statFemale.textContent = data.female;
            }
        })
        .catch(error => console.error('Error loading stats:', error));
}

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    showSkeleton();
    loadStats();
    loadTeachers();

    const searchInput = document.getElementById('searchInput');
    const departmentFilter = document.getElementById('departmentFilter');
    const statusFilter = document.getElementById('statusFilter');

    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                currentSearch = this.value.trim();
                currentPage = 1;
                loadTeachers();
            }, 300);
        });
    }

    if (departmentFilter) {
        departmentFilter.addEventListener('change', function() {
            currentDepartment = this.value;
            currentPage = 1;
            loadTeachers();
        });
    }

    if (statusFilter) {
        statusFilter.addEventListener('change', function() {
            currentStatus = this.value;
            currentPage = 1;
            loadTeachers();
        });
    }

    document.addEventListener('click', function(event) {
        if (!event.target.closest('.action-menu')) {
            closeAllActionMenus();
        }
    });
});

// ============================================
// DATA LOADING
// ============================================

function loadTeachers() {
    showSkeleton();

    const params = new URLSearchParams({
        page: currentPage,
        per_page: perPage,
        department_id: currentDepartment,
        status: currentStatus,
        search: currentSearch
    });

    fetch(`/admin/api/teachers?${params}`)
        .then(r => r.json())
        .then(data => {
            hideSkeleton();
            if (data.success) {
                renderTeachers(data.teachers);
                totalPages = data.total_pages;
                updatePagination();
                updateResultCount(data.total);
            } else {
                showNotification(data.message, 'error');
                showEmptyState();
            }
        })
        .catch(error => {
            hideSkeleton();
            console.error('Error loading teachers:', error);
            showNotification('Failed to load teachers', 'error');
            showEmptyState();
        });
}

function showEmptyState() {
    const tbody = document.getElementById('teachersTableBody');
    const table = document.getElementById('tableContainer');
    const empty = document.getElementById('emptyState');
    const pagination = document.getElementById('paginationContainer');

    if (tbody) tbody.innerHTML = '';
    if (table) table.style.display = 'none';
    if (empty) empty.style.display = 'block';
    if (pagination) pagination.style.display = 'none';
}

// ============================================
// TABLE RENDERING
// ============================================

function renderTeachers(teachers) {
    const tbody = document.getElementById('teachersTableBody');
    const emptyState = document.getElementById('emptyState');
    const tableContainer = document.getElementById('tableContainer');

    if (!teachers || teachers.length === 0) {
        showEmptyState();
        return;
    }

    if (emptyState) emptyState.style.display = 'none';
    if (tableContainer) tableContainer.style.display = 'block';

    if (tbody) {
        tbody.innerHTML = teachers.map(teacher => `
            <tr>
                <td><strong>${escapeHtml(teacher.employee_id || 'N/A')}</strong></td>
                <td>${escapeHtml(formatName(teacher))}</td>
                <td>${escapeHtml(teacher.email || '')}</td>
                <td><span class="program-badge">${escapeHtml(teacher.department_code || '')}</span></td>
                <td>${renderStatusBadge(teacher.status)}</td>
                <td style="text-align: center;">
                    <div class="action-menu">
                        <button class="action-menu-btn" onclick="toggleActionMenu(event, '${teacher.user_id}')" title="Actions">
                            <i class="fas fa-ellipsis-v"></i>
                        </button>
                        <div class="action-menu-dropdown" id="actionMenu-${teacher.user_id}">
                            <button class="action-menu-item" onclick="viewTeacher(${teacher.user_id})">
                                <i class="fas fa-eye text-primary"></i> View
                            </button>
                            <button class="action-menu-item" onclick="editTeacher(${teacher.user_id})">
                                <i class="fas fa-edit text-success"></i> Edit Profile
                            </button>
                            <button class="action-menu-item" onclick="assignTeacher(${teacher.user_id})">
                                <i class="fas fa-tasks text-primary"></i> Assign
                            </button>
                            <button class="action-menu-item" onclick="resetTeacherPassword(${teacher.user_id})">
                                <i class="fas fa-key text-warning"></i> Reset Password
                            </button>
                            <button class="action-menu-item warning" onclick="toggleTeacherStatus(${teacher.user_id}, '${(teacher.status || '').toLowerCase() === 'active' ? 'Inactive' : 'Active'}')">
                                <i class="fas fa-${(teacher.status || '').toLowerCase() === 'active' ? 'pause' : 'play'}"></i> ${(teacher.status || '').toLowerCase() === 'active' ? 'Deactivate' : 'Activate'}
                            </button>
                            <button class="action-menu-item danger" onclick="deleteTeacher(${teacher.user_id})">
                                <i class="fas fa-trash-alt"></i> Delete Teacher
                            </button>
                        </div>
                    </div>
                </td>
            </tr>
        `).join('');
    }
}

function formatName(teacher) {
    const parts = [teacher.first_name, teacher.middle_name, teacher.last_name].filter(Boolean);
    return parts.join(' ');
}

function renderStatusBadge(status) {
    console.log('Status value:', status, 'Type:', typeof status);
    const normalizedStatus = (status || '').toLowerCase();
    const cls = normalizedStatus === 'active' ? 'status-active' : 'status-inactive';
    const icon = normalizedStatus === 'active' ? 'fa-check-circle' : 'fa-times-circle';
    return `<span class="status-badge ${cls}"><i class="fas ${icon}"></i> ${escapeHtml(status || 'Unknown')}</span>`;
}

// ============================================
// 3-DOT ACTION MENU
// ============================================

function toggleActionMenu(event, userId) {
    event.stopPropagation();
    const menu = document.getElementById(`actionMenu-${userId}`);
    if (!menu) return;

    if (activeMenuId === userId) {
        closeAllActionMenus();
        return;
    }

    closeAllActionMenus();
    menu.classList.add('active');
    activeMenuId = userId;
}

function closeAllActionMenus() {
    document.querySelectorAll('.action-menu-dropdown.active').forEach(m => m.classList.remove('active'));
    activeMenuId = null;
}

// ============================================
// PAGINATION
// ============================================

function updatePagination() {
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    const paginationInfo = document.getElementById('paginationInfo');
    const paginationContainer = document.getElementById('paginationContainer');
    const pageNumbers = document.getElementById('pageNumbers');
    const perPageSelect = document.getElementById('perPageSelect');

    const hasData = totalPages > 0;

    if (paginationContainer) paginationContainer.style.display = hasData ? 'flex' : 'none';
    if (prevBtn) prevBtn.disabled = currentPage <= 1;
    if (nextBtn) nextBtn.disabled = currentPage >= totalPages || totalPages === 0;
    if (paginationInfo) paginationInfo.textContent = `Page ${currentPage} of ${totalPages || 1}`;

    if (perPageSelect) perPageSelect.value = perPage;

    if (pageNumbers) {
        pageNumbers.innerHTML = '';
        const maxPages = 5;
        let startPage = Math.max(1, currentPage - Math.floor(maxPages / 2));
        let endPage = Math.min(totalPages, startPage + maxPages - 1);
        if (endPage - startPage < maxPages - 1) {
            startPage = Math.max(1, endPage - maxPages + 1);
        }

        for (let i = startPage; i <= endPage; i++) {
            const btn = document.createElement('button');
            btn.className = `pagination-btn ${i === currentPage ? 'active' : ''}`;
            btn.textContent = i;
            btn.onclick = () => goToPage(i);
            pageNumbers.appendChild(btn);
        }
    }
}

function changePage(direction) {
    const newPage = currentPage + direction;
    if (newPage >= 1 && newPage <= totalPages) {
        currentPage = newPage;
        loadTeachers();
    }
}

function goToPage(pageNum) {
    if (pageNum >= 1 && pageNum <= totalPages && pageNum !== currentPage) {
        currentPage = pageNum;
        loadTeachers();
    }
}

function changePerPage(value) {
    perPage = parseInt(value);
    currentPage = 1;
    loadTeachers();
}

function updateResultCount(total) {
    const resultCount = document.getElementById('resultCount');
    if (resultCount) {
        resultCount.textContent = `${total} teacher${total !== 1 ? 's' : ''}`;
        resultCount.style.display = total > 0 ? 'inline-flex' : 'none';
    }
}

// ============================================
// ADD TEACHER
// ============================================



// ============================================
// ACTION HANDLERS
// ============================================

function viewTeacher(userId) {
    closeAllActionMenus();
    
    fetch(`/admin/api/teachers/view/${userId}`)
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                const teacher = data.teacher;
                const content = document.getElementById('viewTeacherContent');
                
                const fullName = [teacher.first_name, teacher.middle_name, teacher.last_name].filter(Boolean).join(' ');
                const normalizedStatus = (teacher.status || '').toLowerCase();
                const statusColor = normalizedStatus === 'active' ? '#22c55e' : '#ff6b6b';
                const displayStatus = teacher.status ? teacher.status.charAt(0).toUpperCase() + teacher.status.slice(1).toLowerCase() : 'Unknown';
                
                content.innerHTML = `
                    <div style="margin-bottom: 24px;">
                        <h4 style="margin: 0 0 8px 0; color: var(--text-dark);">${escapeHtml(fullName)}</h4>
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span style="color: ${statusColor}; font-weight: 600; font-size: 0.9em;">
                                ${displayStatus === 'Active' ? '● Active' : '● Inactive'}
                            </span>
                        </div>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px;">
                        <div>
                            <label style="font-size: 0.8em; color: var(--text-gray); font-weight: 600;">Teacher ID</label>
                            <div style="font-size: 0.95em; color: var(--text-dark);">${escapeHtml(teacher.employee_id || 'N/A')}</div>
                        </div>
                        <div>
                            <label style="font-size: 0.8em; color: var(--text-gray); font-weight: 600;">Email</label>
                            <div style="font-size: 0.95em; color: var(--text-dark);">${escapeHtml(teacher.email || 'N/A')}</div>
                        </div>
                        <div>
                            <label style="font-size: 0.8em; color: var(--text-gray); font-weight: 600;">Department</label>
                            <div style="font-size: 0.95em; color: var(--text-dark);">${escapeHtml(teacher.department_name || 'Not assigned')}</div>
                        </div>
                        <div>
                            <label style="font-size: 0.8em; color: var(--text-gray); font-weight: 600;">Gender</label>
                            <div style="font-size: 0.95em; color: var(--text-dark);">${escapeHtml(teacher.gender || 'Not specified')}</div>
                        </div>
                        <div>
                            <label style="font-size: 0.8em; color: var(--text-gray); font-weight: 600;">Birthdate</label>
                            <div style="font-size: 0.95em; color: var(--text-dark);">${teacher.birthdate ? escapeHtml(teacher.birthdate) : 'Not available'}</div>
                        </div>
                        <div>
                            <label style="font-size: 0.8em; color: var(--text-gray); font-weight: 600;">Address</label>
                            <div style="font-size: 0.95em; color: var(--text-dark);">${escapeHtml(teacher.address || 'Not provided')}</div>
                        </div>
                        <div>
                            <label style="font-size: 0.8em; color: var(--text-gray); font-weight: 600;">Contact Number</label>
                            <div style="font-size: 0.95em; color: var(--text-dark);">${escapeHtml(teacher.contact_number || 'Not provided')}</div>
                        </div>
                    </div>
                    
                    <div style="padding-top: 16px; border-top: 1px solid var(--border-color);">
                        <label style="font-size: 0.8em; color: var(--text-gray); font-weight: 600; margin-bottom: 8px; display: block;">Subjects handled</label>
                        <div style="font-size: 0.9em; color: var(--text-gray);">No subjects assigned</div>
                    </div>
                    
                    <div style="padding-top: 16px; border-top: 1px solid var(--border-color);">
                        <label style="font-size: 0.8em; color: var(--text-gray); font-weight: 600; margin-bottom: 8px; display: block;">Blocks / Sections handled</label>
                        <div style="font-size: 0.9em; color: var(--text-gray);">No blocks assigned</div>
                    </div>
                `;
                
                openModal('viewTeacherModal');
            } else {
                showNotification(data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error loading teacher details:', error);
            showNotification('Failed to load teacher details', 'error');
        });
}

function editTeacher(userId) {
    closeAllActionMenus();
    
    // Clear form first
    const form = document.getElementById('editTeacherForm');
    if (form) form.reset();
    
    fetch(`/admin/api/teachers/view/${userId}`)
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                const teacher = data.teacher;
                console.log('Teacher data:', teacher);
                console.log('Gender value:', teacher.gender, 'Type:', typeof teacher.gender);
                
                document.getElementById('editUserId').value = teacher.user_id;
                document.getElementById('editFirstName').value = teacher.first_name || '';
                document.getElementById('editMiddleName').value = teacher.middle_name || '';
                document.getElementById('editLastName').value = teacher.last_name || '';
                
                // Handle gender - try multiple approaches
                const genderSelect = document.getElementById('editGender');
                const genderValue = teacher.gender ? teacher.gender.trim() : '';
                console.log('Setting gender to:', genderValue);
                
                // First try direct assignment
                genderSelect.value = genderValue;
                
                // If direct assignment didn't work, try finding matching option
                if (genderSelect.value !== genderValue && genderValue) {
                    for (let option of genderSelect.options) {
                        if (option.value === genderValue || option.text === genderValue) {
                            option.selected = true;
                            break;
                        }
                    }
                }
                
                console.log('Gender select value after setting:', genderSelect.value);
                
                // Handle birthdate - ensure it's in YYYY-MM-DD format for date input
                if (teacher.birthdate) {
                    let birthdateStr = teacher.birthdate;
                    // If it's a date string that's not in YYYY-MM-DD format, convert it
                    if (birthdateStr.length > 10) {
                        birthdateStr = birthdateStr.substring(0, 10);
                    }
                    document.getElementById('editBirthdate').value = birthdateStr;
                } else {
                    document.getElementById('editBirthdate').value = '';
                }
                
                document.getElementById('editAddress').value = teacher.address || '';
                document.getElementById('editContactNumber').value = teacher.contact_number || '';
                
                openModal('editTeacherModal');
            } else {
                showNotification(data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error loading teacher details:', error);
            showNotification('Failed to load teacher details', 'error');
        });
}

function submitEditTeacher() {
    const form = document.getElementById('editTeacherForm');
    if (!form) return;

    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    if (!data.first_name.trim() || !data.last_name.trim() || !data.gender) {
        showNotification('First name, last name, and gender are required', 'warning');
        return;
    }

    const spinner = document.getElementById('editTeacherSpinner');
    if (spinner) spinner.style.display = 'inline-block';

    fetch(`/admin/api/teachers/edit/${data.user_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(r => r.json())
    .then(result => {
        if (spinner) spinner.style.display = 'none';
        if (result.success) {
            showNotification(result.message || 'Teacher profile updated successfully', 'success');
            closeModal('editTeacherModal');
            loadTeachers();
        } else {
            showNotification(result.message, 'error');
        }
    })
    .catch(error => {
        if (spinner) spinner.style.display = 'none';
        console.error('Error updating teacher:', error);
        showNotification('Failed to update teacher', 'error');
    });
}

function assignTeacher(userId) {
    closeAllActionMenus();
    showNotification('Assign feature is coming soon', 'info');
}

function resetTeacherPassword(userId) {
    closeAllActionMenus();
    showNotification('Reset Password feature is coming soon', 'info');
}

function toggleTeacherStatus(userId, newStatus) {
    closeAllActionMenus();
    const normalizedStatus = (newStatus || '').toLowerCase();
    const action = normalizedStatus === 'active' ? 'activate' : 'deactivate';
    if (!confirm(`Are you sure you want to ${action} this teacher?`)) return;

    fetch(`/admin/api/teachers/update-status/${userId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus })
    })
    .then(r => r.json())
    .then(result => {
        if (result.success) {
            showNotification(result.message, 'success');
            loadTeachers();
        } else {
            showNotification(result.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error updating status:', error);
        showNotification('Failed to update status', 'error');
    });
}

function deleteTeacher(userId) {
    closeAllActionMenus();
    if (!confirm('Are you sure you want to delete this teacher? This action cannot be undone.')) return;

    fetch(`/admin/api/teachers/delete/${userId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(r => r.json())
    .then(result => {
        if (result.success) {
            showNotification(result.message, 'success');
            loadStats();
            loadTeachers();
        } else {
            showNotification(result.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error deleting teacher:', error);
        showNotification('Failed to delete teacher', 'error');
    });
}

// ============================================
// UTILITY FUNCTIONS
// ============================================

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showNotification(message, type = 'info') {
    document.querySelectorAll('.custom-notification').forEach(n => n.remove());
    const notification = document.createElement('div');
    notification.className = 'custom-notification';
    notification.style.cssText = 'position: fixed; top: 24px; right: 24px; padding: 16px 24px; border-radius: 12px; color: white; font-weight: 500; z-index: 9999; box-shadow: 0 8px 24px rgba(0,0,0,0.15); max-width: 400px; word-wrap: break-word; display: flex; align-items: center; gap: 12px; animation: slideInRight 0.4s cubic-bezier(0.4,0,0.2,1)';
    const colors = { success: '#22c55e', error: '#ff6b6b', warning: '#fb923c', info: '#3b82f6' };
    const icons = { success: 'fa-check-circle', error: 'fa-exclamation-circle', warning: 'fa-exclamation-triangle', info: 'fa-info-circle' };
    notification.style.backgroundColor = colors[type] || colors.info;
    notification.innerHTML = `<i class="fas ${icons[type] || icons.info}" style="font-size:1.2em"></i><span>${escapeHtml(message)}</span>`;
    document.body.appendChild(notification);
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.4s cubic-bezier(0.4,0,0.2,1) forwards';
        setTimeout(() => notification.remove(), 400);
    }, 3000);
}

const style = document.createElement('style');
style.textContent = '@keyframes slideInRight{from{transform:translateX(100%);opacity:0}to{transform:translateX(0);opacity:1}}@keyframes slideOutRight{from{transform:translateX(0);opacity:1}to{transform:translateX(100%);opacity:0}}';
document.head.appendChild(style);
