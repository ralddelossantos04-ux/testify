// ============================================
// SUBJECTS MANAGEMENT MODULE
// ============================================

let allSubjects=[];
let filteredSubjects=[];
let currentPage=1;
const itemsPerPage=10;
let allSpecializations=[];
let programSpecializations={};

// ============================================
// CUSTOM MODAL SYSTEM
// ============================================

function openModal(modalId){
    const modal=document.getElementById(modalId);
    const backdrop=document.getElementById('modalBackdrop');
    if(modal&&backdrop){
        closeAllModals();
        backdrop.classList.add('active');
        modal.classList.add('active');
        document.body.style.overflow='hidden';
    }
}

function closeModal(modalId){
    const modal=document.getElementById(modalId);
    const backdrop=document.getElementById('modalBackdrop');
    if(modal)modal.classList.remove('active');
    const anyModalOpen=document.querySelector('.modal.active');
    if(!anyModalOpen&&backdrop){
        backdrop.classList.remove('active');
        document.body.style.overflow='';
    }
}

function closeAllModals(){
    document.querySelectorAll('.modal.active').forEach(m=>m.classList.remove('active'));
    const backdrop=document.getElementById('modalBackdrop');
    if(backdrop)backdrop.classList.remove('active');
    document.body.style.overflow='';
}

document.addEventListener('keydown',function(e){
    if(e.key==='Escape')closeAllModals();
});

// ============================================
// LOADING STATES
// ============================================

function showSkeleton(){
    const skeleton=document.getElementById('skeletonLoader');
    const table=document.getElementById('tableContainer');
    const cards=document.getElementById('cardGridContainer');
    const empty=document.getElementById('emptyState');
    const pagination=document.getElementById('paginationContainer');
    if(skeleton)skeleton.style.display='block';
    if(table)table.style.display='none';
    if(cards)cards.style.display='none';
    if(empty)empty.style.display='none';
    if(pagination)pagination.style.display='none';
}

function hideSkeleton(){
    const skeleton=document.getElementById('skeletonLoader');
    if(skeleton)skeleton.style.display='none';
}

// ============================================
// STATS
// ============================================

function updateStats(){
    const totalSubjects=allSubjects.length;
    const uniquePrograms=new Set(allSubjects.map(s=>s.program_id)).size;
    const uniqueYears=new Set(allSubjects.map(s=>s.year_level)).size;
    const totalFiltered=filteredSubjects.length;

    const statTotal=document.getElementById('statTotalSubjects');
    const statPrograms=document.getElementById('statTotalPrograms');
    const statYears=document.getElementById('statYearLevels');

    if(statTotal)statTotal.textContent=totalSubjects;
    if(statPrograms)statPrograms.textContent=uniquePrograms;
    if(statYears)statYears.textContent=uniqueYears||4;

    const resultCount=document.getElementById('resultCount');
    if(resultCount){
        resultCount.textContent=totalFiltered+' subject'+(totalFiltered!==1?'s':'');
        resultCount.style.display=totalFiltered>0?'inline-flex':'none';
    }
}

// ============================================
// SPECIALIZATION HELPERS
// ============================================

function loadAllSpecializations(){
    fetch('/api/programs')
        .then(r=>r.json())
        .then(data=>{
            if(data.success){
                allSpecializations=[];
                programSpecializations={};
                data.programs.forEach(program=>{
                    if(program.specialization_names){
                        // We need to fetch specializations per program
                    }
                });
                // Fetch all specializations directly
                return fetch('/api/all-specializations');
            }
        })
        .then(r=>{
            if(r)return r.json();
            return {success:true, specializations:[]};
        })
        .then(data=>{
            if(data.success){
                allSpecializations=data.specializations||[];
                allSpecializations.forEach(spec=>{
                    if(!programSpecializations[spec.program_id]){
                        programSpecializations[spec.program_id]=[];
                    }
                    programSpecializations[spec.program_id].push(spec);
                });
            }
        })
        .catch(error=>{
            console.error('Error loading specializations:',error);
        });
}

function populateSpecializationSelect(programId, selectId, groupId){
    const select=document.getElementById(selectId);
    const group=document.getElementById(groupId);
    if(!select||!group)return;

    const specs=programSpecializations[programId]||[];
    select.innerHTML='<option value="">No Specialization</option>';
    
    if(specs.length>0){
        specs.forEach(spec=>{
            select.innerHTML+=`<option value="${spec.specialization_id}">${spec.specialization_code} - ${spec.specialization_name}</option>`;
        });
        group.style.display='block';
    }else{
        group.style.display='none';
    }
}

