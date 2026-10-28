import { type FormEvent, useEffect, useMemo, useState } from 'react';
import { Link, Navigate, Route, Routes, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Award, BookOpen, CalendarClock, Check, ChevronRight, ClipboardCheck, ClipboardList, GraduationCap, LayoutDashboard, LogOut, Menu, Plus, Search, ShieldCheck, Users, X } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import './faculty.css';
import './faculty-progress.css';
import './faculty-roster.css';
import './faculty-assignments.css';
import './white-accent.css';

type FacultyMe = { id: number; email: string; role: string };
type Course = { id: number; title: string; code: string; description: string; faculty_id: number | null; active: boolean };
type Question = { id: number; title: string; slug: string; difficulty: string; topic: string };
type Assessment = { id: number; course_id: number; title: string; description: string; starts_at: string | null; ends_at: string | null; published: boolean };
type Student = { id: number; email: string; registration_number: string | null; full_name?: string | null; year_of_study?: number | null; department?: string | null; section?: string | null; course_count?: number; mapped_at?: string };
type AcademicDepartment = { id: number; name: string; sections: { id: number; name: string }[] };
const fallbackAcademicOptions: AcademicDepartment[] = [
  { id: 1, name: 'CSE', sections: [{ id: 101, name: 'Section A' }, { id: 102, name: 'Section B' }, { id: 103, name: 'Section C' }] },
  { id: 2, name: 'IT', sections: [{ id: 201, name: 'Section A' }, { id: 202, name: 'Section B' }, { id: 203, name: 'Section C' }] },
  { id: 3, name: 'AIDS', sections: [{ id: 301, name: 'Section A' }, { id: 302, name: 'Section B' }, { id: 303, name: 'Section C' }] },
  { id: 4, name: 'CYBER', sections: [{ id: 401, name: 'Section A' }, { id: 402, name: 'Section B' }, { id: 403, name: 'Section C' }] },
  { id: 5, name: 'MECH', sections: [{ id: 501, name: 'Section A' }, { id: 502, name: 'Section B' }, { id: 503, name: 'Section C' }] },
  { id: 6, name: 'ECE', sections: [{ id: 601, name: 'Section A' }, { id: 602, name: 'Section B' }, { id: 603, name: 'Section C' }] },
  { id: 7, name: 'EEE', sections: [{ id: 701, name: 'Section A' }, { id: 702, name: 'Section B' }, { id: 703, name: 'Section C' }] },
];
type ProgressRow = { student_id: number; email: string; registration_number: string | null; solved: number; total: number; attempts: number; submissions: number; last_active: string | null };
type ResultRow = { student_id: number; email: string; registration_number: string | null; score: number; out_of: number; submitted_at: string | null; shared: boolean };
type ProblemAssignment = { id: number; student_id: number; student_email: string; registration_number: string | null; question_id: number; question_title: string; difficulty: string; topic: string; due_at: string | null; note: string; created_at: string; completed: boolean };

const api = async (path: string, options: RequestInit = {}) => {
  const response = await fetch(`/api${path}`, { credentials: 'include', headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }, ...options });
  if (!response.ok) throw Error((await response.json().catch(() => ({ detail: response.statusText }))).detail || response.statusText);
  return response.status === 204 ? null : response.json();
};

const navigation = [
  ['Overview', '/faculty/overview', LayoutDashboard],
  ['Courses & students', '/faculty/courses', Users],
  ['Student progress', '/faculty/progress', GraduationCap],
  ['Problem', '/faculty/problem-assignments', ClipboardList],
  ['Assessments', '/faculty/assessments', CalendarClock],
  ['Results', '/faculty/results', ClipboardCheck],
] as const;

function initials(value: string) { return value.split('@')[0].split(/[._-]/).map((part) => part[0]).join('').slice(0, 2).toUpperCase() || 'F'; }
function prettyDate(value: string | null) { return value ? new Date(value).toLocaleString() : '—'; }
function assessmentState(assessment: Assessment) {
  if (!assessment.published) return 'Draft';
  const now = Date.now();
  if (assessment.starts_at && now < new Date(assessment.starts_at).getTime()) return 'Scheduled';
  if (assessment.ends_at && now > new Date(assessment.ends_at).getTime()) return 'Closed';
  return 'Live';
}

function FacultySidebar({ me, open, close }: { me: FacultyMe; open: boolean; close: () => void }) {
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const logout = async () => { await api('/auth/logout', { method: 'POST' }); queryClient.clear(); navigate('/'); };
  return <><aside className={`faculty-sidebar ${open ? 'open' : ''}`}><div className="faculty-brand"><Award/><span><b>CodePrince</b><small>Faculty workspace</small></span><button className="faculty-close" onClick={close} aria-label="Close navigation"><X/></button></div><p className="faculty-nav-label">TEACHING</p><nav>{navigation.map(([label, path, Icon]) => <Link key={path} to={path} className={location.pathname === path ? 'active' : ''} onClick={(event) => { event.preventDefault(); close(); navigate(path); }}><Icon/><span>{label}</span></Link>)}</nav><div className="faculty-account"><span className="faculty-avatar">{initials(me.email)}</span><span><b>{me.email.split('@')[0]}</b><small>Faculty</small></span><button onClick={logout} title="Log out"><LogOut/></button></div></aside>{open && <button className="faculty-backdrop" onClick={close} aria-label="Close navigation"/>}</>;
}

function FacultyLayout({ me }: { me: FacultyMe }) {
  const [open, setOpen] = useState(false);
  return <div className="faculty-app"><FacultySidebar me={me} open={open} close={() => setOpen(false)}/><main className="faculty-main"><header className="faculty-header"><button className="faculty-menu" onClick={() => setOpen(true)} aria-label="Open navigation"><Menu/></button><div><span className="faculty-eyebrow">FACULTY PORTAL</span><b>Teaching workspace</b></div><div className="faculty-header-user"><span className="faculty-avatar">{initials(me.email)}</span><span>{me.email}</span></div></header><Routes><Route path="/faculty" element={<Navigate to="/faculty/overview" replace/>}/><Route path="/faculty/overview" element={<FacultyOverview/>}/><Route path="/faculty/courses/*" element={<CoursesPage/>}/><Route path="/faculty/progress" element={<ProgressPage/>}/><Route path="/faculty/problem-assignments" element={<ProblemAssignmentsPage/>}/><Route path="/faculty/assessments" element={<AssessmentsPage/>}/><Route path="/faculty/results" element={<ResultsPage/>}/><Route path="*" element={<Navigate to="/faculty/overview" replace/>}/></Routes></main></div>;
}

