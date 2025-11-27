from typing import Optional
from datetime import date

from pydantic import BaseModel, EmailStr


# -----------------------------
# Employee schemas
# -----------------------------
class EmployeeBase(BaseModel):
    name: str
    email: EmailStr
    role: Optional[str] = None
    department: Optional[str] = None
    status: str = "active"


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(EmployeeBase):
    pass


class EmployeeOut(EmployeeBase):
    id: int

    class Config:
        from_attributes = True


# -----------------------------
# Goal schemas (with progress)
# -----------------------------
class GoalBase(BaseModel):
    title: str
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: str = "in-progress"
    employee_id: int
    # Progress percentage 0–100
    progress: int = 0


class GoalCreate(GoalBase):
    pass


class GoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    employee_id: Optional[int] = None
    progress: Optional[int] = None


class GoalOut(GoalBase):
    id: int

    class Config:
        from_attributes = True


# -----------------------------
# Performance Review schemas
# -----------------------------
class ReviewBase(BaseModel):
    # e.g., "2025-01" for January 2025
    month: str
    rating: int
    feedback: Optional[str] = None
    reviewer_name: str
    employee_id: int


class ReviewCreate(ReviewBase):
    pass


class ReviewUpdate(BaseModel):
    month: Optional[str] = None
    rating: Optional[int] = None
    feedback: Optional[str] = None
    reviewer_name: Optional[str] = None
    employee_id: Optional[int] = None


class ReviewOut(ReviewBase):
    id: int

    class Config:
        from_attributes = True


# -----------------------------
# User / Auth schemas
# -----------------------------
class UserBase(BaseModel):
    name: str
    email: EmailStr
    role: str = "employee"  # 'admin' | 'manager' | 'employee'
    is_active: bool = True
    employee_id: Optional[int] = None


class UserCreate(UserBase):
    """
    Used when Admin creates a new user.
    Includes plain password (will be hashed in backend).
    """
    password: str


class UserOut(UserBase):
    """
    Data returned to the client about a user (no password).
    """
    id: int

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    """
    Used for /login requests.
    """
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """
    Data returned after successful login.
    (Later we will include a real JWT token here.)
    """
    access_token: str
    token_type: str = "bearer"
    user: UserOut
