"""DSA Forge API application setup and router registration."""
from __future__ import annotations

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
<<<<<<< HEAD
from .routes import router
from .startup import seed

app = FastAPI(title="DSA Forge API", version="0.1.0")
origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
app.on_event("startup")(seed)
=======
from pydantic import BaseModel, Field
from pwdlib import PasswordHash
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine, func, inspect, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session, sessionmaker

DB_URL = os.getenv("DATABASE_URL", "sqlite:///./dsa_forge.db")
engine = create_engine(DB_URL, connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
password_hash = PasswordHash.recommended()

class Base(DeclarativeBase): pass
class User(Base):
    __tablename__="users"; id: Mapped[int]=mapped_column(primary_key=True); email: Mapped[str]=mapped_column(String(255),unique=True,index=True); password_hash: Mapped[str]=mapped_column(String(255)); role: Mapped[str]=mapped_column(String(20),default="student",index=True); registration_number: Mapped[str|None]=mapped_column(String(64),unique=True,nullable=True,index=True); created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class LoginSession(Base):
    __tablename__="sessions"; id: Mapped[int]=mapped_column(primary_key=True); token_hash: Mapped[str]=mapped_column(String(64),unique=True,index=True); user_id: Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE")); expires_at: Mapped[datetime]=mapped_column(DateTime)
class Topic(Base):
    __tablename__="topics"; id: Mapped[int]=mapped_column(primary_key=True); name: Mapped[str]=mapped_column(String(100),unique=True); position: Mapped[int]=mapped_column(default=0)
class Question(Base):
    __tablename__="questions"; id: Mapped[int]=mapped_column(primary_key=True); owner_id: Mapped[int|None]=mapped_column(ForeignKey("users.id",ondelete="CASCADE"),nullable=True,index=True); title: Mapped[str]=mapped_column(String(200)); slug: Mapped[str]=mapped_column(String(220),unique=True,index=True); statement: Mapped[str]=mapped_column(Text); difficulty: Mapped[str]=mapped_column(String(12),default="Easy"); topic: Mapped[str]=mapped_column(String(100),default="Arrays"); tags: Mapped[str]=mapped_column(Text,default="[]"); constraints: Mapped[str]=mapped_column(Text,default=""); input_format: Mapped[str]=mapped_column(Text,default=""); output_format: Mapped[str]=mapped_column(Text,default=""); hints: Mapped[str]=mapped_column(Text,default=""); editorial: Mapped[str]=mapped_column(Text,default=""); starter_code: Mapped[str]=mapped_column(Text,default="{}"); published: Mapped[bool]=mapped_column(Boolean,default=False); created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
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
class Assessment(Base):
    __tablename__="assessments"; id: Mapped[int]=mapped_column(primary_key=True); course_id: Mapped[int]=mapped_column(ForeignKey("courses.id",ondelete="CASCADE"),index=True); faculty_id: Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE")); title: Mapped[str]=mapped_column(String(160)); description: Mapped[str]=mapped_column(Text,default=""); starts_at: Mapped[datetime|None]=mapped_column(DateTime,nullable=True); ends_at: Mapped[datetime|None]=mapped_column(DateTime,nullable=True); published: Mapped[bool]=mapped_column(Boolean,default=False); created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class AssessmentQuestion(Base):
    __tablename__="assessment_questions"; assessment_id: Mapped[int]=mapped_column(ForeignKey("assessments.id",ondelete="CASCADE"),primary_key=True); question_id: Mapped[int]=mapped_column(ForeignKey("questions.id",ondelete="CASCADE"),primary_key=True); points: Mapped[int]=mapped_column(default=10)
class AssessmentAttempt(Base):
    __tablename__="assessment_attempts"; __table_args__=(UniqueConstraint("assessment_id","student_id"),); id: Mapped[int]=mapped_column(primary_key=True); assessment_id: Mapped[int]=mapped_column(ForeignKey("assessments.id",ondelete="CASCADE"),index=True); student_id: Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE"),index=True); score: Mapped[int]=mapped_column(default=0); submitted_at: Mapped[datetime|None]=mapped_column(DateTime,nullable=True); shared: Mapped[bool]=mapped_column(Boolean,default=False)
class Progress(Base):
    __tablename__="progress"; __table_args__=(UniqueConstraint("user_id","question_id"),); id: Mapped[int]=mapped_column(primary_key=True); user_id: Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE")); question_id: Mapped[int]=mapped_column(ForeignKey("questions.id",ondelete="CASCADE")); attempts: Mapped[int]=mapped_column(default=0); solved: Mapped[bool]=mapped_column(Boolean,default=False); bookmarked: Mapped[bool]=mapped_column(Boolean,default=False); notes: Mapped[str]=mapped_column(Text,default=""); confidence: Mapped[int]=mapped_column(default=0); revision_due: Mapped[datetime|None]=mapped_column(DateTime,nullable=True); last_attempted: Mapped[datetime|None]=mapped_column(DateTime,nullable=True)

class Credentials(BaseModel): email: str = Field(min_length=3,max_length=255); password: str = Field(min_length=8,max_length=128); registration_number: str|None = Field(default=None,max_length=64)
class TestIn(BaseModel): input: str = Field(max_length=10000); expected_output: str = Field(max_length=10000); is_hidden: bool=False
class QuestionIn(BaseModel):
    title: str=Field(min_length=3,max_length=200); statement: str=Field(min_length=3); difficulty: Literal["Easy","Medium","Hard"]="Easy"; topic: str="Arrays"; tags: list[str]=[]; constraints: str=""; input_format: str=""; output_format: str=""; hints: str=""; editorial: str=""; starter_code: dict[str,str]={}; published: bool=False; tests: list[TestIn]=[]
class SheetIn(BaseModel): title: str=Field(min_length=2,max_length=160); description: str=""; is_public: bool=False; target_date: str=""
class ExecuteIn(BaseModel): question_id:int; language: Literal["c","cpp","java","python","go"]; source:str=Field(min_length=1,max_length=100000); input: str|None=None
class ProgressIn(BaseModel): bookmarked: bool|None=None; notes: str|None=Field(default=None,max_length=10000); confidence: int|None=Field(default=None,ge=0,le=5); revision_due: datetime|None=None

app=FastAPI(title="DSA Forge API",version="0.1.0")
origins=os.getenv("CORS_ORIGINS","http://localhost:5173").split(",")
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
def db():
    s=SessionLocal()
    try: yield s
    finally: s.close()
def token_hash(x:str): return hashlib.sha256(x.encode()).hexdigest()
def current(request:Request, s:Session=Depends(db)):
    raw=request.cookies.get(os.getenv("SESSION_COOKIE_NAME","dsa_forge_session"))
    row=s.scalar(select(LoginSession).where(LoginSession.token_hash==token_hash(raw or ""),LoginSession.expires_at>datetime.utcnow()))
    if not row: raise HTTPException(401,"Authentication required")
    return s.get(User,row.user_id)
def slugify(title:str):
    base="".join(c.lower() if c.isalnum() else "-" for c in title).strip("-")[:180] or "question"; return f"{base}-{secrets.token_hex(4)}"
def visible(q:Question,s:Session):
    return {"id":q.id,"title":q.title,"slug":q.slug,"statement":q.statement,"difficulty":q.difficulty,"topic":q.topic,"tags":json.loads(q.tags),"constraints":q.constraints,"input_format":q.input_format,"output_format":q.output_format,"hints":q.hints,"editorial":q.editorial,"starter_code":json.loads(q.starter_code),"published":q.published,"created_at":q.created_at,"tests":[{"id":t.id,"input":t.input,"expected_output":t.expected_output} for t in s.scalars(select(TestCase).where(TestCase.question_id==q.id,TestCase.is_hidden==False))]}
def owned(q:Question,u:User): return q.owner_id==u.id
def progress_for(s,u,qid):
    p=s.scalar(select(Progress).where(Progress.user_id==u.id,Progress.question_id==qid))
    if not p: p=Progress(user_id=u.id,question_id=qid); s.add(p); s.flush()
    return p

@app.on_event("startup")
def seed():
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
      columns={column["name"] for column in inspect(conn).get_columns("users")}
      if "role" not in columns: conn.exec_driver_sql("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'student'")
      if "registration_number" not in columns: conn.exec_driver_sql("ALTER TABLE users ADD COLUMN registration_number VARCHAR(64)")
    with SessionLocal() as s:
      admin_email=os.getenv("ADMIN_EMAIL","").strip().lower(); admin_password=os.getenv("ADMIN_PASSWORD","")
      if admin_email and admin_password and not s.scalar(select(User).where(User.email==admin_email)):
        s.add(User(email=admin_email,password_hash=password_hash.hash(admin_password),role="admin"));s.commit()
      if not s.scalar(select(Question.id).limit(1)):
        q=Question(title="Pair Sum",slug="pair-sum",statement="Given integers on one line, print `YES` if any two values sum to the target on the second line; otherwise print `NO`.",difficulty="Easy",topic="Arrays",tags='["hashing","arrays"]',constraints="2 <= n <= 100000",input_format="space-separated integers, then target",output_format="YES or NO",hints="Store seen values in a set.",editorial="For each number x, check whether target-x was already seen.",starter_code=json.dumps({"python":"nums=list(map(int,input().split()))\ntarget=int(input())\n# print('YES' or 'NO')\n","cpp":"#include <bits/stdc++.h>\nusing namespace std; int main(){ /* read input */ }\n","c":"#include <stdio.h>\nint main(void){ return 0; }\n","java":"import java.util.*; class Main { public static void main(String[] a){} }\n","go":"package main\nfunc main() {}\n"}),published=True)
        s.add(q);s.flush();s.add_all([TestCase(question_id=q.id,input="2 7 11 15\n9\n",expected_output="YES\n"),TestCase(question_id=q.id,input="1 2 3\n10\n",expected_output="NO\n",is_hidden=True)]);s.commit()
    with SessionLocal() as s:
      if not s.scalar(select(Question).where(Question.slug=="pair-sum-function")):
        fq=Question(title="Pair Sum (Function)",slug="pair-sum-function",statement="Implement `has_pair_sum(nums, target)`. Return true when two distinct values sum to target; otherwise return false. Write only the function: the judge supplies inputs and calls it.",difficulty="Easy",topic="Arrays",tags='["hashing","function-contract"]',constraints="2 <= n <= 100000",input_format="The judge calls has_pair_sum(nums, target).",output_format="Return a boolean.",hints="Track values seen so far in a set.",editorial="For each x, check whether target-x has already appeared.",starter_code=json.dumps({"python":"def has_pair_sum(nums, target):\n    # return True or False\n    pass\n","cpp":"#include <bits/stdc++.h>\nusing namespace std;\nclass Solution { public: bool hasPairSum(vector<int>& nums, int target) { return false; } };\n","c":"#include <stdbool.h>\nbool has_pair_sum(const int* nums, int n, int target) { return false; }\n","java":"import java.util.*;\nclass Solution { public boolean hasPairSum(int[] nums, int target) { return false; } }\n","go":"package main\nimport \"fmt\"\nfunc hasPairSum(nums []int, target int) bool { return false }\n"}),published=True)
        s.add(fq);s.flush();s.add_all([TestCase(question_id=fq.id,input='{"nums":[2,7,11,15],"target":9}',expected_output="true\n"),TestCase(question_id=fq.id,input='{"nums":[1,2,3],"target":10}',expected_output="false\n",is_hidden=True)]);s.commit()
    with SessionLocal() as s:
      fq=s.scalar(select(Question).where(Question.slug=="pair-sum-function"))
      if fq:
        visible_cases=[
          ({"nums":[2,7,11,15],"target":9},"true\n"),
          ({"nums":[3,1,4,8],"target":12},"true\n"),
          ({"nums":[-5,12,7,20],"target":2},"true\n"),
          ({"nums":[1,2,3,4],"target":20},"false\n"),
          ({"nums":[0,0,5,-5],"target":0},"true\n"),
        ]
        hidden_cases=[]
        for index in range(30):
          nums=[index+3, -(index+8), 1000+index]
          if index % 2 == 0:
            target=nums[0]+nums[1]
            expected="true\n"
          else:
            target=999999
            expected="false\n"
          hidden_cases.append(({"nums":nums,"target":target},expected))
        existing={t.input for t in s.scalars(select(TestCase).where(TestCase.question_id==fq.id))}
        for payload,expected in visible_cases+hidden_cases:
          raw=json.dumps(payload,separators=(",",":"))
          if raw not in existing:
            s.add(TestCase(question_id=fq.id,input=raw,expected_output=expected,is_hidden=(payload,expected) in hidden_cases))
        s.commit()
with SessionLocal() as s:
      for slug, clean_constraints in (("pair-sum", "2 <= n <= 100000"), ("pair-sum-function", "2 <= n <= 100000")):
        question = s.scalar(select(Question).where(Question.slug == slug))
        if question and ("?" in question.constraints or question.constraints.strip() != clean_constraints):
          question.constraints = clean_constraints
      s.commit()

@app.get("/api/health")
def health(): return {"status":"ok","executor":"docker" if _docker() else "unavailable"}
@app.post("/api/auth/register",status_code=201)
def register(body:Credentials,response:Response,s:Session=Depends(db)):
    if s.scalar(select(User).where(User.email==body.email.lower())): raise HTTPException(409,"Email already registered")
    u=User(email=body.email.lower(),password_hash=password_hash.hash(body.password),registration_number=body.registration_number,role="student");s.add(u);s.commit();s.refresh(u); return _login(u,response,s)
@app.post("/api/auth/login")
def login(body:Credentials,response:Response,s:Session=Depends(db)):
    u=s.scalar(select(User).where(User.email==body.email.lower()))
    if not u or not password_hash.verify(body.password,u.password_hash): raise HTTPException(401,"Invalid email or password")
    return _login(u,response,s)
def _login(u,response,s):
    raw=secrets.token_urlsafe(32);s.add(LoginSession(token_hash=token_hash(raw),user_id=u.id,expires_at=datetime.utcnow()+timedelta(days=14)));s.commit();response.set_cookie(os.getenv("SESSION_COOKIE_NAME","dsa_forge_session"),raw,httponly=True,samesite="lax",secure=False,max_age=1209600);return {"id":u.id,"email":u.email,"role":u.role,"registration_number":u.registration_number}
@app.post("/api/auth/logout",status_code=204)
def logout(request:Request,response:Response,s:Session=Depends(db)):
    raw=request.cookies.get(os.getenv("SESSION_COOKIE_NAME","dsa_forge_session"));
    if raw:
      x=s.scalar(select(LoginSession).where(LoginSession.token_hash==token_hash(raw)))
      if x:s.delete(x);s.commit()
    response.delete_cookie(os.getenv("SESSION_COOKIE_NAME","dsa_forge_session"))
@app.get("/api/auth/me")
def me(u:User=Depends(current)): return {"id":u.id,"email":u.email,"role":u.role,"registration_number":u.registration_number,"username":f"student-{u.id}" if u.role=="student" else None}

def profile_summary(user:User,s:Session):
    progress=list(s.scalars(select(Progress).where(Progress.user_id==user.id)))
    solved_ids=[p.question_id for p in progress if p.solved]
    difficulties={"Easy":0,"Medium":0,"Hard":0}
    if solved_ids:
        for difficulty in s.scalars(select(Question.difficulty).where(Question.id.in_(solved_ids))): difficulties[difficulty]=difficulties.get(difficulty,0)+1
    submissions=list(s.scalars(select(Submission).where(Submission.user_id==user.id)))
    days={item.created_at.date() for item in submissions}; streak=0; cursor=date.today()
    while cursor in days: streak+=1; cursor-=timedelta(days=1)
    activity=[{"date":str(day),"count":sum(item.created_at.date()==day for item in submissions)} for day in sorted(days)]
    return {"username":f"student-{user.id}","display_name":user.email.split("@",1)[0].replace("."," ").replace("_"," ").title(),"solved":len(solved_ids),"attempted":len(progress),"streak":streak,"submissions":len(submissions),"easy":difficulties["Easy"],"medium":difficulties["Medium"],"hard":difficulties["Hard"],"activity":activity}

@app.get("/api/profile/me")
def own_profile(u:User=Depends(current),s:Session=Depends(db)):
    return profile_summary(u,s)

@app.get("/api/students/search")
def search_students(q: str = "", u: User = Depends(current), s: Session = Depends(db)):
    term = q.strip().lower()
    if len(term) < 2:
        return []
    statement = select(User).where(User.role == "student")
    if term.startswith("student-") and term[8:].isdigit():
        statement = statement.where(User.id == int(term[8:]))
    else:
        statement = statement.where(func.lower(User.email).contains(term))
    users = list(s.scalars(statement.order_by(User.id).limit(10)))
    return [{
        "username": f"student-{user.id}",
        "display_name": user.email.split("@", 1)[0].replace(".", " ").replace("_", " ").title(),
    } for user in users]

@app.get("/api/u/{username}")
def public_profile(username:str,s:Session=Depends(db)):
    if not username.lower().startswith("student-") or not username[8:].isdigit(): raise HTTPException(404,"Profile not found")
    user=s.get(User,int(username[8:]))
    if not user or user.role!="student": raise HTTPException(404,"Profile not found")
    return profile_summary(user,s)

@app.get("/api/questions")
def questions(search:str="",difficulty:str="",topic:str="",status_filter:str="",page:int=1,page_size:int=20,u:User=Depends(current),s:Session=Depends(db)):
    stmt=select(Question).where((Question.published==True)|(Question.owner_id==u.id))
    if search: stmt=stmt.where(Question.title.ilike(f"%{search}%"))
    if difficulty: stmt=stmt.where(Question.difficulty==difficulty)
    if topic: stmt=stmt.where(Question.topic==topic)
    items=list(s.scalars(stmt.order_by(Question.id.desc()).offset((page-1)*min(page_size,100)).limit(min(page_size,100))))
    result=[]
    for q in items:
      data=visible(q,s);p=s.scalar(select(Progress).where(Progress.user_id==u.id,Progress.question_id==q.id));data["progress"]={"solved":p.solved,"bookmarked":p.bookmarked,"attempts":p.attempts} if p else {"solved":False,"bookmarked":False,"attempts":0}
      if not status_filter or (status_filter=="solved" and data["progress"]["solved"]) or (status_filter=="bookmarked" and data["progress"]["bookmarked"]) or (status_filter=="unsolved" and not data["progress"]["solved"]):result.append(data)
    return {"items":result,"page":page}
@app.get("/api/questions/{slug}")
def question(slug:str,u:User=Depends(current),s:Session=Depends(db)):
    q=s.scalar(select(Question).where(Question.slug==slug));
    if not q or not(q.published or owned(q,u)):raise HTTPException(404,"Question not found")
    return visible(q,s)
@app.post("/api/questions",status_code=201)
def create_question(body:QuestionIn,u:User=Depends(current),s:Session=Depends(db)): return save_question(None,body,u,s)
@app.patch("/api/questions/{qid}")
def edit_question(qid:int,body:QuestionIn,u:User=Depends(current),s:Session=Depends(db)):
    q=s.get(Question,qid)
    if not q or not owned(q,u):raise HTTPException(404,"Question not found")
    return save_question(q,body,u,s)
def save_question(q,body,u,s):
    q=q or Question(owner_id=u.id,slug=slugify(body.title));
    for k,v in body.model_dump(exclude={"tests"}).items(): setattr(q,k,json.dumps(v) if k in {"tags","starter_code"} else v)
    s.add(q);s.flush()
    if body.tests:
      if q.id: s.query(TestCase).filter(TestCase.question_id==q.id).delete()
      s.add_all(TestCase(question_id=q.id,**t.model_dump()) for t in body.tests)
    s.commit();return visible(q,s)
@app.delete("/api/questions/{qid}",status_code=204)
def delete_question(qid:int,u:User=Depends(current),s:Session=Depends(db)):
    q=s.get(Question,qid)
    if not q or not owned(q,u):raise HTTPException(404,"Question not found")
    s.delete(q);s.commit()

@app.get("/api/sheets")
def sheets(u:User=Depends(current),s:Session=Depends(db)): return [{"id":x.id,"title":x.title,"description":x.description,"is_public":x.is_public,"target_date":x.target_date,"count":s.scalar(select(func.count()).select_from(SheetQuestion).where(SheetQuestion.sheet_id==x.id))} for x in s.scalars(select(Sheet).where(Sheet.owner_id==u.id))]
@app.post("/api/sheets",status_code=201)
def create_sheet(body:SheetIn,u:User=Depends(current),s:Session=Depends(db)): x=Sheet(owner_id=u.id,share_token=secrets.token_urlsafe(18),**body.model_dump());s.add(x);s.commit();return {"id":x.id,"title":x.title,"share_token":x.share_token}
@app.get("/api/sheets/{sid}")
def sheet(sid:int,u:User=Depends(current),s:Session=Depends(db)):
    x=s.get(Sheet,sid)
    if not x or x.owner_id!=u.id:raise HTTPException(404,"Sheet not found")
    return {"id":x.id,"title":x.title,"description":x.description,"share_token":x.share_token,"questions":[visible(s.get(Question,r.question_id),s) for r in s.scalars(select(SheetQuestion).where(SheetQuestion.sheet_id==sid).order_by(SheetQuestion.position))]}
@app.patch("/api/sheets/{sid}")
def update_sheet(sid:int,body:SheetIn,u:User=Depends(current),s:Session=Depends(db)):
    x=s.get(Sheet,sid)
    if not x or x.owner_id!=u.id:raise HTTPException(404,"Sheet not found")
    for k,v in body.model_dump().items():setattr(x,k,v)
    s.commit();return {"id":x.id,"title":x.title}
@app.delete("/api/sheets/{sid}",status_code=204)
def delete_sheet(sid:int,u:User=Depends(current),s:Session=Depends(db)):
    x=s.get(Sheet,sid)
    if not x or x.owner_id!=u.id:raise HTTPException(404,"Sheet not found")
    s.delete(x);s.commit()
@app.post("/api/sheets/{sid}/questions",status_code=201)
def add_to_sheet(sid:int,question_id:int,u:User=Depends(current),s:Session=Depends(db)):
    x=s.get(Sheet,sid);q=s.get(Question,question_id)
    if not x or x.owner_id!=u.id or not q or not(q.published or owned(q,u)):raise HTTPException(404,"Resource not found")
    if s.get(SheetQuestion,{"sheet_id":sid,"question_id":question_id}):raise HTTPException(409,"Already in sheet")
    s.add(SheetQuestion(sheet_id=sid,question_id=question_id,position=s.scalar(select(func.count()).select_from(SheetQuestion).where(SheetQuestion.sheet_id==sid))));s.commit();return {"ok":True}

def _docker_client():
    if docker is None: return None
    try:
        client=docker.DockerClient(base_url="unix:///var/run/docker.sock", timeout=3)
        client.ping()
        return client
    except Exception as error:
        print(f"Docker probe failed: {type(error).__name__}: {error}", flush=True)
        return None
def _docker():
    client=_docker_client()
    if client is None: return False
    client.close()
    return True
def function_source(source:str, language:str, raw_input:str):
    data=json.loads(raw_input); nums=data["nums"]; target=data["target"]; values=",".join(map(str,nums))
    if language=="python": return source+f"\nimport json\nprint(json.dumps(has_pair_sum({nums!r}, {target})))\n"
    if language=="cpp": return source+f'\nint main(){{ vector<int> nums={{{values}}}; cout << (Solution().hasPairSum(nums,{target}) ? "true" : "false"); }}\n'
    if language=="c": return source+f"\n#include <stdio.h>\nint main(void){{ int nums[]={{ {values} }}; printf(\"%s\",has_pair_sum(nums,{len(nums)},{target}) ? \"true\" : \"false\"); return 0; }}\n"
    if language=="java": return source+f"\nclass Main {{ public static void main(String[] args) {{ System.out.print(new Solution().hasPairSum(new int[]{{{values}}},{target})); }} }}\n"
    if language=="go": return source+f"\nfunc main() {{ fmt.Print(hasPairSum([]int{{{values}}}, {target})) }}\n"
    raise ValueError("Unsupported language")
def is_function_question(q):
    return q.slug.endswith("-function") or "function" in q.title.lower()
def outputs_match(actual:str,expected:str):
    a=actual.strip(); e=expected.strip()
    if a.lower() in {"true","false"} and e.lower() in {"true","false"}: return a.lower()==e.lower()
    return a==e
def split_docker_logs(raw: bytes):
    if not raw:
        return b"", b""
    stdout_parts=[]; stderr_parts=[]; offset=0
    while offset+8 <= len(raw) and raw[offset] in (0,1,2):
        size=int.from_bytes(raw[offset+4:offset+8],"big")
        end=offset+8+size
        if end > len(raw):
            break
        (stdout_parts if raw[offset]==1 else stderr_parts).append(raw[offset+8:end])
        offset=end
    if offset != len(raw):
        stdout_parts.append(raw[offset:])
    return b"".join(stdout_parts), b"".join(stderr_parts)

def execute(body:ExecuteIn,inputs:list[str],function_mode:bool=False,verify:bool=False):
    client=_docker_client()
    if client is None: raise HTTPException(503,"Docker executor unavailable. Check the Docker socket and executor image.")
    suffix={"c":"main.c","cpp":"main.cpp","java":"Main.java","python":"main.py","go":"main.go"}[body.language]
    commands={"c":"gcc /tmp/main.c -O2 -o /tmp/a && /tmp/a","cpp":"g++ /tmp/main.cpp -O2 -o /tmp/a && /tmp/a","java":"javac -d /tmp /tmp/Main.java && java -cp /tmp Main","python":"python3 -I /tmp/main.py","go":"go build -o /tmp/a /tmp/main.go && /tmp/a"}
    with tempfile.TemporaryDirectory() as d:
      Path(d,suffix).write_text(body.source,encoding="utf-8"); out=[]
      for inp in inputs:
       if function_mode and body.language=="python":
        Path(d,"solution.py").write_text(body.source,encoding="utf-8")
        data=json.loads(inp)
        runner=f"import json\nnamespace={{}}\nexec(compile(open(\"/tmp/solution.py\", encoding=\"utf-8\").read(), \"solution.py\", \"exec\"), namespace)\nprint(json.dumps(namespace[\"has_pair_sum\"]({data['nums']!r}, {data['target']})))\n"
        Path(d,"main.py").write_text(runner,encoding="utf-8")
       elif function_mode:
        Path(d,suffix).write_text(function_source(body.source,body.language,inp),encoding="utf-8")
       else:
        Path(d,suffix).write_text(body.source,encoding="utf-8")
       Path(d,"input").write_text("" if function_mode else inp,encoding="utf-8")
       container_id=None; start=time.perf_counter()
       try:
        host_config=client.api.create_host_config(network_mode="none",read_only=False,pids_limit=64,mem_limit="256m",nano_cpus=1_000_000_000,cap_drop=["ALL"],security_opt=["no-new-privileges"])
        container_id=client.api.create_container(image=os.getenv("EXECUTOR_IMAGE","dsa-forge-executor:local"),command=["/bin/sh","-c",f"{commands[body.language]} < /tmp/input"],user="10001",host_config=host_config)["Id"]
        archive=io.BytesIO()
        with tarfile.open(fileobj=archive,mode="w") as bundle:
         for item in Path(d).iterdir(): bundle.add(item,arcname=item.name)
        client.api.put_archive(container_id,"/tmp",archive.getvalue())
        client.api.start(container_id)
        result=client.api.wait(container_id,timeout=8); status_code=result.get("StatusCode",1) if isinstance(result,dict) else int(result)
        raw_logs=client.api.logs(container_id,stdout=True,stderr=True)
        stdout_bytes,stderr_bytes=split_docker_logs(raw_logs)
        stdout=stdout_bytes.decode(errors="replace"); stderr=stderr_bytes.decode(errors="replace"); elapsed=int((time.perf_counter()-start)*1000)
       except Exception as error:
        elapsed=int((time.perf_counter()-start)*1000); out.append({"output":"","stderr":str(error),"runtime_ms":elapsed}); return {"verdict":"Runtime Error","results":out,"runtime_ms":elapsed}
       finally:
        if container_id:
         try: client.api.remove_container(container_id,force=True)
         except docker.errors.DockerException: pass
       if len(stdout)+len(stderr)>65536:return {"verdict":"Output Limit Exceeded","results":out+[{"output":"","stderr":"Output exceeded 64KB","runtime_ms":elapsed}],"runtime_ms":elapsed}
       if status_code:
        case={"output":stdout,"stderr":stderr,"runtime_ms":elapsed};out.append(case)
        compile_failure=body.language != "python" and ("error:" in stderr.lower() or "fatal" in stderr.lower() or "cannot find symbol" in stderr.lower())
        return {"verdict":"Compilation Error" if compile_failure else "Runtime Error","results":out,"runtime_ms":elapsed}
       out.append({"output":stdout,"stderr":stderr,"runtime_ms":elapsed})
      return {"verdict":"Accepted" if verify else "Executed","results":out,"runtime_ms":max((x["runtime_ms"] for x in out),default=0)}
@app.post("/api/run")
def run(body:ExecuteIn,u:User=Depends(current),s:Session=Depends(db)):
    q=s.get(Question,body.question_id)
    if not q or not(q.published or owned(q,u)):raise HTTPException(404,"Question not found")
    sample=s.scalar(select(TestCase).where(TestCase.question_id==q.id,TestCase.input==body.input,TestCase.is_hidden==False))
    inputs=[body.input] if body.input is not None else list(s.scalars(select(TestCase.input).where(TestCase.question_id==q.id,TestCase.is_hidden==False)))
    result=execute(body,inputs,is_function_question(q),False)
    if sample and result.get("verdict")=="Executed":
        actual=result.get("results",[{}])[0].get("output","").strip()
        passed=outputs_match(actual,sample.expected_output)
        result["verdict"]="Accepted" if passed else "Wrong Answer"
        if result.get("results"):
            result["results"][0].update({"passed":passed,"input":sample.input,"expected":sample.expected_output})
    return result
@app.post("/api/submit")
def submit(body:ExecuteIn,u:User=Depends(current),s:Session=Depends(db)):
    q=s.get(Question,body.question_id)
    if not q or not(q.published or owned(q,u)):raise HTTPException(404,"Question not found")
    tests=list(s.scalars(select(TestCase).where(TestCase.question_id==q.id)));result=execute(body,[t.input for t in tests],is_function_question(q),True); verdict=result["verdict"]
    results=result.get("results",[])
    mismatches=[]; case_results=[]
    for i,(r,t) in enumerate(zip(results,tests)):
        passed=outputs_match(r.get("output",""),t.expected_output)
        case_results.append({"case":i+1,"passed":passed,"runtime_ms":r.get("runtime_ms",0),"input":t.input if not t.is_hidden else None,"output":r.get("output","") if not t.is_hidden else None,"expected":t.expected_output if not t.is_hidden else None,"stderr":r.get("stderr","")})
        if not passed: mismatches.append({"case":i+1,"expected":t.expected_output if not t.is_hidden else "hidden","actual":r.get("output","") if not t.is_hidden else "hidden"})
    if verdict=="Accepted" and mismatches: verdict="Wrong Answer"
    if mismatches: result["mismatches"]=mismatches
    result["results"]=case_results
    p=progress_for(s,u,q.id);p.attempts+=1;p.last_attempted=datetime.utcnow();p.solved=p.solved or verdict=="Accepted"
    if verdict=="Accepted":p.revision_due=datetime.utcnow()+timedelta(days=7)
    s.add(Submission(user_id=u.id,question_id=q.id,language=body.language,source=body.source,verdict=verdict,runtime_ms=result.get("runtime_ms",0)));s.commit();return {"verdict":verdict,"runtime_ms":result.get("runtime_ms",0),"details":result}
@app.get("/api/submissions")
def submissions(u:User=Depends(current),s:Session=Depends(db)):return [{"id":x.id,"question_id":x.question_id,"language":x.language,"verdict":x.verdict,"runtime_ms":x.runtime_ms,"created_at":x.created_at} for x in s.scalars(select(Submission).where(Submission.user_id==u.id).order_by(Submission.id.desc()).limit(100))]
@app.get("/api/submissions/{sid}")
def submission(sid:int,u:User=Depends(current),s:Session=Depends(db)):
    x=s.get(Submission,sid)
    if not x or x.user_id!=u.id:raise HTTPException(404,"Submission not found")
    return {"id":x.id,"question_id":x.question_id,"language":x.language,"source":x.source,"verdict":x.verdict,"runtime_ms":x.runtime_ms,"created_at":x.created_at}

@app.patch("/api/progress/questions/{qid}")
def update_progress(qid:int,body:ProgressIn,u:User=Depends(current),s:Session=Depends(db)):
    if not s.get(Question,qid):raise HTTPException(404,"Question not found")
    p=progress_for(s,u,qid)
    for k,v in body.model_dump(exclude_none=True).items():setattr(p,k,v)
    s.commit();return {"solved":p.solved,"bookmarked":p.bookmarked,"notes":p.notes,"confidence":p.confidence,"revision_due":p.revision_due}
@app.get("/api/progress/overview")
def overview(u:User=Depends(current),s:Session=Depends(db)):
    ps=list(s.scalars(select(Progress).where(Progress.user_id==u.id)));subs=list(s.scalars(select(Submission).where(Submission.user_id==u.id)))
    days={x.created_at.date() for x in subs};streak=0;d=date.today()
    while d in days:streak+=1;d-=timedelta(days=1)
    return {"solved":sum(x.solved for x in ps),"attempted":len(ps),"bookmarked":sum(x.bookmarked for x in ps),"current_streak":streak,"submissions":len(subs),"activity":[{"date":str(d),"count":sum(x.created_at.date()==d for x in subs)} for d in sorted(days)]}
@app.get("/api/progress/topics")
def topics(u:User=Depends(current),s:Session=Depends(db)):
    qs=list(s.scalars(select(Question).where((Question.published==True)|(Question.owner_id==u.id))));res={}
    for q in qs:
      p=s.scalar(select(Progress).where(Progress.user_id==u.id,Progress.question_id==q.id));r=res.setdefault(q.topic,{"topic":q.topic,"total":0,"solved":0});r["total"]+=1;r["solved"]+=bool(p and p.solved)
    return list(res.values())
@app.get("/api/revision-queue")
def revision(u:User=Depends(current),s:Session=Depends(db)):return [visible(s.get(Question,p.question_id),s) for p in s.scalars(select(Progress).where(Progress.user_id==u.id,Progress.revision_due<=datetime.utcnow(),Progress.solved==True))]
@app.get("/api/export")
def export(u:User=Depends(current),s:Session=Depends(db)):return {"version":1,"questions":[visible(q,s) for q in s.scalars(select(Question).where(Question.owner_id==u.id))]}
@app.post("/api/import")
def import_data(payload:dict,u:User=Depends(current),s:Session=Depends(db)):
    if payload.get("version")!=1 or not isinstance(payload.get("questions"),list):raise HTTPException(422,"Expected version 1 question export")
    count=0
    for raw in payload["questions"]:
      try: save_question(None,QuestionIn.model_validate(raw),u,s);count+=1
      except Exception as e: raise HTTPException(422,f"Invalid question import: {e}")
    return {"imported":count}

# Academic role APIs
def require_role(user: User, *roles: str):
    if user.role not in roles: raise HTTPException(403, "This action is not permitted for your account role")
def course_view(course: Course): return {"id":course.id,"title":course.title,"code":course.code,"description":course.description,"faculty_id":course.faculty_id,"active":course.active}
class AccountIn(Credentials): role: Literal["admin","faculty","student"]="student"
class CourseIn(BaseModel): title: str=Field(min_length=2,max_length=160); code: str=Field(min_length=2,max_length=40); description: str=""; faculty_id: int|None=None
class AssessmentIn(BaseModel): course_id:int; title:str=Field(min_length=2,max_length=160); description:str=""; starts_at:datetime|None=None; ends_at:datetime|None=None; question_ids:list[int]=[]

@app.post("/api/admin/users",status_code=201)
def admin_create_user(body:AccountIn,u:User=Depends(current),s:Session=Depends(db)):
    require_role(u,"admin")
    if s.scalar(select(User).where(User.email==body.email.lower())): raise HTTPException(409,"Email already registered")
    if body.registration_number and s.scalar(select(User).where(User.registration_number==body.registration_number)): raise HTTPException(409,"Registration number already registered")
    x=User(email=body.email.lower(),password_hash=password_hash.hash(body.password),role=body.role,registration_number=body.registration_number);s.add(x);s.commit();return {"id":x.id,"email":x.email,"role":x.role,"registration_number":x.registration_number}
@app.get("/api/admin/users")
def admin_users(u:User=Depends(current),s:Session=Depends(db)):
    require_role(u,"admin");return [{"id":x.id,"email":x.email,"role":x.role,"registration_number":x.registration_number} for x in s.scalars(select(User).order_by(User.id))]
@app.get("/api/admin/statistics")
def admin_statistics(u:User=Depends(current),s:Session=Depends(db)):
    require_role(u,"admin");return {"users":{r:s.scalar(select(func.count()).select_from(User).where(User.role==r)) for r in ("admin","faculty","student")},"courses":s.scalar(select(func.count()).select_from(Course)),"assessments":s.scalar(select(func.count()).select_from(Assessment)),"submissions":s.scalar(select(func.count()).select_from(Submission)),"problems":s.scalar(select(func.count()).select_from(Question))}
@app.get("/api/admin/analytics")
def admin_analytics(u:User=Depends(current),s:Session=Depends(db)):
    require_role(u,"admin")
    submissions=list(s.scalars(select(Submission).order_by(Submission.created_at)).all())
    users=list(s.scalars(select(User).order_by(User.created_at)).all())
    days={}
    for item in submissions:
        key=item.created_at.date().isoformat()
        bucket=days.setdefault(key,{"date":key,"accepted":0,"wrong":0,"runtime":0,"compile":0})
        verdict=item.verdict.lower()
        bucket["accepted" if verdict=="accepted" else "wrong" if "wrong" in verdict else "runtime" if "runtime" in verdict else "compile"]+=1
    growth={}
    for item in users:
        key=item.created_at.strftime("%Y-%m")
        growth[key]=growth.get(key,0)+1
    return {"submissions":list(days.values())[-30:],"user_growth":[{"month":key,"value":value} for key,value in sorted(growth.items())]}
@app.post("/api/courses",status_code=201)
def create_course(body:CourseIn,u:User=Depends(current),s:Session=Depends(db)):
    require_role(u,"admin","faculty")
    faculty_id=body.faculty_id if u.role=="admin" else u.id
    if faculty_id and (not s.get(User,faculty_id) or s.get(User,faculty_id).role!="faculty"): raise HTTPException(422,"faculty_id must identify a faculty account")
    if s.scalar(select(Course).where(Course.code==body.code.upper())): raise HTTPException(409,"Course code already exists")
    c=Course(title=body.title,code=body.code.upper(),description=body.description,faculty_id=faculty_id);s.add(c);s.commit();return course_view(c)
@app.get("/api/courses")
def list_courses(u:User=Depends(current),s:Session=Depends(db)):
    if u.role=="admin": rows=s.scalars(select(Course)).all()
    elif u.role=="faculty": rows=s.scalars(select(Course).where(Course.faculty_id==u.id)).all()
    else: rows=s.scalars(select(Course).join(Enrollment,Enrollment.course_id==Course.id).where(Enrollment.student_id==u.id)).all()
    return [course_view(c) for c in rows]
@app.post("/api/courses/{course_id}/students",status_code=201)
def map_student(course_id:int,registration_number:str,u:User=Depends(current),s:Session=Depends(db)):
    c=s.get(Course,course_id)
    if not c: raise HTTPException(404,"Course not found")
    if u.role=="faculty" and c.faculty_id!=u.id: raise HTTPException(403,"Not your course")
    require_role(u,"admin","faculty")
    student=s.scalar(select(User).where(User.registration_number==registration_number,User.role=="student"))
    if not student: raise HTTPException(404,"Student registration number not found")
    if s.scalar(select(Enrollment).where(Enrollment.course_id==course_id,Enrollment.student_id==student.id)): raise HTTPException(409,"Student is already mapped")
    s.add(Enrollment(course_id=course_id,student_id=student.id,faculty_id=c.faculty_id));s.commit();return {"course_id":course_id,"student_id":student.id}
@app.post("/api/courses/{course_id}/questions",status_code=201)
def add_course_question(course_id:int,question_id:int,u:User=Depends(current),s:Session=Depends(db)):
    c=s.get(Course,course_id)
    if not c or (u.role=="faculty" and c.faculty_id!=u.id): raise HTTPException(404,"Course not found")
    require_role(u,"admin","faculty")
    if not s.get(Question,question_id): raise HTTPException(404,"Question not found")
    if s.get(CourseQuestion,{"course_id":course_id,"question_id":question_id}): raise HTTPException(409,"Question already mapped")
    s.add(CourseQuestion(course_id=course_id,question_id=question_id,position=s.scalar(select(func.count()).select_from(CourseQuestion).where(CourseQuestion.course_id==course_id))));s.commit();return {"ok":True}
@app.get("/api/courses/{course_id}/progress")
def course_progress(course_id:int,u:User=Depends(current),s:Session=Depends(db)):
    c=s.get(Course,course_id)
    if not c: raise HTTPException(404,"Course not found")
    enrolled=s.scalar(select(Enrollment).where(Enrollment.course_id==course_id,Enrollment.student_id==u.id))
    if u.role=="student" and not enrolled: raise HTTPException(403,"Not enrolled in this course")
    qids=list(s.scalars(select(CourseQuestion.question_id).where(CourseQuestion.course_id==course_id))); students=[u.id] if u.role=="student" else list(s.scalars(select(Enrollment.student_id).where(Enrollment.course_id==course_id)))
    return [{"student_id":sid,"solved":s.scalar(select(func.count()).select_from(Progress).where(Progress.user_id==sid,Progress.question_id.in_(qids),Progress.solved==True)) or 0,"total":len(qids)} for sid in students]
@app.post("/api/assessments",status_code=201)
def create_assessment(body:AssessmentIn,u:User=Depends(current),s:Session=Depends(db)):
    require_role(u,"faculty");c=s.get(Course,body.course_id)
    if not c or c.faculty_id!=u.id: raise HTTPException(404,"Course not found")
    a=Assessment(course_id=c.id,faculty_id=u.id,title=body.title,description=body.description,starts_at=body.starts_at,ends_at=body.ends_at);s.add(a);s.flush()
    for qid in body.question_ids:
      if not s.get(Question,qid): raise HTTPException(422,"Unknown question")
      s.add(AssessmentQuestion(assessment_id=a.id,question_id=qid))
    s.commit();return {"id":a.id,"title":a.title,"published":a.published}
@app.patch("/api/assessments/{assessment_id}/publish")
def publish_assessment(assessment_id:int,u:User=Depends(current),s:Session=Depends(db)):
    a=s.get(Assessment,assessment_id)
    if not a or a.faculty_id!=u.id: raise HTTPException(404,"Assessment not found")
    require_role(u,"faculty");a.published=True;s.commit();return {"id":a.id,"published":True}
@app.get("/api/assessments")
def assessments(u:User=Depends(current),s:Session=Depends(db)):
    if u.role=="faculty": rows=s.scalars(select(Assessment).where(Assessment.faculty_id==u.id)).all()
    elif u.role=="student": rows=s.scalars(select(Assessment).join(Enrollment,Enrollment.course_id==Assessment.course_id).where(Enrollment.student_id==u.id,Assessment.published==True)).all()
    else: rows=s.scalars(select(Assessment)).all()
    return [{"id":a.id,"course_id":a.course_id,"title":a.title,"description":a.description,"starts_at":a.starts_at,"ends_at":a.ends_at,"published":a.published} for a in rows]
@app.post("/api/assessments/{assessment_id}/submit",status_code=201)
def submit_assessment(assessment_id:int,u:User=Depends(current),s:Session=Depends(db)):
    require_role(u,"student");a=s.get(Assessment,assessment_id)
    if not a or not a.published: raise HTTPException(404,"Assessment not found")
    if not s.scalar(select(Enrollment).where(Enrollment.course_id==a.course_id,Enrollment.student_id==u.id)): raise HTTPException(403,"Not enrolled")
    qids=list(s.scalars(select(AssessmentQuestion.question_id).where(AssessmentQuestion.assessment_id==a.id))); score=s.scalar(select(func.count()).select_from(Progress).where(Progress.user_id==u.id,Progress.question_id.in_(qids),Progress.solved==True)) or 0
    attempt=s.scalar(select(AssessmentAttempt).where(AssessmentAttempt.assessment_id==a.id,AssessmentAttempt.student_id==u.id)) or AssessmentAttempt(assessment_id=a.id,student_id=u.id)
    attempt.score=score;attempt.submitted_at=datetime.utcnow();s.add(attempt);s.commit();return {"assessment_id":a.id,"score":score,"out_of":len(qids)}
@app.get("/api/assessments/{assessment_id}/results")
def assessment_results(assessment_id:int,u:User=Depends(current),s:Session=Depends(db)):
    a=s.get(Assessment,assessment_id)
    if not a: raise HTTPException(404,"Assessment not found")
    if u.role=="faculty" and a.faculty_id!=u.id: raise HTTPException(403,"Not your assessment")
    if u.role=="student":
      x=s.scalar(select(AssessmentAttempt).where(AssessmentAttempt.assessment_id==a.id,AssessmentAttempt.student_id==u.id))
      if not x or not x.shared: raise HTTPException(403,"Results are not shared yet")
      return {"score":x.score,"submitted_at":x.submitted_at}
    require_role(u,"admin","faculty");return [{"student_id":x.student_id,"score":x.score,"submitted_at":x.submitted_at,"shared":x.shared} for x in s.scalars(select(AssessmentAttempt).where(AssessmentAttempt.assessment_id==a.id))]
@app.patch("/api/assessments/{assessment_id}/share-results")
def share_results(assessment_id:int,u:User=Depends(current),s:Session=Depends(db)):
    a=s.get(Assessment,assessment_id)
    if not a or a.faculty_id!=u.id: raise HTTPException(404,"Assessment not found")
    require_role(u,"faculty");s.query(AssessmentAttempt).filter(AssessmentAttempt.assessment_id==a.id).update({AssessmentAttempt.shared:True});s.commit();return {"shared":True}
@app.get("/api/courses/{course_id}/leaderboard")
def leaderboard(course_id:int,u:User=Depends(current),s:Session=Depends(db)):
    if u.role=="student" and not s.scalar(select(Enrollment).where(Enrollment.course_id==course_id,Enrollment.student_id==u.id)): raise HTTPException(403,"Not enrolled")
    rows=course_progress(course_id,u,s);return sorted(rows,key=lambda x:x["solved"],reverse=True)

@app.post("/api/admin/problems", status_code=201)
def admin_create_problem(body: QuestionIn, u: User = Depends(current), s: Session = Depends(db)):
    """Create a published platform problem; enforced independently of the UI."""
    require_role(u, "admin")
    return save_question(None, body, u, s)
>>>>>>> origin/main
