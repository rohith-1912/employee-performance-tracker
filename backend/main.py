from typing import List

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError

from db import Base, engine, get_db
import models
import schemas
from auth_utils import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)

# Create all database tables (if they don't already exist)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Employee Performance Tracker API",
    description="Backend API for managing employees, goals, performance reviews, and authentication.",
    version="0.4.0",
)

# CORS: allow React frontend to call this API
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OAuth2 scheme to read "Authorization: Bearer <token>"
from fastapi.security import APIKeyHeader
oauth2_scheme = APIKeyHeader(name="Authorization")


# =====================================================
# AUTH HELPERS / DEPENDENCIES
# =====================================================

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """
    Decode JWT token and return the current user.
    Raises 401 if token is invalid, expired, or user not found.
    """

    # If the header value starts with "Bearer ", strip it so we only decode the raw token.
    if token.lower().startswith("bearer "):
        token = token.split(" ", 1)[1].strip()

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        user_id = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise credentials_exception

    return user



def get_current_active_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """
    Ensure the user is active.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user.",
        )
    return current_user


def get_current_admin(
    current_user: models.User = Depends(get_current_active_user),
) -> models.User:
    """
    Ensure the user is an Admin.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required.",
        )
    return current_user

def get_current_admin_or_manager(
    current_user: models.User = Depends(get_current_active_user),
) -> models.User:
    """
    Ensure the user is an Admin or Manager.
    """
    if current_user.role not in ("admin", "manager"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or Manager privileges required.",
        )
    return current_user


# =====================================================
# BASIC ROOT / HEALTH
# =====================================================

@app.get("/")
def read_root():
    return {"message": "Employee Performance Tracker API is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


# =====================================================
# AUTH & USERS
# =====================================================

@app.post(
    "/users",
    response_model=schemas.UserOut,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    user_in: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin),
):
    """
    Create a new user account.
    Only Admin can create users.
    """
    existing = db.query(models.User).filter(models.User.email == user_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists.",
        )

    # If linked to an employee, ensure that employee exists
    if user_in.employee_id is not None:
        employee = (
            db.query(models.Employee)
            .filter(models.Employee.id == user_in.employee_id)
            .first()
        )
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Employee with id {user_in.employee_id} does not exist.",
            )

    user = models.User(
        name=user_in.name,
        email=user_in.email,
        password_hash=hash_password(user_in.password),
        role=user_in.role,
        is_active=user_in.is_active,
        employee_id=user_in.employee_id,
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.get("/users", response_model=List[schemas.UserOut])
def list_users(
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(get_current_admin),
):
    """
    List all users.
    Only Admin can view all users.
    """
    users = db.query(models.User).all()
    return users


@app.post("/auth/login", response_model=schemas.LoginResponse)
def login(login_in: schemas.LoginRequest, db: Session = Depends(get_db)):
    """
    Login with email + password.

    Returns:
    - access_token (JWT)
    - user info (id, name, email, role, employee_id, is_active)
    """
    user = db.query(models.User).filter(models.User.email == login_in.email).first()

    if not user or not verify_password(login_in.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    token_data = {
        "sub": user.email,
        "user_id": user.id,
        "role": user.role,
        "employee_id": user.employee_id,
    }

    access_token = create_access_token(token_data)

    return schemas.LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=user,
    )
@app.get("/auth/me", response_model=schemas.UserOut)
def read_current_user(
    current_user: models.User = Depends(get_current_active_user),
):
    """
    Return the currently authenticated user (requires valid token).
    Frontend will use this after login to know who is logged in.
    """
    return current_user


# =====================================================
# EMPLOYEES CRUD
# =====================================================

# =====================================================
# EMPLOYEES CRUD (role-based)
# =====================================================

@app.get("/employees", response_model=List[schemas.EmployeeOut])
def list_employees(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """
    List employees.

    - Admin & Manager: see all employees
    - Employee: see only their own employee record (if linked)
    """
    # Admin and Manager: full list
    if current_user.role in ("admin", "manager"):
        employees = db.query(models.Employee).all()
        return employees

    # Employee: only their own record (if linked)
    if current_user.role == "employee":
        if current_user.employee_id is None:
            # No linked employee record
            return []
        employee = (
            db.query(models.Employee)
            .filter(models.Employee.id == current_user.employee_id)
            .first()
        )
        if not employee:
            return []
        return [employee]

    # Any other unknown role: deny
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions to view employees.",
    )


@app.get("/employees/{employee_id}", response_model=schemas.EmployeeOut)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """
    Get a single employee by ID.

    - Admin & Manager: can view any employee
    - Employee: can only view themselves
    """
    employee = (
        db.query(models.Employee)
        .filter(models.Employee.id == employee_id)
        .first()
    )
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with id {employee_id} not found",
        )

    # Admin & Manager: allowed
    if current_user.role in ("admin", "manager"):
        return employee

    # Employee: only own record
    if current_user.role == "employee":
        if current_user.employee_id == employee_id:
            return employee
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own employee record.",
        )

    # Unknown role
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions to view this employee.",
    )


