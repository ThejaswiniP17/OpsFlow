# OpsFlow - Smart Team & Task Management Platform

OpsFlow is a production-style, scalable, collaborative workflow and productivity platform inspired by real-world systems like Jira, ClickUp, and Linear. It features custom security boundaries, role-based access controls, automatic audit logging, and in-app notifications.

Designed as an interview-ready full-stack portfolio project, the backend is built using **Python 3.12** and **Django 5.0 / Django REST Framework**, and the frontend features a responsive **Bootstrap 5 & JavaScript** analytics dashboard.

---

## Key Modules & Features

1. **Authentication & Custom User Model**: Extends Django's `AbstractUser` to support system-wide roles (`ADMIN`, `TEAM_LEAD`, `MEMBER`). Implements **dual-auth** (Session auth for template navigation and **Simple JWT** tokens for secure REST API access).
2. **Team Scoping & Boundary Security**: Dynamic team directories where users can create teams, manage memberships, and assign roles. Security checks guarantee that members can only query or view tasks belonging to their teams.
3. **Task & Workflow Lifecycles**: Task tracking with statuses (`PENDING`, `IN_PROGRESS`, `COMPLETED`, `BLOCKED`, `CLOSED`) and priorities (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), file attachments, and collaborative comment logs.
4. **Analytics Dashboard**: Interactive dashboard powered by **Chart.js** displaying task status doughnut charts, task priority distribution bar charts, and weekly completion rate trendlines.
5. **Audit Logging & Notifications**: Automated activity logging (`ActivityLog` database model) to track team actions (creation, task updates, status changes) and custom in-app alerts (`Notification` model) for task assignments.
6. **Dual Database Layout**: Locally runs zero-configuration SQLite for development; automatically switches to PostgreSQL in production via environment variables and `dj-database-url`.

---

## Database Schema Model Relationship

*   **User** (Custom model extending `AbstractUser`)
    *   Has custom fields: `role`, `bio`, `profile_picture`.
*   **Team**
    *   Linked `created_by` -> `User` (`SET_NULL`).
*   **TeamMember** (Through-table mapping User to Team)
    *   Linked `user` -> `User` (`CASCADE`), `team` -> `Team` (`CASCADE`).
    *   Unique constraint on `(team, user)`.
*   **Task**
    *   Linked `team` -> `Team` (`CASCADE`), `assigned_to` -> `User` (`SET_NULL`), `created_by` -> `User` (`SET_NULL`).
    *   Indexed on `status`, `priority`, and `due_date` fields.
*   **Comment**
    *   Linked `task` -> `Task` (`CASCADE`), `user` -> `User` (`CASCADE`).
*   **Notification**
    *   Linked `recipient` -> `User` (`CASCADE`).
    *   Indexed on `recipient` and `is_read`.
*   **ActivityLog**
    *   Linked `actor` -> `User` (`SET_NULL`), `task` -> `Task` (`SET_NULL`), `team` -> `Team` (`SET_NULL`).

---

## Folder Architecture

```text
OpsFlow/
├── config/                  # Global Settings and root URL mappings
├── accounts/                # Custom User profile, role flags, signup/login
├── teams/                   # Team listings, adding/removing members
├── tasks/                   # Task CRUD views, comment postings, and file attachments
├── dashboard/               # Main analytics dashboard & notifications lists
├── notifications/           # In-app notifications models & utils
├── activity_logs/           # System activity logging helper
├── api/                     # DRF serializers, viewsets, and routers
├── templates/               # Global templates (base.html, accounts/, teams/, etc.)
├── static/                  # Shared stylesheet styles.css, images
├── media/                   # User uploaded files and profiles
├── docs/                    # API Postman collections
├── manage.py
├── requirements.txt
├── .env.example
└── .env
```

---

## Local Setup & Run Guide

### 1. Clone the project and set up virtual environment
```bash
# Clone the repository (or navigate to directory)
cd opsflow

# Create Python virtual environment
python -m venv venv

# Activate Virtual Environment
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On macOS/Linux:
source venv/bin/activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Setup environment variables
Create a `.env` file in the root folder (using `.env.example` as a template):
```ini
DEBUG=True
SECRET_KEY=your-development-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1
# In production, define DATABASE_URL to connect to PostgreSQL:
# DATABASE_URL=postgres://user:password@localhost:5432/opsflow
```

### 4. Run database migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Create a Superuser (Admin)
```bash
python manage.py createsuperuser
```
Follow the prompts to enter a username, email, and password. Log in to register a team!

### 6. Run the local development server
```bash
python manage.py runserver
```
Visit the application at `http://127.0.0.1:8000/`. Log in with your superuser credentials.