function FacultyOverview() {
  const courses = useQuery<Course[]>({ queryKey: ['faculty-courses'], queryFn: () => api('/courses') });
  const assessments = useQuery<Assessment[]>({ queryKey: ['faculty-assessments'], queryFn: () => api('/assessments') });
  const courseRows = courses.data || [];
  const roster = useQuery<Student[]>({ queryKey: ['faculty-students'], queryFn: () => api('/faculty/students') });
  const studentCount = roster.data?.length ?? 0;
  const published = (assessments.data || []).filter((item) => item.published).length;
  const live = (assessments.data || []).filter((item) => assessmentState(item) === 'Live').length;
  return <div className="faculty-page"><section className="faculty-welcome"><div><span className="faculty-eyebrow">YOUR TEACHING SPACE</span><h1>Welcome to your faculty portal.</h1><p>Connect students to courses, follow their progress, and run assessments from one place.</p><div className="faculty-actions"><Link to="/faculty/courses" className="faculty-primary">Manage courses <ChevronRight/></Link><Link to="/faculty/assessments" className="faculty-secondary">Plan an assessment</Link></div></div><div className="faculty-welcome-mark"><BookOpen/><span>TEACH · GUIDE · GROW</span></div></section><section className="faculty-stats"><Stat label="Your courses" value={courses.data?.length ?? '—'} detail="Courses assigned to you" icon={BookOpen}/><Stat label="Mapped students" value={roster.isLoading ? '—' : studentCount} detail="Unique students in your courses" icon={Users}/><Stat label="Published assessments" value={published} detail="Visible to enrolled students" icon={ClipboardCheck}/><Stat label="Live now" value={live} detail="Open assessment windows" icon={CalendarClock}/></section><div className="faculty-grid"><section className="faculty-card"><div className="faculty-section-title"><div><span className="faculty-eyebrow">COURSES</span><h2>Teaching roster</h2></div><Link to="/faculty/courses">View all</Link></div>{courseRows.slice(0, 5).map((course) => <div className="faculty-list-row" key={course.id}><span className="faculty-row-icon"><BookOpen/></span><div><b>{course.title}</b><small>{course.code} · {course.description || 'Course workspace'}</small></div><Link to="/faculty/progress" aria-label={`View progress for ${course.title}`}><ChevronRight/></Link></div>)}{courses.isLoading && <p className="faculty-empty">Loading your courses…</p>}{courses.isError && <p className="faculty-error">{courses.error.message}</p>}{!courses.isLoading && !courseRows.length && <p className="faculty-empty">No assigned courses yet. Ask an administrator to assign a course to your faculty account.</p>}</section><section className="faculty-card"><div className="faculty-section-title"><div><span className="faculty-eyebrow">ASSESSMENTS</span><h2>Assessment activity</h2></div><Link to="/faculty/assessments">Manage</Link></div>{(assessments.data || []).slice(0, 5).map((item) => <div className="faculty-list-row" key={item.id}><span className="faculty-row-icon"><CalendarClock/></span><div><b>{item.title}</b><small>{prettyDate(item.starts_at)}</small></div><span className={`faculty-badge ${assessmentState(item).toLowerCase()}`}>{assessmentState(item)}</span></div>)}{assessments.isLoading && <p className="faculty-empty">Loading assessments…</p>}{!assessments.isLoading && !assessments.data?.length && <p className="faculty-empty">Your assessments will appear here.</p>}</section></div><section className="faculty-card faculty-steps"><span className="faculty-eyebrow">QUICK START</span><div><b>1. Get an assigned course</b><span>An administrator creates a course and assigns it to your account.</span></div><div><b>2. Map students</b><span>Use each student's registration number to enroll them.</span></div><div><b>3. Run and share</b><span>Publish assessments, review results, and share scores.</span></div></section></div>;
}

function Stat({ label, value, detail, icon: Icon }: { label: string; value: string | number; detail: string; icon: typeof Award }) { return <article className="faculty-stat"><span className="faculty-stat-icon"><Icon/></span><div><small>{label}</small><strong>{value}</strong><em>{detail}</em></div></article>; }

function CoursesPage() {
  const courses = useQuery<Course[]>({ queryKey: ['faculty-courses'], queryFn: () => api('/courses') });
  const courseRows = courses.data || [];
  return <div className="faculty-page"><PageHeading eyebrow="COURSES & STUDENTS" title="Manage your teaching roster." description="Choose a course, then map students by registration number directly into that course."/>
    <section className="faculty-card faculty-course-directory">
      <div className="faculty-section-title"><div><span className="faculty-eyebrow">ASSIGNED COURSES</span><h2>Your course list</h2></div><span className="faculty-count">{courseRows.length} course{courseRows.length === 1 ? '' : 's'}</span></div>
      {courseRows.length > 0 && <div className="faculty-course-directory-list">{courseRows.map((course) => <a href={`#faculty-course-${course.id}`} key={course.id}><span className="faculty-course-code">{course.code}</span><span><b>{course.title}</b><small>{course.description || 'Course workspace'}</small></span><span className="faculty-directory-action">Map students <ChevronRight/></span></a>)}</div>}
      {courses.isLoading && <p className="faculty-empty">Loading your assigned courses…</p>}
      {courses.isError && <p className="faculty-error">{courses.error.message}</p>}
      {!courses.isLoading && !courses.isError && !courseRows.length && <p className="faculty-empty">No courses are assigned to your account yet. Ask an administrator to create a course and assign it to you.</p>}
    </section>
    <div className="faculty-course-list">{courseRows.map((course) => <CourseCard key={course.id} course={course}/>)} </div>
    <FacultyStudentMapper courses={courseRows}/>
  </div>;
}

