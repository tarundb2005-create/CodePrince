from __future__ import annotations

import hashlib, io, json, os, re, secrets, subprocess, tarfile, tempfile, time
try:
    import docker
except ImportError:
    docker = None
from datetime import datetime, date, timedelta
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from .db import SessionLocal
from .models import *
from .schemas import *
from .core import *

router = APIRouter()

@router.get("/api/health")
def health(): return {"status":"ok","executor":"docker" if _docker() else "unavailable"}
@router.post("/api/auth/register",status_code=201)
def register(body:StudentRegisterIn,response:Response,s:Session=Depends(db)):
    email=body.email.lower()
    if s.scalar(select(User).where(User.email==email)): raise HTTPException(409,"Email already registered")
    if s.scalar(select(User).where(User.registration_number==body.registration_number)): raise HTTPException(409,"Registration number already registered")
    u=User(email=email,password_hash=password_hash.hash(body.password),registration_number=body.registration_number,full_name=body.full_name.strip(),academic_year=body.academic_year,department=body.department,section=body.section,role="student")
    s.add(u);s.commit();s.refresh(u);return _login(u,response,s)
@router.post("/api/auth/login")
def login(body:Credentials,response:Response,s:Session=Depends(db)):
    u=s.scalar(select(User).where(User.email==body.email.lower()))
    if not u or not password_hash.verify(body.password,u.password_hash): raise HTTPException(401,"Invalid email or password")
    return _login(u,response,s)
def _login(u,response,s):
    raw=secrets.token_urlsafe(32);s.add(LoginSession(token_hash=token_hash(raw),user_id=u.id,expires_at=datetime.utcnow()+timedelta(days=14)));s.commit();response.set_cookie(os.getenv("SESSION_COOKIE_NAME","dsa_forge_session"),raw,httponly=True,samesite="lax",secure=False,max_age=1209600);return {"id":u.id,"email":u.email,"role":u.role,"registration_number":u.registration_number}
@router.post("/api/auth/logout",status_code=204)
def logout(request:Request,response:Response,s:Session=Depends(db)):
    raw=request.cookies.get(os.getenv("SESSION_COOKIE_NAME","dsa_forge_session"));
    if raw:
      x=s.scalar(select(LoginSession).where(LoginSession.token_hash==token_hash(raw)))
      if x:s.delete(x);s.commit()
    response.delete_cookie(os.getenv("SESSION_COOKIE_NAME","dsa_forge_session"))
@router.get("/api/auth/me")
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

@router.get("/api/profile/me")
def own_profile(u:User=Depends(current),s:Session=Depends(db)):
    return profile_summary(u,s)

@router.get("/api/u/{username}")
def public_profile(username:str,s:Session=Depends(db)):
    if not username.lower().startswith("student-") or not username[8:].isdigit(): raise HTTPException(404,"Profile not found")
    user=s.get(User,int(username[8:]))
    if not user or user.role!="student": raise HTTPException(404,"Profile not found")
    return profile_summary(user,s)

@router.get("/api/questions")
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
@router.get("/api/questions/{slug}")
def question(slug:str,u:User=Depends(current),s:Session=Depends(db)):
    q=s.scalar(select(Question).where(Question.slug==slug));
    if not q or not(q.published or owned(q,u)):raise HTTPException(404,"Question not found")
    return visible(q,s)
@router.post("/api/questions",status_code=201)
def create_question(body:QuestionIn,u:User=Depends(current),s:Session=Depends(db)): return save_question(None,body,u,s)
@router.patch("/api/questions/{qid}")
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
@router.delete("/api/questions/{qid}",status_code=204)
def delete_question(qid:int,u:User=Depends(current),s:Session=Depends(db)):
    q=s.get(Question,qid)
    if not q or not owned(q,u):raise HTTPException(404,"Question not found")
    s.delete(q);s.commit()