---

## REST API Documentation

All REST APIs are structured under `/api/v1/` and secured using JWT (JSON Web Tokens).

### Authentication Endpoints
*   `POST /api/v1/token/`: Obtain JWT tokens (Access and Refresh) by providing `username` and `password`.
*   `POST /api/v1/token/refresh/`: Renew expired access tokens using the refresh token.

### API ViewSet Endpoints (Required Authorization Header: `Authorization: Bearer <access_token>`)
*   `GET /api/v1/teams/`: List all teams user belongs to.
*   `POST /api/v1/teams/`: Create a new team (Team Lead / Admin only).
*   `GET /api/v1/teams/{id}/members/`: Get member list of a team.
*   `POST /api/v1/teams/{id}/members/`: Add a user to a team (Team Lead / Admin only).
*   `GET /api/v1/tasks/`: List all tasks (supports query param filters: `?status=PENDING&priority=HIGH`).
*   `POST /api/v1/tasks/`: Create a task (Team Lead / Admin only).
*   `PATCH /api/v1/tasks/{id}/`: Update task (e.g. status changes).
*   `GET /api/v1/activities/`: View system-wide activity logs.
*   `GET /api/v1/notifications/`: List user in-app notifications.
*   `POST /api/v1/notifications/mark_all_read/`: Mark all notifications as read.

> [!TIP]
> **Postman Verification**:
> Import the Postman environment collection from [docs/postman_collection.json](file:///C:/Users/hp/.gemini/antigravity/scratch/opsflow/docs/postman_collection.json) to start testing endpoints with pre-configured templates!

---

## Production Readiness Setup

1.  **Static Files Serving**: Configured **WhiteNoise** middleware with gzip compression and caching enabled (`CompressedManifestStaticFilesStorage`) for asset hosting directly from Django without Nginx configurations.
2.  **Database Connection Pooling**: Configured `dj-database-url` with `conn_max_age=600` and TLS verification dynamically checking debug modes.
3.  **WSGI Server**: Production deployment instructions utilize **Gunicorn** for process management.

---

## Future AI Extensibility Plan

OpsFlow's modular codebase is optimized for future AI features:
*   **AI Task Summarization**: Add a backend endpoint inside `tasks` communicating with Gemini/GPT API to generate quick markdown summaries of long comment discussions.
*   **AI Workload Prediction**: Run local data processing on task lists to identify user bottlenecks and suggest task delegations.
*   **AI Conversational Assistant**: Integrate a WebSocket or AJAX API to provide chat help inside the dashboard resolving tasks questions.

---

## Technical Interview Q&A Cheatsheet

### Q: Why did you override Django's default User model?
**A**: Overriding `AbstractUser` before running migrations is a best practice. It allowed us to add system-wide role classifications (`role = ADMIN, TEAM_LEAD, MEMBER`) and custom fields (`bio`, `profile_picture`) directly on the authentication table. This avoids messy multi-table joins or one-to-one profile tables.

### Q: How does the application handle boundaries and scope security?
**A**: Scoping queries is handled at both the template and API levels:
1.  In template views, tasks are filtered to only return records belonging to teams that the user is a member of: `Task.objects.filter(team__memberships__user=request.user)`.
2.  In the DRF API, ViewSets override `get_queryset()` to enforce this same scoping.
3.  We implemented custom decorators (`admin_required`, `team_lead_required`) and DRF custom verification layers to raise a `PermissionDenied` (403 HTTP response) if non-authorized users try to access scoped views.

### Q: Why are `status`, `priority`, and `due_date` indexed?
**A**: These fields are heavily used in dashboard sorting, status groupings, search operations, and filter requests. Adding database indexes on these fields (`Meta.indexes` inside the model definitions) speeds up lookup times and index-scan operations.

### Q: What is the benefit of using `dj-database-url`?
**A**: It allows us to follow Twelve-Factor App methodologies by storing configurations in environment variables. If `DATABASE_URL` is set (e.g. by Render or Railway connecting to PostgreSQL), Django connects to it automatically; otherwise, it falls back to a local SQLite database for development, creating a zero-setup local dev experience.
