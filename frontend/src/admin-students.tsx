import { type FormEvent, useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, ChevronLeft, ChevronRight, Pencil, Plus, Search, ShieldCheck, SlidersHorizontal, Trash2, UserRound, Users, X } from 'lucide-react';
import { adminApi, ConfirmDialog, ResetPasswordDialog } from './admin-shared';
import './admin-students.css';

type YearCounts = { '1': number; '2': number; '3': number; '4': number; unset: number };
type DepartmentRef = { id: number; name: string };
type SectionRef = { id: number; name: string };
type Mentor = { id: number; email: string; full_name: string | null; faculty_code: string | null };
type Student = {
  id: number;
  email: string;
  role: string;
  registration_number: string | null;
  full_name: string | null;
  year_of_study: number | null;
  department_id: number | null;
  department: DepartmentRef | null;
  section_id: number | null;
  section: SectionRef | null;
  mentor: Mentor | null;
  approval_status: 'Approved' | 'Pending';
  created_at: string;
};
type StudentPage = { items: Student[]; total: number; page: number; page_size: number; pages: number };
type AcademicSection = { id: number; name: string; student_count: number; year_counts: YearCounts };
type Department = {
  id: number;
  name: string;
  student_count: number;
  faculty_count: number;
  year_counts: YearCounts;
  sections: AcademicSection[];
};
type FormValues = {
  fullName: string;
  email: string;
  password: string;
  registrationNumber: string;
  year: string;
  departmentId: string;
  sectionId: string;
  approvalStatus: 'Approved' | 'Pending';
};

const emptyForm: FormValues = {
  fullName: '',
  email: '',
  password: '',
  registrationNumber: '',
  year: '',
  departmentId: '',
  sectionId: '',
  approvalStatus: 'Approved',
};
const yearOptions = [1, 2, 3, 4];
const yearCountLabels: [keyof YearCounts, string][] = [
  ['1', '1st'],
  ['2', '2nd'],
  ['3', '3rd'],
  ['4', '4th'],
  ['unset', 'Not set'],
];

const yearName = (year: number | null) => {
  if (!year) return 'Not set';
  return `${year}${year === 1 ? 'st' : year === 2 ? 'nd' : year === 3 ? 'rd' : 'th'} Year`;
};
const studentName = (student: Pick<Student, 'full_name' | 'email'>) => student.full_name || student.email.split('@')[0];

function YearCountStrip({ counts, compact = false }: { counts: YearCounts; compact?: boolean }) {
  return <div className={`admin-year-counts${compact ? ' compact' : ''}`}>{yearCountLabels.map(([key, label]) => <span key={key}><b>{counts[key]}</b>{label}</span>)}</div>;
}