@router.get("/api/sheets")
def sheets(u:User=Depends(current),s:Session=Depends(db)): return [{"id":x.id,"title":x.title,"description":x.description,"is_public":x.is_public,"target_date":x.target_date,"count":s.scalar(select(func.count()).select_from(SheetQuestion).where(SheetQuestion.sheet_id==x.id))} for x in s.scalars(select(Sheet).where(Sheet.owner_id==u.id))]
@router.post("/api/sheets",status_code=201)
def create_sheet(body:SheetIn,u:User=Depends(current),s:Session=Depends(db)): x=Sheet(owner_id=u.id,share_token=secrets.token_urlsafe(18),**body.model_dump());s.add(x);s.commit();return {"id":x.id,"title":x.title,"share_token":x.share_token}
@router.get("/api/sheets/{sid}")
def sheet(sid:int,u:User=Depends(current),s:Session=Depends(db)):
    x=s.get(Sheet,sid)
    if not x or x.owner_id!=u.id:raise HTTPException(404,"Sheet not found")
    return {"id":x.id,"title":x.title,"description":x.description,"share_token":x.share_token,"questions":[visible(s.get(Question,r.question_id),s) for r in s.scalars(select(SheetQuestion).where(SheetQuestion.sheet_id==sid).order_by(SheetQuestion.position))]}
@router.patch("/api/sheets/{sid}")
def update_sheet(sid:int,body:SheetIn,u:User=Depends(current),s:Session=Depends(db)):
    x=s.get(Sheet,sid)
    if not x or x.owner_id!=u.id:raise HTTPException(404,"Sheet not found")
    for k,v in body.model_dump().items():setattr(x,k,v)
    s.commit();return {"id":x.id,"title":x.title}
@router.delete("/api/sheets/{sid}",status_code=204)
def delete_sheet(sid:int,u:User=Depends(current),s:Session=Depends(db)):
    x=s.get(Sheet,sid)
    if not x or x.owner_id!=u.id:raise HTTPException(404,"Sheet not found")
    s.delete(x);s.commit()
@router.post("/api/sheets/{sid}/questions",status_code=201)
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
def function_source(source:str, language:str, raw_input:str, slug:str="pair-sum-function"):
    data=json.loads(raw_input)
    if language=="c" and slug.startswith("c-"):
        runners={
          "c-print-student-details": f"\nint main(void){{ print_student_details(); return 0; }}\n",
          "c-arithmetic-operations": f"\nint main(void){{ int sum,difference,product,remainder; double quotient; calculate_operations({data.get('a', 0)},{data.get('b', 0)},&sum,&difference,&product,&quotient,&remainder); printf(\"%d\\n%d\\n%d\\n%.2f\\n%d\\n\",sum,difference,product,quotient,remainder); return 0; }}\n",
          "c-data-types": "\nint main(void){ demonstrate_data_types(); return 0; }\n",
          "c-rectangle-metrics": f"\nint main(void){{ double area,perimeter; rectangle_metrics({data.get('length', 0)},{data.get('width', 0)},&area,&perimeter); printf(\"%.2f\\n%.2f\\n\",area,perimeter); return 0; }}\n",
          "c-circle-metrics": f"\nint main(void){{ double area,circumference; circle_metrics({data.get('radius', 0)},&area,&circumference); printf(\"%.2f\\n%.2f\\n\",area,circumference); return 0; }}\n",
        }
        return source+runners[slug]
    nums=data["nums"]; target=data["target"]; values=",".join(map(str,nums))
    if language=="python": return source+f"\nimport json\nprint(json.dumps(has_pair_sum({nums!r}, {target})))\n"
    if language=="cpp": return source+f'\nint main(){{ vector<int> nums={{{values}}}; cout << (Solution().hasPairSum(nums,{target}) ? "true" : "false"); }}\n'
    if language=="c": return source+f"\n#include <stdio.h>\nint main(void){{ int nums[]={{ {values} }}; printf(\"%s\",has_pair_sum(nums,{len(nums)},{target}) ? \"true\" : \"false\"); return 0; }}\n"
    if language=="java": return source+f"\nclass Main {{ public static void main(String[] args) {{ System.out.print(new Solution().hasPairSum(new int[]{{{values}}},{target})); }} }}\n"
    if language=="go": return source+f"\nfunc main() {{ fmt.Print(hasPairSum([]int{{{values}}}, {target})) }}\n"
    raise ValueError("Unsupported language")
def is_function_question(q):
    return q.slug.endswith("-function") or q.slug.startswith("c-") or "function" in q.title.lower()
def outputs_match(actual:str,expected:str):
    a=actual.replace("\\n", "\n").strip(); e=expected.replace("\\n", "\n").strip()
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

