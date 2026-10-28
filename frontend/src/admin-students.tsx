import { type FormEvent, useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, ChevronLeft, ChevronRight, Plus, Search, SlidersHorizontal, UserRound, Users, X } from 'lucide-react';
import './admin-students.css';

type Student = { id: number; email: string; role: string; registration_number: string | null; full_name: string | null; year_of_study: number | null; department_id: number | null; department: string | null; section_id: number | null; section: string | null; approval_status: 'Approved' | 'Pending'; created_at: string };
type Department = { id: number; name: string; sections: { id: number; name: string }[] };
type FormValues = { fullName: string; email: string; password: string; registrationNumber: string; year: string; departmentId: string; sectionId: string; approvalStatus: 'Approved' | 'Pending' };

const emptyForm: FormValues = { fullName: '', email: '', password: '', registrationNumber: '', year: '', departmentId: '', sectionId: '', approvalStatus: 'Approved' };
const api = async <T,>(path: string, options: RequestInit = {}): Promise<T> => {
  const response = await fetch(`/api${path}`, { credentials: 'include', headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }, ...options });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw Error(body.detail || response.statusText);
  }
  return (response.status === 204 ? null : response.json()) as Promise<T>;
};
const yearName = (year: number | null) => year ? `${year}${year === 1 ? 'st' : year === 2 ? 'nd' : year === 3 ? 'rd' : 'th'} Year` : '—';

export function AdminStudentsPage() {
  const queryClient = useQueryClient();
  const students = useQuery<Student[]>({ queryKey: ['admin-students'], queryFn: () => api('/admin/users?role=student') });
  const departments = useQuery<Department[]>({ queryKey: ['admin-departments'], queryFn: () => api('/admin/departments') });
  const [search, setSearch] = useState('');
  const [yearFilter, setYearFilter] = useState('');
  const [departmentFilter, setDepartmentFilter] = useState('');
  const [sectionFilter, setSectionFilter] = useState('');
  const [approvalFilter, setApprovalFilter] = useState('');
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<Student | null>(null);
  const [studentModal, setStudentModal] = useState(false);
  const [departmentModal, setDepartmentModal] = useState(false);
  const pageSize = 10;
  const visibleStudents = useMemo(() => (students.data || []).filter((student) => {
    const term = search.trim().toLowerCase();
    return (!term || [student.full_name, student.email, student.registration_number].some((value) => value?.toLowerCase().includes(term)))
      && (!yearFilter || String(student.year_of_study) === yearFilter)
      && (!departmentFilter || String(student.department_id) === departmentFilter)
      && (!sectionFilter || String(student.section_id) === sectionFilter)
      && (!approvalFilter || student.approval_status === approvalFilter);
  }), [students.data, search, yearFilter, departmentFilter, sectionFilter, approvalFilter]);
  const pageCount = Math.max(1, Math.ceil(visibleStudents.length / pageSize));
  const pageRows = visibleStudents.slice((page - 1) * pageSize, page * pageSize);
  const hasFilters = Boolean(search || yearFilter || departmentFilter || sectionFilter || approvalFilter);
  const clearFilters = () => { setSearch(''); setYearFilter(''); setDepartmentFilter(''); setSectionFilter(''); setApprovalFilter(''); setPage(1); };
  const openAdd = () => { setEditing(null); setStudentModal(true); };
  const openEdit = (student: Student) => { setEditing(student); setStudentModal(true); };
  const refresh = async () => { await queryClient.invalidateQueries({ queryKey: ['admin-students'] }); await queryClient.invalidateQueries({ queryKey: ['stats'] }); };

  return <div className="admin-students-page">
    <div className="admin-students-heading">
      <div><span className="admin-students-eyebrow">ACADEMIC DIRECTORY</span><h1>Students</h1><p>{visibleStudents.length} {visibleStudents.length === 1 ? 'student' : 'students'} in this view</p></div>
      <div className="admin-students-actions"><button className="admin-directory-secondary" onClick={() => setDepartmentModal(true)}><SlidersHorizontal/>Manage departments &amp; sections</button><button className="admin-directory-primary" onClick={openAdd}><Plus/>Add student</button></div>
    </div>
    <section className="admin-student-filters">
      <label className="admin-student-search"><span>Search</span><div><Search/><input placeholder="Name, email or registration number" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }}/></div></label>
      <label><span>Year of study</span><select value={yearFilter} onChange={(event) => { setYearFilter(event.target.value); setPage(1); }}><option value="">All years</option>{[1,2,3,4,5,6,7,8].map((year) => <option key={year} value={year}>{yearName(year)}</option>)}</select></label>
      <label><span>Department</span><select value={departmentFilter} onChange={(event) => { setDepartmentFilter(event.target.value); setSectionFilter(''); setPage(1); }}><option value="">All departments</option>{(departments.data || []).map((department) => <option key={department.id} value={department.id}>{department.name}</option>)}</select></label>
      <label><span>Section</span><select value={sectionFilter} onChange={(event) => { setSectionFilter(event.target.value); setPage(1); }}><option value="">All sections</option>{(departments.data || []).filter((department) => !departmentFilter || String(department.id) === departmentFilter).flatMap((department) => department.sections.map((section) => <option key={section.id} value={section.id}>{departmentFilter ? section.name : `${department.name} · ${section.name}`}</option>))}</select></label>
      <label><span>Approval</span><select value={approvalFilter} onChange={(event) => { setApprovalFilter(event.target.value); setPage(1); }}><option value="">All statuses</option><option value="Approved">Approved</option><option value="Pending">Pending</option></select></label>
      <button className="admin-student-clear" onClick={clearFilters} disabled={!hasFilters}>Clear</button>
    </section>
    <section className="admin-student-directory">
      <header><div><span className="admin-students-eyebrow">ROSTER</span><h2>Student directory</h2></div><span className="admin-student-result-count">{visibleStudents.length ? `${(page - 1) * pageSize + 1}–${Math.min(page * pageSize, visibleStudents.length)} of ${visibleStudents.length}` : '0 of 0'}</span></header>
      <div className="admin-student-table-scroll"><table><thead><tr><th>Reg No</th><th>Student</th><th>Year</th><th>Department</th><th>Section</th><th>Status</th><th>Actions</th></tr></thead><tbody>
        {pageRows.map((student) => <tr key={student.id}><td className="admin-reg-number">{student.registration_number || '—'}</td><td><div className="admin-student-identity"><span><UserRound/></span><div><b>{student.full_name || student.email.split('@')[0]}</b><small>{student.email}</small></div></div></td><td>{yearName(student.year_of_study)}</td><td>{student.department || '—'}</td><td>{student.section || '—'}</td><td><span className={`admin-approval-badge ${student.approval_status.toLowerCase()}`}><i/>{student.approval_status}</span></td><td><button className="admin-student-edit" onClick={() => openEdit(student)}>Edit</button></td></tr>)}
      </tbody></table>{students.isLoading && <div className="admin-student-empty"><span className="admin-student-spinner"/>Loading student directory…</div>}{students.isError && <div className="admin-student-empty admin-student-error">{students.error.message}</div>}{!students.isLoading && !students.isError && !pageRows.length && <div className="admin-student-empty"><Users/><b>{hasFilters ? 'No students match these filters.' : 'No students yet.'}</b><span>{hasFilters ? 'Clear a filter or adjust your search to see more students.' : 'Add a student to start building the academic directory.'}</span></div>}</div>
      <footer><span>Page {page} of {pageCount}</span><div><button onClick={() => setPage((value) => Math.max(1, value - 1))} disabled={page <= 1}><ChevronLeft/>Previous</button><button onClick={() => setPage((value) => Math.min(pageCount, value + 1))} disabled={page >= pageCount}>Next<ChevronRight/></button></div></footer>
    </section>
    {studentModal && <StudentModal student={editing} departments={departments.data || []} close={() => setStudentModal(false)} refresh={refresh}/>}
    {departmentModal && <AcademicSetupModal departments={departments.data || []} close={() => setDepartmentModal(false)}/>}
  </div>;
}