function updateSpecializationFilter(programId){
    const specFilter=document.getElementById('specializationFilter');
    if(!specFilter)return;

    const specs=programSpecializations[programId]||[];
    specFilter.innerHTML='<option value="">All Specializations</option>';
    
    if(specs.length>0&&programId){
        specs.forEach(spec=>{
            specFilter.innerHTML+=`<option value="${spec.specialization_id}">${spec.specialization_code}</option>`;
        });
        specFilter.disabled=false;
    }else{
        specFilter.disabled=true;
    }
}

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded',function(){
    showSkeleton();
    loadAllSpecializations();
    loadSubjects();

    const programFilter=document.getElementById('programFilter');
    const yearFilter=document.getElementById('yearFilter');
    const specializationFilter=document.getElementById('specializationFilter');
    const searchInput=document.getElementById('searchInput');

    if(programFilter){
        programFilter.addEventListener('change',function(){
            updateSpecializationFilter(this.value);
            applyFilters();
        });
    }
    if(yearFilter)yearFilter.addEventListener('change',applyFilters);
    if(specializationFilter)specializationFilter.addEventListener('change',applyFilters);
    if(searchInput){
        let searchTimeout;
        searchInput.addEventListener('input',function(){
            clearTimeout(searchTimeout);
            searchTimeout=setTimeout(()=>applyFilters(),300);
        });
    }

    // Add modal event listeners
    const addProgram=document.getElementById('addSubjectProgram');
    const editProgram=document.getElementById('editSubjectProgram');
    if(addProgram){
        addProgram.addEventListener('change',function(){
            populateSpecializationSelect(this.value,'addSubjectSpecialization','addSpecializationGroup');
        });
    }
    if(editProgram){
        editProgram.addEventListener('change',function(){
            populateSpecializationSelect(this.value,'editSubjectSpecialization','editSpecializationGroup');
        });
    }
});

// ============================================
// DATA LOADING
// ============================================

function loadSubjects(){
    fetch('/admin/subjects/list')
        .then(r=>r.json())
        .then(data=>{
            hideSkeleton();
            if(data.success){
                allSubjects=data.subjects;
                applyFilters();
            }else{
                showNotification(data.message,'error');
            }
        })
        .catch(error=>{
            hideSkeleton();
            console.error('Error loading subjects:',error);
            showNotification('Failed to load subjects','error');
        });
}

// ============================================
// FILTERING
// ============================================

function applyFilters(){
    const programFilter=document.getElementById('programFilter');
    const yearFilter=document.getElementById('yearFilter');
    const specializationFilter=document.getElementById('specializationFilter');
    const searchInput=document.getElementById('searchInput');
    const clearBtn=document.getElementById('clearFiltersBtn');

    const programId=programFilter?programFilter.value:'';
    const yearLevel=yearFilter?yearFilter.value:'';
    const specializationId=specializationFilter?specializationFilter.value:'';
    const search=searchInput?searchInput.value.trim().toLowerCase():'';

    filteredSubjects=allSubjects.filter(subject=>{
        const matchProgram=!programId||subject.program_id.toString()===programId;
        const matchYear=!yearLevel||subject.year_level.toString()===yearLevel;
        const matchSpecialization=!specializationId||(subject.specialization_id&&subject.specialization_id.toString()===specializationId);
        const matchSearch=!search||
            subject.subject_code.toLowerCase().includes(search)||
            subject.subject_name.toLowerCase().includes(search);
        return matchProgram&&matchYear&&matchSpecialization&&matchSearch;
    });

    if(clearBtn){
        const hasFilters=programId||yearLevel||specializationId||search;
        clearBtn.classList.toggle('hidden',!hasFilters);
    }

    currentPage=1;
    updateStats();
    renderSubjects();
    updatePagination();
}

function clearFilters(){
    const programFilter=document.getElementById('programFilter');
    const yearFilter=document.getElementById('yearFilter');
    const specializationFilter=document.getElementById('specializationFilter');
    const searchInput=document.getElementById('searchInput');

    if(programFilter){
        programFilter.value='';
        updateSpecializationFilter('');
    }
    if(yearFilter)yearFilter.value='';
    if(specializationFilter){
        specializationFilter.value='';
        specializationFilter.disabled=true;
    }
    if(searchInput)searchInput.value='';

    applyFilters();
}

// ============================================
// TABLE & CARD RENDERING
// ============================================

