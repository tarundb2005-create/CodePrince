# DSA Forge

Local-first, personalized DSA practice platform. It uses FastAPI + PostgreSQL and a React/Vite client.

## Quick start

```powershell
ts\python.exe -m pip install -r backend/requirements.txt
$env:DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/dsa_forge"
$env:ADMIN_EMAIL="admin@example.com"
$env:ADMIN_PASSWORD="use-a-strong-local-password"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
uvicorn app.main:app --app-dir backend --reload --port 8000

cd frontend
npm install
npm run dev

Open `http://localhost:5173`. The API is available at `http://localhost:8000/docs`.

### Create a faculty login

The first backend start creates the administrator account from `ADMIN_EMAIL` and `ADMIN_PASSWORD` if it does not already exist. Sign in with the **Admin** role, open **Students**, and create a user with tvenhe **Faculty** role. Sign out, choose **Faculty** on the login screen, and sign in with that faculty email and password. Faculty accounts are issued by an administrator.

Students can sign up with a unique registration number; existing accounts can add one under **Settings**. An administrator creates a course under **Courses** and assigns it to a faculty account. Faculty add questions to the assigned course and map students by registration number. Course progress is tracked against those questions. Faculty can schedule and publish assessments; enrolled students open them under **Exams**, solve the assigned problems, and submit. Assessment scores stay private until faculty shares them from **Results**.

Using `npm.cmd` and the virtual environment's `python.exe` avoids PowerShell's blocked `.ps1` shims; no execution-policy change is needed.

## Docker startup

Docker Desktop must be running. From the repository root:

```powershell
$env:ADMIN_EMAIL="admin@example.com"
$env:ADMIN_PASSWORD="use-a-strong-local-password"
docker compose up --build
```

Open `http://localhost:5174`; the API is available at `http://localhost:8001/docs`. The API container uses the Docker socket only to launch short-lived, network-disabled executor containers. The executor image is built locally as `dsa-forge-executor:local` and is never exposed as a network service.
## Execution security

`POST /api/run` and `POST /api/submit` use a short-lived Docker container when Docker is installed. The supplied executor disables networking, drops capabilities, runs as an unprivileged user, has read-only root storage, and applies CPU/memory/process/output/time limits. Docker is not installed in this environment, so the API reports `503` instead of falling back to unsafe in-process execution.

For public use, put the executor on isolated hosts/VMs and add queueing, per-user rate limits, image scanning, kernel hardening, observability, and a stronger sandbox such as gVisor or Firecracker.

## Database and import format

Set `DATABASE_URL` to a PostgreSQL connection string before starting the API. The project accepts standard SQLAlchemy URLs such as `postgresql+psycopg://user:password@host:5432/dsa_forge`. Seed data is created automatically on first start. Existing SQLite data is not migrated automatically; export it with `GET /api/export` before switching databases, then import it with `POST /api/import`.

For local configuration, copy `.env.example` to `.env` and replace the placeholder connection string. The PostgreSQL driver is installed from `backend/requirements.txt`.

`GET /api/export` returns versioned JSON; `POST /api/import` accepts `{ "version": 1, "questions": [...] }` and validates required fields.

## Test

```powershell
pytest backend/tests
cd frontend; npm run build
```
