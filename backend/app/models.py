from __future__ import annotations

from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

class User(Base):
    __tablename__="users"; id: Mapped[int]=mapped_column(primary_key=True); email: Mapped[str]=mapped_column(String(255),unique=True,index=True); password_hash: Mapped[str]=mapped_column(String(255)); role: Mapped[str]=mapped_column(String(20),default="student",index=True); registration_number: Mapped[str|None]=mapped_column(String(64),unique=True,nullable=True,index=True); full_name: Mapped[str|None]=mapped_column(String(160),nullable=True); academic_year: Mapped[str|None]=mapped_column(String(20),nullable=True); department: Mapped[str|None]=mapped_column(String(20),nullable=True); section: Mapped[str|None]=mapped_column(String(2),nullable=True); created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class LoginSession(Base):
    __tablename__="sessions"; id: Mapped[int]=mapped_column(primary_key=True); token_hash: Mapped[str]=mapped_column(String(64),unique=True,index=True); user_id: Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE")); expires_at: Mapped[datetime]=mapped_column(DateTime)
class Topic(Base):
    __tablename__="topics"; id: Mapped[int]=mapped_column(primary_key=True); name: Mapped[str]=mapped_column(String(100),unique=True); position: Mapped[int]=mapped_column(default=0)
class Question(Base):
    __tablename__="questions"; id: Mapped[int]=mapped_column(primary_key=True); image_url: Mapped[str]=mapped_column(Text,default="",nullable=False); owner_id: Mapped[int|None]=mapped_column(ForeignKey("users.id",ondelete="CASCADE"),nullable=True,index=True); title: Mapped[str]=mapped_column(String(200)); slug: Mapped[str]=mapped_column(String(220),unique=True,index=True); statement: Mapped[str]=mapped_column(Text); difficulty: Mapped[str]=mapped_column(String(12),default="Easy"); topic: Mapped[str]=mapped_column(String(100),default="Arrays"); tags: Mapped[str]=mapped_column(Text,default="[]"); constraints: Mapped[str]=mapped_column(Text,default=""); input_format: Mapped[str]=mapped_column(Text,default=""); output_format: Mapped[str]=mapped_column(Text,default=""); hints: Mapped[str]=mapped_column(Text,default=""); editorial: Mapped[str]=mapped_column(Text,default=""); starter_code: Mapped[str]=mapped_column(Text,default="{}"); published: Mapped[bool]=mapped_column(Boolean,default=False); created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class TestCase(Base):
    __tablename__="test_cases"; id: Mapped[int]=mapped_column(primary_key=True); question_id: Mapped[int]=mapped_column(ForeignKey("questions.id",ondelete="CASCADE"),index=True); input: Mapped[str]=mapped_column(Text); expected_output: Mapped[str]=mapped_column(Text); is_hidden: Mapped[bool]=mapped_column(Boolean,default=False)
class Sheet(Base):
    __tablename__="sheets"; id: Mapped[int]=mapped_column(primary_key=True); owner_id: Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE"),index=True); title: Mapped[str]=mapped_column(String(160)); description: Mapped[str]=mapped_column(Text,default=""); share_token: Mapped[str]=mapped_column(String(48),unique=True); is_public: Mapped[bool]=mapped_column(Boolean,default=False); target_date: Mapped[str]=mapped_column(String(20),default=""); created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class SheetQuestion(Base):
    __tablename__="sheet_questions"; sheet_id: Mapped[int]=mapped_column(ForeignKey("sheets.id",ondelete="CASCADE"),primary_key=True); question_id: Mapped[int]=mapped_column(ForeignKey("questions.id",ondelete="CASCADE"),primary_key=True); position: Mapped[int]=mapped_column(default=0)
