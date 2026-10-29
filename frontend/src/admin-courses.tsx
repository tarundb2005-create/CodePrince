import { type FormEvent, useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, ChevronLeft, ChevronRight, Plus, Search, ShieldCheck, Trash2, X, Pencil, Users, BookOpen, Edit3 } from 'lucide-react';
import { adminApi, ConfirmDialog } from './admin-shared';
import './admin-courses.css';

type Course = {
  id: number;
  title: string;
  code: string;
  description: string;
  faculty_id: number | null;
  active: boolean;
};

type Faculty = {
  id: number;
  email: string;
  full_name: string | null;
  faculty_code: string | null;
};

type FacultyPage = { items: Faculty[]; total: number; page: number; page_size: number; pages: number };

type FormValues = {
  title: string;
  code: string;
  description: string;
  facultyId: string;
};

const emptyForm: FormValues = { title: '', code: '', description: '', facultyId: '' };

export function AdminCoursesPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 10;
  const [courseModal, setCourseModal] = useState(false);
  const [editing, setEditing] = useState<Course | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Course | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState('');
  const [notice, setNotice] = useState('');
  const [actionError, setActionError] = useState('');

  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (search.trim()) params.set('search', search.trim());

  const courses = useQuery<Course[]>({
    queryKey: ['admin-courses', params.toString()],
    queryFn: () => adminApi<Course[]>(`/courses`),
  });
  const faculty = useQuery<FacultyPage>({
    queryKey: ['admin-faculty-all'],
    queryFn: () => adminApi<FacultyPage>('/admin/users?role=faculty&page_size=100'),
  });

  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(''), 4500);
    return () => window.clearTimeout(timer);
  }, [notice]);

  const total = courses.data?.length ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const pageRows = courses.data?.slice((page - 1) * pageSize, page * pageSize) ?? [];
  const hasFilters = Boolean(search);

  const clearFilters = () => {
    setSearch('');
    setPage(1);
  };
  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['admin-courses'] }),
      queryClient.invalidateQueries({ queryKey: ['admin-faculty-all'] }),
      queryClient.invalidateQueries({ queryKey: ['stats'] }),
    ]);
  };
  const openAdd = () => {
    setEditing(null);
    setCourseModal(true);
  };
  const openEdit = (course: Course) => {
    setEditing(course);
    setCourseModal(true);
  };

  async function removeCourse() {
    if (!deleteTarget) return;
    setDeleting(true);
    setDeleteError('');
    try {
      await adminApi(`/courses/${deleteTarget.id}`, { method: 'DELETE' });
      const name = deleteTarget.title;
      setDeleteTarget(null);
      await refresh();
      setNotice(`${name} removed.`);
    } catch (exception) {
      setDeleteError(exception instanceof Error ? exception.message : String(exception));
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="admin-courses-page">
      <div className="admin-students-heading">
        <div>
          <span className="admin-students-eyebrow">COURSE DIRECTORY</span>
          <h1>Courses</h1>
          <p>{total} {total === 1 ? 'course' : 'courses'} in this view</p>
        </div>
        <div className="admin-students-actions">
          <button className="admin-directory-primary" onClick={openAdd}><Plus />Add course</button>
        </div>
      </div>

      {notice && <div className="admin-toast" role="status"><Check /><span>{notice}</span><button onClick={() => setNotice('')} aria-label="Dismiss"><X /></button></div>}
      {actionError && <div className="admin-toast admin-toast-error" role="alert"><span>{actionError}</span><button onClick={() => setActionError('')} aria-label="Dismiss"><X /></button></div>}

      <section className="admin-student-filters admin-courses-filters">
        <label className="admin-student-search">
          <span>Search</span>
          <div><Search /><input placeholder="Course title or code" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} /></div>
        </label>
        <button className="admin-student-clear" onClick={clearFilters} disabled={!hasFilters}>Clear</button>
      </section>

      <section className="admin-student-directory">
        <header>
          <div><span className="admin-students-eyebrow">CATALOG</span><h2>Course directory</h2></div>
          <span className="admin-student-result-count">{total ? `${(page - 1) * pageSize + 1}–${Math.min(page * pageSize, total)} of ${total}` : '0 of 0'}</span>
        </header>
        <div className="admin-student-table-scroll">
          <table>
            <thead>
              <tr>
                <th>Code</th>
                <th>Course</th>
                <th>Faculty</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {pageRows.map((course) => (
                <tr key={course.id}>
                  <td className="admin-course-code">{course.code}</td>
                  <td>
                    <div className="admin-course-identity">
                      <span><BookOpen /></span>
                      <div>
                        <b>{course.title}</b>
                        {course.description && <small>{course.description}</small>}
                      </div>
                    </div>
                  </td>
                  <td>
                    {course.faculty_id ? (
                      (() => {
                        const f = faculty.data?.items?.find((fac) => fac.id === course.faculty_id);
                        return f ? (
                          <div className="admin-faculty-cell">
                            <span className="admin-faculty-avatar"><ShieldCheck /></span>
                            <div className="admin-faculty-info">
                              <b>{f.faculty_code || f.full_name || f.email}</b>
                              <small>{f.full_name || f.email}</small>
                            </div>
                          </div>
                        ) : (
                          <span className="admin-muted">Unknown faculty</span>
                        );
                      })()
                    ) : (
                      <span className="admin-muted">Not assigned</span>
                    )}
                  </td>
                  <td>
                    <span className={`admin-course-status ${course.active ? 'active' : 'inactive'}`}>
                      <i />
                      {course.active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td>
                    <div className="admin-student-row-actions">
                      <button type="button" className="admin-student-action" onClick={() => openEdit(course)} title="Edit course"><Pencil /></button>
                      <button type="button" className="admin-student-action" onClick={() => { /* TODO: View course details */ }} title="View course"><Users /></button>
                      <button type="button" className="admin-student-action danger" onClick={() => { setDeleteError(''); setDeleteTarget(course); }} title="Delete course"><Trash2 /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {courses.isLoading && <div className="admin-student-empty"><span className="admin-student-spinner" />Loading course directory…</div>}
          {courses.isError && <div className="admin-student-empty admin-student-error">{courses.error.message}</div>}
          {!courses.isLoading && !courses.isError && !pageRows.length && (
            <div className="admin-student-empty">
              <BookOpen />
              <b>{hasFilters ? 'No courses match these filters.' : 'No courses yet.'}</b>
              <span>{hasFilters ? 'Clear a filter or adjust your search to see more courses.' : 'Add a course to start building the catalog.'}</span>
            </div>
          )}
        </div>
        <footer>
          <span>Page {page} of {pageCount}</span>
          <div>
            <button onClick={() => setPage((value) => Math.max(1, value - 1))} disabled={page <= 1}><ChevronLeft />Previous</button>
            <button onClick={() => setPage((value) => Math.min(pageCount, value + 1))} disabled={page >= pageCount}>Next<ChevronRight /></button>
          </div>
        </footer>
      </section>

      {courseModal && <CourseModal course={editing} faculty={faculty.data?.items || []} close={() => setCourseModal(false)} refresh={refresh} notify={setNotice} />}
      {deleteTarget && (
        <ConfirmDialog
          title="Delete course permanently?"
          description={`${deleteTarget.title} (${deleteTarget.code}) will be removed. Any enrolled students, assessments, and problem mappings will be unlinked.`}
          confirmLabel="Delete course"
          pending={deleting}
          error={deleteError}
          close={() => setDeleteTarget(null)}
          onConfirm={removeCourse}
        />
      )}
    </div>
  );
}

function CourseModal({ course, faculty, close, refresh, notify }: { course: Course | null; faculty: Faculty[]; close: () => void; refresh: () => Promise<void>; notify: (message: string) => void }) {
  const [form, setForm] = useState<FormValues>(course ? {
    title: course.title,
    code: course.code,
    description: course.description || '',
    facultyId: course.faculty_id ? String(course.faculty_id) : '',
  } : emptyForm);
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);
  const update = (field: keyof FormValues, value: string) => setForm((current) => ({ ...current, [field]: value }));

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    setPending(true);
    const payload = {
      title: form.title.trim(),
      code: form.code.trim().toUpperCase(),
      description: form.description.trim() || '',
      faculty_id: form.facultyId ? Number(form.facultyId) : null,
    };
    try {
      if (course) {
        await adminApi(`/courses/${course.id}`, { method: 'PATCH', body: JSON.stringify(payload) });
        notify('Course updated.');
      } else {
        await adminApi('/courses', { method: 'POST', body: JSON.stringify(payload) });
        notify('Course created.');
      }
      await refresh();
      close();
    } catch (exception) {
      setError(exception instanceof Error ? exception.message : String(exception));
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="admin-modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) close(); }}>
      <form className="admin-modal admin-modal-md" onSubmit={submit}>
        <header className="admin-modal-header">
          <div className="admin-modal-header-content">
            <span className="admin-modal-eyebrow">COURSE DIRECTORY</span>
            <h2>{course ? 'Edit course' : 'Add course'}</h2>
            <p>{course ? 'Update course details and faculty assignment.' : 'Create a new course with its code, title, and assigned faculty.'}</p>
          </div>
          <button type="button" className="admin-modal-close" onClick={close} aria-label="Close"><X /></button>
        </header>
        <div className="admin-modal-body">
          <div className="admin-modal-form-grid">
            <label>Course title<input value={form.title} onChange={(event) => update('title', event.target.value)} required placeholder="e.g. Data Structures & Algorithms" /></label>
            <label>Course code<input value={form.code} onChange={(event) => update('code', event.target.value.toUpperCase())} required maxLength={40} placeholder="e.g. CS201" /></label>
            <label className="admin-modal-form-span-2">Description<textarea value={form.description} onChange={(event) => update('description', event.target.value)} placeholder="Optional description" rows={3} /></label>
            <label>Faculty<select value={form.facultyId} onChange={(event) => update('facultyId', event.target.value)}><option value="">Not assigned</option>{faculty.map((member) => <option key={member.id} value={member.id}>{member.faculty_code || member.full_name || member.email}</option>)}</select></label>
          </div>
          {error && <p className="admin-modal-form-error">{error}</p>}
        </div>
        <footer className="admin-modal-footer">
          <button type="button" className="admin-btn admin-btn-secondary" onClick={close}>Cancel</button>
          <button type="submit" className="admin-btn admin-btn-primary" disabled={pending}>{pending ? 'Saving…' : course ? 'Save changes' : <><Check />Create course</>}</button>
        </footer>
      </form>
    </div>
  );
}