@app.post(
    "/employees",
    response_model=schemas.EmployeeOut,
    status_code=status.HTTP_201_CREATED,
)
def create_employee(
    employee_in: schemas.EmployeeCreate,
    db: Session = Depends(get_db),
    current_admin_or_manager: models.User = Depends(get_current_admin_or_manager),
):
    """
    Create a new employee.

    - Admin & Manager: allowed
    - Employee: not allowed
    """
    existing = (
        db.query(models.Employee)
        .filter(models.Employee.email == employee_in.email)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An employee with this email already exists.",
        )

    employee = models.Employee(
        name=employee_in.name,
        email=employee_in.email,
        role=employee_in.role,
        department=employee_in.department,
        status=employee_in.status,
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


@app.put("/employees/{employee_id}", response_model=schemas.EmployeeOut)
def update_employee(
    employee_id: int,
    employee_in: schemas.EmployeeUpdate,
    db: Session = Depends(get_db),
    current_admin_or_manager: models.User = Depends(get_current_admin_or_manager),
):
    """
    Update an employee.

    - Admin & Manager: allowed
    - Employee: not allowed
    """
    employee = (
        db.query(models.Employee)
        .filter(models.Employee.id == employee_id)
        .first()
    )
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with id {employee_id} not found",
        )

    if employee.email != employee_in.email:
        existing = (
            db.query(models.Employee)
            .filter(models.Employee.email == employee_in.email)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Another employee with this email already exists.",
            )

    employee.name = employee_in.name
    employee.email = employee_in.email
    employee.role = employee_in.role
    employee.department = employee_in.department
    employee.status = employee_in.status

    db.commit()
    db.refresh(employee)
    return employee


@app.delete("/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_admin_or_manager: models.User = Depends(get_current_admin_or_manager),
):
    """
    Delete an employee.

    - Admin & Manager: allowed
    - Employee: not allowed
    """
    employee = (
        db.query(models.Employee)
        .filter(models.Employee.id == employee_id)
        .first()
    )
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Employee with id {employee_id} not found",
        )

    db.delete(employee)
    db.commit()
    return None

# =====================================================
# GOALS CRUD (with progress)
# =====================================================

# =====================================================
# GOALS CRUD (role-based, with progress)
# =====================================================

@app.get("/goals", response_model=List[schemas.GoalOut])
def list_goals(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """
    List goals.

    - Admin & Manager: see all goals
    - Employee: see only goals linked to their employee_id
    """
    if current_user.role in ("admin", "manager"):
        goals = db.query(models.Goal).all()
        return goals

    if current_user.role == "employee":
        if current_user.employee_id is None:
            return []
        goals = (
            db.query(models.Goal)
            .filter(models.Goal.employee_id == current_user.employee_id)
            .all()
        )
        return goals

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions to view goals.",
    )


@app.get("/goals/{goal_id}", response_model=schemas.GoalOut)
def get_goal(
    goal_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """
    Get a single goal.

    - Admin & Manager: can view any goal
    - Employee: can only view goals for their own employee_id
    """
    goal = db.query(models.Goal).filter(models.Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Goal with id {goal_id} not found",
        )

    if current_user.role in ("admin", "manager"):
        return goal

    if current_user.role == "employee":
        if current_user.employee_id == goal.employee_id:
            return goal
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own goals.",
        )

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions to view this goal.",
    )