def execute(body:ExecuteIn,inputs:list[str],function_mode:bool=False,verify:bool=False,slug:str="pair-sum-function"):
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
        Path(d,suffix).write_text(function_source(body.source,body.language,inp,slug),encoding="utf-8")
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
@router.post("/api/run")
def run(body:ExecuteIn,u:User=Depends(current),s:Session=Depends(db)):
    q=s.get(Question,body.question_id)
    if not q or not(q.published or owned(q,u)):raise HTTPException(404,"Question not found")
    sample=s.scalar(select(TestCase).where(TestCase.question_id==q.id,TestCase.input==body.input,TestCase.is_hidden==False))
    if sample is None and body.language == "c" and q.slug.startswith("c-"):
        sample=s.scalar(select(TestCase).where(TestCase.question_id==q.id,TestCase.is_hidden==False).order_by(TestCase.id))
    inputs=[body.input] if body.input is not None else list(s.scalars(select(TestCase.input).where(TestCase.question_id==q.id,TestCase.is_hidden==False)))
    if body.input is not None and body.language == "c" and q.slug.startswith("c-"):
        required_key = {"c-arithmetic-operations":"a", "c-rectangle-metrics":"length", "c-circle-metrics":"radius"}.get(q.slug)
        if required_key:
            try:
                if required_key not in json.loads(body.input):
                    inputs = [s.scalar(select(TestCase.input).where(TestCase.question_id==q.id, TestCase.is_hidden==False))]
            except json.JSONDecodeError:
                raise HTTPException(400, "Input must be valid JSON")
    result=execute(body,inputs,is_function_question(q),False,q.slug)
    if sample and result.get("verdict")=="Executed":
        actual=result.get("results",[{}])[0].get("output","").strip()
        passed=outputs_match(actual,sample.expected_output)
        result["verdict"]="Accepted" if passed else "Wrong Answer"
        if result.get("results"):
            result["results"][0].update({"passed":passed,"input":sample.input,"expected":sample.expected_output})
    return result
@router.post("/api/submit")
def submit(body:ExecuteIn,u:User=Depends(current),s:Session=Depends(db)):
    q=s.get(Question,body.question_id)
    if not q or not(q.published or owned(q,u)):raise HTTPException(404,"Question not found")
    tests=list(s.scalars(select(TestCase).where(TestCase.question_id==q.id)));result=execute(body,[t.input for t in tests],is_function_question(q),True,q.slug); verdict=result["verdict"]
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
@router.get("/api/submissions")
def submissions(u:User=Depends(current),s:Session=Depends(db)):return [{"id":x.id,"question_id":x.question_id,"language":x.language,"verdict":x.verdict,"runtime_ms":x.runtime_ms,"created_at":x.created_at} for x in s.scalars(select(Submission).where(Submission.user_id==u.id).order_by(Submission.id.desc()).limit(100))]
@router.get("/api/submissions/{sid}")
def submission(sid:int,u:User=Depends(current),s:Session=Depends(db)):
    x=s.get(Submission,sid)
    if not x or x.user_id!=u.id:raise HTTPException(404,"Submission not found")
    return {"id":x.id,"question_id":x.question_id,"language":x.language,"source":x.source,"verdict":x.verdict,"runtime_ms":x.runtime_ms,"created_at":x.created_at}

@router.patch("/api/progress/questions/{qid}")
def update_progress(qid:int,body:ProgressIn,u:User=Depends(current),s:Session=Depends(db)):
    if not s.get(Question,qid):raise HTTPException(404,"Question not found")
    p=progress_for(s,u,qid)
    for k,v in body.model_dump(exclude_none=True).items():setattr(p,k,v)
    s.commit();return {"solved":p.solved,"bookmarked":p.bookmarked,"notes":p.notes,"confidence":p.confidence,"revision_due":p.revision_due}
@router.get("/api/progress/overview")
def overview(u:User=Depends(current),s:Session=Depends(db)):
    ps=list(s.scalars(select(Progress).where(Progress.user_id==u.id)));subs=list(s.scalars(select(Submission).where(Submission.user_id==u.id)))
    days={x.created_at.date() for x in subs};streak=0;d=date.today()
    while d in days:streak+=1;d-=timedelta(days=1)
    return {"solved":sum(x.solved for x in ps),"attempted":len(ps),"bookmarked":sum(x.bookmarked for x in ps),"current_streak":streak,"submissions":len(subs),"activity":[{"date":str(d),"count":sum(x.created_at.date()==d for x in subs)} for d in sorted(days)]}
