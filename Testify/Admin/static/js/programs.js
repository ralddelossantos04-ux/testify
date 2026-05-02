// ============================================
// PROGRAMS & BLOCKS MANAGEMENT MODULE
// ============================================

// Global state
let currentPrograms = [];
let currentBlocks = [];
let currentProgramId = null;
let currentProgramCode = '';
let currentSpecializations = [];
let specializationCounter = 0;
let editSpecializationCounter = 0;
let allProgramsData = [];
let currentPage = 1;
let rowsPerPage = 10;


// ============================================
// CUSTOM MODAL SYSTEM
// ============================================

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    const backdrop = document.getElementById('modalBackdrop');
    
    if (modal && backdrop) {
        // Close any open modals first
        closeAllModals();
        
        backdrop.classList.add('active');
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    const backdrop = document.getElementById('modalBackdrop');
    
    if (modal) {
        modal.classList.remove('active');
    }
    
    // Only hide backdrop if no other modals are open
    const anyModalOpen = document.querySelector('.modal.active');
    if (!anyModalOpen && backdrop) {
        backdrop.classList.remove('active');
        document.body.style.overflow = '';
    }
}

function closeAllModals() {
    document.querySelectorAll('.modal.active').forEach(modal => {
        modal.classList.remove('active');
    });
    
    const backdrop = document.getElementById('modalBackdrop');
    if (backdrop) {
        backdrop.classList.remove('active');
    }
    document.body.style.overflow = '';
}

// Close modal on Escape key
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeAllModals();
    }
});

// ============================================
// INITIALIZATION
// ============================================
document.addEventListener('DOMContentLoaded', function() {
    // Load initial data
    loadPrograms();

    // Search handler
    const searchInput = document.getElementById('searchInput');
    let searchTimeout;
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                searchPrograms(this.value);
            }, 300);
        });
    }
});

// ============================================
// PROGRAMS CRUD OPERATIONS
// ============================================

function loadPrograms() {
    fetch('/api/programs')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                allProgramsData = data.programs;
                currentPrograms = data.programs;
                renderPrograms(data.programs);
                updateStats(data.programs);
                populateProgramFilter();
            } else {
                showNotification(data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error loading programs:', error);
            showNotification('Failed to load programs', 'error');
        });
}

function searchPrograms(query) {
    const url = query.trim() 
        ? `/api/programs/search?q=${encodeURIComponent(query.trim())}`
        : '/api/programs';
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                allProgramsData = data.programs;
                currentPrograms = data.programs;
                applyFilters();
            } else {
                showNotification(data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error searching programs:', error);
            showNotification('Search failed', 'error');
        });
}

function populateProgramFilter() {
    const programFilter = document.getElementById('filterProgram');
    if (!programFilter) return;
    
    programFilter.innerHTML = '<option value="">All Programs</option>';
    
    const programs = [...new Set(allProgramsData.map(p => ({
        id: p.program_id,
        code: p.program_code,
        name: p.program_name
    })))];
    
    programs.sort((a, b) => a.code.localeCompare(b.code));
    
    programs.forEach(program => {
        const option = document.createElement('option');
        option.value = program.id;
        option.textContent = `${program.code} - ${program.name}`;
        programFilter.appendChild(option);
    });
}