function StudentModal({ student, departments, close, refresh }: { student: Student | null; departments: Department[]; close: () => void; refresh: () => Promise<void> }) {
  const [form, setForm] = useState<FormValues>(student ? { fullName: student.full_name || '', email: student.email, password: '', registrationNumber: student.registration_number || '', year: student.year_of_study ? String(student.year_of_study) : '', departmentId: student.department_id ? String(student.department_id) : '', sectionId: student.section_id ? String(student.section_id) : '', approvalStatus: student.approval_status } : emptyForm);
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);
  const sections = departments.find((department) => String(department.id) === form.departmentId)?.sections || [];
  const submit = async (event: FormEvent) => {
    event.preventDefault(); setError(''); setPending(true);
    const academic = { full_name: form.fullName.trim() || null, year_of_study: form.year ? Number(form.year) : null, department_id: form.departmentId ? Number(form.departmentId) : null, section_id: form.sectionId ? Number(form.sectionId) : null, approval_status: form.approvalStatus };
    try {
      if (student) await api(`/admin/users/${student.id}`, { method: 'PATCH', body: JSON.stringify(academic) });
      else await api('/admin/users', { method: 'POST', body: JSON.stringify({ email: form.email.trim(), password: form.password, role: 'student', registration_number: form.registrationNumber.trim(), ...academic }) });
      await refresh(); close();
    } catch (exception) { setError((exception as Error).message); }
    finally { setPending(false); }
  };
  const update = (field: keyof FormValues, value: string) => setForm((current) => ({ ...current, [field]: value }));
  return <div className="admin-directory-modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) close(); }}><form className="admin-directory-modal" onSubmit={submit}>
    <button className="admin-directory-modal-close" type="button" onClick={close} aria-label="Close"><X/></button><span className="admin-students-eyebrow">ACADEMIC DIRECTORY</span><h2>{student ? 'Edit student' : 'Add student'}</h2><p>Keep student account and academic details together.</p>
    <div className="admin-student-form-grid">
      <label>Full name<input value={form.fullName} onChange={(event) => update('fullName', event.target.value)} placeholder="Student name"/></label>
      {!student && <label>Email address<input type="email" value={form.email} onChange={(event) => update('email', event.target.value)} required placeholder="student@college.edu"/></label>}
      {!student && <label>Temporary password<input type="password" value={form.password} onChange={(event) => update('password', event.target.value)} minLength={8} required placeholder="At least 8 characters"/></label>}
      <label>Registration number<input value={form.registrationNumber} onChange={(event) => update('registrationNumber', event.target.value)} required={!student} disabled={Boolean(student)} placeholder="e.g. 23CS1042"/></label>
      <label>Year of study<select value={form.year} onChange={(event) => update('year', event.target.value)}><option value="">Select year</option>{[1,2,3,4,5,6,7,8].map((year) => <option key={year} value={year}>{yearName(year)}</option>)}</select></label>
      <label>Department<select value={form.departmentId} onChange={(event) => setForm((current) => ({ ...current, departmentId: event.target.value, sectionId: '' }))}><option value="">Select department</option>{departments.map((department) => <option key={department.id} value={department.id}>{department.name}</option>)}</select></label>
      <label>Section<select value={form.sectionId} onChange={(event) => update('sectionId', event.target.value)} disabled={!form.departmentId}><option value="">Select section</option>{sections.map((section) => <option key={section.id} value={section.id}>{section.name}</option>)}</select></label>
      <label>Approval status<select value={form.approvalStatus} onChange={(event) => update('approvalStatus', event.target.value as FormValues['approvalStatus'])}><option value="Approved">Approved</option><option value="Pending">Pending</option></select></label>
    </div>
    {error && <p className="admin-student-form-error">{error}</p>}<div className="admin-directory-modal-actions"><button type="button" className="admin-directory-secondary" onClick={close}>Cancel</button><button type="submit" className="admin-directory-primary" disabled={pending}>{pending ? 'Saving…' : student ? 'Save changes' : <><Check/>Create student</>}</button></div>
  </form></div>;
}