function renderSubjects(){
    const tbody=document.getElementById('subjectsTableBody');
    const cardGrid=document.getElementById('cardGridContainer');
    const emptyState=document.getElementById('emptyState');
    const tableContainer=document.getElementById('tableContainer');

    if(!tbody&&!cardGrid)return;

    if(filteredSubjects.length===0){
        if(tbody)tbody.innerHTML='';
        if(cardGrid)cardGrid.innerHTML='';
        if(emptyState)emptyState.style.display='block';
        if(tableContainer)tableContainer.style.display='none';
        return;
    }

    if(emptyState)emptyState.style.display='none';
    if(tableContainer)tableContainer.style.display='block';

    const start=(currentPage-1)*itemsPerPage;
    const end=start+itemsPerPage;
    const pageSubjects=filteredSubjects.slice(start,end);

    // Render desktop table
    if(tbody){
        tbody.innerHTML=pageSubjects.map(subject=>`
            <tr>
                <td><span class="subject-code">${escapeHtml(subject.subject_code)}</span></td>
                <td class="subject-name">${escapeHtml(subject.subject_name)}</td>
                <td><span class="badge badge-primary">${escapeHtml(subject.program_code)}</span></td>
                <td>${subject.year_level}${getYearSuffix(subject.year_level)} Year</td>
                <td>${escapeHtml(subject.specialization_code||'-')}</td>
                <td style="text-align:center">
                    <button class="action-btn btn-edit" onclick="openEditSubjectModal(${subject.subject_id})" title="Edit"><i class="fas fa-edit"></i></button>
                    <button class="action-btn btn-delete" onclick="deleteSubject(${subject.subject_id})" title="Delete"><i class="fas fa-trash-alt"></i></button>
                </td>
            </tr>
        `).join('');
    }

    // Render mobile cards
    if(cardGrid){
        cardGrid.innerHTML=pageSubjects.map(subject=>`
            <div class="subject-card">
                <div class="subject-card-header">
                    <span class="subject-card-code">${escapeHtml(subject.subject_code)}</span>
                    <span class="badge badge-primary">${escapeHtml(subject.program_code)}</span>
                </div>
                <div class="subject-card-name">${escapeHtml(subject.subject_name)}</div>
                <div class="subject-card-meta">
                    <span class="badge badge-success">${subject.year_level}${getYearSuffix(subject.year_level)} Year</span>
                    ${subject.specialization_code?`<span class="badge badge-info">${escapeHtml(subject.specialization_code)}</span>`:''}
                </div>
                <div class="subject-card-actions">
                    <button class="action-btn btn-edit" onclick="openEditSubjectModal(${subject.subject_id})" title="Edit"><i class="fas fa-edit"></i></button>
                    <button class="action-btn btn-delete" onclick="deleteSubject(${subject.subject_id})" title="Delete"><i class="fas fa-trash-alt"></i></button>
                </div>
            </div>
        `).join('');
    }
}

function getYearSuffix(year){
    const suffixes={1:'st',2:'nd',3:'rd',4:'th'};
    return suffixes[year]||'th';
}

// ============================================
// PAGINATION
// ============================================

function updatePagination(){
    const totalPages=Math.ceil(filteredSubjects.length/itemsPerPage)||1;
    const prevBtn=document.getElementById('prevBtn');
    const nextBtn=document.getElementById('nextBtn');
    const paginationInfo=document.getElementById('paginationInfo');
    const paginationContainer=document.getElementById('paginationContainer');

    if(paginationContainer)paginationContainer.style.display=filteredSubjects.length>0?'flex':'none';
    if(prevBtn)prevBtn.disabled=currentPage<=1;
    if(nextBtn)nextBtn.disabled=currentPage>=totalPages;
    if(paginationInfo)paginationInfo.textContent=`Page ${currentPage} of ${totalPages}`;
}

function changePage(direction){
    const totalPages=Math.ceil(filteredSubjects.length/itemsPerPage)||1;
    const newPage=currentPage+direction;
    if(newPage>=1&&newPage<=totalPages){
        currentPage=newPage;
        renderSubjects();
        updatePagination();
    }
}

// ============================================
// ADD SUBJECT
// ============================================

function openAddSubjectModal(){
    const form=document.getElementById('addSubjectForm');
    if(form)form.reset();
    const specGroup=document.getElementById('addSpecializationGroup');
    if(specGroup)specGroup.style.display='none';
    openModal('addSubjectModal');
}

function submitAddSubject(){
    const form=document.getElementById('addSubjectForm');
    if(!form)return;
    const formData=new FormData(form);
    const data=Object.fromEntries(formData.entries());

    if(!data.subject_code.trim()||!data.subject_name.trim()||!data.program_id||!data.year_level){
        showNotification('Please fill in all fields','warning');
        return;
    }

    // Handle specialization_id - send null if empty
    if(!data.specialization_id){
        data.specialization_id=null;
    }

    const spinner=document.getElementById('addSubjectSpinner');
    if(spinner)spinner.style.display='inline-block';

    fetch('/admin/subjects/add',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify(data)
    })
    .then(r=>r.json())
    .then(result=>{
        if(spinner)spinner.style.display='none';
        if(result.success){
            showNotification(result.message,'success');
            closeModal('addSubjectModal');
            form.reset();
            loadSubjects();
        }else{
            showNotification(result.message,'error');
        }
    })
    .catch(error=>{
        if(spinner)spinner.style.display='none';
        console.error('Error adding subject:',error);
        showNotification('Failed to add subject','error');
    });
}