export function AdminStudentsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [yearFilter, setYearFilter] = useState('');
  const [departmentFilter, setDepartmentFilter] = useState('');
  const [sectionFilter, setSectionFilter] = useState('');
  const [approvalFilter, setApprovalFilter] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 10;
  const [studentModal, setStudentModal] = useState(false);
  const [editing, setEditing] = useState<Student | null>(null);
  const [departmentModal, setDepartmentModal] = useState(false);
  const [resetTarget, setResetTarget] = useState<Student | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Student | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState('');
  const [approvingId, setApprovingId] = useState<number | null>(null);
  const [notice, setNotice] = useState('');
  const [actionError, setActionError] = useState('');

  const params = new URLSearchParams({ role: 'student', page: String(page), page_size: String(pageSize), sort: 'newest' });
  if (search.trim()) params.set('search', search.trim());
  if (yearFilter === 'unset') params.set('year_unset', 'true');
  else if (yearFilter) params.set('year_of_study', yearFilter);
  if (departmentFilter) params.set('department_id', departmentFilter);
  if (sectionFilter) params.set('section_id', sectionFilter);
  if (approvalFilter) params.set('status', approvalFilter);

  const students = useQuery<StudentPage>({
    queryKey: ['admin-students', params.toString()],
    queryFn: () => adminApi<StudentPage>(`/admin/users?${params.toString()}`),
  });
  const departments = useQuery<Department[]>({
    queryKey: ['admin-departments'],
    queryFn: () => adminApi<Department[]>('/admin/departments'),
  });

  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(''), 4500);
    return () => window.clearTimeout(timer);
  }, [notice]);
  useEffect(() => {
    if (students.data && page > students.data.pages) setPage(students.data.pages);
  }, [students.data, page]);

  const total = students.data?.total ?? 0;
  const pageCount = students.data?.pages ?? 1;
  const pageRows = students.data?.items ?? [];
  const hasFilters = Boolean(search || yearFilter || departmentFilter || sectionFilter || approvalFilter);

  const clearFilters = () => {
    setSearch('');
    setYearFilter('');
    setDepartmentFilter('');
    setSectionFilter('');
    setApprovalFilter('');
    setPage(1);
  };
  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['admin-students'] }),
      queryClient.invalidateQueries({ queryKey: ['admin-departments'] }),
      queryClient.invalidateQueries({ queryKey: ['stats'] }),
    ]);
  };
  const openAdd = () => {
    setEditing(null);
    setStudentModal(true);
  };
  const openEdit = (student: Student) => {
    setEditing(student);
    setStudentModal(true);
  };
  const approve = async (student: Student) => {
    setApprovingId(student.id);
    setActionError('');
    try {
      await adminApi(`/admin/students/${student.id}`, { method: 'PATCH', body: JSON.stringify({ approval_status: 'Approved' }) });
      await refresh();
      setNotice(`${studentName(student)} approved.`);
    } catch (exception) {
      setActionError((exception as Error).message);
    } finally {
      setApprovingId(null);
    }
  };
  const removeStudent = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    setDeleteError('');
    try {
      await adminApi(`/admin/students/${deleteTarget.id}`, { method: 'DELETE' });
      const name = studentName(deleteTarget);
      setDeleteTarget(null);
      await refresh();
      setNotice(`${name} removed permanently.`);
    } catch (exception) {
      setDeleteError((exception as Error).message);
    } finally {
      setDeleting(false);
    }
  };

  return <div className="admin-students-page">
    <div className="admin-students-heading">
      <div><span className="admin-students-eyebrow">ACADEMIC DIRECTORY</span><h1>Students</h1><p>{total} {total === 1 ? 'student' : 'students'} in this view</p></div>
      <div className="admin-students-actions"><button className="admin-directory-secondary" onClick={() => setDepartmentModal(true)}><SlidersHorizontal/>Manage departments & sections</button><button className="admin-directory-primary" onClick={openAdd}><Plus/>Add student</button></div>
    </div>

    {notice && <div className="admin-toast" role="status"><Check/><span>{notice}</span><button onClick={() => setNotice('')} aria-label="Dismiss"><X/></button></div>}
    {actionError && <div className="admin-toast admin-toast-error" role="alert"><span>{actionError}</span><button onClick={() => setActionError('')} aria-label="Dismiss"><X/></button></div>}

    <section className="admin-student-filters">
      <label className="admin-student-search"><span>Search</span><div><Search/><input placeholder="Name, email or registration number" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }}/></div></label>
      <label><span>Year of study</span><select value={yearFilter} onChange={(event) => { setYearFilter(event.target.value); setPage(1); }}><option value="">All years</option>{yearOptions.map((year) => <option key={year} value={year}>{yearName(year)}</option>)}<option value="unset">Not set</option></select></label>
      <label><span>Department</span><select value={departmentFilter} onChange={(event) => { setDepartmentFilter(event.target.value); setSectionFilter(''); setPage(1); }}><option value="">All departments</option>{(departments.data || []).map((department) => <option key={department.id} value={department.id}>{department.name}</option>)}</select></label>
      <label><span>Section</span><select value={sectionFilter} onChange={(event) => { setSectionFilter(event.target.value); setPage(1); }}><option value="">All sections</option>{(departments.data || []).filter((department) => !departmentFilter || String(department.id) === departmentFilter).flatMap((department) => department.sections.map((section) => <option key={section.id} value={section.id}>{departmentFilter ? section.name : `${department.name} · ${section.name}`}</option>))}</select></label>
      <label><span>Approval</span><select value={approvalFilter} onChange={(event) => { setApprovalFilter(event.target.value); setPage(1); }}><option value="">All statuses</option><option value="Approved">Approved</option><option value="Pending">Pending</option></select></label>
      <button className="admin-student-clear" onClick={clearFilters} disabled={!hasFilters}>Clear</button>
    </section>

    <section className="admin-student-directory">
      <header><div><span className="admin-students-eyebrow">ROSTER</span><h2>Student directory</h2></div><span className="admin-student-result-count">{total ? `${(page - 1) * pageSize + 1}–${Math.min(page * pageSize, total)} of ${total}` : '0 of 0'}</span></header>
      <div className="admin-student-table-scroll"><table><thead><tr><th>Reg No</th><th>Student</th><th>Year</th><th>Department</th><th>Section</th><th>Mentor</th><th>Status</th><th>Actions</th></tr></thead><tbody>
        {pageRows.map((student) => <tr key={student.id}>
          <td className="admin-reg-number">{student.registration_number || 'Not set'}</td>
          <td><div className="admin-student-identity"><span><UserRound/></span><div><b>{studentName(student)}</b><small>{student.email}</small></div></div></td>
          <td>{yearName(student.year_of_study)}</td>
          <td>{student.department?.name || 'Not set'}</td>
          <td>{student.section?.name || 'Not set'}</td>
          <td>{student.mentor ? (
            <div className="admin-mentor-cell admin-mentor-badge" title={`${student.mentor.full_name || student.mentor.email}${student.mentor.faculty_code ? ` · ${student.mentor.faculty_code}` : ''}`}>
              <span className="admin-mentor-avatar"><ShieldCheck/></span>
              <div className="admin-mentor-info">
                <b>{student.mentor.faculty_code || studentName(student.mentor)}</b>
                <small>{student.mentor.full_name || student.mentor.email}</small>
              </div>
            </div>
          ) : (
            <span className="admin-mentor-unassigned admin-muted">Not assigned</span>
          )}</td>
          <td><span className={`admin-approval-badge ${student.approval_status.toLowerCase()}`}><i/>{student.approval_status}</span></td>
          <td><div className="admin-student-row-actions">
            {student.approval_status === 'Pending' && <button type="button" className="admin-student-action approve" onClick={() => approve(student)} disabled={approvingId === student.id}>{approvingId === student.id ? 'Approving…' : 'Approve'}</button>}
            <button type="button" className="admin-student-action" onClick={() => openEdit(student)}>Edit</button>
            <button type="button" className="admin-student-action" title="Reset password" onClick={() => setResetTarget(student)}>Reset</button>
            <button type="button" className="admin-student-action danger" onClick={() => { setDeleteError(''); setDeleteTarget(student); }}>Delete</button>
          </div></td>
        </tr>)}
      </tbody></table>
      {students.isLoading && <div className="admin-student-empty"><span className="admin-student-spinner"/>Loading student directory…</div>}
      {students.isError && <div className="admin-student-empty admin-student-error">{students.error.message}</div>}
      {!students.isLoading && !students.isError && !pageRows.length && <div className="admin-student-empty"><Users/><b>{hasFilters ? 'No students match these filters.' : 'No students yet.'}</b><span>{hasFilters ? 'Clear a filter or adjust your search to see more students.' : 'Add a student to start building the academic directory.'}</span></div>}
      </div>
      <footer><span>Page {page} of {pageCount}</span><div><button onClick={() => setPage((value) => Math.max(1, value - 1))} disabled={page <= 1}><ChevronLeft/>Previous</button><button onClick={() => setPage((value) => Math.min(pageCount, value + 1))} disabled={page >= pageCount}>Next<ChevronRight/></button></div></footer>
    </section>

    {studentModal && <StudentModal student={editing} departments={departments.data || []} close={() => setStudentModal(false)} refresh={refresh} notify={setNotice}/>}
    {departmentModal && <AcademicSetupModal departments={departments.data || []} close={() => setDepartmentModal(false)}/>}
    {resetTarget && <ResetPasswordDialog title="Reset student password" subject={`Set a new password for ${studentName(resetTarget)} (${resetTarget.email}).`} endpoint={`/admin/students/${resetTarget.id}/reset-password`} close={() => setResetTarget(null)} onDone={() => { setNotice(`Password reset for ${studentName(resetTarget)}.`); void refresh(); }}/>}
    {deleteTarget && <ConfirmDialog title="Remove student permanently?" description={`${studentName(deleteTarget)} (${deleteTarget.email}) will lose access immediately. Their personal data and submissions are deleted; problems they authored stay in the bank without an owner.`} confirmLabel="Remove student" pending={deleting} error={deleteError} close={() => setDeleteTarget(null)} onConfirm={removeStudent}/>}
  </div>;
}

