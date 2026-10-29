from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import FacultyStudent, Question, SessionLocal, app


def unique_email(prefix: str = "test") -> str:
    return f"{prefix}-{uuid4().hex}@example.com"


def admin_login(client: TestClient) -> TestClient:
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@test.local", "password": "admin-test-password"},
    )
    assert response.status_code == 200, response.text
    return client


def student_login(client: TestClient, email: str, password: str = "supersecret") -> TestClient:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return client


def academic_options(client: TestClient):
    response = client.get("/api/admin/departments")
    assert response.status_code == 200, response.text
    return response.json()


def create_student(client: TestClient, **overrides):
    payload = {
        "email": unique_email("student"),
        "password": "supersecret",
        "full_name": "Test Student",
        "registration_number": f"REG-{uuid4().hex[:12].upper()}",
        "year_of_study": 1,
        "department_id": None,
        "section_id": None,
        "approval_status": "Approved",
    }
    payload.update(overrides)
    response = client.post("/api/admin/students", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def create_faculty(client: TestClient, **overrides):
    payload = {
        "email": unique_email("faculty"),
        "password": "supersecret",
        "full_name": "Test Faculty",
        "faculty_code": f"FAC-{uuid4().hex[:8].upper()}",
        "department_id": None,
    }
    payload.update(overrides)
    response = client.post("/api/admin/faculty", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def create_course(client: TestClient, faculty_id: int | None = None):
    payload = {
        "title": f"Course {uuid4().hex[:8]}",
        "code": f"CS{uuid4().hex[:6].upper()}",
        "description": "Test course",
        "faculty_id": faculty_id,
    }
    response = client.post("/api/courses", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_signup_is_pending_until_admin_approval():
    email = unique_email("pending")
    with TestClient(app) as student, TestClient(app) as admin:
        response = student.post(
            "/api/auth/register",
            json={"email": email, "password": "supersecret"},
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["approval_status"] == "Pending"
        assert "message" in body
        assert student.get("/api/auth/me").status_code == 401
        blocked = student.post(
            "/api/auth/login", json={"email": email, "password": "supersecret"}
        )
        assert blocked.status_code == 403
        assert "pending" in blocked.json()["detail"].lower()

        admin_login(admin)
        listing = admin.get("/api/admin/users", params={"role": "student", "search": email})
        assert listing.status_code == 200, listing.text
        items = listing.json()["items"]
        assert len(items) == 1
        student_id = items[0]["id"]
        assert items[0]["approval_status"] == "Pending"
        assert items[0]["department"] is None
        assert items[0]["section"] is None

        approved = admin.patch(
            f"/api/admin/students/{student_id}", json={"approval_status": "Approved"}
        )
        assert approved.status_code == 200, approved.text
        assert approved.json()["approval_status"] == "Approved"

        student_login(student, email)
        me = student.get("/api/auth/me")
        assert me.status_code == 200
        assert me.json()["approval_status"] == "Approved"


def test_admin_student_directory_filters_and_year_counts():
    with TestClient(app) as admin:
        admin_login(admin)
        departments = academic_options(admin)
        cse = next(department for department in departments if department["name"] == "CSE")
        section_a = next(section for section in cse["sections"] if section["name"] == "A")
        section_b = next(section for section in cse["sections"] if section["name"] == "B")

        first = create_student(
            admin,
            full_name="First Year Student",
            year_of_study=1,
            department_id=cse["id"],
            section_id=section_a["id"],
        )
        second = create_student(
            admin,
            full_name="Second Year Student",
            year_of_study=2,
            department_id=cse["id"],
            section_id=section_b["id"],
        )
        unset = create_student(
            admin,
            full_name="Unset Year Student",
            year_of_study=None,
            department_id=cse["id"],
        )

        assert first["department"]["name"] == "CSE"
        assert first["section"]["name"] == "A"
        assert unset["year_of_study"] is None

        filtered = admin.get(
            "/api/admin/users",
            params={"role": "student", "year_of_study": 1, "department_id": cse["id"]},
        )
        assert filtered.status_code == 200, filtered.text
        assert all(item["year_of_study"] == 1 for item in filtered.json()["items"])
        assert all(item["department"]["id"] == cse["id"] for item in filtered.json()["items"])

        searched = admin.get("/api/admin/users", params={"role": "student", "search": second["email"]})
        assert searched.status_code == 200, searched.text
        assert [item["id"] for item in searched.json()["items"]] == [second["id"]]

        paged = admin.get("/api/admin/users", params={"role": "student", "page": 1, "page_size": 2})
        assert paged.status_code == 200, paged.text
        assert paged.json()["page_size"] == 2
        assert paged.json()["pages"] >= 1

        refreshed = academic_options(admin)
        cse_after = next(department for department in refreshed if department["id"] == cse["id"])
        assert cse_after["year_counts"]["1"] >= 1
        assert cse_after["year_counts"]["2"] >= 1
        assert cse_after["year_counts"]["unset"] >= 1
        section_a_after = next(section for section in cse_after["sections"] if section["id"] == section_a["id"])
        assert section_a_after["year_counts"]["1"] >= 1

        updated = admin.patch(
            f"/api/admin/students/{first['id']}",
            json={
                "full_name": "Renamed Student",
                "year_of_study": 3,
                "department_id": cse["id"],
                "section_id": section_b["id"],
            },
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["full_name"] == "Renamed Student"
        assert updated.json()["year_of_study"] == 3
        assert updated.json()["section"]["name"] == "B"


def test_departments_and_sections_guards():
    with TestClient(app) as admin:
        admin_login(admin)
        name = f"TEST-{uuid4().hex[:6].upper()}"
        created = admin.post("/api/admin/departments", json={"name": name.lower()})
        assert created.status_code == 201, created.text
        department = created.json()
        assert department["name"] == name

        duplicate = admin.post("/api/admin/departments", json={"name": name})
        assert duplicate.status_code == 409

        section = admin.post(
            f"/api/admin/departments/{department['id']}/sections", json={"name": "z"}
        )
        assert section.status_code == 201, section.text
        assert section.json()["name"] == "Z"

        renamed = admin.patch(
            f"/api/admin/sections/{section.json()['id']}", json={"name": "Y"}
        )
        assert renamed.status_code == 200, renamed.text
        assert renamed.json()["name"] == "Y"

        student = create_student(
            admin,
            department_id=department["id"],
            section_id=renamed.json()["id"],
        )
        assert student["department"]["name"] == name

        blocked_department = admin.delete(f"/api/admin/departments/{department['id']}")
        assert blocked_department.status_code == 409
        blocked_section = admin.delete(f"/api/admin/sections/{renamed.json()['id']}")
        assert blocked_section.status_code == 409

        admin.delete(f"/api/admin/students/{student['id']}")
        assert admin.delete(f"/api/admin/sections/{renamed.json()['id']}").status_code == 204
        assert admin.delete(f"/api/admin/departments/{department['id']}").status_code == 204


def test_student_password_reset_and_permanent_delete_preserves_questions():
    with TestClient(app) as admin, TestClient(app) as student:
        admin_login(admin)
        email = unique_email("delete")
        created = create_student(admin, email=email, full_name="Delete Me")
        student_id = created["id"]
        student_login(student, email)

        question = student.post(
            "/api/questions",
            json={
                "title": f"Student authored {uuid4().hex[:8]}",
                "statement": "Print hello",
                "tests": [{"input": "", "expected_output": "hello", "is_hidden": True}],
            },
        )
        assert question.status_code == 201, question.text
        slug = question.json()["slug"]

        reset = admin.post(
            f"/api/admin/students/{student_id}/reset-password",
            json={"password": "newpassword"},
        )
        assert reset.status_code == 204, reset.text
        assert student.get("/api/auth/me").status_code == 401
        old_login = student.post("/api/auth/login", json={"email": email, "password": "supersecret"})
        assert old_login.status_code == 401
        student_login(student, email, "newpassword")

        removed = admin.delete(f"/api/admin/students/{student_id}")
        assert removed.status_code == 204, removed.text
        assert student.get("/api/auth/me").status_code == 401
        gone_login = student.post("/api/auth/login", json={"email": email, "password": "newpassword"})
        assert gone_login.status_code == 401

        with SessionLocal() as session:
            preserved = session.query(Question).filter(Question.slug == slug).one()
            assert preserved.owner_id is None


def test_faculty_ids_mentorship_and_course_enrollment_is_separate():
    with TestClient(app) as admin, TestClient(app) as faculty, TestClient(app) as student:
        admin_login(admin)
        departments = academic_options(admin)
        cse = next(department for department in departments if department["name"] == "CSE")
        it = next(department for department in departments if department["name"] == "IT")
        cse_section = cse["sections"][0]
        it_section = it["sections"][0]

        code = f"fac-{uuid4().hex[:8]}"
        created = create_faculty(
            admin,
            full_name="Mentor Faculty",
            faculty_code=code,
            department_id=cse["id"],
        )
        faculty_id = created["id"]
        assert created["faculty_code"] == code.upper()
        assert created["department"]["name"] == "CSE"

        duplicate = admin.post(
            "/api/admin/faculty",
            json={
                "email": unique_email("faculty2"),
                "password": "supersecret",
                "faculty_code": code.upper(),
                "department_id": cse["id"],
            },
        )
        assert duplicate.status_code == 409

        missing_code = admin.post(
            "/api/admin/faculty",
            json={
                "email": unique_email("faculty3"),
                "password": "supersecret",
                "department_id": cse["id"],
            },
        )
        assert missing_code.status_code == 422

        student_login(faculty, created["email"])
        me = faculty.get("/api/auth/me")
        assert me.status_code == 200
        assert me.json()["faculty_code"] == code.upper()
        profile = faculty.get("/api/faculty/profile")
        assert profile.status_code == 200, profile.text
        assert profile.json()["mentee_count"] == 0

        mentee_one = create_student(
            admin,
            full_name="Mentee One",
            department_id=cse["id"],
            section_id=cse_section["id"],
        )
        mentee_two = create_student(
            admin,
            full_name="Mentee Two",
            department_id=it["id"],
            section_id=it_section["id"],
        )

        assigned = admin.post(
            f"/api/admin/faculty/{faculty_id}/mentees",
            json={"student_ids": [mentee_one["id"], mentee_two["id"]]},
        )
        assert assigned.status_code == 201, assigned.text
        assert assigned.json()["assigned"] == 2

        mentees = admin.get(f"/api/admin/faculty/{faculty_id}/mentees")
        assert mentees.status_code == 200, mentees.text
        assert {item["id"] for item in mentees.json()} == {mentee_one["id"], mentee_two["id"]}

        faculty_mentees = faculty.get("/api/faculty/mentees")
        assert faculty_mentees.status_code == 200, faculty_mentees.text
        assert {item["id"] for item in faculty_mentees.json()} == {mentee_one["id"], mentee_two["id"]}
        assert faculty.get("/api/faculty/profile").json()["mentee_count"] == 2

        roster = faculty.get("/api/faculty/students")
        assert roster.status_code == 200, roster.text
        assert all(item["is_mentee"] for item in roster.json())
        assert {item["id"] for item in roster.json()} == {mentee_one["id"], mentee_two["id"]}

        # A second faculty takes over one mentee: a student can only have one mentor.
        second = create_faculty(admin, department_id=it["id"])
        reassigned = admin.post(
            f"/api/admin/faculty/{second['id']}/mentees",
            json={"student_ids": [mentee_one["id"]]},
        )
        assert reassigned.status_code == 201, reassigned.text
        first_mentees = admin.get(f"/api/admin/faculty/{faculty_id}/mentees").json()
        assert [item["id"] for item in first_mentees] == [mentee_two["id"]]

        # Course enrollment is separate from mentorship and must not create a mentor link.
        course = create_course(admin, faculty_id=faculty_id)
        enrolled = admin.post(
            f"/api/courses/{course['id']}/students",
            params={"registration_number": mentee_one["registration_number"]},
        )
        assert enrolled.status_code == 201, enrolled.text
        with SessionLocal() as session:
            links = session.query(FacultyStudent).filter(FacultyStudent.student_id == mentee_one["id"]).all()
            assert len(links) == 1
            assert links[0].faculty_id == second["id"]

        roster_after = faculty.get("/api/faculty/students").json()
        mentee_two_entry = next(item for item in roster_after if item["id"] == mentee_two["id"])
        assert mentee_two_entry["is_mentee"] is True

        removed = admin.delete(f"/api/admin/faculty/{faculty_id}/mentees/{mentee_two['id']}")
        assert removed.status_code == 204
        assert admin.get(f"/api/admin/faculty/{faculty_id}/mentees").json() == []


def test_faculty_problem_assignments_reach_mentees_and_assessments_flow():
    with TestClient(app) as admin, TestClient(app) as faculty, TestClient(app) as student:
        admin_login(admin)
        departments = academic_options(admin)
        cse = next(department for department in departments if department["name"] == "CSE")
        mentor = create_faculty(admin, department_id=cse["id"])
        mentee = create_student(
            admin,
            department_id=cse["id"],
            section_id=cse["sections"][0]["id"],
        )
        admin.post(
            f"/api/admin/faculty/{mentor['id']}/mentees",
            json={"student_ids": [mentee["id"]]},
        )

        student_login(faculty, mentor["email"])
        questions = faculty.get("/api/questions", params={"page_size": 5})
        assert questions.status_code == 200, questions.text
        question = questions.json()["items"][0]

        assigned = faculty.post(
            "/api/faculty/problem-assignments",
            json={"question_id": question["id"], "student_ids": [mentee["id"]], "note": "Practice"},
        )
        assert assigned.status_code == 201, assigned.text
        assert assigned.json()["created"] == 1
        assignments = faculty.get("/api/faculty/problem-assignments")
        assert assignments.status_code == 200, assignments.text
        assert len(assignments.json()) == 1

        student_login(student, mentee["email"])
        student_assignments = student.get("/api/student/problem-assignments")
        assert student_assignments.status_code == 200, student_assignments.text
        assert student_assignments.json()[0]["question_id"] == question["id"]
        assert student_assignments.json()[0]["completed"] is False

        course = create_course(admin, faculty_id=mentor["id"])
        admin.post(
            f"/api/courses/{course['id']}/students",
            params={"registration_number": mentee["registration_number"]},
        )
        admin.post(
            f"/api/courses/{course['id']}/questions",
            params={"question_id": question["id"]},
        )
        assessment = faculty.post(
            "/api/assessments",
            json={
                "course_id": course["id"],
                "title": "Weekly assessment",
                "description": "One problem",
                "question_ids": [question["id"]],
            },
        )
        assert assessment.status_code == 201, assessment.text
        assessment_id = assessment.json()["id"]
        assert faculty.patch(f"/api/assessments/{assessment_id}/publish").status_code == 200

        listed = student.get("/api/assessments")
        assert listed.status_code == 200, listed.text
        assert [item["id"] for item in listed.json()] == [assessment_id]
        paper = student.get(f"/api/assessments/{assessment_id}/questions")
        assert paper.status_code == 200, paper.text
        assert [item["id"] for item in paper.json()] == [question["id"]]

        submitted = student.post(f"/api/assessments/{assessment_id}/submit")
        assert submitted.status_code == 201, submitted.text
        assert student.get(f"/api/assessments/{assessment_id}/results").status_code == 403
        assert faculty.patch(f"/api/assessments/{assessment_id}/share-results").status_code == 200
        result = student.get(f"/api/assessments/{assessment_id}/results")
        assert result.status_code == 200, result.text
        assert result.json()["out_of"] == 1

        assignment_id = assignments.json()[0]["id"]
        assert faculty.delete(f"/api/faculty/problem-assignments/{assignment_id}").status_code == 204


def test_private_tests_stay_hidden_and_profile_summary_is_safe():
    with TestClient(app) as admin, TestClient(app) as student:
        admin_login(admin)
        listing = admin.get("/api/questions", params={"page_size": 50})
        assert listing.status_code == 200, listing.text
        item = next(q for q in listing.json()["items"] if q["slug"] == "pair-sum-function")
        detail = admin.get(f"/api/questions/{item['slug']}")
        assert detail.status_code == 200
        assert len(detail.json()["tests"]) == 5

        email = unique_email("profile")
        created = create_student(admin, email=email)
        student_login(student, email)
        profile = student.get("/api/profile/me")
        assert profile.status_code == 200
        body = profile.json()
        assert body["username"].startswith("student-")
        assert "email" not in body
        public = student.get("/api/u/" + body["username"])
        assert public.status_code == 200
        assert public.json()["username"] == body["username"]


def create_student_with_regno(client: TestClient, registration_number: str, **overrides):
    payload = {
        "email": unique_email("student"),
        "password": "supersecret",
        "full_name": "Test Student",
        "registration_number": registration_number,
        "year_of_study": 2,
        "department_id": None,
        "section_id": None,
        "approval_status": "Approved",
    }
    payload.update(overrides)
    response = client.post("/api/admin/students", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_student_mentor_endpoint():
    """Student can view their assigned mentor via GET /api/student/mentor."""
    with TestClient(app) as admin, TestClient(app) as student_client:
        admin_login(admin)
        departments = academic_options(admin)
        cse = next(d for d in departments if d["name"] == "CSE")
        sections = cse["sections"]
        section_a = next(s for s in sections if s["name"] == "A")

        # Create faculty
        faculty = create_faculty(admin)
        faculty_code = faculty["faculty_code"]

        # Create a student with no mentor
        student = create_student_with_regno(
            admin,
            "411424243021",
            department_id=cse["id"],
            section_id=section_a["id"],
        )
        student_login(student_client, student["email"])

        # No mentor yet
        resp = student_client.get("/api/student/mentor")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["mentor"] is None
        assert "No mentor has been assigned" in body["message"]

        # Assign the student to this faculty
        assigned = admin.post(
            f"/api/admin/faculty/{faculty['id']}/mentees",
            json={"student_ids": [student["id"]]},
        )
        assert assigned.status_code == 201, assigned.text

        # Student can now see their mentor
        resp = student_client.get("/api/student/mentor")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["mentor"] is not None
        assert body["mentor"]["faculty_code"] == faculty_code
        assert body["mentor"]["email"] == faculty["email"]

        # Faculty sees the student as mentee
        f_mentees = admin.get(f"/api/admin/faculty/{faculty['id']}/mentees")
        assert f_mentees.status_code == 200
        mentee_ids = {m["id"] for m in f_mentees.json()}
        assert student["id"] in mentee_ids

        # Faculty profile count updates
        profile = admin.patch(f"/api/admin/faculty/{faculty['id']}", json={})
        assert profile.status_code == 200
        assert profile.json()["mentee_count"] == 1


def test_bulk_range_assignment_inclusive():
    """Bulk range assignment includes both endpoints."""
    with TestClient(app) as admin:
        admin_login(admin)
        departments = academic_options(admin)
        cse = next(d for d in departments if d["name"] == "CSE")
        sections = cse["sections"]
        section_a = next(s for s in sections if s["name"] == "A")

        faculty = create_faculty(admin, department_id=cse["id"])
        faculty_code = faculty["faculty_code"]

        # Create 4 students with reg numbers 100, 101, 102, 103
        students = []
        for i in range(100, 104):
            s = create_student_with_regno(
                admin,
                f"REG{i:04d}",
                department_id=cse["id"],
                section_id=section_a["id"],
            )
            students.append(s)

        # Preview: range 100-103 should match all 4
        preview = admin.post(
            f"/api/admin/faculty/{faculty['id']}/mentees/range",
            json={
                "from_registration_number": "REG0100",
                "to_registration_number": "REG0103",
                "preview": True,
            },
        )
        assert preview.status_code == 201, preview.text
        preview_body = preview.json()
        assert preview_body["total_matched"] == 4
        assert preview_body["assigned"] == 4
        assert preview_body["skipped"] == 0
        assert preview_body["conflicts"] == 0

        # Assign: range 100-103
        result = admin.post(
            f"/api/admin/faculty/{faculty['id']}/mentees/range",
            json={
                "from_registration_number": "REG0100",
                "to_registration_number": "REG0103",
            },
        )
        assert result.status_code == 201, result.text
        body = result.json()
        assert body["total_matched"] == 4
        assert body["assigned"] == 4
        assert body["skipped"] == 0
        assert body["conflicts"] == 0

        # Verify all 4 are now mentees of this faculty
        mentees = admin.get(f"/api/admin/faculty/{faculty['id']}/mentees")
        assert mentees.status_code == 200
        mentee_ids = {m["id"] for m in mentees.json()}
        for s in students:
            assert s["id"] in mentee_ids

        # Faculty profile count should be 4
        profile = admin.patch(f"/api/admin/faculty/{faculty['id']}", json={})
        assert profile.json()["mentee_count"] == 4


def test_bulk_range_assignment_filters():
    """Department, year, and section filters work on range assignment."""
    with TestClient(app) as admin:
        admin_login(admin)
        departments = academic_options(admin)
        cse = next(d for d in departments if d["name"] == "CSE")
        it = next(d for d in departments if d["name"] == "IT")
        sections = cse["sections"]
        section_a = next(s for s in sections if s["name"] == "A")
        section_b = next(s for s in sections if s["name"] == "B")
        it_sections = next(d for d in departments if d["name"] == "IT")["sections"]
        it_section_a = next(s for s in it_sections if s["name"] == "A")

        faculty = create_faculty(admin, department_id=cse["id"])

        # CSE Section A, Year 2
        s1 = create_student_with_regno(admin, "FILT0001", department_id=cse["id"], section_id=section_a["id"], year_of_study=2)
        # CSE Section B, Year 2
        s2 = create_student_with_regno(admin, "FILT0002", department_id=cse["id"], section_id=section_b["id"], year_of_study=2)
        # IT Section A, Year 2
        s3 = create_student_with_regno(admin, "FILT0003", department_id=it["id"], section_id=it_section_a["id"], year_of_study=2)
        # CSE Section A, Year 3
        s4 = create_student_with_regno(admin, "FILT0004", department_id=cse["id"], section_id=section_a["id"], year_of_study=3)

        # Filter by department CSE only -> s1, s2, s4 (3 students)
        r = admin.post(
            f"/api/admin/faculty/{faculty['id']}/mentees/range",
            json={
                "from_registration_number": "FILT0001",
                "to_registration_number": "FILT0004",
                "department_id": cse["id"],
                "preview": True,
            },
        )
        assert r.status_code == 201
        assert r.json()["total_matched"] == 3

        # Filter by department CSE + section A -> s1, s4 (2 students)
        r = admin.post(
            f"/api/admin/faculty/{faculty['id']}/mentees/range",
            json={
                "from_registration_number": "FILT0001",
                "to_registration_number": "FILT0004",
                "department_id": cse["id"],
                "section_id": section_a["id"],
                "preview": True,
            },
        )
        assert r.status_code == 201
        assert r.json()["total_matched"] == 2

        # Filter by year 3 -> s4 (1 student)
        r = admin.post(
            f"/api/admin/faculty/{faculty['id']}/mentees/range",
            json={
                "from_registration_number": "FILT0001",
                "to_registration_number": "FILT0004",
                "year_of_study": 3,
                "preview": True,
            },
        )
        assert r.status_code == 201
        assert r.json()["total_matched"] == 1


def test_bulk_range_assignment_nonexistent_no_records_created():
    """Nonexistent registration numbers do not create records."""
    with TestClient(app) as admin:
        admin_login(admin)
        departments = academic_options(admin)
        cse = next(d for d in departments if d["name"] == "CSE")
        faculty = create_faculty(admin, department_id=cse["id"])

        before = admin.get(f"/api/admin/faculty/{faculty['id']}/mentees")
        before_count = len(before.json())

        # Range that matches nothing
        r = admin.post(
            f"/api/admin/faculty/{faculty['id']}/mentees/range",
            json={
                "from_registration_number": "ZZZ99999",
                "to_registration_number": "ZZZ99999",
                "preview": True,
            },
        )
        assert r.status_code == 201
        assert r.json()["total_matched"] == 0
        assert r.json()["assigned"] == 0

        # After preview, no new records
        after = admin.get(f"/api/admin/faculty/{faculty['id']}/mentees")
        assert len(after.json()) == before_count


def test_bulk_range_assignment_duplicate_and_conflict():
    """Duplicate assignments are skipped; conflicts with another mentor are identified."""
    with TestClient(app) as admin:
        admin_login(admin)
        departments = academic_options(admin)
        cse = next(d for d in departments if d["name"] == "CSE")
        sections = cse["sections"]
        section_a = next(s for s in sections if s["name"] == "A")

        faculty_a = create_faculty(admin, department_id=cse["id"])
        faculty_a_code = faculty_a["faculty_code"]

        faculty_b = create_faculty(admin, department_id=cse["id"])
        faculty_b_code = faculty_b["faculty_code"]

        # Create students
        s_dup = create_student_with_regno(admin, "DUP0001", department_id=cse["id"], section_id=section_a["id"])
        s_conf = create_student_with_regno(admin, "DUP0002", department_id=cse["id"], section_id=section_a["id"])
        s_new = create_student_with_regno(admin, "DUP0003", department_id=cse["id"], section_id=section_a["id"])

        # Pre-assign s_dup to faculty_a (duplicate case)
        admin.post(
            f"/api/admin/faculty/{faculty_a['id']}/mentees",
            json={"student_ids": [s_dup["id"]]},
        )
        # Pre-assign s_conf to faculty_b (conflict case)
        admin.post(
            f"/api/admin/faculty/{faculty_b['id']}/mentees",
            json={"student_ids": [s_conf["id"]]},
        )

        # Range DUP0001-DUP0003 to faculty_a without reassign
        r = admin.post(
            f"/api/admin/faculty/{faculty_a['id']}/mentees/range",
            json={
                "from_registration_number": "DUP0001",
                "to_registration_number": "DUP0003",
                "reassign_conflicts": False,
            },
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["total_matched"] == 3
        assert body["assigned"] == 1       # only s_new
        assert body["skipped"] == 1        # s_dup already assigned to faculty_a
        assert body["conflicts"] == 1      # s_conf assigned to faculty_b

        # Verify s_conf still belongs to faculty_b (not overwritten)
        b_mentees = admin.get(f"/api/admin/faculty/{faculty_b['id']}/mentees")
        assert b_mentees.status_code == 200
        b_ids = {m["id"] for m in b_mentees.json()}
        assert s_conf["id"] in b_ids

        # Verify faculty_a now has s_dup (skipped, already there) and s_new (newly assigned)
        a_mentees = admin.get(f"/api/admin/faculty/{faculty_a['id']}/mentees")
        assert a_mentees.status_code == 200
        a_ids = {m["id"] for m in a_mentees.json()}
        assert s_dup["id"] in a_ids
        assert s_new["id"] in a_ids
        assert s_conf["id"] not in a_ids

        # Faculty profile count for faculty_a should be 2
        profile = admin.patch(f"/api/admin/faculty/{faculty_a['id']}", json={})
        assert profile.json()["mentee_count"] == 2


def test_bulk_range_assignment_validation():
    """Validation: both registration numbers required, from <= to."""
    with TestClient(app) as admin:
        admin_login(admin)
        departments = academic_options(admin)
        cse = next(d for d in departments if d["name"] == "CSE")
        faculty = create_faculty(admin, department_id=cse["id"])

        # Missing from
        r = admin.post(
            f"/api/admin/faculty/{faculty['id']}/mentees/range",
            json={"to_registration_number": "REG0001"},
        )
        assert r.status_code == 422, r.text

        # Missing to
        r = admin.post(
            f"/api/admin/faculty/{faculty['id']}/mentees/range",
            json={"from_registration_number": "REG0001"},
        )
        assert r.status_code == 422, r.text

        # from > to
        r = admin.post(
            f"/api/admin/faculty/{faculty['id']}/mentees/range",
            json={
                "from_registration_number": "REG0100",
                "to_registration_number": "REG0001",
            },
        )
        assert r.status_code == 422, r.text


def test_student_cannot_access_another_mentor():
    """One student cannot access another student's mentor info."""
    with TestClient(app) as admin, TestClient(app) as s1_client, TestClient(app) as s2_client:
        admin_login(admin)
        departments = academic_options(admin)
        cse = next(d for d in departments if d["name"] == "CSE")
        sections = cse["sections"]
        section_a = next(s for s in sections if s["name"] == "A")

        faculty = create_faculty(admin, department_id=cse["id"])
        faculty_code = faculty["faculty_code"]

        s1 = create_student_with_regno(admin, "XREG0001", department_id=cse["id"], section_id=section_a["id"])
        s2 = create_student_with_regno(admin, "XREG0002", department_id=cse["id"], section_id=section_a["id"])

        # Assign s1 to this faculty only
        assign_resp = admin.post(
            f"/api/admin/faculty/{faculty['id']}/mentees",
            json={"student_ids": [s1["id"]]},
        )
        assert assign_resp.status_code == 201, assign_resp.text

        student_login(s1_client, s1["email"])
        student_login(s2_client, s2["email"])

        # s1 sees their mentor
        r1 = s1_client.get("/api/student/mentor")
        assert r1.status_code == 200
        assert r1.json()["mentor"]["faculty_code"] == faculty_code

        # s2 sees no mentor
        r2 = s2_client.get("/api/student/mentor")
        assert r2.status_code == 200
        assert r2.json()["mentor"] is None


def test_faculty_cannot_access_another_faculty_mentees():
    """One faculty cannot access another faculty's mentee list."""
    with TestClient(app) as admin:
        admin_login(admin)
        departments = academic_options(admin)
        cse = next(d for d in departments if d["name"] == "CSE")

        f1 = create_faculty(admin, department_id=cse["id"])
        f2 = create_faculty(admin, department_id=cse["id"])

        # f1's mentees endpoint should only show f1's mentees
        r = admin.get(f"/api/admin/faculty/{f2['id']}/mentees")
        assert r.status_code == 200
        # f2 has no mentees
        assert r.json() == []