function FacultyStudentMapper({ courses }: { courses: Course[] }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const students = useQuery<Student[]>({ queryKey: ['faculty-students'], queryFn: () => api('/faculty/students') });
  const academicOptions = useQuery<AcademicDepartment[]>({ queryKey: ['faculty-academic-options'], retry: false, queryFn: async () => { try { const options = await api('/faculty/academic-options') as AcademicDepartment[]; return options.length ? options : fallbackAcademicOptions; } catch { return fallbackAcademicOptions; } } });
  const [courseId, setCourseId] = useState('');
  const [registrationNumber, setRegistrationNumber] = useState('');
  const [mapping, setMapping] = useState(false);
  const [mapMessage, setMapMessage] = useState('');
  const [mapError, setMapError] = useState('');
  const [search, setSearch] = useState('');
  const [yearFilter, setYearFilter] = useState('');
  const [departmentFilter, setDepartmentFilter] = useState('');
  const [sectionFilter, setSectionFilter] = useState('');
  const [enrollmentFilter, setEnrollmentFilter] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 8;
  const studentRows = students.data || [];
  const years = [1, 2, 3, 4];
  const departments = academicOptions.data || [];
  const sections = departments.find((department) => department.name === departmentFilter)?.sections || [];
  const visibleStudents = useMemo(() => studentRows.filter((student) => {
    const term = search.trim().toLowerCase();
    return (!term || [student.full_name, student.email, student.registration_number].some((value) => value?.toLowerCase().includes(term)))
      && (!yearFilter || String(student.year_of_study || '') === yearFilter)
      && (!departmentFilter || student.department === departmentFilter)
      && (!sectionFilter || student.section === sectionFilter)
      && (!enrollmentFilter || (enrollmentFilter === 'enrolled' ? (student.course_count || 0) > 0 : (student.course_count || 0) === 0));
  }), [studentRows, search, yearFilter, departmentFilter, sectionFilter, enrollmentFilter]);
  const pageCount = Math.max(1, Math.ceil(visibleStudents.length / pageSize));
  const pageRows = visibleStudents.slice((page - 1) * pageSize, page * pageSize);
  const hasFilters = Boolean(search || yearFilter || departmentFilter || sectionFilter || enrollmentFilter);
  useEffect(() => {
    if (!courses.length) {
      setCourseId('');
    } else if (!courses.some((course) => String(course.id) === courseId)) {
      setCourseId(String(courses[0].id));
    }
  }, [courses, courseId]);
  useEffect(() => { if (students.error?.message === 'Authentication required') navigate('/', { replace: true }); }, [students.error, navigate]);
  const clearFilters = () => { setSearch(''); setYearFilter(''); setDepartmentFilter(''); setSectionFilter(''); setEnrollmentFilter(''); setPage(1); };
  const mapStudent = async (event: FormEvent) => {
    event.preventDefault();
    if (!courseId || !registrationNumber.trim()) return;
    setMapping(true); setMapMessage(''); setMapError('');
    try {
      await api(`/courses/${courseId}/students?registration_number=${encodeURIComponent(registrationNumber.trim())}`, { method: 'POST' });
      setRegistrationNumber('');
      setMapMessage('Student mapped to the selected course.');
      await queryClient.invalidateQueries({ queryKey: ['faculty-students'] });
      await queryClient.invalidateQueries({ queryKey: ['faculty-course-students', Number(courseId)] });
    } catch (exception) {
      setMapError((exception as Error).message);
    } finally {
      setMapping(false);
    }
  };
  return <section className="faculty-card faculty-account-roster-card">
    <div className="faculty-section-title"><div><span className="faculty-eyebrow">FACULTY ROSTER</span><h2>Student directory</h2></div><span className="faculty-count">{studentRows.length} mapped</span></div>
    <p className="faculty-account-roster-description">Students appear here after they are mapped into one of your courses. Use the registration-number form inside the relevant course card above.</p>
    <div className="faculty-directory-map">
      <div><b>Map a student</b><p>Choose a course and enter the student's registration number to enroll them immediately.</p></div>
      <form className="faculty-inline-form" onSubmit={mapStudent}>
        <select aria-label="Course for mapped student" value={courseId} onChange={(event) => setCourseId(event.target.value)} disabled={!courses.length || mapping} required>
          {!courses.length && <option value="">Assign a course first</option>}
          {courses.map((course) => <option value={course.id} key={course.id}>{course.code} · {course.title}</option>)}
        </select>
        <input aria-label="Student registration number" value={registrationNumber} onChange={(event) => setRegistrationNumber(event.target.value)} disabled={!courses.length || mapping} required placeholder="Registration number"/>
        <button className="faculty-primary" disabled={!courses.length || mapping}>{mapping ? 'Mapping…' : <><Plus/>Map student</>}</button>
      </form>
    </div>
    {mapMessage && <p className="faculty-success">{mapMessage}</p>}
    {mapError && <p className="faculty-error">{mapError}</p>}
    <div className="faculty-directory-filters">
      <label className="faculty-directory-search"><span>Search</span><div><Search/><input value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} placeholder="Name, email or registration number"/></div></label>
      <label><span>Year</span><select value={yearFilter} onChange={(event) => { setYearFilter(event.target.value); setPage(1); }}><option value="">All years</option>{years.map((year) => <option key={year} value={year}>{year === 1 ? '1st' : year === 2 ? '2nd' : year === 3 ? '3rd' : `${year}th`} Year</option>)}</select></label>
      <label><span>Department</span><select value={departmentFilter} onChange={(event) => { setDepartmentFilter(event.target.value); setSectionFilter(''); setPage(1); }}><option value="">All departments</option>{departments.map((department) => <option key={department.id} value={department.name}>{department.name}</option>)}</select></label>
      <label><span>Section</span><select value={sectionFilter} onChange={(event) => { setSectionFilter(event.target.value); setPage(1); }} disabled={!departmentFilter || academicOptions.isLoading}><option value="">{departmentFilter ? 'All sections' : 'Year & department'}</option>{sections.map((section) => <option key={section.id} value={section.name}>{section.name}</option>)}</select></label>
      <label><span>Course status</span><select value={enrollmentFilter} onChange={(event) => { setEnrollmentFilter(event.target.value); setPage(1); }}><option value="">All students</option><option value="enrolled">Enrolled</option><option value="unassigned">Not enrolled</option></select></label>
      <button className="faculty-directory-clear" onClick={clearFilters} disabled={!hasFilters}>Clear</button>
    </div>
    <div className="faculty-directory-table-wrap">
      <table className="faculty-table"><thead><tr><th>Registration no.</th><th>Student</th><th>Year</th><th>Department</th><th>Section</th><th>Status</th><th>Actions</th></tr></thead><tbody>
        {pageRows.map((student) => <tr key={student.id}><td><strong className="faculty-directory-reg">{student.registration_number || '—'}</strong></td><td><div className="faculty-directory-student"><span className="faculty-avatar">{initials(student.email)}</span><span><b>{student.full_name || student.email.split('@')[0]}</b><small>{student.email}</small></span></div></td><td>{student.year_of_study ? `${student.year_of_study}${student.year_of_study === 1 ? 'st' : student.year_of_study === 2 ? 'nd' : student.year_of_study === 3 ? 'rd' : 'th'} Year` : '—'}</td><td>{student.department || '—'}</td><td>{student.section || '—'}</td><td><span className={`faculty-badge ${(student.course_count || 0) ? 'shared' : 'draft'}`}>{(student.course_count || 0) ? `${student.course_count} course${student.course_count === 1 ? '' : 's'}` : 'Roster only'}</span></td><td><Link className="faculty-directory-action" to="/faculty/progress">Progress <ChevronRight/></Link></td></tr>)}
      </tbody></table>
      {students.isLoading && <p className="faculty-empty">Loading your student directory…</p>}
      {students.isError && <p className="faculty-error">Your session has expired. Please sign in again.</p>}
      {!students.isLoading && !students.isError && !pageRows.length && <div className="faculty-directory-empty"><Users/><b>{hasFilters ? 'No students match these filters.' : 'No students mapped yet.'}</b><span>{hasFilters ? 'Clear a filter or adjust your search.' : 'Map a student with their registration number above.'}</span></div>}
    </div>
    <div className="faculty-directory-pagination"><span>{visibleStudents.length ? `${(page - 1) * pageSize + 1}–${Math.min(page * pageSize, visibleStudents.length)} of ${visibleStudents.length}` : '0 of 0'}</span><div><button onClick={() => setPage((value) => Math.max(1, value - 1))} disabled={page <= 1}><ChevronRight className="faculty-page-prev"/>Previous</button><span>Page {page} of {pageCount}</span><button onClick={() => setPage((value) => Math.min(pageCount, value + 1))} disabled={page >= pageCount}>Next<ChevronRight/></button></div></div>
  </section>;
}
function CourseCard({ course }: { course: Course }) {
  const queryClient = useQueryClient();
  const students = useQuery<Student[]>({ queryKey: ['faculty-course-students', course.id], queryFn: () => api(`/courses/${course.id}/students`) });
  const courseQuestions = useQuery<Question[]>({ queryKey: ['faculty-course-questions', course.id], queryFn: () => api(`/courses/${course.id}/questions`) });
  const bank = useQuery<{ items: Question[] }>({ queryKey: ['faculty-question-bank'], queryFn: () => api('/questions?page_size=100') });
  const [registrationNumber, setRegistrationNumber] = useState('');
  const [questionId, setQuestionId] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const mappedIds = new Set((courseQuestions.data || []).map((question) => question.id));
  const available = (bank.data?.items || []).filter((question) => !mappedIds.has(question.id));
  const mapStudent = async (event: FormEvent) => { event.preventDefault(); setMessage(''); setError(''); try { await api(`/courses/${course.id}/students?registration_number=${encodeURIComponent(registrationNumber.trim())}`, { method: 'POST' }); setRegistrationNumber(''); setMessage('Student mapped to this course.'); await queryClient.invalidateQueries({ queryKey: ['faculty-course-students', course.id] }); await queryClient.invalidateQueries({ queryKey: ['faculty-students'] }); } catch (exception) { setError((exception as Error).message); } };
  const addQuestion = async (event: FormEvent) => { event.preventDefault(); if (!questionId) return; setMessage(''); setError(''); try { await api(`/courses/${course.id}/questions?question_id=${questionId}`, { method: 'POST' }); setQuestionId(''); setMessage('Question added to the course.'); await queryClient.invalidateQueries({ queryKey: ['faculty-course-questions', course.id] }); } catch (exception) { setError((exception as Error).message); } };
  return <section id={`faculty-course-${course.id}`} className="faculty-card faculty-course-card"><div className="faculty-course-heading"><span className="faculty-course-code">{course.code}</span><div><h2>{course.title}</h2><p>{course.description || 'Course workspace'}</p></div><span className="faculty-count">{students.data?.length ?? '—'} students</span></div><div className="faculty-course-columns"><div><h3>Map a student to this course</h3><p>Enter the registration number used on the student account. This also adds the student to your faculty roster.</p><form className="faculty-inline-form" onSubmit={mapStudent}><input aria-label={`Student registration number for ${course.title}`} value={registrationNumber} onChange={(event) => setRegistrationNumber(event.target.value)} required placeholder="e.g. 23CS1042"/><button className="faculty-secondary" disabled={students.isFetching}>Map student</button></form><div className="faculty-roster">{(students.data || []).map((student) => <div key={student.id}><span className="faculty-avatar">{initials(student.email)}</span><span><b>{student.email}</b><small>{student.registration_number || 'No registration number'}</small></span></div>)}{students.isLoading && <small className="faculty-muted">Loading student roster…</small>}{!students.isLoading && !students.data?.length && <small className="faculty-muted">No students mapped to this course yet.</small>}</div></div><div><h3>Course problem set</h3><p>Questions added here power course progress and can be used in assessments.</p><form className="faculty-inline-form" onSubmit={addQuestion}><select aria-label="Question to add" value={questionId} onChange={(event) => setQuestionId(event.target.value)} required><option value="">Choose a question</option>{available.map((question) => <option value={question.id} key={question.id}>{question.title}</option>)}</select><button className="faculty-secondary" disabled={!available.length}>Add</button></form><div className="faculty-question-list">{(courseQuestions.data || []).map((question) => <div key={question.id}><span>{question.title}</span><small>{question.difficulty} · {question.topic}</small></div>)}{courseQuestions.isLoading && <small className="faculty-muted">Loading problem set…</small>}{!courseQuestions.isLoading && !courseQuestions.data?.length && <small className="faculty-muted">Add questions to begin tracking course progress.</small>}</div></div></div>{message && <p className="faculty-success">{message}</p>}{error && <p className="faculty-error">{error}</p>}</section>;
}

