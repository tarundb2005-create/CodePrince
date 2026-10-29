import { type FormEvent, useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, ChevronLeft, ChevronRight, Plus, Search, ShieldCheck, UserRound, Users, X, Trash2, RefreshCw, Clock } from 'lucide-react';
import { adminApi, ResetPasswordDialog } from './admin-shared';
import './admin-faculty.css';

type YearCounts = { '1': number; '2': number; '3': number; '4': number; unset: number };
type DepartmentRef = { id: number; name: string };
type Department = { id: number; name: string; student_count: number; faculty_count: number; year_counts: YearCounts; sections: { id: number; name: string }[] };
type Mentor = { id: number; email: string; full_name: string | null; faculty_code: string | null };
type Faculty = {
  id: number;
  email: string;
  full_name: string | null;
  role: string;
  faculty_code: string | null;
  department_id: number | null;
  department: DepartmentRef | null;
  mentee_count: number;
  course_count: number;
  created_at: string;
};
type FacultyPage = { items: Faculty[]; total: number; page: number; page_size: number; pages: number };
type Student = {
  id: number;
  email: string;
  full_name: string | null;
  registration_number: string | null;
  year_of_study: number | null;
  department: DepartmentRef | null;
  section: { id: number; name: string } | null;
  mentor: Mentor | null;
  approval_status: 'Approved' | 'Pending';
};
type StudentPage = { items: Student[]; total: number; page: number; page_size: number; pages: number };
type FormValues = { fullName: string; email: string; password: string; facultyCode: string; departmentId: string };

type RangePreviewResult = {
  student_id: number;
  registration_number: string | null;
  full_name: string | null;
  email: string;
};
type MentorConflictInfo = { faculty_code: string | null; full_name: string | null; email: string };
type RangeAssignmentSummary = {
  faculty_id: number;
  faculty_code: string | null;
  total_in_range: number;
  total_matched: number;
  assigned: number;
  skipped: number;
  conflicts: number;
  assigned_details: RangePreviewResult[];
  skipped_details: RangePreviewResult[];
  conflict_details: Array<RangePreviewResult & { current_mentor: MentorConflictInfo }>;
};

const emptyForm: FormValues = { fullName: '', email: '', password: '', facultyCode: '', departmentId: '' };
const facultyName = (faculty: Pick<Faculty, 'full_name' | 'email'>) => faculty.full_name || faculty.email.split('@')[0];
const yearName = (year: number | null) => year ? `${year}${year === 1 ? 'st' : year === 2 ? 'nd' : year === 3 ? 'rd' : 'th'} Year` : 'Not set';