@app.post(
    "/goals",
    response_model=schemas.GoalOut,
    status_code=status.HTTP_201_CREATED,
)
def create_goal(
    goal_in: schemas.GoalCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """
    Create a new goal.

    - Admin & Manager: can create goals for any employee
    - Employee: can create goals only for themselves (employee_id must match)
    """
    # If employee, enforce that they only create goals for themselves
    if current_user.role == "employee":
        if current_user.employee_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You are not linked to an employee record.",
            )
        if goal_in.employee_id != current_user.employee_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Employees can only create goals for themselves.",
            )
    elif current_user.role not in ("admin", "manager"):
        # Any other (unknown) role: deny
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to create goals.",
        )

    employee = (
        db.query(models.Employee)
        .filter(models.Employee.id == goal_in.employee_id)
        .first()
    )
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Employee with id {goal_in.employee_id} does not exist.",
        )

    goal = models.Goal(
        title=goal_in.title,
        description=goal_in.description,
        start_date=goal_in.start_date,
        end_date=goal_in.end_date,
        status=goal_in.status,
        employee_id=goal_in.employee_id,
        progress=goal_in.progress,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


@app.put("/goals/{goal_id}", response_model=schemas.GoalOut)
def update_goal(
    goal_id: int,
    goal_in: schemas.GoalUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """
    Update a goal.

    - Admin & Manager: can update any field of any goal
    - Employee: can only update progress (and optionally status) of their own goals
    """
    goal = db.query(models.Goal).filter(models.Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Goal with id {goal_id} not found",
        )

    # Admin & Manager: full update logic
    if current_user.role in ("admin", "manager"):
        if goal_in.employee_id is not None and goal_in.employee_id != goal.employee_id:
            new_employee = (
                db.query(models.Employee)
                .filter(models.Employee.id == goal_in.employee_id)
                .first()
            )
            if not new_employee:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Employee with id {goal_in.employee_id} does not exist.",
                )
            goal.employee_id = goal_in.employee_id

        if goal_in.title is not None:
            goal.title = goal_in.title
        if goal_in.description is not None:
            goal.description = goal_in.description
        if goal_in.start_date is not None:
            goal.start_date = goal_in.start_date
        if goal_in.end_date is not None:
            goal.end_date = goal_in.end_date
        if goal_in.status is not None:
            goal.status = goal_in.status
        if goal_in.progress is not None:
            goal.progress = goal_in.progress

        db.commit()
        db.refresh(goal)
        return goal

    # Employee: can only update their own goals (and only progress/status)
    if current_user.role == "employee":
        if current_user.employee_id != goal.employee_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own goals.",
            )

        # Only allow progress and status fields
        if goal_in.progress is not None:
            goal.progress = goal_in.progress
        if goal_in.status is not None:
            goal.status = goal_in.status

        db.commit()
        db.refresh(goal)
        return goal

    # Unknown role
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions to update this goal.",
    )


@app.delete("/goals/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(
    goal_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """
    Delete a goal.

    - Admin & Manager: allowed
    - Employee: not allowed
    """
    goal = db.query(models.Goal).filter(models.Goal.id == goal_id).first()
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Goal with id {goal_id} not found",
        )

    if current_user.role not in ("admin", "manager"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin or Manager can delete goals.",
        )

    db.delete(goal)
    db.commit()
    return None


# =====================================================
# REVIEWS CRUD (role-based, supports self-evaluation)
# =====================================================

@app.get("/reviews", response_model=List[schemas.ReviewOut])
def list_reviews(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """
    List performance reviews.

    - Admin & Manager: see all reviews
    - Employee: see only reviews for their own employee_id
    """
    if current_user.role in ("admin", "manager"):
        reviews = db.query(models.PerformanceReview).all()
        return reviews

    if current_user.role == "employee":
        if current_user.employee_id is None:
            return []
        reviews = (
            db.query(models.PerformanceReview)
            .filter(models.PerformanceReview.employee_id == current_user.employee_id)
            .all()
        )
        return reviews

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions to view reviews.",
    )