function updateSpecializationFilter(programId) {
    const specializationFilter = document.getElementById('filterSpecialization');
    if (!specializationFilter) return;
    
    specializationFilter.innerHTML = '<option value="">All Specializations</option>';
    
    if (!programId) {
        specializationFilter.disabled = true;
        return;
    }
    
    // Fetch specializations for the selected program
    fetch(`/api/program/${programId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success && data.specializations && data.specializations.length > 0) {
                specializationFilter.disabled = false;
                data.specializations.forEach(spec => {
                    const option = document.createElement('option');
                    option.value = spec.specialization_id;
                    option.textContent = `${spec.specialization_code} - ${spec.specialization_name}`;
                    specializationFilter.appendChild(option);
                });
            } else {
                specializationFilter.disabled = true;
            }
        })
        .catch(error => {
            console.error('Error loading specializations:', error);
            specializationFilter.disabled = true;
        });
}

function applyFilters() {
    const departmentFilter = document.getElementById('filterDepartment');
    const programFilter = document.getElementById('filterProgram');
    const specializationFilter = document.getElementById('filterSpecialization');
    const searchInput = document.getElementById('searchInput');
    
    const departmentId = departmentFilter ? departmentFilter.value : '';
    const programId = programFilter ? programFilter.value : '';
    const specializationId = specializationFilter ? specializationFilter.value : '';
    const searchTerm = searchInput ? searchInput.value.toLowerCase() : '';
    
    let filtered = [...allProgramsData];
    
    // Filter by department
    if (departmentId) {
        filtered = filtered.filter(p => p.department_id == departmentId);
    }
    
    // Filter by program
    if (programId) {
        filtered = filtered.filter(p => p.program_id == programId);
    }
    
    // Filter by specialization (need to check if program has this specialization)
    if (specializationId && programId) {
        // Since we're filtering by program already, we need to check if that program has the specialization
        // This requires fetching the program's specializations
        fetch(`/api/program/${programId}`)
            .then(response => response.json())
            .then(data => {
                if (data.success && data.specializations) {
                    const hasSpecialization = data.specializations.some(s => s.specialization_id == specializationId);
                    if (!hasSpecialization) {
                        filtered = [];
                    }
                }
                currentPrograms = filtered;
                currentPage = 1;
                renderPrograms(filtered);
                updateClearFiltersButton();
            });
        return;
    }
    
    // Filter by search term
    if (searchTerm) {
        filtered = filtered.filter(p => 
            p.program_code.toLowerCase().includes(searchTerm) ||
            p.program_name.toLowerCase().includes(searchTerm) ||
            (p.department_name && p.department_name.toLowerCase().includes(searchTerm))
        );
    }
    
    currentPrograms = filtered;
    currentPage = 1;
    renderPrograms(filtered);
    updateClearFiltersButton();
}

function clearAllFilters() {
    const departmentFilter = document.getElementById('filterDepartment');
    const programFilter = document.getElementById('filterProgram');
    const specializationFilter = document.getElementById('filterSpecialization');
    const searchInput = document.getElementById('searchInput');
    
    if (departmentFilter) departmentFilter.value = '';
    if (programFilter) programFilter.value = '';
    if (specializationFilter) {
        specializationFilter.value = '';
        specializationFilter.disabled = true;
    }
    if (searchInput) searchInput.value = '';
    
    currentPrograms = [...allProgramsData];
    currentPage = 1;
    renderPrograms(currentPrograms);
    updateClearFiltersButton();
}

function updateClearFiltersButton() {
    const departmentFilter = document.getElementById('filterDepartment');
    const programFilter = document.getElementById('filterProgram');
    const specializationFilter = document.getElementById('filterSpecialization');
    const searchInput = document.getElementById('searchInput');
    const clearBtn = document.getElementById('clearFiltersBtn');
    
    if (!clearBtn) return;
    
    const hasFilters = 
        (departmentFilter && departmentFilter.value !== '') ||
        (programFilter && programFilter.value !== '') ||
        (specializationFilter && specializationFilter.value !== '') ||
        (searchInput && searchInput.value !== '');
    
    if (hasFilters) {
        clearBtn.classList.add('visible');
    } else {
        clearBtn.classList.remove('visible');
    }
}

function renderPrograms(programs) {
    const tbody = document.getElementById('programsTableBody');
    const emptyState = document.getElementById('emptyState');
    const table = document.getElementById('programsTable');
    const paginationContainer = document.getElementById('paginationContainer');

    if (!tbody) return;

    if (programs.length === 0) {
        tbody.innerHTML = '';
        if (emptyState) emptyState.style.display = 'block';
        if (table) table.style.display = 'none';
        if (paginationContainer) paginationContainer.style.display = 'none';
        return;
    }

    if (emptyState) emptyState.style.display = 'none';
    if (table) table.style.display = 'table';

    // Calculate pagination
    const totalPages = Math.ceil(programs.length / rowsPerPage);
    const startIndex = (currentPage - 1) * rowsPerPage;
    const endIndex = Math.min(startIndex + rowsPerPage, programs.length);
    const paginatedPrograms = programs.slice(startIndex, endIndex);

    tbody.innerHTML = paginatedPrograms.map(program => `
        <tr>
            <td style="font-weight: 500; color: var(--text-dark);">
                ${program.department_name ? escapeHtml(program.department_name) + ' (' + escapeHtml(program.department_code) + ')' : '<span style="color: var(--text-light); font-style: italic;">No department</span>'}
            </td>
            <td>
                <span class="program-code-badge">${escapeHtml(program.program_code)}</span>
            </td>
            <td style="font-weight: 500; color: var(--text-dark);">${escapeHtml(program.program_name)}</td>
            <td>
                <span class="badge badge-primary">
                    <i class="fas fa-cubes"></i> ${program.total_blocks} block${program.total_blocks !== 1 ? 's' : ''}
                </span>
            </td>
            <td style="color: var(--text-gray); font-size: 0.9em;">
                ${program.specialization_names ? escapeHtml(program.specialization_names) : '<span style="color: var(--text-light); font-style: italic;">No specialization</span>'}
            </td>
            <td style="text-align: center;">
                <div class="actions-dropdown">
                    <button class="actions-dropdown-btn" onclick="toggleActionsDropdown(${program.program_id})">
                        <span class="dot"></span>
                        <span class="dot"></span>
                        <span class="dot"></span>
                    </button>
                    <div class="actions-dropdown-menu" id="actionsDropdown-${program.program_id}">
                        <button class="actions-dropdown-item btn-view" onclick="openViewProgramModal(${program.program_id})">
                            <i class="fas fa-eye"></i> View Blocks
                        </button>
                        <button class="actions-dropdown-item btn-edit" onclick="openEditProgramModal(${program.program_id})">
                            <i class="fas fa-edit"></i> Edit Program
                        </button>
                        <button class="actions-dropdown-item btn-delete" onclick="deleteProgram(${program.program_id})">
                            <i class="fas fa-trash-alt"></i> Delete Program
                        </button>
                    </div>
                </div>
            </td>
        </tr>
    `).join('');

    // Update pagination UI
    if (paginationContainer) {
        if (programs.length > 0) {
            paginationContainer.style.display = 'flex';
            updatePaginationUI(programs.length, startIndex, endIndex, totalPages);
        } else {
            paginationContainer.style.display = 'none';
        }
    }
}

function updatePaginationUI(total, start, end, totalPages) {
    const paginationStart = document.getElementById('paginationStart');
    const paginationEnd = document.getElementById('paginationEnd');
    const paginationTotal = document.getElementById('paginationTotal');
    const prevPageBtn = document.getElementById('prevPageBtn');
    const nextPageBtn = document.getElementById('nextPageBtn');
    const pageNumbers = document.getElementById('pageNumbers');

    if (paginationStart) paginationStart.textContent = start + 1;
    if (paginationEnd) paginationEnd.textContent = end;
    if (paginationTotal) paginationTotal.textContent = total;

    if (prevPageBtn) prevPageBtn.disabled = currentPage === 1;
    if (nextPageBtn) nextPageBtn.disabled = currentPage === totalPages;

    // Generate page numbers
    if (pageNumbers) {
        pageNumbers.innerHTML = '';
        const maxVisiblePages = 5;
        let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
        let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);

        if (endPage - startPage + 1 < maxVisiblePages) {
            startPage = Math.max(1, endPage - maxVisiblePages + 1);
        }

        for (let i = startPage; i <= endPage; i++) {
            const pageBtn = document.createElement('button');
            pageBtn.className = 'pagination-btn';
            pageBtn.textContent = i;
            if (i === currentPage) {
                pageBtn.classList.add('active');
            }
            pageBtn.onclick = () => goToPage(i);
            pageNumbers.appendChild(pageBtn);
        }
    }
}

function prevPage() {
    if (currentPage > 1) {
        currentPage--;
        renderPrograms(currentPrograms);
    }
}

function nextPage() {
    const totalPages = Math.ceil(currentPrograms.length / rowsPerPage);
    if (currentPage < totalPages) {
        currentPage++;
        renderPrograms(currentPrograms);
    }
}

function goToPage(page) {
    currentPage = page;
    renderPrograms(currentPrograms);
}

function changeRowsPerPage() {
    const rowsSelect = document.getElementById('rowsPerPage');
    if (rowsSelect) {
        rowsPerPage = parseInt(rowsSelect.value);
        currentPage = 1;
        renderPrograms(currentPrograms);
    }
}

function updateStats(programs) {
    const totalPrograms = programs.length;
    const totalBlocks = programs.reduce((sum, p) => sum + (p.total_blocks || 0), 0);
    
    const totalProgramsEl = document.getElementById('totalPrograms');
    const totalBlocksEl = document.getElementById('totalBlocks');
    
    if (totalProgramsEl) totalProgramsEl.textContent = totalPrograms;
    if (totalBlocksEl) totalBlocksEl.textContent = totalBlocks;
}

function toggleActionsDropdown(programId) {
    // Close all other dropdowns first
    document.querySelectorAll('.actions-dropdown-menu').forEach(menu => {
        if (menu.id !== `actionsDropdown-${programId}`) {
            menu.classList.remove('active');
        }
    });
    
    // Toggle the clicked dropdown
    const dropdown = document.getElementById(`actionsDropdown-${programId}`);
    if (dropdown) {
        dropdown.classList.toggle('active');
    }
}

// Close dropdowns when clicking outside
document.addEventListener('click', function(event) {
    if (!event.target.closest('.actions-dropdown')) {
        document.querySelectorAll('.actions-dropdown-menu').forEach(menu => {
            menu.classList.remove('active');
        });
    }
});

// ============================================
// FILTER EVENT LISTENERS
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    // Department filter change
    const departmentFilter = document.getElementById('filterDepartment');
    if (departmentFilter) {
        departmentFilter.addEventListener('change', applyFilters);
    }
    
    // Program filter change
    const programFilter = document.getElementById('filterProgram');
    if (programFilter) {
        programFilter.addEventListener('change', function() {
            const programId = this.value;
            updateSpecializationFilter(programId);
            applyFilters();
        });
    }
    
    // Specialization filter change
    const specializationFilter = document.getElementById('filterSpecialization');
    if (specializationFilter) {
        specializationFilter.addEventListener('change', applyFilters);
    }
    
    // Search input change (real-time)
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        let debounceTimer;
        searchInput.addEventListener('input', function() {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                applyFilters();
            }, 300);
        });
    }
});

// ============================================
// ADD DEPARTMENT
// ============================================

function openAddDepartmentModal() {
    const form = document.getElementById('addDepartmentForm');
    if (form) form.reset();
    openModal('addDepartmentModal');
}

function submitAddDepartment() {
    const form = document.getElementById('addDepartmentForm');
    if (!form) return;
    
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    if (!data.department_code.trim() || !data.department_name.trim()) {
        showNotification('Please fill in all fields', 'warning');
        return;
    }

    const spinner = document.getElementById('addDepartmentSpinner');
    if (spinner) spinner.style.display = 'inline-block';

    fetch('/api/department/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (spinner) spinner.style.display = 'none';
        if (result.success) {
            showNotification(result.message, 'success');
            closeModal('addDepartmentModal');
            form.reset();
            // Reload page to update department dropdowns
            location.reload();
        } else {
            showNotification(result.message, 'error');
        }
    })
    .catch(error => {
        if (spinner) spinner.style.display = 'none';
        console.error('Error adding department:', error);
        showNotification('Failed to add department', 'error');
    });
}

// ============================================
// ADD PROGRAM
// ============================================

function addSpecializationField() {
    specializationCounter++;
    const container = document.getElementById('specializationsFields');
    if (!container) return;
    
    const card = document.createElement('div');
    card.className = 'specialization-card';
    card.id = `specialization-${specializationCounter}`;
    
    card.innerHTML = `
        <div class="specialization-card-header">
            <span class="specialization-card-title">Specialization #${specializationCounter}</span>
            <button type="button" class="specialization-remove-btn" onclick="removeSpecializationField(${specializationCounter})" title="Remove Specialization">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div class="specialization-inputs">
            <div>
                <label class="form-label" style="font-size: 0.8em; margin-bottom: 4px;">Specialization Name</label>
                <input type="text" class="form-control" name="specialization_name_${specializationCounter}" required maxlength="100" placeholder="e.g., Software Engineering">
            </div>
            <div>
                <label class="form-label" style="font-size: 0.8em; margin-bottom: 4px;">Specialization Code</label>
                <input type="text" class="form-control" name="specialization_code_${specializationCounter}" required maxlength="20" placeholder="e.g., SE">
            </div>
        </div>
    `;
    
    container.appendChild(card);
}

function removeSpecializationField(index) {
    const card = document.getElementById(`specialization-${index}`);
    if (card) {
        card.remove();
    }
}

function collectSpecializations() {
    const container = document.getElementById('specializationsFields');
    if (!container) return [];
    
    const specializations = [];
    const cards = container.querySelectorAll('.specialization-card');
    
    cards.forEach(card => {
        const nameInput = card.querySelector('input[name^="specialization_name_"]');
        const codeInput = card.querySelector('input[name^="specialization_code_"]');
        
        if (nameInput && codeInput) {
            const name = nameInput.value.trim();
            const code = codeInput.value.trim().toUpperCase();
            
            if (name && code) {
                specializations.push({
                    specialization_name: name,
                    specialization_code: code
                });
            }
        }
    });
    
    return specializations;
}

function openAddProgramModal() {
    const form = document.getElementById('addProgramForm');
    if (form) form.reset();
    
    // Clear specialization fields
    const container = document.getElementById('specializationsFields');
    if (container) container.innerHTML = '';
    specializationCounter = 0;
    
    openModal('addProgramModal');
}

function submitAddProgram() {
    const form = document.getElementById('addProgramForm');
    if (!form) return;
    
    const formData = new FormData(form);
    const data = Object.fromEntries(formData.entries());

    if (!data.program_code.trim() || !data.program_name.trim() || !data.department_id) {
        showNotification('Please fill in all fields', 'warning');
        return;
    }

    // Collect specializations
    data.specializations = collectSpecializations();

    const spinner = document.getElementById('addProgramSpinner');
    if (spinner) spinner.style.display = 'inline-block';

    fetch('/program/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (spinner) spinner.style.display = 'none';
        if (result.success) {
            showNotification(result.message, 'success');
            closeModal('addProgramModal');
            form.reset();
            loadPrograms();
        } else {
            showNotification(result.message, 'error');
        }
    })
    .catch(error => {
        if (spinner) spinner.style.display = 'none';
        console.error('Error adding program:', error);
        showNotification('Failed to add program', 'error');
    });
}

// ============================================
// VIEW PROGRAM (WITH BLOCKS)
// ============================================

function openViewProgramModal(programId) {
    currentProgramId = programId;
    
    fetch(`/api/program/${programId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                currentProgramCode = data.program.program_code;
                currentSpecializations = data.specializations || [];
                
                const viewProgramTitle = document.getElementById('viewProgramTitle');
                const viewProgramCode = document.getElementById('viewProgramCode');
                
                if (viewProgramTitle) viewProgramTitle.textContent = escapeHtml(data.program.program_name);
                if (viewProgramCode) viewProgramCode.textContent = escapeHtml(data.program.program_code);
                
                currentBlocks = data.blocks;
                renderBlocks(data.blocks);
                
                // Reset year level tabs
                document.querySelectorAll('.year-tab').forEach(tab => {
                    tab.classList.remove('active');
                    if (tab.dataset.year === '') {
                        tab.classList.add('active');
                    }
                });
                
                openModal('viewProgramModal');
            } else {
                showNotification(data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error loading program details:', error);
            showNotification('Failed to load program details', 'error');
        });
}

function renderBlocks(blocks) {
    const tbody = document.getElementById('blocksTableBody');
    const emptyState = document.getElementById('emptyBlocksState');
    const table = document.getElementById('blocksTable');

    if (!tbody) return;

    if (blocks.length === 0) {
        tbody.innerHTML = '';
        if (emptyState) emptyState.style.display = 'block';
        if (table) table.style.display = 'none';
        return;
    }

    if (emptyState) emptyState.style.display = 'none';
    if (table) table.style.display = 'table';

    tbody.innerHTML = blocks.map(block => `
        <tr data-year-level="${block.year_level}">
            <td style="font-weight: 600; color: var(--primary);">${escapeHtml(block.block_name)}</td>
            <td>${block.year_level}${getYearSuffix(block.year_level)} Year</td>
            <td>
                <span class="badge badge-primary">${escapeHtml(block.section)}</span>
            </td>
            <td style="color: var(--text-light); font-style: italic;">${block.total_students === null ? '-' : block.total_students + ' students'}</td>
            <td style="text-align: center;">
                <button class="action-btn btn-students" onclick="viewBlockStudents(${block.block_id})" title="View Students">
                    <i class="fas fa-user-graduate"></i>
                </button>
                <button class="action-btn btn-edit" onclick="openEditBlockModal(${block.block_id}, '${escapeHtml(block.block_name)}', ${block.year_level})" title="Edit Block">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="action-btn btn-delete" onclick="deleteBlock(${block.block_id})" title="Delete Block">
                    <i class="fas fa-trash-alt"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

function filterBlocksByYearTab(clickedTab) {
    // Update active tab
    document.querySelectorAll('.year-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    clickedTab.classList.add('active');
    
    const yearLevel = clickedTab.dataset.year;
    
    if (!yearLevel) {
        renderBlocks(currentBlocks);
        return;
    }
    
    const filtered = currentBlocks.filter(block => block.year_level.toString() === yearLevel);
    renderBlocks(filtered);
}

function getYearSuffix(year) {
    const suffixes = { 1: 'st', 2: 'nd', 3: 'rd', 4: 'th' };
    return suffixes[year] || 'th';
}

function viewBlockStudents(blockId) {
    showNotification('Student management coming soon!', 'info');
}

// ============================================
// EDIT PROGRAM
// ============================================

function openEditProgramModal(programId) {
    // Fetch program details including specializations
    fetch(`/api/program/${programId}`)
        .then(response => response.json())
        .then(data => {
            if (!data.success) {
                showNotification(data.message, 'error');
                return;
            }

            const program = data.program;
            const specializations = data.specializations || [];

            // Set basic fields
            document.getElementById('editProgramId').value = programId;
            document.getElementById('editProgramCode').value = program.program_code;
            document.getElementById('editProgramName').value = program.program_name;
            document.getElementById('editProgramDepartment').value = program.department_id;

            // Handle specializations
            const container = document.getElementById('editSpecializationsFields');
            const containerWrapper = document.getElementById('editSpecializationsContainer');
            
            container.innerHTML = '';
            editSpecializationCounter = 0;

            if (specializations.length > 0) {
                containerWrapper.style.display = 'block';
                specializations.forEach(spec => {
                    addEditSpecializationField(spec.specialization_id, spec.specialization_name, spec.specialization_code);
                });
            } else {
                containerWrapper.style.display = 'none';
            }

            openModal('editProgramModal');
        })
        .catch(error => {
            console.error('Error loading program for edit:', error);
            showNotification('Failed to load program details', 'error');
        });
}

function addEditSpecializationField(specializationId = null, name = '', code = '') {
    editSpecializationCounter++;
    const container = document.getElementById('editSpecializationsFields');
    if (!container) return;
    
    const card = document.createElement('div');
    card.className = 'specialization-card';
    card.id = `edit-specialization-${editSpecializationCounter}`;
    
    const idInput = specializationId 
        ? `<input type="hidden" name="edit_specialization_id_${editSpecializationCounter}" value="${specializationId}">`
        : '';
    
    card.innerHTML = `
        ${idInput}
        <div class="specialization-card-header">
            <span class="specialization-card-title">Specialization #${editSpecializationCounter}</span>
            <button type="button" class="specialization-remove-btn" onclick="removeEditSpecializationField(${editSpecializationCounter})" title="Remove Specialization">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div class="specialization-inputs">
            <div>
                <label class="form-label" style="font-size: 0.8em; margin-bottom: 4px;">Specialization Name</label>
                <input type="text" class="form-control" name="edit_specialization_name_${editSpecializationCounter}" required maxlength="100" placeholder="e.g., Software Engineering" value="${escapeHtml(name)}">
            </div>
            <div>
                <label class="form-label" style="font-size: 0.8em; margin-bottom: 4px;">Specialization Code</label>
                <input type="text" class="form-control" name="edit_specialization_code_${editSpecializationCounter}" required maxlength="20" placeholder="e.g., SE" value="${escapeHtml(code)}">
            </div>
        </div>
    `;
    
    container.appendChild(card);
}

function removeEditSpecializationField(index) {
    const card = document.getElementById(`edit-specialization-${index}`);
    if (card) {
        card.remove();
    }
}

function collectEditSpecializations() {
    const container = document.getElementById('editSpecializationsFields');
    if (!container) return [];
    
    const specializations = [];
    const cards = container.querySelectorAll('.specialization-card');
    
    cards.forEach(card => {
        const idInput = card.querySelector('input[name^="edit_specialization_id_"]');
        const nameInput = card.querySelector('input[name^="edit_specialization_name_"]');
        const codeInput = card.querySelector('input[name^="edit_specialization_code_"]');
        
        if (nameInput && codeInput) {
            const spec = {
                specialization_name: nameInput.value.trim(),
                specialization_code: codeInput.value.trim().toUpperCase()
            };
            
            if (idInput && idInput.value) {
                spec.specialization_id = parseInt(idInput.value);
            }
            
            if (spec.specialization_name && spec.specialization_code) {
                specializations.push(spec);
            }
        }
    });
    
    return specializations;
}

function submitEditProgram() {
    const programId = document.getElementById('editProgramId');
    const editProgramCode = document.getElementById('editProgramCode');
    const editProgramName = document.getElementById('editProgramName');
    const editProgramDepartment = document.getElementById('editProgramDepartment');
    
    if (!programId || !editProgramCode || !editProgramName || !editProgramDepartment) return;
    
    const code = editProgramCode.value.trim();
    const name = editProgramName.value.trim();
    const departmentId = editProgramDepartment.value;

    if (!code || !name || !departmentId) {
        showNotification('Please fill in all fields', 'warning');
        return;
    }

    const data = {
        program_code: code,
        program_name: name,
        department_id: departmentId
    };

    // Add specializations if visible
    const containerWrapper = document.getElementById('editSpecializationsContainer');
    if (containerWrapper && containerWrapper.style.display !== 'none') {
        data.specializations = collectEditSpecializations();
    } else {
        data.specializations = [];
    }

    const spinner = document.getElementById('editProgramSpinner');
    if (spinner) spinner.style.display = 'inline-block';

    fetch(`/program/edit/${programId.value}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (spinner) spinner.style.display = 'none';
        if (result.success) {
            showNotification(result.message, 'success');
            closeModal('editProgramModal');
            loadPrograms();
        } else {
            showNotification(result.message, 'error');
        }
    })
    .catch(error => {
        if (spinner) spinner.style.display = 'none';
        console.error('Error updating program:', error);
        showNotification('Failed to update program', 'error');
    });
}

