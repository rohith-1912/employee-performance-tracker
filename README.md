# Employee Performance Tracker

A full-stack web application to manage employees, assign goals, track performance reviews, and visualize progress and recognition.

This system is designed for small to medium organizations that want a simple way to:
- Manage employees
- Assign and track goals/KPIs
- Record monthly performance reviews (including self-evaluations)
- Highlight top performers
- Visualize performance with charts

---

## 🚀 Tech Stack

**Frontend**
- React (JavaScript)
- HTML5 / CSS3
- Recharts (for charts/graphs)
- Fetch API for HTTP calls

**Backend**
- Python
- FastAPI
- SQLAlchemy (ORM)
- Pydantic (data validation)
- Passlib + bcrypt (password hashing)
- Python-JOSE (JWT authentication)

**Database**
- SQL database (currently configured for SQLite by default, can be switched to MySQL)

---

## ✨ Core Features

### 1. Authentication & Authorization
- Login with **email + password**
- Passwords are securely hashed
- JSON Web Tokens (JWT) used for authentication
- Role-based access control:
  - **Admin**
    - Full access to employees, goals, and reviews
    - Can create new users (admin, manager, employee)
  - **Manager**
    - Can view and manage all employees, goals, and reviews
    - Cannot create users
  - **Employee**
    - Can log in and see only **their own** goals and reviews
    - Employees tab is hidden
    - Can submit **self-evaluations** and update progress on their goals

---

### 2. Employee Management

- CRUD operations for employees (Create / Read / Update / Delete)
- Fields:
  - `id`
  - `name`
  - `email`
  - `role` (job title / designation)
  - `department`
  - `status` (active / inactive)
- Admin & Manager:
  - Can add and manage employees from the **Employees** page
- Employee:
  - Cannot access full employees list (blocked by role)

---

### 3. Goals & Progress Tracking

- Each goal is assigned to a specific employee.
- Goal fields:
  - `id`
  - `title`
  - `description`
  - `start_date`
  - `end_date`
  - `status` (e.g. planned, in-progress, completed)
  - `employee_id`
  - `progress` (0–100%)

**Key capabilities:**
- Admin/Manager can create/edit goals for any employee.
- Employee can view and update **progress** (and sometimes status) of their **own goals**.
- The Dashboard shows:
  - Total number of goals
  - Goals in progress
  - Completed goals
  - A **goal completion percentage bar**

---

### 4. Performance Reviews & Self-Evaluations

- Performance reviews are stored with:
  - `id`
  - `month`
  - `rating` (numeric, e.g. 1–5)
  - `feedback`
  - `reviewer_name`
  - `employee_id`

**Admin & Manager:**
- Can create performance reviews for any employee.
- Can update or delete reviews.

**Employee:**
- Can create **self-evaluation** reviews for themself.
- Can update their own reviews.
- Can only see reviews linked to their `employee_id`.

The Dashboard shows:
- Total number of reviews
- A **bar chart** of ratings distribution (e.g. how many 3/4/5 ratings)

---

### 5. Rewards & Recognition

The system automatically calculates simple recognition labels based on:
- **Average performance rating** per employee
- **Number of completed goals** per employee

On the **Employees** page, a **Recognition** column can display:
- `Top Performer` – employee with highest average rating (above a threshold and with at least one review)
- `Employee of the Month` – employee with the most completed goals
- `Top Performer / Employee of the Month` – if the same person qualifies for both
- `-` – no recognition yet

This gives managers a quick way to see standout employees.

---

### 6. Dashboard & Visual Reports

The Dashboard page provides:

- **Summary cards**:
  - Total employees
  - Active employees
  - Total goals
  - Goals in progress
  - Goals completed
  - Total reviews

- **Visual charts** (using Recharts):
  - **Pie chart** – Goal status distribution (in-progress, completed, other)
  - **Bar chart** – Review ratings distribution (e.g. how many 1–5 star ratings)

- **Goal completion bar**:
  - A visual bar showing **% of goals completed** in the system.

---

## 📁 Project Structure

High-level structure:

```bash
employee-performance-tracker/
├── backend/
│   ├── main.py           # FastAPI app, routes & business logic
│   ├── models.py         # SQLAlchemy models (User, Employee, Goal, PerformanceReview)
│   ├── schemas.py        # Pydantic schemas (request/response models)
│   ├── database.py       # Database config and session
│   ├── auth_utils.py     # JWT generation, password hashing/verification
│   └── ...               # Other backend helpers
│
├── frontend/
│   ├── src/
│   │   ├── App.js                    # Main React app with navigation & role handling
│   │   ├── App.css                   # Global, colourful styling
│   │   ├── components/
│   │   │   ├── auth/LoginPage.js     # Login form (email + password)
│   │   │   ├── dashboard/DashboardPage.js
│   │   │   ├── employees/EmployeesPage.js
│   │   │   ├── goals/GoalsPage.js
│   │   │   └── reviews/ReviewsPage.js
│   │   └── ...
│   └── package.json
│
├── .gitignore
└── README.md