export function AdminFacultyPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [departmentFilter, setDepartmentFilter] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 10;
  const [facultyModal, setFacultyModal] = useState(false);
  const [editing, setEditing] = useState<Faculty | null>(null);
  const [menteeTarget, setMenteeTarget] = useState<Faculty | null>(null);
  const [resetTarget, setResetTarget] = useState<Faculty | null>(null);
  const [notice, setNotice] = useState('');
  const [actionError, setActionError] = useState('');

  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (search.trim()) params.set('search', search.trim());
  if (departmentFilter) params.set('department_id', departmentFilter);

  const faculty = useQuery<FacultyPage>({
    queryKey: ['admin-faculty', params.toString()],
    queryFn: () => adminApi<FacultyPage>(`/admin/faculty?${params.toString()}`),
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
    if (faculty.data && page > faculty.data.pages) setPage(faculty.data.pages);
  }, [faculty.data, page]);

  const total = faculty.data?.total ?? 0;
  const pageCount = faculty.data?.pages ?? 1;
  const rows = faculty.data?.items ?? [];
  const hasFilters = Boolean(search || departmentFilter);
  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['admin-faculty'] }),
      queryClient.invalidateQueries({ queryKey: ['admin-departments'] }),
      queryClient.invalidateQueries({ queryKey: ['stats'] }),
    ]);
  };
  const openAdd = () => {
    setEditing(null);
    setFacultyModal(true);
  };
  const openEdit = (member: Faculty) => {
    setEditing(member);
    setFacultyModal(true);
  };
  const clearFilters = () => {
    setSearch('');
    setDepartmentFilter('');
    setPage(1);
  };

  return <div className="admin-faculty-page">
    <div className="admin-students-heading">
      <div><span className="admin-students-eyebrow">ACADEMIC DIRECTORY</span><h1>Faculty</h1><p>{total} {total === 1 ? 'faculty member' : 'faculty members'} in this view</p></div>
      <div className="admin-students-actions"><button className="admin-directory-primary" onClick={openAdd}><Plus/>Add faculty</button></div>
    </div>

    {notice && <div className="admin-toast" role="status"><Check/><span>{notice}</span><button onClick={() => setNotice('')} aria-label="Dismiss"><X/></button></div>}
    {actionError && <div className="admin-toast admin-toast-error" role="alert"><span>{actionError}</span><button onClick={() => setActionError('')} aria-label="Dismiss"><X/></button></div>}

    <section className="admin-student-filters admin-faculty-filters">
      <label className="admin-student-search"><span>Search</span><div><Search/><input placeholder="Name, email or faculty ID" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }}/></div></label>
      <label><span>Department</span><select value={departmentFilter} onChange={(event) => { setDepartmentFilter(event.target.value); setPage(1); }}><option value="">All departments</option>{(departments.data || []).map((department) => <option key={department.id} value={department.id}>{department.name}</option>)}</select></label>
      <button className="admin-student-clear" onClick={clearFilters} disabled={!hasFilters}>Clear</button>
    </section>

    <section className="admin-student-directory">
      <header><div><span className="admin-students-eyebrow">ROSTER</span><h2>Faculty directory</h2></div><span className="admin-student-result-count">{total ? `${(page - 1) * pageSize + 1}–${Math.min(page * pageSize, total)} of ${total}` : '0 of 0'}</span></header>
      <div className="admin-student-table-scroll"><table><thead><tr><th>Faculty ID</th><th>Faculty</th><th>Department</th><th>Mentees</th><th>Courses</th><th>Actions</th></tr></thead><tbody>
        {rows.map((member) => <tr key={member.id}>
          <td className="admin-reg-number">{member.faculty_code || 'Not set'}</td>
          <td><div className="admin-student-identity"><span><UserRound/></span><div><b>{facultyName(member)}</b><small>{member.email}</small></div></div></td>
          <td>{member.department?.name || 'Not set'}</td>
          <td><div className="admin-mentor-count"><span className="admin-mentor-count-icon"><ShieldCheck/></span><div className="admin-mentor-count-info"><b>{member.mentee_count}</b><small>{member.mentee_count === 1 ? 'mentee' : 'mentees'}</small></div></div></td>
          <td>{member.course_count}</td>
          <td><div className="admin-student-row-actions">
            <button type="button" className="admin-student-action" onClick={() => openEdit(member)}>Edit</button>
            <button type="button" className="admin-student-action mentor" onClick={() => setMenteeTarget(member)}>Mentees</button>
            <button type="button" className="admin-student-action" title="Reset password" onClick={() => setResetTarget(member)}>Reset</button>
          </div></td>
        </tr>)}
      </tbody></table>
      {faculty.isLoading && <div className="admin-student-empty"><span className="admin-student-spinner"/>Loading faculty directory…</div>}
      {faculty.isError && <div className="admin-student-empty admin-student-error">{faculty.error.message}</div>}
      {!faculty.isLoading && !faculty.isError && !rows.length && <div className="admin-student-empty"><Users/><b>{hasFilters ? 'No faculty match these filters.' : 'No faculty yet.'}</b><span>{hasFilters ? 'Clear a filter or adjust your search to see more faculty.' : 'Add a faculty account with its unique faculty ID and department.'}</span></div>}
      </div>
      <footer><span>Page {page} of {pageCount}</span><div><button onClick={() => setPage((value) => Math.max(1, value - 1))} disabled={page <= 1}><ChevronLeft/>Previous</button><button onClick={() => setPage((value) => Math.min(pageCount, value + 1))} disabled={page >= pageCount}>Next<ChevronRight/></button></div></footer>
    </section>

    {facultyModal && <FacultyModal faculty={editing} departments={departments.data || []} close={() => setFacultyModal(false)} refresh={refresh} notify={setNotice}/>}
    {menteeTarget && <MenteeModal faculty={menteeTarget} departments={departments.data || []} close={() => setMenteeTarget(null)} onDone={(message) => { setNotice(message); setActionError(''); void refresh(); }}/>}
    {resetTarget && <ResetPasswordDialog title="Reset faculty password" subject={`Set a new password for ${facultyName(resetTarget)} (${resetTarget.email}).`} endpoint={`/admin/faculty/${resetTarget.id}/reset-password`} close={() => setResetTarget(null)} onDone={() => { setNotice(`Password reset for ${facultyName(resetTarget)}.`); void refresh(); }}/>}
  </div>;
}