// ============================================
// DELETE PROGRAM
// ============================================

function deleteProgram(programId) {
    if (!confirm('Are you sure you want to delete this program? This will also delete all associated blocks and specializations. This action cannot be undone.')) {
        return;
    }

    fetch(`/program/delete/${programId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            showNotification(result.message, 'success');
            loadPrograms();
        } else {
            showNotification(result.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error deleting program:', error);
        showNotification('Failed to delete program', 'error');
    });
}

// ============================================
// ADD BLOCK
// ============================================

function openAddBlockModal() {
    if (!currentProgramId) return;
    
    const addBlockForm = document.getElementById('addBlockForm');
    const addBlockProgramId = document.getElementById('addBlockProgramId');
    const nextSectionDisplay = document.getElementById('nextSectionDisplay');
    const blockNamePreview = document.getElementById('blockNamePreview');
    const addBlockYearLevel = document.getElementById('addBlockYearLevel');
    
    if (addBlockForm) addBlockForm.reset();
    if (addBlockProgramId) addBlockProgramId.value = currentProgramId;
    if (nextSectionDisplay) nextSectionDisplay.value = '';
    if (blockNamePreview) blockNamePreview.value = '';
    if (addBlockYearLevel) addBlockYearLevel.value = '';
    
    openModal('addBlockModal');
}


function updateBlockPreview() {
    const yearLevel = document.getElementById('addBlockYearLevel');
    const nextSectionDisplay = document.getElementById('nextSectionDisplay');
    const blockNamePreview = document.getElementById('blockNamePreview');
    
    if (!yearLevel || !currentProgramId || !yearLevel.value) {
        if (nextSectionDisplay) nextSectionDisplay.value = '';
        if (blockNamePreview) blockNamePreview.value = '';
        return;
    }

    // Calculate next section based on current blocks
    const yearBlocks = currentBlocks.filter(b => b.year_level.toString() === yearLevel.value);
    let nextSection = 'A';
    
    if (yearBlocks.length > 0) {
        const sections = yearBlocks.map(b => b.section).sort();
        const lastSection = sections[sections.length - 1];
        nextSection = String.fromCharCode(lastSection.charCodeAt(0) + 1);
    }
    
    if (currentSpecializations && currentSpecializations.length > 0) {
        // Show preview for all specializations that will be created
        const previews = currentSpecializations.map((spec, index) => {
            const section = String.fromCharCode(nextSection.charCodeAt(0) + index);
            const name = `${currentProgramCode}-${spec.specialization_code}${yearLevel.value}${section}`;
            return `${spec.specialization_name}: ${name}`;
        }).join(' | ');
        if (blockNamePreview) blockNamePreview.value = previews;
        if (nextSectionDisplay) nextSectionDisplay.value = nextSection;
    } else {
        const blockName = `${currentProgramCode}${yearLevel.value}${nextSection}`;
        if (blockNamePreview) blockNamePreview.value = blockName;
        if (nextSectionDisplay) nextSectionDisplay.value = nextSection;
    }
}


async function submitAddBlock() {
    const programId = document.getElementById('addBlockProgramId');
    const yearLevel = document.getElementById('addBlockYearLevel');
    
    if (!programId || !yearLevel) return;

    if (!yearLevel.value) {
        showNotification('Please select a year level', 'warning');
        return;
    }

    const spinner = document.getElementById('addBlockSpinner');
    if (spinner) spinner.style.display = 'inline-block';

    // If program has specializations, create a block for each sequentially
    if (currentSpecializations && currentSpecializations.length > 0) {
        const results = [];
        for (const spec of currentSpecializations) {
            const data = {
                program_id: programId.value,
                year_level: yearLevel.value,
                specialization_id: spec.specialization_id
            };
            try {
                const response = await fetch('/block/add', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                const result = await response.json();
                results.push(result);
                if (!result.success) break;
            } catch (error) {
                results.push({ success: false, message: error.message });
                break;
            }
        }

        if (spinner) spinner.style.display = 'none';
        
        const allSuccess = results.every(r => r.success);
        if (allSuccess) {
            showNotification(`Created ${results.length} block(s) successfully`, 'success');
            closeModal('addBlockModal');
            openViewProgramModal(currentProgramId);
            loadPrograms();
        } else {
            const failed = results.find(r => !r.success);
            showNotification(failed ? failed.message : 'Some blocks failed to create', 'error');
            openViewProgramModal(currentProgramId);
            loadPrograms();
        }
    } else {
        // No specializations - create single block
        const data = {
            program_id: programId.value,
            year_level: yearLevel.value
        };

        fetch('/block/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(result => {
            if (spinner) spinner.style.display = 'none';
            if (result.success) {
                showNotification(result.message, 'success');
                closeModal('addBlockModal');
                openViewProgramModal(currentProgramId);
                loadPrograms();
            } else {
                showNotification(result.message, 'error');
            }
        })
        .catch(error => {
            if (spinner) spinner.style.display = 'none';
            console.error('Error adding block:', error);
            showNotification('Failed to add block', 'error');
        });
    }
}


// ============================================
// EDIT BLOCK
// ============================================

function openEditBlockModal(blockId, blockName, yearLevel) {
    const editBlockId = document.getElementById('editBlockId');
    const editBlockName = document.getElementById('editBlockName');
    const editBlockYearLevel = document.getElementById('editBlockYearLevel');
    
    if (editBlockId) editBlockId.value = blockId;
    if (editBlockName) editBlockName.value = blockName;
    if (editBlockYearLevel) editBlockYearLevel.value = yearLevel;
    
    openModal('editBlockModal');
}

function submitEditBlock() {
    const blockId = document.getElementById('editBlockId');
    const yearLevel = document.getElementById('editBlockYearLevel');
    
    if (!blockId || !yearLevel) return;

    const spinner = document.getElementById('editBlockSpinner');
    if (spinner) spinner.style.display = 'inline-block';

    fetch(`/block/edit/${blockId.value}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ year_level: yearLevel.value })
    })
    .then(response => response.json())
    .then(result => {
        if (spinner) spinner.style.display = 'none';
        if (result.success) {
            showNotification(result.message, 'success');
            closeModal('editBlockModal');
            
            // Refresh the view program modal
            if (currentProgramId) {
                openViewProgramModal(currentProgramId);
            }
            
            // Refresh programs list
            loadPrograms();
        } else {
            showNotification(result.message, 'error');
        }
    })
    .catch(error => {
        if (spinner) spinner.style.display = 'none';
        console.error('Error updating block:', error);
        showNotification('Failed to update block', 'error');
    });
}

