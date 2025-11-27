from sqlalchemy import Column, Integer, String, Text, Date, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from db import Base


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    role = Column(String(100), nullable=True)
    department = Column(String(100), nullable=True)
    status = Column(String(50), nullable=False, default="active")

    # Relationships
    goals = relationship(
        "Goal",
        back_populates="employee",
        cascade="all, delete-orphan",
    )
    reviews = relationship(
        "PerformanceReview",
        back_populates="employee",
        cascade="all, delete-orphan",
    )

    # Optional one-to-one link to a user account
    user = relationship(
        "User",
        back_populates="employee",
        uselist=False,
    )


class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    status = Column(String(50), nullable=False, default="in-progress")

    # Progress tracking, 0–100 (% of goal completed)
    progress = Column(Integer, nullable=False, default=0)

    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)

    # Relationships
    employee = relationship("Employee", back_populates="goals")


class PerformanceReview(Base):
    __tablename__ = "performance_reviews"

    id = Column(Integer, primary_key=True, index=True)
    # e.g., "2025-01" for January 2025
    month = Column(String(7), nullable=False)
    rating = Column(Integer, nullable=False)
    feedback = Column(Text, nullable=True)
    reviewer_name = Column(String(100), nullable=False)

    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)

    # Relationships
    employee = relationship("Employee", back_populates="reviews")


class User(Base):
    """
    User account used for authentication.

    - email + password_hash are used for login
    - role controls permissions: 'admin', 'manager', 'employee'
    - employee_id links this user to an Employee (for filtering data)
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="employee")
    is_active = Column(Boolean, nullable=False, default=True)

    # Optional link to Employee row
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)

    employee = relationship("Employee", back_populates="user")