function FacultyModal({ faculty, departments, close, refresh, notify }: { faculty: Faculty | null; departments: Department[]; close: () => void; refresh: () => Promise<void>; notify: (message: string) => void }) {
  const [form, setForm] = useState<FormValues>(faculty ? {
    fullName: faculty.full_name || '',
    email: faculty.email,
    password: '',
    facultyCode: faculty.faculty_code || '',
    departmentId: faculty.department_id ? String(faculty.department_id) : '',
  } : emptyForm);
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);
  const update = (field: keyof FormValues, value: string) => setForm((current) => ({ ...current, [field]: value }));
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    setPending(true);
    const payload = {
      email: form.email.trim(),
      full_name: form.fullName.trim() || null,
      faculty_code: form.facultyCode.trim().toUpperCase(),
      department_id: form.departmentId ? Number(form.departmentId) : null,
    };
    try {
      if (faculty) {
        await adminApi(`/admin/faculty/${faculty.id}`, { method: 'PATCH', body: JSON.stringify(payload) });
        notify('Faculty details updated.');
      } else {
        await adminApi('/admin/faculty', { method: 'POST', body: JSON.stringify({ ...payload, password: form.password }) });
        notify('Faculty account created.');
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
          <h2>{faculty ? 'Edit faculty' : 'Add faculty'}</h2>
          <p>Faculty sign in with their email address. The faculty ID is a unique employee reference, not a login.</p>
        </div>
        <button type="button" className="admin-modal-close" onClick={close} aria-label="Close"><X/></button>
      </header>
      <div className="admin-modal-body">
        <div className="admin-modal-form-grid">
          <label>Full name<input value={form.fullName} onChange={(event) => update('fullName', event.target.value)} placeholder="Faculty name"/></label>
          <label>Email address<input type="email" value={form.email} onChange={(event) => update('email', event.target.value)} required placeholder="faculty@college.edu"/></label>
          {!faculty && <label className="admin-modal-form-span-2">Temporary password<input type="password" value={form.password} onChange={(event) => update('password', event.target.value)} minLength={8} required placeholder="At least 8 characters"/></label>}
          <label>Faculty ID<input value={form.facultyCode} onChange={(event) => update('facultyCode', event.target.value.toUpperCase())} required maxLength={40} placeholder="e.g. FAC-001"/></label>
          <label>Department<select value={form.departmentId} onChange={(event) => update('departmentId', event.target.value)}><option value="">Not set</option>{departments.map((department) => <option key={department.id} value={department.id}>{department.name}</option>)}</select></label>
        </div>
        {error && <p className="admin-modal-form-error">{error}</p>}
      </div>
      <footer className="admin-modal-footer">
        <button type="button" className="admin-btn admin-btn-secondary" onClick={close}>Cancel</button>
        <button type="submit" className="admin-btn admin-btn-primary" disabled={pending}>{pending ? 'Saving…' : faculty ? 'Save changes' : <><Check/>Create faculty</>}</button>
      </footer>
    </form>
  </div>;
}

function MenteeModal({ faculty, departments, close, onDone }: { faculty: Faculty; departments: Department[]; close: () => void; onDone: (message: string) => void }) {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [departmentFilter, setDepartmentFilter] = useState(faculty.department_id ? String(faculty.department_id) : '');
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [initialized, setInitialized] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  // Range assignment state
  const [rangeFrom, setRangeFrom] = useState('');
  const [rangeTo, setRangeTo] = useState('');
  const [rangeDepartment, setRangeDepartment] = useState('');
  const [rangeYear, setRangeYear] = useState('');
  const [rangeSection, setRangeSection] = useState('');
  const [previewResults, setPreviewResults] = useState<RangePreviewResult[]>([]);
  const [previewCount, setPreviewCount] = useState(0);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState('');
  const [previewMessage, setPreviewMessage] = useState('');
  const [assigningRange, setAssigningRange] = useState(false);
  const [rangeResult, setRangeResult] = useState<RangeAssignmentSummary | null>(null);

  const mentees = useQuery<Student[]>({
    queryKey: ['admin-faculty-mentees', faculty.id],
    queryFn: () => adminApi<Student[]>(`/admin/faculty/${faculty.id}/mentees`),
  });
  useEffect(() => {
    if (mentees.data && !initialized) {
      setSelected(new Set(mentees.data.map((student) => student.id)));
      setInitialized(true);
    }
  }, [mentees.data, initialized]);

  const studentParams = new URLSearchParams({ role: 'student', page_size: '100', sort: 'name' });
  if (search.trim()) studentParams.set('search', search.trim());
  if (departmentFilter) studentParams.set('department_id', departmentFilter);
  const students = useQuery<StudentPage>({
    queryKey: ['admin-faculty-student-picker', faculty.id, studentParams.toString()],
    queryFn: () => adminApi<StudentPage>(`/admin/users?${studentParams.toString()}`),
  });

  const existingIds = new Set((mentees.data || []).map((student) => student.id));
  const toggle = (studentId: number) => setSelected((current) => {
    const next = new Set(current);
    if (next.has(studentId)) next.delete(studentId);
    else next.add(studentId);
    return next;
  });
  const invalidate = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['admin-faculty'] }),
      queryClient.invalidateQueries({ queryKey: ['admin-faculty-mentees', faculty.id] }),
      queryClient.invalidateQueries({ queryKey: ['faculty-mentees'] }),
      queryClient.invalidateQueries({ queryKey: ['faculty-students'] }),
      queryClient.invalidateQueries({ queryKey: ['faculty-profile'] }),
    ]);
  };
  const removeMentee = async (studentId: number) => {
    setSaving(true);
    setError('');
    try {
      await adminApi(`/admin/faculty/${faculty.id}/mentees/${studentId}`, { method: 'DELETE' });
      setSelected((current) => {
        const next = new Set(current);
        next.delete(studentId);
        return next;
      });
      await invalidate();
    } catch (exception) {
      setError((exception as Error).message);
    } finally {
      setSaving(false);
    }
  };
  const save = async () => {
    setSaving(true);
    setError('');
    try {
      const toAdd = [...selected].filter((studentId) => !existingIds.has(studentId));
      const toRemove = [...existingIds].filter((studentId) => !selected.has(studentId));
      for (const studentId of toRemove) await adminApi(`/admin/faculty/${faculty.id}/mentees/${studentId}`, { method: 'DELETE' });
      if (toAdd.length) await adminApi(`/admin/faculty/${faculty.id}/mentees`, { method: 'POST', body: JSON.stringify({ student_ids: toAdd }) });
      await invalidate();
      onDone(toAdd.length || toRemove.length ? 'Mentee assignments updated.' : 'Mentee assignments are unchanged.');
      close();
    } catch (exception) {
      setError((exception as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const clearRange = () => {
    setRangeFrom('');
    setRangeTo('');
    setRangeDepartment('');
    setRangeYear('');
    setRangeSection('');
    setPreviewResults([]);
    setPreviewCount(0);
    setPreviewError('');
    setPreviewMessage('');
    setRangeResult(null);
  };

  const previewRangeStudents = async () => {
    setPreviewError('');
    setPreviewMessage('');
    setPreviewResults([]);
    setPreviewCount(0);
    setRangeResult(null);
    if (!rangeFrom.trim() || !rangeTo.trim()) {
      setPreviewError('Both From and To registration numbers are required.');
      return;
    }
    setPreviewLoading(true);
    try {
      const payload: Record<string, unknown> = {
        from_registration_number: rangeFrom.trim(),
        to_registration_number: rangeTo.trim(),
        preview: true,
      };
      if (rangeDepartment) payload.department_id = Number(rangeDepartment);
      if (rangeYear) payload.year_of_study = Number(rangeYear);
      if (rangeSection) payload.section_id = Number(rangeSection);
      const result = await adminApi<RangeAssignmentSummary>(`/admin/faculty/${faculty.id}/mentees/range`, {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      setPreviewResults(result.assigned_details || []);
      setPreviewCount(result.total_matched || 0);
      if (result.total_matched === 0) {
        setPreviewMessage('No students match the selected range and filters.');
      } else {
        setPreviewMessage(`Found ${result.total_matched} student${result.total_matched === 1 ? '' : 's'} in range. ${result.skipped} already assigned to this faculty, ${result.conflicts} assigned to another faculty.`);
      }
    } catch (exception) {
      setPreviewError((exception as Error).message);
    } finally {
      setPreviewLoading(false);
    }
  };

  const assignRangeStudents = async () => {
    setPreviewError('');
    setRangeResult(null);
    if (!rangeFrom.trim() || !rangeTo.trim()) {
      setPreviewError('Both From and To registration numbers are required.');
      return;
    }
    setAssigningRange(true);
    try {
      const payload: Record<string, unknown> = {
        from_registration_number: rangeFrom.trim(),
        to_registration_number: rangeTo.trim(),
        reassign_conflicts: false,
      };
      if (rangeDepartment) payload.department_id = Number(rangeDepartment);
      if (rangeYear) payload.year_of_study = Number(rangeYear);
      if (rangeSection) payload.section_id = Number(rangeSection);
      const result = await adminApi<RangeAssignmentSummary>(`/admin/faculty/${faculty.id}/mentees/range`, {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      setRangeResult(result);
      await invalidate();
      setPreviewResults(result.assigned_details || []);
      setPreviewCount(result.total_matched || 0);
      onDone(`Range assignment complete: ${result.assigned} assigned, ${result.skipped} skipped (already yours), ${result.conflicts} require reassignment.`);
      close();
    } catch (exception) {
      setPreviewError((exception as Error).message);
    } finally {
      setAssigningRange(false);
    }
  };

  return <div className="admin-modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) close(); }}>
    <section className="admin-modal admin-modal-lg">
      <header className="admin-modal-header">
        <div className="admin-modal-header-content">
          <span className="admin-modal-eyebrow">MENTOR ASSIGNMENT</span>
          <h2>{facultyName(faculty)} · {faculty.faculty_code || 'No faculty ID'}</h2>
          <p>Each student has at most one mentor. Assigning a student who already has a mentor moves them to this faculty member.</p>
        </div>
        <button type="button" className="admin-modal-close" onClick={close} aria-label="Close"><X/></button>
      </header>
      <div className="admin-modal-body">
        <section className="admin-current-mentees">
          <div className="admin-current-mentees-header">
            <b>Current mentees</b>
            <span className="admin-current-mentees-count">{mentees.data?.length ?? 0}</span>
          </div>
          {mentees.isLoading && <small className="admin-muted">Loading current mentees…</small>}
          {mentees.isError && <small className="admin-modal-form-error">{mentees.error.message}</small>}
          <div className="admin-current-mentees-list">
            {mentees.data?.map((student) => <div key={student.id} className="admin-current-mentee-row">
              <span className="admin-current-mentee-info"><b>{student.full_name || student.email.split('@')[0]}</b><small>{student.registration_number || 'No registration number'} · {student.department?.name || 'Not set'} · {student.section?.name || 'Not set'}</small></span>
              <button type="button" className="admin-btn admin-btn-ghost admin-btn-danger" disabled={saving} onClick={() => removeMentee(student.id)}><Trash2/>Remove</button>
            </div>)}
            {!mentees.isLoading && !mentees.isError && !mentees.data?.length && <small className="admin-current-mentee-empty">No mentees assigned yet.</small>}
          </div>
        </section>

        <div className="admin-modal-filter-bar">
          <label className="admin-search-field"><span>Search students</span><div><Search/><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Name, email or registration number"/></div></label>
          <label className="admin-select-field"><span>Department</span><select value={departmentFilter} onChange={(event) => setDepartmentFilter(event.target.value)}><option value="">All departments</option>{departments.map((department) => <option key={department.id} value={department.id}>{department.name}</option>)}</select></label>
        </div>
        <p className="admin-mentee-note">The picker starts in this faculty member's department. Choose All departments to assign cross-department mentees.</p>

        <div className="admin-mentee-list">
          {students.isLoading && <div className="admin-modal-loading"><span className="admin-modal-spinner"/>Loading students…</div>}
          {students.isError && <div className="admin-modal-error">{students.error.message}</div>}
          {!students.isLoading && !students.isError && !students.data?.items.length && <div className="admin-modal-empty"><Users/><b>No students match this filter.</b><span>Choose All departments to assign across departments.</span></div>}
          {students.data?.items.map((student) => {
            const checked = selected.has(student.id);
            const currentMentor = student.mentor?.id === faculty.id;
            return <label key={student.id} className={`admin-student-row${checked ? ' selected' : ''}`}>
              <span className="admin-student-row-checkbox">
                <input type="checkbox" className="admin-checkbox-input" checked={checked} onChange={() => toggle(student.id)}/>
                <span className="admin-checkbox-box"><Check/></span>
              </span>
              <span className="admin-student-row-main"><b>{student.full_name || student.email.split('@')[0]}</b><small>{student.email} · {student.registration_number || 'No registration number'}</small></span>
              <span className="admin-student-row-meta"><span>{student.department?.name || 'Not set'}</span><span>{student.section?.name || 'Not set'}</span><span>{yearName(student.year_of_study)}</span></span>
              <span className={currentMentor ? 'admin-student-row-status current' : student.mentor ? 'admin-student-row-status moving' : 'admin-student-row-status none'}>
                {currentMentor ? 'Current mentee' : student.mentor ? `Moves from ${student.mentor.faculty_code || student.mentor.full_name || student.mentor.email}` : 'No mentor'}
              </span>
            </label>;
          })}
        </div>

        {/* Assign by Register Number Range section */}
        <section className="admin-range-assign-section">
          <div className="admin-range-assign-header">
            <span className="admin-range-assign-title">Assign by Register Number Range</span>
          </div>
          <div className="admin-range-assign-form">
            <label className="admin-range-field">
              <span>From Register Number</span>
              <input value={rangeFrom} onChange={(event) => setRangeFrom(event.target.value)} placeholder="e.g. 411424243021" maxLength={64}/>
            </label>
            <label className="admin-range-field">
              <span>To Register Number</span>
              <input value={rangeTo} onChange={(event) => setRangeTo(event.target.value)} placeholder="e.g. 411424243054" maxLength={64}/>
            </label>
            <label className="admin-range-field">
              <span>Department</span>
              <select value={rangeDepartment} onChange={(event) => { setRangeDepartment(event.target.value); setRangeSection(''); }}>
                <option value="">All departments</option>
                {departments.map((department) => <option key={department.id} value={department.id}>{department.name}</option>)}
              </select>
            </label>
            <label className="admin-range-field">
              <span>Year of Study</span>
              <select value={rangeYear} onChange={(event) => setRangeYear(event.target.value)}>
                <option value="">All years</option>
                {[1, 2, 3, 4].map((year) => <option key={year} value={year}>{year === 1 ? '1st' : year === 2 ? '2nd' : year === 3 ? '3rd' : `${year}th`} Year</option>)}
              </select>
            </label>
            <label className="admin-range-field">
              <span>Section</span>
              <select value={rangeSection} onChange={(event) => setRangeSection(event.target.value)} disabled={!rangeDepartment}>
                <option value="">All sections</option>
                {departments.find((department) => String(department.id) === rangeDepartment)?.sections.map((section) => <option key={section.id} value={section.id}>{section.name}</option>)}
              </select>
            </label>
          </div>
          <div className="admin-range-assign-actions">
            <button type="button" className="admin-btn admin-btn-secondary" disabled={previewLoading || assigningRange} onClick={previewRangeStudents}>
              {previewLoading ? <span><RefreshCw className="admin-range-icon"/>Previewing…</span> : <span><Search/>Preview Students</span>}
            </button>
            <button type="button" className="admin-btn admin-btn-primary" disabled={assigningRange || !rangeFrom.trim() || !rangeTo.trim()} onClick={assignRangeStudents}>
              {assigningRange ? <span><Clock className="admin-range-icon"/>Assigning…</span> : <span><Check/>Assign Students</span>}
            </button>
            <button type="button" className="admin-btn admin-btn-ghost" onClick={clearRange} disabled={!rangeFrom && !rangeTo && !previewResults.length && !rangeResult}>Clear</button>
          </div>

          {previewError && <p className="admin-modal-form-error">{previewError}</p>}
          {previewMessage && <p className="admin-range-preview-message">{previewMessage}</p>}

          {previewLoading && <div className="admin-modal-loading"><span className="admin-modal-spinner"/>Finding students…</div>}

          {!previewLoading && previewResults.length > 0 && (
            <div className="admin-range-preview-list">
              <span className="admin-range-preview-count">{previewCount} student{previewCount === 1 ? '' : 's'} in preview</span>
              {previewResults.map((student) => <div key={student.student_id} className="admin-range-preview-row">
                <span className="admin-range-preview-reg">{student.registration_number || 'No reg number'}</span>
                <span className="admin-range-preview-name">{student.full_name || student.email.split('@')[0]}</span>
                <span className="admin-range-preview-email">{student.email}</span>
              </div>)}
            </div>
          )}

          {!previewLoading && !previewError && previewResults.length === 0 && previewMessage && (
            <div className="admin-modal-empty admin-range-empty-state">
              <Users/><b>{previewMessage}</b>
            </div>
          )}

          {rangeResult && (
            <div className="admin-range-result-summary">
              <div className="admin-range-result-header">
                <h3>Assignment Summary</h3>
              </div>
              <div className="admin-range-result-stats">
                <div className="admin-range-stat">
                  <span className="admin-range-stat-label">Total in range</span>
                  <span className="admin-range-stat-value">{rangeResult.total_matched}</span>
                </div>
                <div className="admin-range-stat admin-range-stat-assigned">
                  <span className="admin-range-stat-label">Assigned</span>
                  <span className="admin-range-stat-value">{rangeResult.assigned}</span>
                </div>
                <div className="admin-range-stat admin-range-stat-skipped">
                  <span className="admin-range-stat-label">Skipped (already yours)</span>
                  <span className="admin-range-stat-value">{rangeResult.skipped}</span>
                </div>
                <div className="admin-range-stat admin-range-stat-conflicts">
                  <span className="admin-range-stat-label">Conflicts (another mentor)</span>
                  <span className="admin-range-stat-value">{rangeResult.conflicts}</span>
                </div>
              </div>
              {rangeResult.conflict_details.length > 0 && (
                <div className="admin-range-conflicts">
                  <span className="admin-range-conflicts-title">Students requiring reassignment:</span>
                  {rangeResult.conflict_details.map((conflict) => <div key={conflict.student_id} className="admin-range-conflict-row">
                    <span>{conflict.registration_number}</span>
                    <span>{conflict.full_name}</span>
                    <span>{conflict.current_mentor?.faculty_code || conflict.current_mentor?.full_name || 'Unknown'}</span>
                  </div>)}
                </div>
              )}
            </div>
          )}
        </section>

        {error && <p className="admin-modal-form-error">{error}</p>}
      </div>
      <footer className="admin-modal-footer">
        <button type="button" className="admin-btn admin-btn-secondary" onClick={close}>Cancel</button>
        <button type="button" className="admin-btn admin-btn-primary" disabled={saving} onClick={save}>{saving ? 'Saving…' : 'Save mentees'}</button>
      </footer>
    </section>
  </div>;
}