// ============================================
// DELETE BLOCK
// ============================================

function deleteBlock(blockId) {
    if (!confirm('Are you sure you want to delete this block? This action cannot be undone.')) {
        return;
    }

    fetch(`/block/delete/${blockId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            showNotification(result.message, 'success');
            
            // Refresh the view program modal
            if (currentProgramId) {
                openViewProgramModal(currentProgramId);
            }
            
            // Refresh programs list
            loadPrograms();
        } else {
            showNotification(result.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error deleting block:', error);
        showNotification('Failed to delete block', 'error');
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
    // Remove existing notifications
    document.querySelectorAll('.custom-notification').forEach(n => n.remove());
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = 'custom-notification';
    notification.style.cssText = `
        position: fixed;
        top: 24px;
        right: 24px;
        padding: 16px 24px;
        border-radius: 12px;
        color: white;
        font-weight: 500;
        z-index: 9999;
        box-shadow: 0 8px 24px rgba(0,0,0,0.15);
        max-width: 400px;
        word-wrap: break-word;
        display: flex;
        align-items: center;
        gap: 12px;
        animation: slideInRight 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    `;
    
    const colors = {
        success: '#22c55e',
        error: '#ff6b6b',
        warning: '#fb923c',
        info: '#3b82f6'
    };
    
    const icons = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };
    
    notification.style.backgroundColor = colors[type] || colors.info;
    notification.innerHTML = `
        <i class="fas ${icons[type] || icons.info}" style="font-size: 1.2em;"></i>
        <span>${escapeHtml(message)}</span>
    `;
    
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.4s cubic-bezier(0.4, 0, 0.2, 1) forwards';
        setTimeout(() => notification.remove(), 400);
    }, 3000);
}

// Add animation styles
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOutRight {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);