// ============================================
// EDIT SUBJECT
// ============================================

function openEditSubjectModal(subjectId){
    const subject=allSubjects.find(s=>s.subject_id===subjectId);
    if(!subject){
        showNotification('Subject not found','error');
        return;
    }
    document.getElementById('editSubjectId').value=subject.subject_id;
    document.getElementById('editSubjectCode').value=subject.subject_code;
    document.getElementById('editSubjectName').value=subject.subject_name;
    document.getElementById('editSubjectProgram').value=subject.program_id;
    
    // Populate and show specialization dropdown
    populateSpecializationSelect(subject.program_id,'editSubjectSpecialization','editSpecializationGroup');
    
    document.getElementById('editSubjectSpecialization').value=subject.specialization_id||'';
    document.getElementById('editSubjectYearLevel').value=subject.year_level;
    openModal('editSubjectModal');
}

function submitEditSubject(){
    const subjectId=document.getElementById('editSubjectId');
    const code=document.getElementById('editSubjectCode');
    const name=document.getElementById('editSubjectName');
    const program=document.getElementById('editSubjectProgram');
    const year=document.getElementById('editSubjectYearLevel');
    const specialization=document.getElementById('editSubjectSpecialization');

    if(!subjectId||!code||!name||!program||!year)return;
    const c=code.value.trim(),n=name.value.trim(),p=program.value,y=year.value;
    const spec=specialization?specialization.value:null;
    
    if(!c||!n||!p||!y){
        showNotification('Please fill in all fields','warning');
        return;
    }

    const spinner=document.getElementById('editSubjectSpinner');
    if(spinner)spinner.style.display='inline-block';

    fetch(`/admin/subjects/edit/${subjectId.value}`,{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({subject_code:c,subject_name:n,program_id:p,year_level:y,specialization_id:spec||null})
    })
    .then(r=>r.json())
    .then(result=>{
        if(spinner)spinner.style.display='none';
        if(result.success){
            showNotification(result.message,'success');
            closeModal('editSubjectModal');
            loadSubjects();
        }else{
            showNotification(result.message,'error');
        }
    })
    .catch(error=>{
        if(spinner)spinner.style.display='none';
        console.error('Error updating subject:',error);
        showNotification('Failed to update subject','error');
    });
}

// ============================================
// DELETE SUBJECT
// ============================================

function deleteSubject(subjectId){
    if(!confirm('Are you sure you want to delete this subject? This action cannot be undone.'))return;
    fetch(`/admin/subjects/delete/${subjectId}`,{
        method:'POST',
        headers:{'Content-Type':'application/json'}
    })
    .then(r=>r.json())
    .then(result=>{
        if(result.success){
            showNotification(result.message,'success');
            loadSubjects();
        }else{
            showNotification(result.message,'error');
        }
    })
    .catch(error=>{
        console.error('Error deleting subject:',error);
        showNotification('Failed to delete subject','error');
    });
}

// ============================================
// UTILITY FUNCTIONS
// ============================================

function escapeHtml(text){
    if(!text)return'';
    const div=document.createElement('div');
    div.textContent=text;
    return div.innerHTML;
}

function showNotification(message,type='info'){
    document.querySelectorAll('.custom-notification').forEach(n=>n.remove());
    const notification=document.createElement('div');
    notification.className='custom-notification';
    notification.style.cssText='position:fixed;top:24px;right:24px;padding:16px 24px;border-radius:12px;color:white;font-weight:500;z-index:9999;box-shadow:0 8px 24px rgba(0,0,0,0.15);max-width:400px;word-wrap:break-word;display:flex;align-items:center;gap:12px;animation:slideInRight 0.4s cubic-bezier(0.4,0,0.2,1)';
    const colors={success:'#22c55e',error:'#ff6b6b',warning:'#fb923c',info:'#3b82f6'};
    const icons={success:'fa-check-circle',error:'fa-exclamation-circle',warning:'fa-exclamation-triangle',info:'fa-info-circle'};
    notification.style.backgroundColor=colors[type]||colors.info;
    notification.innerHTML=`<i class="fas ${icons[type]||icons.info}" style="font-size:1.2em"></i><span>${escapeHtml(message)}</span>`;
    document.body.appendChild(notification);
    setTimeout(()=>{
        notification.style.animation='slideOutRight 0.4s cubic-bezier(0.4,0,0.2,1) forwards';
        setTimeout(()=>notification.remove(),400);
    },3000);
}

const style=document.createElement('style');
style.textContent='@keyframes slideInRight{from{transform:translateX(100%);opacity:0}to{transform:translateX(0);opacity:1}}@keyframes slideOutRight{from{transform:translateX(0);opacity:1}to{transform:translateX(100%);opacity:0}}';
document.head.appendChild(style);