@router.get("/api/progress/topics")
def topics(u:User=Depends(current),s:Session=Depends(db)):
    qs=list(s.scalars(select(Question).where((Question.published==True)|(Question.owner_id==u.id))));res={}
    for q in qs:
      p=s.scalar(select(Progress).where(Progress.user_id==u.id,Progress.question_id==q.id));r=res.setdefault(q.topic,{"topic":q.topic,"total":0,"solved":0});r["total"]+=1;r["solved"]+=bool(p and p.solved)
    return list(res.values())
@router.get("/api/revision-queue")
def revision(u:User=Depends(current),s:Session=Depends(db)):return [visible(s.get(Question,p.question_id),s) for p in s.scalars(select(Progress).where(Progress.user_id==u.id,Progress.revision_due<=datetime.utcnow(),Progress.solved==True))]
@router.get("/api/export")
def export(u:User=Depends(current),s:Session=Depends(db)):return {"version":1,"questions":[visible(q,s) for q in s.scalars(select(Question).where(Question.owner_id==u.id))]}
@router.post("/api/import")
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
class AssessmentIn(BaseModel): course_id:int; title:str=Field(min_length=2,max_length=160); description:str=""; academic_year:str|None=None; department:str|None=None; section:str|None=None; starts_at:datetime|None=None; ends_at:datetime|None=None; question_ids:list[int]=Field(min_length=1)
class ProblemAssignmentIn(BaseModel): question_id:int; student_ids:list[int]=Field(min_length=1); due_at:datetime|None=None; note:str=Field(default="",max_length=5000)

@router.post("/api/admin/users",status_code=201)
def admin_create_user(body:AccountIn,u:User=Depends(current),s:Session=Depends(db)):
    require_role(u,"admin")
    if s.scalar(select(User).where(User.email==body.email.lower())): raise HTTPException(409,"Email already registered")
    if body.registration_number and s.scalar(select(User).where(User.registration_number==body.registration_number)): raise HTTPException(409,"Registration number already registered")
    x=User(email=body.email.lower(),password_hash=password_hash.hash(body.password),role=body.role,registration_number=body.registration_number);s.add(x);s.commit();return {"id":x.id,"email":x.email,"role":x.role,"registration_number":x.registration_number}
@router.get("/api/admin/users")
def admin_users(u:User=Depends(current),s:Session=Depends(db)):
    require_role(u,"admin");return [{"id":x.id,"email":x.email,"role":x.role,"registration_number":x.registration_number} for x in s.scalars(select(User).order_by(User.id))]
@router.get("/api/admin/statistics")
def admin_statistics(u:User=Depends(current),s:Session=Depends(db)):
    require_role(u,"admin");return {"users":{r:s.scalar(select(func.count()).select_from(User).where(User.role==r)) for r in ("admin","faculty","student")},"courses":s.scalar(select(func.count()).select_from(Course)),"assessments":s.scalar(select(func.count()).select_from(Assessment)),"submissions":s.scalar(select(func.count()).select_from(Submission)),"problems":s.scalar(select(func.count()).select_from(Question))}
@router.get("/api/admin/analytics")
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
@router.get("/api/faculty/academic-options")
def faculty_academic_options(u:User=Depends(current)):
    require_role(u,"faculty")
    return []

def student_view(student:User,course_count:int=0,mapped_at:datetime|None=None):
    year_text=getattr(student,"academic_year",None) or ""
    year_number=int(year_text[0]) if year_text and year_text[0].isdigit() else None
    return {"id":student.id,"email":student.email,"full_name":getattr(student,"full_name",None),"registration_number":student.registration_number,"year_of_study":year_number,"department":getattr(student,"department",None),"section":getattr(student,"section",None),"course_count":course_count,"mapped_at":mapped_at}