@app.get("/reviews/{review_id}", response_model=schemas.ReviewOut)
def get_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """
    Get a single performance review.

    - Admin & Manager: can view any review
    - Employee: can view only their own reviews
    """
    review = (
        db.query(models.PerformanceReview)
        .filter(models.PerformanceReview.id == review_id)
        .first()
    )
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review with id {review_id} not found",
        )

    if current_user.role in ("admin", "manager"):
        return review

    if current_user.role == "employee":
        if current_user.employee_id == review.employee_id:
            return review
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own reviews.",
        )

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions to view this review.",
    )


@app.post(
    "/reviews",
    response_model=schemas.ReviewOut,
    status_code=status.HTTP_201_CREATED,
)
def create_review(
    review_in: schemas.ReviewCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """
    Create a new performance review.

    - Admin & Manager: can create reviews for any employee
    - Employee: can create self-evaluation reviews only for themselves
    """
    # Employee restrictions
    if current_user.role == "employee":
        if current_user.employee_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You are not linked to an employee record.",
            )
        if review_in.employee_id != current_user.employee_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Employees can only create self-reviews for themselves.",
            )

    elif current_user.role not in ("admin", "manager"):
        # Unknown role
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to create reviews.",
        )

    employee = (
        db.query(models.Employee)
        .filter(models.Employee.id == review_in.employee_id)
        .first()
    )
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Employee with id {review_in.employee_id} does not exist.",
        )

    review = models.PerformanceReview(
        month=review_in.month,
        rating=review_in.rating,
        feedback=review_in.feedback,
        reviewer_name=review_in.reviewer_name,
        employee_id=review_in.employee_id,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


@app.put("/reviews/{review_id}", response_model=schemas.ReviewOut)
def update_review(
    review_id: int,
    review_in: schemas.ReviewUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """
    Update a performance review.

    - Admin & Manager: can update any review
    - Employee: can update only their own reviews (e.g., self-evaluation details)
    """
    review = (
        db.query(models.PerformanceReview)
        .filter(models.PerformanceReview.id == review_id)
        .first()
    )
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review with id {review_id} not found",
        )

    # Admin & Manager: full edit allowed
    if current_user.role in ("admin", "manager"):
        if review_in.employee_id is not None and review_in.employee_id != review.employee_id:
            new_employee = (
                db.query(models.Employee)
                .filter(models.Employee.id == review_in.employee_id)
                .first()
            )
            if not new_employee:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Employee with id {review_in.employee_id} does not exist.",
                )
            review.employee_id = review_in.employee_id

        if review_in.month is not None:
            review.month = review_in.month
        if review_in.rating is not None:
            review.rating = review_in.rating
        if review_in.feedback is not None:
            review.feedback = review_in.feedback
        if review_in.reviewer_name is not None:
            review.reviewer_name = review_in.reviewer_name

        db.commit()
        db.refresh(review)
        return review

    # Employee: only own reviews
    if current_user.role == "employee":
        if current_user.employee_id != review.employee_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own reviews.",
            )

        # Allow editing month, rating, feedback, reviewer_name (self-eval text)
        if review_in.month is not None:
            review.month = review_in.month
        if review_in.rating is not None:
            review.rating = review_in.rating
        if review_in.feedback is not None:
            review.feedback = review_in.feedback
        if review_in.reviewer_name is not None:
            review.reviewer_name = review_in.reviewer_name

        db.commit()
        db.refresh(review)
        return review

    # Unknown role
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions to update this review.",
    )


@app.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """
    Delete a performance review.

    - Admin & Manager: allowed
    - Employee: not allowed
    """
    review = (
        db.query(models.PerformanceReview)
        .filter(models.PerformanceReview.id == review_id)
        .first()
    )
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review with id {review_id} not found",
        )

    if current_user.role not in ("admin", "manager"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin or Manager can delete reviews.",
        )

    db.delete(review)
    db.commit()
    return None