function ProgressPage() {
  const courses = useQuery<Course[]>({ queryKey: ['faculty-courses'], queryFn: () => api('/courses') });
  const [courseId, setCourseId] = useState('');
  useEffect(() => { if (!courseId && courses.data?.length) setCourseId(String(courses.data[0].id)); }, [courses.data, courseId]);
  const progress = useQuery<ProgressRow[]>({ queryKey: ['faculty-progress', courseId], queryFn: () => api(`/courses/${courseId}/progress`), enabled: Boolean(courseId) });
  const chartData = useMemo(() => (progress.data || []).map((row) => {
    const studentLabel = row.registration_number?.trim() || row.email.split('@')[0];
    return {
      ...row,
      label: studentLabel.length > 18 ? `${studentLabel.slice(0, 16)}…` : studentLabel,
      remaining: Math.max(0, row.total - row.solved),
      completion: row.total ? Math.min(100, Math.round(row.solved / row.total * 100)) : 0,
    };
  }), [progress.data]);
  const averageCompletion = chartData.length ? Math.round(chartData.reduce((sum, row) => sum + row.completion, 0) / chartData.length) : 0;
  const totalSubmissions = chartData.reduce((sum, row) => sum + row.submissions, 0);
  const questionCount = chartData[0]?.total ?? 0;

  return <div className="faculty-page">
    <PageHeading eyebrow="STUDENT PROGRESS" title="See how each student is progressing." description="Progress is based on the questions attached to the selected course, with submission activity shown alongside it."/>
    <section className="faculty-toolbar faculty-card">
      <label>Course<select value={courseId} onChange={(event) => setCourseId(event.target.value)}><option value="">Choose a course</option>{(courses.data || []).map((course) => <option key={course.id} value={course.id}>{course.code} · {course.title}</option>)}</select></label>
      <span>{progress.data?.length ?? 0} mapped students</span>
    </section>
    <section className="faculty-card faculty-table-wrap">
      <table className="faculty-table"><thead><tr><th>Student</th><th>Registration no.</th><th>Course problems</th><th>Attempts</th><th>Submissions</th><th>Last active</th></tr></thead><tbody>{(progress.data || []).map((row) => <tr key={row.student_id}><td className="faculty-progress-student"><b>{row.email}</b></td><td>{row.registration_number || '—'}</td><td className="faculty-progress-problems">{row.total > 0 ? <><span className="faculty-progress-value">{row.solved}<small> / {row.total} solved</small></span><i className="faculty-progress-track"><em style={{ width: `${Math.min(100, row.solved / row.total * 100)}%` }}/></i></> : <span className="faculty-progress-empty">No problems added</span>}</td><td>{row.attempts}</td><td>{row.submissions}</td><td>{prettyDate(row.last_active)}</td></tr>)}</tbody></table>
      {progress.isLoading && <p className="faculty-empty">Loading student progress…</p>}
      {progress.isError && <p className="faculty-error">{progress.error.message}</p>}
      {!progress.isLoading && progress.data?.length === 0 && <p className="faculty-empty">No mapped students yet. Add students by registration number in Courses & students.</p>}
      {!courses.isLoading && courses.data?.length === 0 && <p className="faculty-empty">Ask an administrator to create and assign a course before viewing student progress.</p>}
    </section>
    <section className="faculty-card faculty-completion-card">
      <div className="faculty-completion-header">
        <div><span className="faculty-eyebrow">COURSE COMPLETION</span><h2>Question completion by student</h2><p>Solved questions compared with the selected course problem set.</p></div>
        {chartData.length > 0 && <div className="faculty-completion-metrics"><div><strong>{averageCompletion}%</strong><small>Average complete</small></div><div><strong>{chartData.length}</strong><small>Students</small></div><div><strong>{totalSubmissions}</strong><small>Submissions</small></div></div>}
      </div>
      {progress.isLoading && <p className="faculty-empty">Loading chart data…</p>}
      {progress.isError && <p className="faculty-error">Could not load chart data.</p>}
      {!progress.isLoading && !progress.isError && !courseId && <p className="faculty-chart-empty">Choose an assigned course to see its progress chart.</p>}
      {!progress.isLoading && !progress.isError && Boolean(courseId) && chartData.length === 0 && <p className="faculty-chart-empty">Map students to this course to see their progress here.</p>}
      {!progress.isLoading && !progress.isError && chartData.length > 0 && questionCount === 0 && <p className="faculty-chart-empty">Add questions to this course to compare student completion.</p>}
      {!progress.isLoading && !progress.isError && chartData.length > 0 && questionCount > 0 && <div className="faculty-completion-chart"><ResponsiveContainer width="100%" height={Math.min(420, Math.max(210, chartData.length * 48))}>
        <BarChart data={chartData} layout="vertical" margin={{ top: 8, right: 20, bottom: 0, left: 8 }} barCategoryGap={14}>
          <defs><linearGradient id="facultySolvedGradient" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stopColor="#c49a59"/><stop offset="100%" stopColor="#f0d49f"/></linearGradient></defs>
          <CartesianGrid horizontal={false} stroke="#ffffff12"/>
          <XAxis type="number" domain={[0, questionCount]} allowDecimals={false} tickLine={false} axisLine={false} tick={{ fill: '#85847f', fontSize: 10 }}/>
          <YAxis type="category" dataKey="label" width={118} tickLine={false} axisLine={false} tick={{ fill: '#c4c2bd', fontSize: 10 }} interval={0}/>
          <Tooltip cursor={{ fill: '#ffffff09' }} contentStyle={{ background: '#151514', border: '1px solid #ffffff20', borderRadius: 10, color: '#f5f4f1' }} labelStyle={{ color: '#e6c688' }} formatter={(value, name) => [`${value} questions`, name === 'Solved' ? 'Solved' : 'Remaining']}/>
          <Bar dataKey="solved" name="Solved" stackId="questions" fill="url(#facultySolvedGradient)" radius={[5, 0, 0, 5]} maxBarSize={18}/>
          <Bar dataKey="remaining" name="Remaining" stackId="questions" fill="#38352f" radius={[0, 5, 5, 0]} maxBarSize={18}/>
        </BarChart>
      </ResponsiveContainer></div>}
      {chartData.length > 0 && questionCount > 0 && <div className="faculty-chart-legend"><span><i className="faculty-legend-solved"/>Solved</span><span><i className="faculty-legend-remaining"/>Remaining</span><small>Questions in course: {questionCount}</small></div>}
    </section>
  </div>;
}