@router.get("/api/faculty/students")
def faculty_students(u:User=Depends(current),s:Session=Depends(db)):
    require_role(u,"faculty")
    course_ids=list(s.scalars(select(Course.id).where(Course.faculty_id==u.id)))
    if not course_ids: return []
    students=list(s.scalars(select(User).where(User.role=="student").order_by(User.email)))
    result=[]
    for student in students:
        enrollments=list(s.scalars(select(Enrollment).where(Enrollment.student_id==student.id,Enrollment.course_id.in_(course_ids))))
        result.append(student_view(student,len(enrollments),enrollments[0].created_at if enrollments else None))
    return result

@router.post("/api/courses",status_code=201)
def create_course(body:CourseIn,u:User=Depends(current),s:Session=Depends(db)):
    require_role(u,"admin","faculty")
    faculty_id=body.faculty_id if u.role=="admin" else u.id
    if faculty_id and (not s.get(User,faculty_id) or s.get(User,faculty_id).role!="faculty"): raise HTTPException(422,"faculty_id must identify a faculty account")
    if s.scalar(select(Course).where(Course.code==body.code.upper())): raise HTTPException(409,"Course code already exists")
    c=Course(title=body.title,code=body.code.upper(),description=body.description,faculty_id=faculty_id);s.add(c);s.commit();return course_view(c)
@router.get("/api/courses")
def list_courses(u:User=Depends(current),s:Session=Depends(db)):
    if u.role=="admin": rows=s.scalars(select(Course)).all()
    elif u.role=="faculty": rows=s.scalars(select(Course).where(Course.faculty_id==u.id)).all()
    else: rows=s.scalars(select(Course).join(Enrollment,Enrollment.course_id==Course.id).where(Enrollment.student_id==u.id)).all()
    return [course_view(c) for c in rows]
@router.get("/api/courses/{course_id}/students")
def course_students(course_id:int,u:User=Depends(current),s:Session=Depends(db)):
    c=s.get(Course,course_id)
    if not c: raise HTTPException(404,"Course not found")
    if u.role=="faculty" and c.faculty_id!=u.id: raise HTTPException(403,"Not your course")
    require_role(u,"admin","faculty")
    rows=s.execute(select(User,Enrollment).join(Enrollment,Enrollment.student_id==User.id).where(Enrollment.course_id==course_id,User.role=="student").order_by(User.email)).all()
    return [student_view(student,1,enrollment.created_at) for student,enrollment in rows]

@router.post("/api/courses/{course_id}/students",status_code=201)
def map_student(course_id:int,registration_number:str,u:User=Depends(current),s:Session=Depends(db)):
    c=s.get(Course,course_id)
    if not c: raise HTTPException(404,"Course not found")
    if u.role=="faculty" and c.faculty_id!=u.id: raise HTTPException(403,"Not your course")
    require_role(u,"admin","faculty")
    student=s.scalar(select(User).where(User.registration_number==registration_number,User.role=="student"))
    if not student: raise HTTPException(404,"Student registration number not found")
    if not re.fullmatch(r"41142\d{6}",registration_number): raise HTTPException(422,"Registration number must be 11 digits and start with 41142")
    if s.scalar(select(Enrollment).where(Enrollment.course_id==course_id,Enrollment.student_id==student.id)): raise HTTPException(409,"Student is already mapped")
    s.add(Enrollment(course_id=course_id,student_id=student.id,faculty_id=c.faculty_id));s.commit();return {"course_id":course_id,"student_id":student.id}
@router.get("/api/courses/{course_id}/questions")
def course_questions(course_id:int,u:User=Depends(current),s:Session=Depends(db)):
    c=s.get(Course,course_id)
    if not c: raise HTTPException(404,"Course not found")
    if u.role=="faculty" and c.faculty_id!=u.id: raise HTTPException(403,"Not your course")
    require_role(u,"admin","faculty")
    qids=list(s.scalars(select(CourseQuestion.question_id).where(CourseQuestion.course_id==course_id).order_by(CourseQuestion.position)))
    return [visible(s.get(Question,qid),s) for qid in qids]