function StudentModal({ student, departments, close, refresh, notify }: { student: Student | null; departments: Department[]; close: () => void; refresh: () => Promise<void>; notify: (message: string) => void }) {
  const [form, setForm] = useState<FormValues>(student ? {
    fullName: student.full_name || '',
    email: student.email,
    password: '',
    registrationNumber: student.registration_number || '',
    year: student.year_of_study ? String(student.year_of_study) : '',
    departmentId: student.department_id ? String(student.department_id) : '',
    sectionId: student.section_id ? String(student.section_id) : '',
    approvalStatus: student.approval_status,
  } : emptyForm);
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);
  const sections = departments.find((department) => String(department.id) === form.departmentId)?.sections || [];
  const update = (field: keyof FormValues, value: string) => setForm((current) => ({ ...current, [field]: value }));
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    setPending(true);
    const payload = {
      email: form.email.trim(),
      full_name: form.fullName.trim() || null,
      registration_number: form.registrationNumber.trim() || null,
      year_of_study: form.year ? Number(form.year) : null,
      department_id: form.departmentId ? Number(form.departmentId) : null,
      section_id: form.sectionId ? Number(form.sectionId) : null,
      approval_status: form.approvalStatus,
    };
    try {
      if (student) {
        await adminApi(`/admin/students/${student.id}`, { method: 'PATCH', body: JSON.stringify(payload) });
        notify('Student details updated.');
      } else {
        await adminApi('/admin/students', { method: 'POST', body: JSON.stringify({ ...payload, password: form.password }) });
        notify('Student account created.');
      }
      await refresh();
      close();
    } catch (exception) {
      setError((exception as Error).message);
    } finally {
      setPending(false);
    }
  };
  return <div className="admin-modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) close(); }}>
    <form className="admin-modal admin-modal-md" onSubmit={submit}>
      <header className="admin-modal-header">
        <div className="admin-modal-header-content">
          <span className="admin-modal-eyebrow">ACADEMIC DIRECTORY</span>
          <h2>{student ? 'Edit student' : 'Add student'}</h2>
          <p>{student ? 'Update account and academic details. Use Reset to change the password.' : 'Create an approved student account with its academic details.'}</p>
        </div>
        <button type="button" className="admin-modal-close" onClick={close} aria-label="Close"><X/></button>
      </header>
      <div className="admin-modal-body">
        <div className="admin-modal-form-grid">
          <label>Full name<input value={form.fullName} onChange={(event) => update('fullName', event.target.value)} placeholder="Student name"/></label>
          <label>Email address<input type="email" value={form.email} onChange={(event) => update('email', event.target.value)} required placeholder="student@college.edu"/></label>
          {!student && <label className="admin-modal-form-span-2">Temporary password<input type="password" value={form.password} onChange={(event) => update('password', event.target.value)} minLength={8} required placeholder="At least 8 characters"/></label>}
          <label>Registration number<input value={form.registrationNumber} onChange={(event) => update('registrationNumber', event.target.value)} required={!student} placeholder="e.g. 23CS1042"/></label>
          <label>Year of study<select value={form.year} onChange={(event) => update('year', event.target.value)}><option value="">Not set</option>{yearOptions.map((year) => <option key={year} value={year}>{yearName(year)}</option>)}</select></label>
          <label>Department<select value={form.departmentId} onChange={(event) => setForm((current) => ({ ...current, departmentId: event.target.value, sectionId: '' }))}><option value="">Not set</option>{departments.map((department) => <option key={department.id} value={department.id}>{department.name}</option>)}</select></label>
          <label>Section<select value={form.sectionId} onChange={(event) => update('sectionId', event.target.value)} disabled={!form.departmentId}><option value="">Not set</option>{sections.map((section) => <option key={section.id} value={section.id}>{section.name}</option>)}</select></label>
          <label>Approval status<select value={form.approvalStatus} onChange={(event) => update('approvalStatus', event.target.value as FormValues['approvalStatus'])}><option value="Approved">Approved</option><option value="Pending">Pending</option></select></label>
        </div>
        {error && <p className="admin-modal-form-error">{error}</p>}
      </div>
      <footer className="admin-modal-footer">
        <button type="button" className="admin-btn admin-btn-secondary" onClick={close}>Cancel</button>
        <button type="submit" className="admin-btn admin-btn-primary" disabled={pending}>{pending ? 'Saving…' : student ? 'Save changes' : <><Check/>Create student</>}</button>
      </footer>
    </form>
  </div>;
}

