(function(){
'use strict';
let allAssignments=[],allTeachers=[],allBlocks=[],selectedTeacherId=null,multipleMode=false,assignTarget=null;
const checkedItems=new Map();
const $=id=>document.getElementById(id);
const filterProgram=$('filterProgram'),filterSpec=$('filterSpecialization'),specWrap=$('specFilterWrap'),
filterYear=$('filterYearLevel'),filterSection=$('filterSection'),
blockInput=$('blockSearchInput'),blockAC=$('blockAutocomplete'),
card=$('assignmentsCard'),initial=$('initialState'),tblWrap=$('tableContainer'),
skeleton=$('skeletonLoader'),empty=$('emptyState'),tbody=$('assignmentsTableBody'),
countBadge=$('assignmentCount'),cardTitle=$('assignmentsCardTitle'),
cbHeader=$('checkboxHeader'),selAll=$('selectAllCheckbox'),
paLeft=$('pageActionsLeft'),paRight=$('pageActionsRight'),
backdrop=$('modalBackdrop'),assignModal=$('assignTeacherModal'),
assignSub=$('assignModalSubtitle'),tSearch=$('teacherSearchInput'),
tDept=$('teacherDeptFilter'),tBody=$('teacherModalTableBody'),btnConfirm=$('btnConfirmAssign'),
vcModal=$('viewCheckedModal'),vcSub=$('viewCheckedSubtitle'),vcList=$('checkedListBody'),vcEmpty=$('checkedEmptyState');

document.addEventListener('DOMContentLoaded',()=>{loadPrograms();loadAllBlocks();bindFilters();bindModal();$('btnMultipleAssign').addEventListener('click',toggleMulti);});

// ── GLOBAL BLOCK SEARCH ──
function loadAllBlocks(){
  fetch('/admin/get-all-blocks').then(r=>r.json()).then(d=>{if(d.success)allBlocks=d.blocks||[];}).catch(()=>{});
}
blockInput.addEventListener('input',function(){
  const q=this.value.trim().toLowerCase();
  if(!q){blockAC.classList.remove('visible');return;}
  const m=allBlocks.filter(b=>b.block_name.toLowerCase().includes(q)).slice(0,12);
  blockAC.innerHTML='';
  if(!m.length){blockAC.innerHTML='<div class="block-ac-empty">No blocks match</div>';blockAC.classList.add('visible');return;}
  m.forEach(b=>{
    const d=document.createElement('div');d.className='block-ac-item';
    d.innerHTML='<span class="block-ac-name">'+esc(b.block_name)+'</span><span class="block-ac-program">'+esc(b.program_code)+' &middot; Year '+b.year_level+'</span>';
    d.addEventListener('click',()=>selectBlock(b));
    blockAC.appendChild(d);
  });
  blockAC.classList.add('visible');
});
blockInput.addEventListener('blur',()=>{setTimeout(()=>blockAC.classList.remove('visible'),200);});
blockInput.addEventListener('keydown',function(e){if(e.key==='Escape')blockAC.classList.remove('visible');});
document.addEventListener('click',e=>{if(!e.target.closest('.block-search-field'))blockAC.classList.remove('visible');});

function selectBlock(b){
  blockAC.classList.remove('visible');blockInput.value=b.block_name;
  // auto-fill filters
  filterProgram.value=b.program_id;onProgramChange(()=>{
    filterYear.value=String(b.year_level);filterYear.disabled=false;
    loadSections(()=>{filterSection.value=b.block_id;onSectionChange();});
  });
}

// ── FILTERS ──
function loadPrograms(){
  fetch('/api/programs').then(r=>r.json()).then(d=>{
    if(!d.success)return;filterProgram.innerHTML='<option value="">Select Program</option>';
    d.programs.forEach(p=>{const o=document.createElement('option');o.value=p.program_id;o.textContent=p.program_code+' \u2014 '+p.program_name;filterProgram.appendChild(o);});
  }).catch(()=>toast('Failed to load programs','error'));
}
function bindFilters(){filterProgram.addEventListener('change',()=>onProgramChange());filterSpec.addEventListener('change',()=>{if(filterYear.value)loadSections();});filterYear.addEventListener('change',onYearChange);filterSection.addEventListener('change',onSectionChange);}
function onProgramChange(cb){
  const pid=filterProgram.value;
  filterSpec.innerHTML='<option value="">Select Specialization</option>';specWrap.style.display='none';
  filterYear.value='';filterYear.disabled=!pid;resetSection();hideTable();
  if(!pid){if(cb)cb();return;}
  fetch('/api/program/'+pid).then(r=>r.json()).then(d=>{
    if(!d.success)return;
    if(d.specializations&&d.specializations.length){specWrap.style.display='';filterSpec.innerHTML='<option value="">All Specializations</option>';d.specializations.forEach(s=>{const o=document.createElement('option');o.value=s.specialization_id;o.textContent=s.specialization_code+' \u2014 '+s.specialization_name;filterSpec.appendChild(o);});}
    if(cb)cb();
  });
}
function onYearChange(){resetSection();hideTable();if(filterProgram.value&&filterYear.value)loadSections();}
function resetSection(){filterSection.innerHTML='<option value="">Select Section</option>';filterSection.disabled=true;}
function loadSections(cb){
  const pid=filterProgram.value,yl=filterYear.value;if(!pid||!yl){if(cb)cb();return;}
  fetch('/api/program/'+pid).then(r=>r.json()).then(d=>{
    if(!d.success)return;const blocks=d.blocks.filter(b=>String(b.year_level)===String(yl));
    filterSection.innerHTML='<option value="">Select Section</option>';
    blocks.forEach(b=>{const o=document.createElement('option');o.value=b.block_id;o.textContent=b.section+' \u2014 '+b.block_name;filterSection.appendChild(o);});
    filterSection.disabled=!blocks.length;if(cb)cb();
  });
}
function onSectionChange(){filterSection.value?loadAssignments():hideTable();}
function hideTable(){card.style.display='none';initial.style.display='';}

// ── ASSIGNMENTS ──
function loadAssignments(){
  const pid=filterProgram.value,yl=filterYear.value,bid=filterSection.value,sid=filterSpec.value;
  if(!pid||!yl||!bid)return;
  initial.style.display='none';card.style.display='';tblWrap.style.display='none';empty.style.display='none';skeleton.style.display='';
  let url='/admin/get-assignments?program_id='+pid+'&year_level='+yl+'&block_id='+bid;if(sid)url+='&specialization_id='+sid;
  fetch(url).then(r=>r.json()).then(d=>{skeleton.style.display='none';if(!d.success){toast(d.message||'Error','error');return;}allAssignments=d.assignments||[];render();}).catch(()=>{skeleton.style.display='none';toast('Failed','error');});
}
function render(){
  tbody.innerHTML='';
  if(!allAssignments.length){empty.style.display='';tblWrap.style.display='none';countBadge.textContent='0 courses';return;}
  empty.style.display='none';tblWrap.style.display='';
  countBadge.textContent=allAssignments.length+' course'+(allAssignments.length!==1?'s':'');
  if(allAssignments[0]&&allAssignments[0].block_name)cardTitle.textContent='Course Assignments \u2014 '+allAssignments[0].block_name;
  allAssignments.forEach(a=>{
    const tr=document.createElement('tr'),key=a.subject_id+'-'+a.block_id,assigned=a.status==='Assigned';
    const tname=assigned?((a.teacher_first_name||'')+' '+(a.teacher_last_name||'')).trim():'\u2014';
    // Display course_code if available, otherwise show a dash for pending
    const courseCodeDisplay = a.course_code ? a.course_code : '\u2014';
    let cb='';
    if(multipleMode){const dis=assigned?'disabled':'',chk=checkedItems.has(key)?'checked':'';
      cb='<td class="checkbox-col"><input type="checkbox" class="rcb" data-key="'+key+'" data-sid="'+a.subject_id+'" data-bid="'+a.block_id+'" data-code="'+esc(a.subject_code)+'" data-name="'+esc(a.subject_name)+'" data-block="'+esc(a.block_name)+'" '+dis+' '+chk+'></td>';}
    tr.innerHTML=cb+
      '<td><span class="subject-code">'+esc(a.subject_code)+'</span></td>'+
      '<td><span class="course-code">'+esc(courseCodeDisplay)+'</span></td>'+
      '<td><span class="subject-name">'+esc(a.subject_name)+'</span></td>'+
      '<td><span class="block-badge"><i class="fas fa-cube"></i> '+esc(a.block_name)+'</span></td>'+
      '<td><span class="teacher-name'+(assigned?'':' unassigned')+'">'+esc(tname)+'</span></td>'+
      '<td><span class="status-badge '+(assigned?'status-assigned':'status-pending')+'">'+(assigned?'Assigned':'Pending')+'</span></td>'+
      '<td style="text-align:center">'+(assigned?'<button class="action-btn btn-unassign" data-us="'+a.subject_id+'" data-ub="'+a.block_id+'"><i class="fas fa-user-minus"></i> Unassign</button>':'<button class="action-btn btn-assign" data-as="'+a.subject_id+'" data-ab="'+a.block_id+'"><i class="fas fa-user-plus"></i> Assign</button>')+'</td>';
    tbody.appendChild(tr);
  });
  tbody.querySelectorAll('.btn-assign').forEach(b=>b.addEventListener('click',function(){openAssign(+this.dataset.as,+this.dataset.ab);}));
  tbody.querySelectorAll('.btn-unassign').forEach(b=>b.addEventListener('click',function(){unassign(+this.dataset.us,+this.dataset.ub);}));
  if(multipleMode){tbody.querySelectorAll('.rcb').forEach(c=>c.addEventListener('change',onCbChange));syncAll();}
}

// ── MULTIPLE MODE ──
function toggleMulti(){multipleMode?exitMulti():enterMulti();}
function enterMulti(){multipleMode=true;cbHeader.style.display='';selAll.checked=false;selAll.addEventListener('change',onSelAll);refreshPA();if(allAssignments.length)render();}
function exitMulti(){multipleMode=false;checkedItems.clear();cbHeader.style.display='none';selAll.checked=false;refreshPA();if(allAssignments.length)render();}
function refreshPA(){
  const n=checkedItems.size;
  if(multipleMode){
    paLeft.innerHTML='<span class="multi-active-indicator">Multiple Assign Mode</span>'+(n?'<span class="checked-badge"><i class="fas fa-check-square"></i> '+n+' checked</span>':'');
    paRight.innerHTML=(n?'<button class="btn btn-sm btn-view-checked" id="bVC"><i class="fas fa-eye"></i> View Checked</button><button class="btn btn-primary btn-sm" id="bAC"><i class="fas fa-user-plus"></i> Assign Teacher</button>':'')+'<button class="btn btn-secondary btn-sm" id="bCM"><i class="fas fa-times"></i> Cancel</button>';
    const v=$('bVC');if(v)v.addEventListener('click',openVC);
    const a=$('bAC');if(a)a.addEventListener('click',openAssignChecked);
    $('bCM').addEventListener('click',exitMulti);
  } else {
    paLeft.innerHTML='';paRight.innerHTML='<button class="btn btn-primary" id="btnMultipleAssign"><i class="fas fa-layer-group"></i> Multiple Assign</button>';
    $('btnMultipleAssign').addEventListener('click',toggleMulti);
  }
}
function onCbChange(e){const cb=e.target,k=cb.dataset.key;cb.checked?checkedItems.set(k,{subject_id:+cb.dataset.sid,block_id:+cb.dataset.bid,subject_code:cb.dataset.code,subject_name:cb.dataset.name,block_name:cb.dataset.block}):checkedItems.delete(k);syncAll();refreshPA();}
function onSelAll(){const c=selAll.checked;tbody.querySelectorAll('.rcb:not(:disabled)').forEach(cb=>{cb.checked=c;const k=cb.dataset.key;c?checkedItems.set(k,{subject_id:+cb.dataset.sid,block_id:+cb.dataset.bid,subject_code:cb.dataset.code,subject_name:cb.dataset.name,block_name:cb.dataset.block}):checkedItems.delete(k);});refreshPA();}
function syncAll(){const a=tbody.querySelectorAll('.rcb:not(:disabled)'),c=tbody.querySelectorAll('.rcb:not(:disabled):checked');selAll.checked=a.length>0&&a.length===c.length;}

// ── VIEW CHECKED MODAL ──
function openVC(){renderVC();backdrop.classList.add('active');vcModal.classList.add('active');document.body.style.overflow='hidden';}
function closeVC(){vcModal.classList.remove('active');backdrop.classList.remove('active');document.body.style.overflow='';}
function renderVC(){
  vcList.innerHTML='';vcSub.textContent=checkedItems.size+' subject'+(checkedItems.size!==1?'s':'')+' selected across blocks';
  if(!checkedItems.size){vcEmpty.style.display='';return;}vcEmpty.style.display='none';
  checkedItems.forEach((item,key)=>{
    const li=document.createElement('li');li.className='checked-list-item';
    li.innerHTML='<div class="checked-item-info"><span class="checked-item-code">'+esc(item.subject_code)+'</span><span class="checked-item-name">'+esc(item.subject_name)+'</span><span class="checked-item-block"><i class="fas fa-cube"></i> '+esc(item.block_name)+'</span></div><button class="checked-item-remove" data-key="'+key+'"><i class="fas fa-times"></i></button>';
    vcList.appendChild(li);
  });
  vcList.querySelectorAll('.checked-item-remove').forEach(b=>b.addEventListener('click',function(){checkedItems.delete(this.dataset.key);renderVC();refreshPA();const cb=tbody.querySelector('.rcb[data-key="'+this.dataset.key+'"]');if(cb)cb.checked=false;syncAll();}));
}

// ── ASSIGN MODAL ──
function openAssign(sid,bid){assignTarget={subject_id:sid,block_id:bid};const a=allAssignments.find(x=>x.subject_id===sid&&x.block_id===bid);assignSub.textContent=a?'Assigning for: '+a.subject_code+' \u2014 '+a.subject_name:'Choose a teacher';showTM();}
function openAssignChecked(){if(!checkedItems.size)return;assignTarget=null;assignSub.textContent='Assigning to '+checkedItems.size+' selected course(s)';showTM();}
function showTM(){selectedTeacherId=null;btnConfirm.disabled=true;tSearch.value='';backdrop.classList.add('active');assignModal.classList.add('active');document.body.style.overflow='hidden';loadTeachers();setTimeout(()=>tSearch.focus(),300);}
window.closeAssignModal=function(){assignModal.classList.remove('active');backdrop.classList.remove('active');document.body.style.overflow='';selectedTeacherId=null;};
function bindModal(){backdrop.addEventListener('click',()=>{closeAssignModal();closeVC();});tSearch.addEventListener('input',filterTM);tDept.addEventListener('change',filterTM);}
function loadTeachers(){tBody.innerHTML='<tr><td colspan="4" class="modal-empty-state"><i class="fas fa-spinner fa-spin"></i><p>Loading...</p></td></tr>';fetch('/admin/get-teachers').then(r=>r.json()).then(d=>{if(!d.success)return;allTeachers=d.teachers||[];popDept(d.departments||[]);renderTM(allTeachers);}).catch(()=>{tBody.innerHTML='<tr><td colspan="4" class="modal-empty-state"><i class="fas fa-exclamation-triangle"></i><p>Error</p></td></tr>';});}
function popDept(ds){tDept.innerHTML='<option value="">All Departments</option>';ds.forEach(d=>{const o=document.createElement('option');o.value=d.department_id;o.textContent=d.department_code+' \u2014 '+d.department_name;tDept.appendChild(o);});}
function renderTM(list){tBody.innerHTML='';if(!list.length){tBody.innerHTML='<tr><td colspan="4" class="modal-empty-state"><i class="fas fa-user-slash"></i><p>No teachers</p></td></tr>';return;}
  list.forEach(t=>{const tr=document.createElement('tr');if(selectedTeacherId===t.teacher_id)tr.classList.add('selected');
    tr.innerHTML='<td style="font-weight:600;color:var(--primary)">'+esc(t.employee_id)+'</td><td style="font-weight:500;color:var(--text-dark)">'+esc(t.first_name)+' '+esc(t.last_name)+'</td><td>'+esc(t.department_name||'\u2014')+'</td><td>'+esc(t.program_code||'\u2014')+'</td>';
    tr.addEventListener('click',()=>{tBody.querySelectorAll('tr.selected').forEach(e=>e.classList.remove('selected'));tr.classList.add('selected');selectedTeacherId=t.teacher_id;btnConfirm.disabled=false;});tBody.appendChild(tr);});}
function filterTM(){const q=tSearch.value.toLowerCase().trim(),dept=tDept.value;let f=allTeachers;if(q)f=f.filter(t=>((t.first_name||'')+' '+(t.last_name||'')).toLowerCase().includes(q)||(t.employee_id||'').toLowerCase().includes(q));if(dept)f=f.filter(t=>String(t.department_id)===dept);renderTM(f);}

// ── ASSIGN / UNASSIGN ──
window.confirmAssignTeacher=function(){if(!selectedTeacherId)return;btnConfirm.disabled=true;btnConfirm.innerHTML='<i class="fas fa-spinner fa-spin"></i> Assigning...';
  if(assignTarget){doAssign(assignTarget.subject_id,assignTarget.block_id,selectedTeacherId).then(()=>{toast('Teacher assigned','success');closeAssignModal();loadAssignments();}).catch(e=>toast(e||'Failed','error')).finally(resetBtn);}
  else{const jobs=[];checkedItems.forEach(i=>{jobs.push(doAssign(i.subject_id,i.block_id,selectedTeacherId));});Promise.all(jobs).then(()=>{toast(jobs.length+' course(s) assigned','success');closeAssignModal();exitMulti();loadAssignments();}).catch(e=>{toast(e||'Some failed','error');loadAssignments();}).finally(resetBtn);}
};
function resetBtn(){btnConfirm.disabled=false;btnConfirm.innerHTML='<i class="fas fa-check"></i> Assign Teacher';}
function doAssign(s,b,t){return fetch('/admin/assign-teacher',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({subject_id:s,block_id:b,teacher_id:t})}).then(r=>r.json()).then(d=>{if(!d.success)throw d.message;return d;});}
function unassign(s,b){if(!confirm('Unassign this teacher?'))return;fetch('/admin/unassign-teacher',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({subject_id:s,block_id:b})}).then(r=>r.json()).then(d=>{d.success?(toast('Unassigned','success'),loadAssignments()):toast(d.message||'Failed','error');}).catch(()=>toast('Error','error'));}

// ── TOAST ──
function toast(m,t){const c=$('toastContainer'),d=document.createElement('div');d.className='toast toast-'+(t||'success');d.innerHTML='<i class="fas '+(t==='error'?'fa-exclamation-circle':'fa-check-circle')+'"></i><span>'+esc(m)+'</span><button class="toast-close" onclick="this.parentElement.remove()"><i class="fas fa-times"></i></button>';c.appendChild(d);requestAnimationFrame(()=>d.classList.add('show'));setTimeout(()=>{d.classList.remove('show');setTimeout(()=>d.remove(),400);},4000);}
function esc(s){if(!s)return '';const d=document.createElement('div');d.textContent=String(s);return d.innerHTML;}

window._assignments={openAssignModal:openAssign,unassignTeacher:unassign,closeViewChecked:closeVC};
})();