@router.post("/api/courses/{course_id}/questions",status_code=201)
def add_course_question(course_id:int,question_id:int,u:User=Depends(current),s:Session=Depends(db)):
    c=s.get(Course,course_id)
    if not c or (u.role=="faculty" and c.faculty_id!=u.id): raise HTTPException(404,"Course not found")
    require_role(u,"admin","faculty")
    if not s.get(Question,question_id): raise HTTPException(404,"Question not found")
    if s.get(CourseQuestion,{"course_id":course_id,"question_id":question_id}): raise HTTPException(409,"Question already mapped")
    s.add(CourseQuestion(course_id=course_id,question_id=question_id,position=s.scalar(select(func.count()).select_from(CourseQuestion).where(CourseQuestion.course_id==course_id))));s.commit();return {"ok":True}
@router.get("/api/courses/{course_id}/progress")
def course_progress(course_id:int,year:str|None=None,department:str|None=None,section:str|None=None,u:User=Depends(current),s:Session=Depends(db)):
    c=s.get(Course,course_id)
    if not c: raise HTTPException(404,"Course not found")
    if u.role=="student" and not s.scalar(select(Enrollment).where(Enrollment.course_id==course_id,Enrollment.student_id==u.id)): raise HTTPException(403,"Not enrolled in this course")
    if u.role=="faculty" and c.faculty_id!=u.id: raise HTTPException(403,"Not your course")
    require_role(u,"student","faculty","admin")
    qids=list(s.scalars(select(CourseQuestion.question_id).where(CourseQuestion.course_id==course_id)))
    student_ids=[u.id] if u.role=="student" else list(s.scalars(select(Enrollment.student_id).where(Enrollment.course_id==course_id)))
    result=[]
    for student_id in student_ids:
        student=s.get(User,student_id)
        if not student or year and student.academic_year != year or department and student.department != department or section and student.section != section:
            continue
        progress=list(s.scalars(select(Progress).where(Progress.user_id==student_id,Progress.question_id.in_(qids)))) if qids else []
        submissions=list(s.scalars(select(Submission).where(Submission.user_id==student_id,Submission.question_id.in_(qids)))) if qids else []
        result.append({"student_id":student_id,"email":student.email if student else "","full_name":student.full_name if student else None,"academic_year":student.academic_year if student else None,"department":student.department if student else None,"section":student.section if student else None,"registration_number":student.registration_number if student else None,"solved":sum(bool(item.solved) for item in progress),"total":len(qids),"attempts":sum(item.attempts for item in progress),"submissions":len(submissions),"last_active":max((item.created_at for item in submissions),default=None)})
    return result
@router.post("/api/assessments",status_code=201)
def create_assessment(body:AssessmentIn,u:User=Depends(current),s:Session=Depends(db)):
    require_role(u,"faculty");c=s.get(Course,body.course_id)
    if not c or c.faculty_id!=u.id: raise HTTPException(404,"Course not found")
    if body.starts_at and body.ends_at and body.ends_at<=body.starts_at: raise HTTPException(422,"Assessment end time must be later than the start time")
    course_question_ids=set(s.scalars(select(CourseQuestion.question_id).where(CourseQuestion.course_id==c.id)))
    a=Assessment(course_id=c.id,faculty_id=u.id,title=body.title,description=body.description,academic_year=body.academic_year,department=body.department,section=body.section,starts_at=body.starts_at,ends_at=body.ends_at);s.add(a);s.flush()
    for qid in body.question_ids:
      if not s.get(Question,qid): raise HTTPException(422,"Unknown question")
      if qid not in course_question_ids: raise HTTPException(403,"Every assessment question must belong to the selected course")
      s.add(AssessmentQuestion(assessment_id=a.id,question_id=qid))
    s.commit();return {"id":a.id,"title":a.title,"published":a.published}
@router.patch("/api/assessments/{assessment_id}/publish")
def publish_assessment(assessment_id:int,u:User=Depends(current),s:Session=Depends(db)):
    a=s.get(Assessment,assessment_id)
    if not a or a.faculty_id!=u.id: raise HTTPException(404,"Assessment not found")
    require_role(u,"faculty");a.published=True;s.commit();return {"id":a.id,"published":True}