class Submission(Base):
    __tablename__="submissions"; id: Mapped[int]=mapped_column(primary_key=True); user_id: Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE"),index=True); question_id: Mapped[int]=mapped_column(ForeignKey("questions.id",ondelete="CASCADE")); language: Mapped[str]=mapped_column(String(20)); source: Mapped[str]=mapped_column(Text); verdict: Mapped[str]=mapped_column(String(32)); runtime_ms: Mapped[int]=mapped_column(default=0); created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class Course(Base):
    __tablename__="courses"; id: Mapped[int]=mapped_column(primary_key=True); title: Mapped[str]=mapped_column(String(160),unique=True); code: Mapped[str]=mapped_column(String(40),unique=True,index=True); description: Mapped[str]=mapped_column(Text,default=""); faculty_id: Mapped[int|None]=mapped_column(ForeignKey("users.id",ondelete="SET NULL"),nullable=True); active: Mapped[bool]=mapped_column(Boolean,default=True); created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class CourseQuestion(Base):
    __tablename__="course_questions"; course_id: Mapped[int]=mapped_column(ForeignKey("courses.id",ondelete="CASCADE"),primary_key=True); question_id: Mapped[int]=mapped_column(ForeignKey("questions.id",ondelete="CASCADE"),primary_key=True); position: Mapped[int]=mapped_column(default=0)
class Enrollment(Base):
    __tablename__="enrollments"; __table_args__=(UniqueConstraint("course_id","student_id"),); id: Mapped[int]=mapped_column(primary_key=True); course_id: Mapped[int]=mapped_column(ForeignKey("courses.id",ondelete="CASCADE"),index=True); student_id: Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE"),index=True); faculty_id: Mapped[int|None]=mapped_column(ForeignKey("users.id",ondelete="SET NULL"),nullable=True); created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class ProblemAssignment(Base):
    __tablename__="problem_assignments"
    __table_args__=(UniqueConstraint("faculty_id","student_id","question_id"),)
    id: Mapped[int]=mapped_column(primary_key=True)
    faculty_id: Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE"),index=True)
    student_id: Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE"),index=True)
    question_id: Mapped[int]=mapped_column(ForeignKey("questions.id",ondelete="CASCADE"),index=True)
    due_at: Mapped[datetime|None]=mapped_column(DateTime,nullable=True)
    note: Mapped[str]=mapped_column(Text,default="")
    created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)

class Assessment(Base):
    __tablename__="assessments"; id: Mapped[int]=mapped_column(primary_key=True); course_id: Mapped[int]=mapped_column(ForeignKey("courses.id",ondelete="CASCADE"),index=True); faculty_id: Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE")); title: Mapped[str]=mapped_column(String(160)); description: Mapped[str]=mapped_column(Text,default=""); academic_year: Mapped[str|None]=mapped_column(String(20),nullable=True); department: Mapped[str|None]=mapped_column(String(20),nullable=True); section: Mapped[str|None]=mapped_column(String(2),nullable=True); starts_at: Mapped[datetime|None]=mapped_column(DateTime,nullable=True); ends_at: Mapped[datetime|None]=mapped_column(DateTime,nullable=True); published: Mapped[bool]=mapped_column(Boolean,default=False); created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class AssessmentQuestion(Base):
    __tablename__="assessment_questions"; assessment_id: Mapped[int]=mapped_column(ForeignKey("assessments.id",ondelete="CASCADE"),primary_key=True); question_id: Mapped[int]=mapped_column(ForeignKey("questions.id",ondelete="CASCADE"),primary_key=True); points: Mapped[int]=mapped_column(default=10)
class AssessmentAttempt(Base):
    __tablename__="assessment_attempts"; __table_args__=(UniqueConstraint("assessment_id","student_id"),); id: Mapped[int]=mapped_column(primary_key=True); assessment_id: Mapped[int]=mapped_column(ForeignKey("assessments.id",ondelete="CASCADE"),index=True); student_id: Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE"),index=True); score: Mapped[int]=mapped_column(default=0); submitted_at: Mapped[datetime|None]=mapped_column(DateTime,nullable=True); shared: Mapped[bool]=mapped_column(Boolean,default=False)
class Progress(Base):
    __tablename__="progress"; __table_args__=(UniqueConstraint("user_id","question_id"),); id: Mapped[int]=mapped_column(primary_key=True); user_id: Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE")); question_id: Mapped[int]=mapped_column(ForeignKey("questions.id",ondelete="CASCADE")); attempts: Mapped[int]=mapped_column(default=0); solved: Mapped[bool]=mapped_column(Boolean,default=False); bookmarked: Mapped[bool]=mapped_column(Boolean,default=False); notes: Mapped[str]=mapped_column(Text,default=""); confidence: Mapped[int]=mapped_column(default=0); revision_due: Mapped[datetime|None]=mapped_column(DateTime,nullable=True); last_attempted: Mapped[datetime|None]=mapped_column(DateTime,nullable=True)