function ProblemAssignmentsPage() {
  const queryClient = useQueryClient();
  const courses = useQuery<Course[]>({ queryKey: ['faculty-courses'], queryFn: () => api('/courses') });
  const students = useQuery<Student[]>({ queryKey: ['faculty-students'], queryFn: () => api('/faculty/students') });
  const questions = useQuery<{ items: Question[] }>({ queryKey: ['faculty-assignment-questions'], queryFn: () => api('/questions?page_size=100') });
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [problemTitle, setProblemTitle] = useState('');
  const [problemStatement, setProblemStatement] = useState('');
  const [problemDifficulty, setProblemDifficulty] = useState('Easy');
  const [problemTopic, setProblemTopic] = useState('Arrays');
  const [problemCourseId, setProblemCourseId] = useState('');
  const [problemSearch, setProblemSearch] = useState('');
  const [creatingProblem, setCreatingProblem] = useState(false);
  const [publishQuestionId, setPublishQuestionId] = useState<number | null>(null);
  const [publishStudents, setPublishStudents] = useState<number[]>([]);
  const [publishDueAt, setPublishDueAt] = useState('');
  const [publishNote, setPublishNote] = useState('');
  const [publishing, setPublishing] = useState(false);
  const createProblem = async (event: FormEvent) => {
    event.preventDefault(); setMessage(''); setError(''); setCreatingProblem(true);
    try {
      const created = await api('/questions', { method: 'POST', body: JSON.stringify({ title: problemTitle.trim(), statement: problemStatement.trim(), difficulty: problemDifficulty, topic: problemTopic.trim() || 'General', tags: [], constraints: '', input_format: '', output_format: '', hints: '', editorial: '', starter_code: {}, published: true, tests: [] }) }) as Question;
      if (problemCourseId) await api(`/courses/${problemCourseId}/questions?question_id=${created.id}`, { method: 'POST' });
      setProblemTitle(''); setProblemStatement(''); setProblemDifficulty('Easy'); setProblemTopic('Arrays'); setProblemCourseId(''); setMessage(problemCourseId ? 'Problem created, published, and added to the selected course.' : 'Problem created and published to the problem bank.');
      await queryClient.invalidateQueries({ queryKey: ['faculty-assignment-questions'] });
    } catch (exception) { setError((exception as Error).message); }
    finally { setCreatingProblem(false); }
  };
  const publishProblem = async (event: FormEvent) => {
    event.preventDefault(); setMessage(''); setError(''); setPublishing(true);
    if (!publishStudents.length) { setError('Map at least one student in Courses & students before publishing.'); setPublishing(false); return; }
    try {
      await api('/faculty/problem-assignments', { method: 'POST', body: JSON.stringify({ question_id: publishQuestionId, student_ids: publishStudents, due_at: publishDueAt ? new Date(publishDueAt).toISOString() : null, note: publishNote }) });
      setPublishQuestionId(null); setPublishStudents([]); setPublishDueAt(''); setPublishNote(''); setMessage('Problem published to the selected students.');
    } catch (exception) { setError((exception as Error).message); }
    finally { setPublishing(false); }
  };
  const selectedPublishQuestion = (questions.data?.items || []).find((question) => question.id === publishQuestionId);
  const problemItems = (questions.data?.items || []).filter((question) => { const term = problemSearch.trim().toLowerCase(); return !term || [question.title, question.topic, question.difficulty].some((value) => value.toLowerCase().includes(term)); });
  return <div className="faculty-page">
    <PageHeading eyebrow="PROBLEM WORKSPACE" title="Create and manage problems." description="Build a focused problem bank for your students and find problems quickly by title, topic, or difficulty."/>
    <form className="faculty-card faculty-problem-create-form" onSubmit={createProblem}>
      <div className="faculty-section-title"><div><span className="faculty-eyebrow">PROBLEM AUTHORING</span><h2>Create a problem</h2></div></div>
      <div className="faculty-form-grid"><label>Problem title<input value={problemTitle} onChange={(event) => setProblemTitle(event.target.value)} required minLength={3} placeholder="e.g. Find the missing number"/></label><label>Topic<input value={problemTopic} onChange={(event) => setProblemTopic(event.target.value)} placeholder="Arrays"/></label><label>Difficulty<select value={problemDifficulty} onChange={(event) => setProblemDifficulty(event.target.value)}><option>Easy</option><option>Medium</option><option>Hard</option></select></label><label>Course<select value={problemCourseId} onChange={(event) => setProblemCourseId(event.target.value)} disabled={courses.isLoading}><option value="">Choose a course</option>{(courses.data || []).map((course) => <option key={course.id} value={course.id}>{course.code} · {course.title}</option>)}</select></label><label className="faculty-wide">Problem statement<textarea className="faculty-problem-statement" value={problemStatement} onChange={(event) => setProblemStatement(event.target.value)} required minLength={3} placeholder="Describe the problem students need to solve"/></label></div>
      <div className="faculty-form-actions"><button className="faculty-primary" disabled={creatingProblem}>{creatingProblem ? 'Creating…' : 'Create problem'}</button>{message && <span className="faculty-success">{message}</span>}{error && <span className="faculty-error">{error}</span>}</div>
    </form>
    <section className="faculty-card faculty-problem-bank"><div className="faculty-section-title"><div><span className="faculty-eyebrow">PROBLEM BANK</span><h2>Find a problem</h2></div><span className="faculty-count">{problemItems.length} in view</span></div><label className="faculty-problem-search"><Search/><input value={problemSearch} onChange={(event) => setProblemSearch(event.target.value)} placeholder="Search problems by title, topic or difficulty"/></label><div className="faculty-problem-bank-list">{problemItems.map((question) => <article key={question.id}><div><b>{question.title}</b><small>{question.difficulty} · {question.topic}</small></div><div className="faculty-problem-row-actions"><button className="faculty-secondary" type="button" onClick={() => { setPublishQuestionId(question.id); setError(''); }}>Publish</button></div></article>)}{questions.isLoading && <p className="faculty-empty">Loading problems…</p>}{!questions.isLoading && !problemItems.length && <p className="faculty-empty">No problems match your search.</p>}</div></section>
    {publishQuestionId !== null && <div className="faculty-publish-modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setPublishQuestionId(null); }}><form className="faculty-publish-modal" onSubmit={publishProblem}><button type="button" className="faculty-publish-modal-close" onClick={() => setPublishQuestionId(null)} aria-label="Close"><X/></button><span className="faculty-eyebrow">PUBLISH TO STUDENTS</span><h2>{selectedPublishQuestion?.title || 'Publish problem'}</h2><p>Choose the mapped students who should receive this problem.</p><label>Due date<input type="datetime-local" value={publishDueAt} onChange={(event) => setPublishDueAt(event.target.value)}/></label><label>Instructions<input value={publishNote} onChange={(event) => setPublishNote(event.target.value)} placeholder="Optional note for students"/></label><div className="faculty-publish-student-list">{(students.data || []).map((student) => <label key={student.id} className={publishStudents.includes(student.id) ? 'selected' : ''}><input type="checkbox" checked={publishStudents.includes(student.id)} onChange={() => { setError(''); setPublishStudents((current) => current.includes(student.id) ? current.filter((id) => id !== student.id) : [...current, student.id]); }}/><span><b>{student.full_name || student.email.split('@')[0]}</b><small>{student.registration_number || student.email}</small></span></label>)}{students.isLoading && <small className="faculty-muted">Loading mapped students…</small>}{!students.isLoading && !students.data?.length && <small className="faculty-muted">Map students in Courses &amp; students first.</small>}</div>{error && <p className="faculty-error">{error}</p>}<div className="faculty-publish-modal-actions"><button type="button" className="faculty-secondary" onClick={() => setPublishQuestionId(null)}>Cancel</button><button className="faculty-primary" disabled={publishing || students.isLoading}>{publishing ? 'Publishing…' : 'Publish problem'}</button></div></form></div>}
  </div>;
}

function AssessmentsPage() {
  const queryClient = useQueryClient();
  const courses = useQuery<Course[]>({ queryKey: ['faculty-courses'], queryFn: () => api('/courses') });
  const assessments = useQuery<Assessment[]>({ queryKey: ['faculty-assessments'], queryFn: () => api('/assessments') });
  const [courseId, setCourseId] = useState('');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [startsAt, setStartsAt] = useState('');
  const [endsAt, setEndsAt] = useState('');
  const [selectedQuestions, setSelectedQuestions] = useState<number[]>([]);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  useEffect(() => { if (!courseId && courses.data?.length) setCourseId(String(courses.data[0].id)); }, [courses.data, courseId]);
  const courseQuestions = useQuery<Question[]>({ queryKey: ['faculty-course-questions', Number(courseId)], queryFn: () => api(`/courses/${courseId}/questions`), enabled: Boolean(courseId) });
  useEffect(() => { setSelectedQuestions((courseQuestions.data || []).map((question) => question.id)); }, [courseQuestions.data]);
  const toggleQuestion = (id: number) => setSelectedQuestions((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);
  const create = async (event: FormEvent) => { event.preventDefault(); setMessage(''); setError(''); try { if (!selectedQuestions.length) throw Error('Add at least one course question before creating an assessment.'); if (startsAt && endsAt && new Date(endsAt) <= new Date(startsAt)) throw Error('The end time must be later than the start time.'); await api('/assessments', { method: 'POST', body: JSON.stringify({ course_id: Number(courseId), title, description, starts_at: startsAt ? new Date(startsAt).toISOString() : null, ends_at: endsAt ? new Date(endsAt).toISOString() : null, question_ids: selectedQuestions }) }); setTitle(''); setDescription(''); setStartsAt(''); setEndsAt(''); setMessage('Assessment created as a draft. Publish it when you are ready for students to take it.'); await queryClient.invalidateQueries({ queryKey: ['faculty-assessments'] }); } catch (exception) { setError((exception as Error).message); } };
  const publish = async (assessment: Assessment) => { setMessage(''); setError(''); try { await api(`/assessments/${assessment.id}/publish`, { method: 'PATCH' }); setMessage(`${assessment.title} is now available to its enrolled students.`); await queryClient.invalidateQueries({ queryKey: ['faculty-assessments'] }); } catch (exception) { setError((exception as Error).message); } };
  const courseName = useMemo(() => new Map((courses.data || []).map((course) => [course.id, course.code])), [courses.data]);
  return <div className="faculty-page"><PageHeading eyebrow="ASSESSMENTS" title="Plan and conduct assessments." description="Choose questions from a course problem set, set the assessment window, publish it to enrolled students, and follow its results."/><form className="faculty-card faculty-assessment-form" onSubmit={create}><div className="faculty-section-title"><div><span className="faculty-eyebrow">NEW ASSESSMENT</span><h2>Create an assessment</h2></div><span className="faculty-badge draft">Draft</span></div><div className="faculty-form-grid"><label>Course<select value={courseId} onChange={(event) => setCourseId(event.target.value)} required><option value="">Choose a course</option>{(courses.data || []).map((course) => <option key={course.id} value={course.id}>{course.code} · {course.title}</option>)}</select></label><label>Assessment title<input value={title} onChange={(event) => setTitle(event.target.value)} required minLength={2} placeholder="e.g. Week 3 DSA Checkpoint"/></label><label>Description<input value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Instructions for students"/></label><label>Starts at<input type="datetime-local" value={startsAt} onChange={(event) => setStartsAt(event.target.value)}/></label><label>Ends at<input type="datetime-local" value={endsAt} onChange={(event) => setEndsAt(event.target.value)}/></label></div><div className="faculty-question-picker"><div><b>Questions in this assessment</b><small>Select from the chosen course's problem set. Add problems from Courses & students first.</small></div>{(courseQuestions.data || []).map((question) => <label key={question.id}><input type="checkbox" checked={selectedQuestions.includes(question.id)} onChange={() => toggleQuestion(question.id)}/><span>{question.title}</span><small>{question.difficulty} · {question.topic}</small></label>)}{courseQuestions.isLoading && <small className="faculty-muted">Loading course questions…</small>}{!courseQuestions.isLoading && !courseQuestions.data?.length && <p className="faculty-empty">This course has no questions yet.</p>}</div><div className="faculty-form-actions"><button className="faculty-primary" disabled={!courseId || !selectedQuestions.length}><Plus/>Create draft</button>{message && <span className="faculty-success">{message}</span>}{error && <span className="faculty-error">{error}</span>}</div></form><section className="faculty-card"><div className="faculty-section-title"><div><span className="faculty-eyebrow">RUNNING & PLANNED</span><h2>Your assessments</h2></div><Link to="/faculty/results">View results <ChevronRight/></Link></div><div className="faculty-assessment-list">{(assessments.data || []).map((assessment) => <article className="faculty-assessment-row" key={assessment.id}><div className="faculty-assessment-icon"><CalendarClock/></div><div className="faculty-assessment-info"><span className="faculty-eyebrow">{courseName.get(assessment.course_id) || 'COURSE'}</span><h3>{assessment.title}</h3><p>{assessment.description || 'Course assessment'} · {prettyDate(assessment.starts_at)}</p></div><span className={`faculty-badge ${assessmentState(assessment).toLowerCase()}`}>{assessmentState(assessment)}</span><div className="faculty-assessment-actions">{!assessment.published && <button className="faculty-secondary" onClick={() => publish(assessment)}>Publish</button>}<Link className="faculty-secondary" to={`/faculty/results?assessment=${assessment.id}`}>Results</Link></div></article>)}{assessments.isLoading && <p className="faculty-empty">Loading assessments…</p>}{!assessments.isLoading && !assessments.data?.length && <p className="faculty-empty">No assessments yet. Create a draft above.</p>}</div>{error && <p className="faculty-error">{error}</p>}{message && <p className="faculty-success">{message}</p>}</section></div>;
}

function ResultsPage() {
  const queryClient = useQueryClient();
  const courses = useQuery<Course[]>({ queryKey: ['faculty-courses'], queryFn: () => api('/courses') });
  const assessments = useQuery<Assessment[]>({ queryKey: ['faculty-assessments'], queryFn: () => api('/assessments') });
  const [assessmentId, setAssessmentId] = useState('');
  const [searchParams] = useSearchParams();
  const requestedAssessment = searchParams.get('assessment') || '';
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  useEffect(() => { if (!assessmentId && assessments.data?.length) setAssessmentId(requestedAssessment || String(assessments.data[0].id)); }, [assessments.data, assessmentId, requestedAssessment]);
  const results = useQuery<ResultRow[]>({ queryKey: ['faculty-results', assessmentId], queryFn: () => api(`/assessments/${assessmentId}/results`), enabled: Boolean(assessmentId) });
  const selected = (assessments.data || []).find((item) => String(item.id) === assessmentId);
  const share = async () => { if (!selected) return; setMessage(''); setError(''); try { await api(`/assessments/${selected.id}/share-results`, { method: 'PATCH' }); setMessage('Results are shared. Students can now see their scores.'); await queryClient.invalidateQueries({ queryKey: ['faculty-results', assessmentId] }); } catch (exception) { setError((exception as Error).message); } };
  const courseById = new Map((courses.data || []).map((course) => [course.id, course]));
  const resultInsights = useMemo(() => {
    const percentages = (results.data || []).map((row) => row.out_of > 0 ? Math.max(0, Math.min(100, row.score / row.out_of * 100)) : 0);
    const average = percentages.length ? Math.round(percentages.reduce((sum, score) => sum + score, 0) / percentages.length) : 0;
    return {
      average,
      highest: percentages.length ? Math.round(Math.max(...percentages)) : 0,
      distribution: [
        { band: '0–49%', count: percentages.filter((score) => score < 50).length },
        { band: '50–69%', count: percentages.filter((score) => score >= 50 && score < 70).length },
        { band: '70–89%', count: percentages.filter((score) => score >= 70 && score < 90).length },
        { band: '90–100%', count: percentages.filter((score) => score >= 90).length },
      ],
    };
  }, [results.data]);

  return <div className="faculty-page">
    <PageHeading eyebrow="ASSESSMENT RESULTS" title="Review and share student results." description="Scores remain private to faculty until you share them with the students enrolled in the course."/>
    <section className="faculty-toolbar faculty-card">
      {selected && <span>{courseById.get(selected.course_id)?.code || 'Course'} · {assessmentState(selected)}</span>}
      {selected && <button className="faculty-primary" onClick={share} disabled={results.isLoading || !results.data?.length || results.data.every((row) => row.shared)}><Check/>Share results with students</button>}
    </section>
    {selected && <section className="faculty-card faculty-table-wrap">
      <div className="faculty-results-summary"><div><span className="faculty-eyebrow">{selected.title}</span><h2>{results.data?.length ?? '—'} submissions</h2></div><span className={`faculty-badge ${results.data?.every((row) => row.shared) && results.data.length ? 'shared' : 'draft'}`}>{results.data?.length && results.data.every((row) => row.shared) ? 'Shared with students' : 'Faculty only'}</span></div>
      <table className="faculty-table"><thead><tr><th>Student</th><th>Registration no.</th><th>Score</th><th>Submitted</th><th>Visibility</th></tr></thead><tbody>{(results.data || []).map((row) => <tr key={row.student_id}><td><b>{row.email}</b></td><td>{row.registration_number || '—'}</td><td><strong>{row.score} / {row.out_of}</strong></td><td>{prettyDate(row.submitted_at)}</td><td><span className={`faculty-badge ${row.shared ? 'shared' : 'draft'}`}>{row.shared ? 'Shared' : 'Private'}</span></td></tr>)}</tbody></table>
      {results.isLoading && <p className="faculty-empty">Loading results…</p>}
      {results.isError && <p className="faculty-error">{results.error.message}</p>}
      {!results.isLoading && !results.data?.length && <p className="faculty-empty">No students have submitted this assessment yet.</p>}
    </section>}
    {message && <p className="faculty-success">{message}</p>}{error && <p className="faculty-error">{error}</p>}
    {!selected && !assessments.isLoading && <section className="faculty-card faculty-empty">Create and publish an assessment to see its results here.</section>}
    <section className="faculty-card faculty-results-insights">
      <div className="faculty-results-insights-header"><div><span className="faculty-eyebrow">ASSESSMENT INSIGHTS</span><h2>Score distribution</h2><p>See how submitted scores are spread across performance bands.</p></div>
        {Boolean(results.data?.length) && <div className="faculty-completion-metrics"><div><strong>{resultInsights.average}%</strong><small>Average score</small></div><div><strong>{resultInsights.highest}%</strong><small>Highest score</small></div><div><strong>{results.data?.length ?? 0}</strong><small>Submissions</small></div></div>}
      </div>
      {assessments.isLoading && <p className="faculty-empty">Loading assessment insights…</p>}
      {selected && results.isLoading && <p className="faculty-empty">Loading score distribution…</p>}
      {results.isError && <p className="faculty-error">Could not load score distribution.</p>}
      {!selected && !assessments.isLoading && <p className="faculty-chart-empty">Choose an assessment with submissions to view its score distribution.</p>}
      {selected && !results.isLoading && !results.isError && !results.data?.length && <p className="faculty-chart-empty">No submitted scores yet. The chart will appear after students complete this assessment.</p>}
      {selected && !results.isLoading && !results.isError && Boolean(results.data?.length) && <div className="faculty-score-chart"><ResponsiveContainer width="100%" height={260}>
        <BarChart data={resultInsights.distribution} margin={{ top: 22, right: 18, bottom: 2, left: 4 }}>
          <defs><linearGradient id="facultyScoreGradient" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#f0d49f"/><stop offset="100%" stopColor="#bd8f4d"/></linearGradient></defs>
          <CartesianGrid vertical={false} stroke="#ffffff12"/>
          <XAxis dataKey="band" tickLine={false} axisLine={false} tick={{ fill: '#aaa8a2', fontSize: 10 }}/>
          <YAxis allowDecimals={false} tickLine={false} axisLine={false} tick={{ fill: '#85847f', fontSize: 10 }} width={28}/>
          <Tooltip cursor={{ fill: '#ffffff08' }} contentStyle={{ background: '#151514', border: '1px solid #ffffff20', borderRadius: 10, color: '#f5f4f1' }} labelStyle={{ color: '#e6c688' }} formatter={(value) => [`${value} ${value === 1 ? 'student' : 'students'}`, 'Submissions']}/>
          <Bar dataKey="count" name="Submissions" fill="url(#facultyScoreGradient)" radius={[6, 6, 0, 0]} maxBarSize={64}><LabelList dataKey="count" position="top" fill="#e9e6df" fontSize={10}/></Bar>
        </BarChart>
      </ResponsiveContainer></div>}
      {selected && !results.isLoading && !results.isError && Boolean(results.data?.length) && <div className="faculty-chart-legend"><span><i className="faculty-score-legend"/>Student submissions</span><small>Score bands are shown as a percentage</small></div>}
    </section>
  </div>;
}

function PageHeading({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) { return <section className="faculty-page-heading"><span className="faculty-eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></section>; }

export function FacultyApp({ me }: { me: FacultyMe }) { if (me.role !== 'faculty') return <Navigate to="/" replace/>; return <FacultyLayout me={me}/>; }