@router.get("/api/assessments")
def assessments(u:User=Depends(current),s:Session=Depends(db)):
    if u.role=="faculty": rows=s.scalars(select(Assessment).where(Assessment.faculty_id==u.id)).all()
    elif u.role=="student":
      rows=s.scalars(select(Assessment).join(Enrollment,Enrollment.course_id==Assessment.course_id).where(Enrollment.student_id==u.id,Assessment.published==True)).all()
      rows=[a for a in rows if (not a.academic_year or a.academic_year==u.academic_year) and (not a.department or a.department==u.department) and (not a.section or a.section==u.section)]
    else: rows=s.scalars(select(Assessment)).all()
    return [{"id":a.id,"course_id":a.course_id,"title":a.title,"description":a.description,"academic_year":a.academic_year,"department":a.department,"section":a.section,"starts_at":a.starts_at,"ends_at":a.ends_at,"published":a.published} for a in rows]
@router.get("/api/faculty/problem-assignments")
def faculty_problem_assignments(u:User=Depends(current),s:Session=Depends(db)):
    require_role(u,"faculty")
    rows=[]
    for assignment in s.scalars(select(ProblemAssignment).where(ProblemAssignment.faculty_id==u.id).order_by(ProblemAssignment.created_at.desc())):
      student=s.get(User,assignment.student_id); question=s.get(Question,assignment.question_id)
      progress=s.scalar(select(Progress).where(Progress.user_id==assignment.student_id,Progress.question_id==assignment.question_id))
      if student and question: rows.append({"id":assignment.id,"student_id":student.id,"student_email":student.email,"registration_number":student.registration_number,"question_id":question.id,"question_title":question.title,"difficulty":question.difficulty,"topic":question.topic,"due_at":assignment.due_at,"note":assignment.note,"created_at":assignment.created_at,"completed":bool(progress and progress.solved)})
    return rows

@router.post("/api/faculty/problem-assignments",status_code=201)
def create_problem_assignments(body:ProblemAssignmentIn,u:User=Depends(current),s:Session=Depends(db)):
    require_role(u,"faculty")
    question=s.get(Question,body.question_id)
    if not question: raise HTTPException(404,"Question not found")
    faculty_course_ids=set(s.scalars(select(Course.id).where(Course.faculty_id==u.id)))
    if not faculty_course_ids: raise HTTPException(403,"You have no assigned courses")
    if question.owner_id!=u.id and not s.scalar(select(CourseQuestion).where(CourseQuestion.question_id==question.id,CourseQuestion.course_id.in_(faculty_course_ids))): raise HTTPException(403,"Question is not available to your courses")
    students=list(s.scalars(select(User).where(User.id.in_(body.student_ids),User.role=="student")))
    if len(students)!=len(set(body.student_ids)): raise HTTPException(422,"One or more student IDs are invalid")
    eligible=set(scalars for scalars in s.scalars(select(Enrollment.student_id).where(Enrollment.student_id.in_(body.student_ids),Enrollment.course_id.in_(faculty_course_ids))))
    if eligible!=set(body.student_ids): raise HTTPException(403,"Every selected student must belong to one of your courses")
    created=[]
    for student_id in sorted(set(body.student_ids)):
      if s.scalar(select(ProblemAssignment).where(ProblemAssignment.faculty_id==u.id,ProblemAssignment.student_id==student_id,ProblemAssignment.question_id==question.id)): continue
      created.append(ProblemAssignment(faculty_id=u.id,student_id=student_id,question_id=question.id,due_at=body.due_at,note=body.note))
    if created: s.add_all(created);s.commit()
    return {"created":len(created),"skipped":len(set(body.student_ids))-len(created)}

@router.delete("/api/faculty/problem-assignments/{assignment_id}",status_code=204)
def delete_problem_assignment(assignment_id:int,u:User=Depends(current),s:Session=Depends(db)):
    require_role(u,"faculty")
    assignment=s.get(ProblemAssignment,assignment_id)
    if not assignment or assignment.faculty_id!=u.id: raise HTTPException(404,"Problem assignment not found")
    s.delete(assignment);s.commit()

@router.get("/api/student/problem-assignments")
def student_problem_assignments(u:User=Depends(current),s:Session=Depends(db)):
    require_role(u,"student")
    rows=[]
    for assignment in s.scalars(select(ProblemAssignment).where(ProblemAssignment.student_id==u.id).order_by(ProblemAssignment.created_at.desc())):
      question=s.get(Question,assignment.question_id); progress=s.scalar(select(Progress).where(Progress.user_id==u.id,Progress.question_id==assignment.question_id))
      if question: rows.append({"id":assignment.id,"question_id":question.id,"question_title":question.title,"difficulty":question.difficulty,"topic":question.topic,"due_at":assignment.due_at,"note":assignment.note,"created_at":assignment.created_at,"completed":bool(progress and progress.solved)})
    return rows

