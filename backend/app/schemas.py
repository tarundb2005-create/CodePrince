from __future__ import annotations

import re
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, field_validator

class Credentials(BaseModel): email: str = Field(min_length=3,max_length=255); password: str = Field(min_length=8,max_length=128); registration_number: str|None = Field(default=None,max_length=64)
class StudentRegisterIn(BaseModel):
    registration_number: str = Field(pattern=r"^41142\d{6}$")
    full_name: str = Field(min_length=2,max_length=160)
    academic_year: Literal["1st year","2nd year","3rd year","4th year"]
    section: Literal["A","B","C","D"]
    department: Literal["AIDS","CSE","ECE","EEE","MECH","IT","CS"]
    email: str = Field(pattern=r"^[^@\s]+@gmail\.com$",min_length=11,max_length=255)
    password: str = Field(min_length=8,max_length=128)

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Name is required")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not re.search(r"[A-Z]", value) or not re.search(r"[^A-Za-z0-9]", value):
            raise ValueError("Password must include an uppercase letter and a special character")
        return value
class TestIn(BaseModel): input: str = Field(max_length=10000); expected_output: str = Field(max_length=10000); is_hidden: bool=False
class QuestionIn(BaseModel):
    title: str=Field(min_length=3,max_length=200); statement: str=Field(min_length=3); difficulty: Literal["Easy","Medium","Hard"]="Easy"; topic: str="Arrays"; tags: list[str]=[]; constraints: str=""; input_format: str=""; output_format: str=""; hints: str=""; editorial: str=""; starter_code: dict[str,str]={}; image_url: str=Field(default="",max_length=4_000_000); published: bool=False; tests: list[TestIn]=[]
class SheetIn(BaseModel): title: str=Field(min_length=2,max_length=160); description: str=""; is_public: bool=False; target_date: str=""
class ExecuteIn(BaseModel): question_id:int; language: Literal["c","cpp","java","python","go"]; source:str=Field(min_length=1,max_length=100000); input: str|None=None
class ProgressIn(BaseModel): bookmarked: bool|None=None; notes: str|None=Field(default=None,max_length=10000); confidence: int|None=Field(default=None,ge=0,le=5); revision_due: datetime|None=None


class AdminDirectoryUserIn(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: Literal["student", "faculty"]
    full_name: str | None = Field(default=None, max_length=160)
    registration_number: str | None = Field(default=None, max_length=64)
    academic_year: str | None = Field(default=None, max_length=20)
    department: str | None = Field(default=None, max_length=20)
    section: str | None = Field(default=None, max_length=2)

class AdminDirectoryCourseIn(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    code: str = Field(min_length=2, max_length=40)
    description: str = ""
    faculty_id: int | None = None
    active: bool = True

class PasswordResetIn(BaseModel):
    password: str = Field(min_length=8, max_length=128)

class ChangePasswordIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)