function AcademicSetupModal({ departments, close }: { departments: Department[]; close: () => void }) {
  const queryClient = useQueryClient();
  const [departmentName, setDepartmentName] = useState('');
  const [sectionNames, setSectionNames] = useState<Record<number, string>>({});
  const [editing, setEditing] = useState<{ kind: 'department' | 'section'; id: number; name: string } | null>(null);
  const [confirming, setConfirming] = useState<{ kind: 'department' | 'section'; id: number; name: string; studentCount: number; facultyCount: number } | null>(null);
  const [error, setError] = useState('');
  const [pendingKey, setPendingKey] = useState('');
  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['admin-departments'] }),
      queryClient.invalidateQueries({ queryKey: ['admin-students'] }),
    ]);
  };
  const saveDepartment = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    setPendingKey('department');
    try {
      await adminApi('/admin/departments', { method: 'POST', body: JSON.stringify({ name: departmentName.trim() }) });
      setDepartmentName('');
      await refresh();
    } catch (exception) {
      setError((exception as Error).message);
    } finally {
      setPendingKey('');
    }
  };
  const saveSection = async (event: FormEvent, departmentId: number) => {
    event.preventDefault();
    const name = (sectionNames[departmentId] || '').trim();
    if (!name) return;
    setError('');
    setPendingKey(`section-${departmentId}`);
    try {
      await adminApi(`/admin/departments/${departmentId}/sections`, { method: 'POST', body: JSON.stringify({ name }) });
      setSectionNames((current) => ({ ...current, [departmentId]: '' }));
      await refresh();
    } catch (exception) {
      setError((exception as Error).message);
    } finally {
      setPendingKey('');
    }
  };
  const saveRename = async () => {
    if (!editing) return;
    setError('');
    setPendingKey('rename');
    try {
      if (editing.kind === 'department') await adminApi(`/admin/departments/${editing.id}`, { method: 'PATCH', body: JSON.stringify({ name: editing.name.trim() }) });
      else await adminApi(`/admin/sections/${editing.id}`, { method: 'PATCH', body: JSON.stringify({ name: editing.name.trim() }) });
      setEditing(null);
      await refresh();
    } catch (exception) {
      setError((exception as Error).message);
    } finally {
      setPendingKey('');
    }
  };
  const deleteItem = async () => {
    if (!confirming) return;
    setError('');
    setPendingKey('delete');
    try {
      if (confirming.kind === 'department') await adminApi(`/admin/departments/${confirming.id}`, { method: 'DELETE' });
      else await adminApi(`/admin/sections/${confirming.id}`, { method: 'DELETE' });
      setConfirming(null);
      await refresh();
    } catch (exception) {
      setError((exception as Error).message);
    } finally {
      setPendingKey('');
    }
  };
  return <>
    <div className="admin-modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) close(); }}>
      <section className="admin-modal admin-modal-lg">
        <header className="admin-modal-header">
          <div className="admin-modal-header-content">
            <span className="admin-modal-eyebrow">DIRECTORY SETTINGS</span>
            <h2>Departments & sections</h2>
            <p>Add, rename, or remove academic options. Year-wise student counts are shown for every department and section.</p>
          </div>
          <button type="button" className="admin-modal-close" onClick={close} aria-label="Close"><X/></button>
        </header>
        <div className="admin-modal-body">
          <form className="admin-add-department-form" onSubmit={saveDepartment}>
            <label className="admin-modal-form-span-2">New department name<input value={departmentName} onChange={(event) => setDepartmentName(event.target.value)} required minLength={2} placeholder="New department name"/></label>
            <button type="submit" className="admin-btn admin-btn-primary" disabled={pendingKey === 'department'}><Plus/>Add department</button>
          </form>
          <div className="admin-department-list">
            {departments.map((department) => <article key={department.id} className="admin-department-card">
              <header className="admin-department-header">
                <div className="admin-department-title">
                  {editing?.kind === 'department' && editing.id === department.id ? (
                    <div className="admin-inline-edit">
                      <input value={editing.name} onChange={(event) => setEditing((current) => current ? { ...current, name: event.target.value } : current)} required minLength={2}/>
                      <button type="button" className="admin-btn admin-btn-primary" disabled={pendingKey === 'rename'} onClick={saveRename}>Save</button>
                      <button type="button" className="admin-btn admin-btn-secondary" onClick={() => setEditing(null)}>Cancel</button>
                    </div>
                  ) : (
                    <>
                      <b>{department.name}</b>
                      <div className="admin-department-meta">
                        <span><b>{department.student_count}</b> {department.student_count === 1 ? 'student' : 'students'}</span>
                        <span><b>{department.faculty_count}</b> {department.faculty_count === 1 ? 'faculty member' : 'faculty'}</span>
                        <span><b>{department.sections.length}</b> section{department.sections.length === 1 ? '' : 's'}</span>
                      </div>
                    </>
                  )}
                </div>
                <div className="admin-department-actions">
                  {editing?.kind !== 'department' || editing.id !== department.id ? (
                    <>
                      <button type="button" className="admin-btn admin-btn-ghost" onClick={() => setEditing({ kind: 'department', id: department.id, name: department.name })}><Pencil/>Rename</button>
                      <button type="button" className="admin-btn admin-btn-ghost admin-btn-danger" onClick={() => setConfirming({ kind: 'department', id: department.id, name: department.name, studentCount: department.student_count, facultyCount: department.faculty_count })}><Trash2/>Delete</button>
                    </>
                  ) : null}
                </div>
              </header>
              <div className="admin-department-sections">
                <div className="admin-department-year-badges">
                  {yearCountLabels.map(([key, label]) => <span key={key} className="admin-year-badge"><b>{department.year_counts[key]}</b>{label}</span>)}
                </div>
                {department.sections.map((section) => <div key={section.id} className="admin-section-row">
                  {editing?.kind === 'section' && editing.id === section.id ? (
                    <div className="admin-inline-edit">
                      <input value={editing.name} onChange={(event) => setEditing((current) => current ? { ...current, name: event.target.value } : current)} required/>
                      <button type="button" className="admin-btn admin-btn-primary" disabled={pendingKey === 'rename'} onClick={saveRename}>Save</button>
                      <button type="button" className="admin-btn admin-btn-secondary" onClick={() => setEditing(null)}>Cancel</button>
                    </div>
                  ) : (
                    <>
                      <div className="admin-section-info"><b>{section.name}</b></div>
                      <span className="admin-section-count">{section.student_count}</span>
                      <div className="admin-section-actions">
                        <button type="button" className="admin-btn admin-btn-icon" title={`Rename section ${section.name}`} onClick={() => setEditing({ kind: 'section', id: section.id, name: section.name })}><Pencil/></button>
                        <button type="button" className="admin-btn admin-btn-icon danger" title={`Delete section ${section.name}`} onClick={() => setConfirming({ kind: 'section', id: section.id, name: section.name, studentCount: section.student_count, facultyCount: 0 })}><Trash2/></button>
                      </div>
                    </>
                  )}
                </div>)}
                {!department.sections.length && <small className="admin-muted">No sections yet.</small>}
              </div>
              <form className="admin-add-section-form" onSubmit={(event) => saveSection(event, department.id)}>
                <input value={sectionNames[department.id] || ''} onChange={(event) => setSectionNames((current) => ({ ...current, [department.id]: event.target.value }))} required placeholder="Add section"/>
                <button type="submit" className="admin-btn admin-btn-secondary" disabled={pendingKey === `section-${department.id}`}><Plus/>Add</button>
              </form>
            </article>)}{!departments.length && <div className="admin-modal-empty"><Users/><b>No departments yet</b><span>Create a department first, then add its sections.</span></div>}
          </div>
          {error && <p className="admin-modal-form-error">{error}</p>}
        </div>
        <footer className="admin-modal-footer">
          <button type="button" className="admin-btn admin-btn-secondary" onClick={close}>Done</button>
        </footer>
      </section>
    </div>
    {confirming && <ConfirmDialog title={`Delete ${confirming.kind}?`} description={`${confirming.name} will be removed. ${confirming.kind === 'department' ? `${confirming.studentCount} students and ${confirming.facultyCount} faculty` : `${confirming.studentCount} students`} are assigned; deletion is blocked until those accounts are moved.`} confirmLabel="Delete" pending={pendingKey === 'delete'} close={() => setConfirming(null)} onConfirm={deleteItem}/>}
  </>;
}