@router.post("/api/assessments/{assessment_id}/submit",status_code=201)
def submit_assessment(assessment_id:int,u:User=Depends(current),s:Session=Depends(db)):
    require_role(u,"student");a=s.get(Assessment,assessment_id)
    if not a or not a.published: raise HTTPException(404,"Assessment not found")
    if not s.scalar(select(Enrollment).where(Enrollment.course_id==a.course_id,Enrollment.student_id==u.id)): raise HTTPException(403,"Not enrolled")
    if a.academic_year and a.academic_year!=u.academic_year or a.department and a.department!=u.department or a.section and a.section!=u.section: raise HTTPException(403,"Assessment is not assigned to your class")
    qids=list(s.scalars(select(AssessmentQuestion.question_id).where(AssessmentQuestion.assessment_id==a.id))); score=s.scalar(select(func.count()).select_from(Progress).where(Progress.user_id==u.id,Progress.question_id.in_(qids),Progress.solved==True)) or 0
    attempt=s.scalar(select(AssessmentAttempt).where(AssessmentAttempt.assessment_id==a.id,AssessmentAttempt.student_id==u.id)) or AssessmentAttempt(assessment_id=a.id,student_id=u.id)
    attempt.score=score;attempt.submitted_at=datetime.utcnow();s.add(attempt);s.commit();return {"assessment_id":a.id,"score":score,"out_of":len(qids)}
@router.get("/api/assessments/{assessment_id}/results")
def assessment_results(assessment_id:int,u:User=Depends(current),s:Session=Depends(db)):
    a=s.get(Assessment,assessment_id)
    if not a: raise HTTPException(404,"Assessment not found")
    if u.role=="faculty" and a.faculty_id!=u.id: raise HTTPException(403,"Not your assessment")
    if u.role=="student":
      x=s.scalar(select(AssessmentAttempt).where(AssessmentAttempt.assessment_id==a.id,AssessmentAttempt.student_id==u.id))
      if not x or not x.shared: raise HTTPException(403,"Results are not shared yet")
      return {"score":x.score,"submitted_at":x.submitted_at}
    require_role(u,"admin","faculty")
    qcount=s.scalar(select(func.count()).select_from(AssessmentQuestion).where(AssessmentQuestion.assessment_id==a.id)) or 0
    rows=[]
    for attempt in s.scalars(select(AssessmentAttempt).where(AssessmentAttempt.assessment_id==a.id)):
      student=s.get(User,attempt.student_id)
      rows.append({"student_id":attempt.student_id,"email":student.email if student else "","registration_number":student.registration_number if student else None,"academic_year":student.academic_year if student else None,"department":student.department if student else None,"section":student.section if student else None,"score":attempt.score,"out_of":qcount,"submitted_at":attempt.submitted_at,"shared":attempt.shared})
    return rows
@router.patch("/api/assessments/{assessment_id}/share-results")
def share_results(assessment_id:int,u:User=Depends(current),s:Session=Depends(db)):
    a=s.get(Assessment,assessment_id)
    if not a or a.faculty_id!=u.id: raise HTTPException(404,"Assessment not found")
    require_role(u,"faculty");s.query(AssessmentAttempt).filter(AssessmentAttempt.assessment_id==a.id).update({AssessmentAttempt.shared:True});s.commit();return {"shared":True}
@router.get("/api/courses/{course_id}/leaderboard")
def leaderboard(course_id:int,u:User=Depends(current),s:Session=Depends(db)):
    if u.role=="student" and not s.scalar(select(Enrollment).where(Enrollment.course_id==course_id,Enrollment.student_id==u.id)): raise HTTPException(403,"Not enrolled")
    rows=course_progress(course_id,u,s);return sorted(rows,key=lambda x:x["solved"],reverse=True)

@router.post("/api/admin/problems", status_code=201)
def admin_create_problem(body: QuestionIn, u: User = Depends(current), s: Session = Depends(db)):
    """Create a published platform problem; enforced independently of the UI."""
    require_role(u, "admin")
    return save_question(None, body, u, s)
