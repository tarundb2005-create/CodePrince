from __future__ import annotations

import hashlib, io, json, os, re, secrets, subprocess, tarfile, tempfile, time
try:
    import docker
except ImportError:
    docker = None
from datetime import datetime
from pathlib import Path
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from pwdlib import PasswordHash
from .db import SessionLocal
from .models import LoginSession, Progress, Question, TestCase, User

password_hash = PasswordHash.recommended()

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
    return {"id":q.id,"title":q.title,"slug":q.slug,"statement":q.statement,"image_url":q.image_url,"difficulty":q.difficulty,"topic":q.topic,"tags":json.loads(q.tags),"constraints":q.constraints,"input_format":q.input_format,"output_format":q.output_format,"hints":q.hints,"editorial":q.editorial,"starter_code":json.loads(q.starter_code),"published":q.published,"created_at":q.created_at,"tests":[{"id":t.id,"input":t.input,"expected_output":t.expected_output} for t in s.scalars(select(TestCase).where(TestCase.question_id==q.id,TestCase.is_hidden==False))]}
def owned(q:Question,u:User): return q.owner_id==u.id
def progress_for(s,u,qid):
    p=s.scalar(select(Progress).where(Progress.user_id==u.id,Progress.question_id==qid))
    if not p: p=Progress(user_id=u.id,question_id=qid); s.add(p); s.flush()
    return p