function AcademicSetupModal({ departments, close }: { departments: Department[]; close: () => void }) {
  const queryClient = useQueryClient();
  const [departmentName, setDepartmentName] = useState('');
  const [sectionNames, setSectionNames] = useState<Record<number, string>>({});
  const [error, setError] = useState('');
  const [pendingKey, setPendingKey] = useState('');
  const saveDepartment = async (event: FormEvent) => { event.preventDefault(); setError(''); setPendingKey('department'); try { await api('/admin/departments', { method: 'POST', body: JSON.stringify({ name: departmentName.trim() }) }); setDepartmentName(''); await queryClient.invalidateQueries({ queryKey: ['admin-departments'] }); } catch (exception) { setError((exception as Error).message); } finally { setPendingKey(''); } };
  const saveSection = async (event: FormEvent, departmentId: number) => { event.preventDefault(); const name = (sectionNames[departmentId] || '').trim(); if (!name) return; setError(''); setPendingKey(String(departmentId)); try { await api(`/admin/departments/${departmentId}/sections`, { method: 'POST', body: JSON.stringify({ name }) }); setSectionNames((current) => ({ ...current, [departmentId]: '' })); await queryClient.invalidateQueries({ queryKey: ['admin-departments'] }); } catch (exception) { setError((exception as Error).message); } finally { setPendingKey(''); } };
  return <div className="admin-directory-modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) close(); }}><section className="admin-directory-modal admin-academic-modal">
    <button className="admin-directory-modal-close" type="button" onClick={close} aria-label="Close"><X/></button><span className="admin-students-eyebrow">DIRECTORY SETTINGS</span><h2>Departments &amp; sections</h2><p>Add the academic options used by student profiles and filters.</p>
    <form className="admin-add-department-form" onSubmit={saveDepartment}><input value={departmentName} onChange={(event) => setDepartmentName(event.target.value)} required minLength={2} placeholder="New department name"/><button className="admin-directory-primary" disabled={pendingKey === 'department'}><Plus/>Add department</button></form>
    <div className="admin-department-list">{departments.map((department) => <article key={department.id}><div><b>{department.name}</b><small>{department.sections.length} {department.sections.length === 1 ? 'section' : 'sections'}</small></div><div className="admin-section-chips">{department.sections.map((section) => <span key={section.id}>{section.name}</span>)}</div><form onSubmit={(event) => saveSection(event, department.id)}><input value={sectionNames[department.id] || ''} onChange={(event) => setSectionNames((current) => ({ ...current, [department.id]: event.target.value }))} required placeholder="Add section"/><button className="admin-directory-secondary" disabled={pendingKey === String(department.id)}><Plus/>Add</button></form></article>)}{!departments.length && <div className="admin-student-empty"><Users/><span>Create a department first, then add its sections.</span></div>}</div>
    {error && <p className="admin-student-form-error">{error}</p>}<div className="admin-directory-modal-actions"><button type="button" className="admin-directory-secondary" onClick={close}>Done</button></div>
  </section></div>;
}
