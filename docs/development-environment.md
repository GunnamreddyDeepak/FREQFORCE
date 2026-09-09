# KISANQUEUE Development Environment

## Version

v1.0

## Purpose

This document defines the common development environment for all
KISANQUEUE contributors.

The goal is to ensure that all team members develop and test against
compatible versions and configurations.

---

# 1. Operating System

Primary development environment:

Windows 10/11

The project should remain compatible with Linux-based deployment
through Docker.

---

# 2. Required Tools

Every developer should have:

- Git
- GitHub account/access
- Visual Studio Code
- Node.js LTS
- npm
- Python 3.x
- Docker Desktop

---

# 3. Repository

Repository:

kisanqueue

Primary development branch:

develop

Stable branch:

main

---

# 4. Git Workflow

Never develop directly on:

main
develop

Use:

feature/*
fix/*

Example:

feature/backend-auth
feature/farmer-request
feature/ml-eta

Workflow:

develop
→ feature branch
→ commit
→ push
→ Pull Request
→ review
→ develop

main is reserved for stable/release code.

---

# 5. Frontend Environment

Frontend applications use:

React
Vite
npm

Applications:

apps/farmer-portal
apps/operator-portal
apps/government-portal

Each portal is an independent React application.

---

# 6. Backend Environment

Backend uses:

Python
FastAPI
Uvicorn
SQLAlchemy

Initial backend structure:

backend/
└── app/

The backend is the single source of truth for transactional
business logic.

---

# 7. Database

Primary database:

PostgreSQL

Spatial extension:

PostGIS

PostgreSQL is the transactional source of truth.

PostGIS is used for geographic operations.

---

# 8. Redis

Redis is used for:

- caching
- rapidly changing operational state
- realtime support
- temporary data where appropriate

Redis must not replace PostgreSQL as the authoritative transactional
database.

---

# 9. AI/ML Environment

AI/ML services use Python.

Expected responsibilities include:

- demand forecasting
- ETA prediction
- processing-time prediction
- overload prediction

ML services must follow:

ML predicts.
Rules decide.

---

# 10. Environment Variables

Local secrets must be stored in:

.env

The repository must contain:

.env.example

but never real credentials.

Required configuration includes:

DATABASE_URL=
REDIS_URL=
JWT_SECRET=
SMS_PROVIDER=
SMS_API_KEY=
AI_SERVICE_URL=

---

# 11. Local Development Ports

Recommended development ports:

Farmer Portal:

5173

Operator Portal:

5174

Government Portal:

5175

FastAPI:

8000

PostgreSQL:

5432

Redis:

6379

If a port conflict occurs, the developer should document the
alternative port rather than silently changing shared configuration.

---

# 12. Local Service Architecture

Expected local environment:

React Portal
     ↓
FastAPI
     ↓
PostgreSQL/PostGIS
     +
Redis

AI/ML services communicate through documented service interfaces.

---

# 13. Docker

Docker Desktop is required for infrastructure services.

Docker should be used to provide a consistent local environment
for:

- PostgreSQL/PostGIS
- Redis
- backend services where appropriate

Docker configuration belongs under:

infrastructure/

---

# 14. Python Virtual Environment

Backend and ML development should use isolated Python environments.

Example:

python -m venv .venv

Windows activation:

.venv\Scripts\activate

Do not commit virtual environments to Git.

---

# 15. Dependency Management

Frontend dependencies are managed through:

package.json

Python dependencies are managed through:

requirements.txt

Dependency changes must be reviewed before introducing unnecessary
libraries.

Avoid adding a library when existing project functionality can
reasonably solve the requirement.

---

# 16. Local Development Rules

Before starting development:

1. Pull the latest develop branch.
2. Create a feature branch.
3. Check the relevant documentation.
4. Implement the change.
5. Run tests/build checks.
6. Commit the change.
7. Push the feature branch.
8. Create a Pull Request.

---

# 17. Required Documentation Before Development

Developers should understand the relevant documents before modifying
shared functionality.

Core documents:

docs/
├── architecture.md
├── api-contract.md
├── database-schema.md
├── data-dictionary.md
├── ml-contract.md
├── realtime-events.md
├── security.md
├── integration-rules.md
├── cross-team-dependencies.md
└── development-environment.md

---

# 18. Security

Never commit:

- passwords
- API keys
- JWT secrets
- database credentials
- SMS provider credentials
- private certificates

Verify:

.env

is ignored by Git.

---

# 19. Data

Official or authorized data is preferred.

Synthetic/demo data must be explicitly labelled.

Do not present synthetic data as official government data.

Raw data containing sensitive information must not be committed
to the public repository.

---

# 20. Testing

Before creating a Pull Request, developers should run the relevant:

- unit tests
- integration tests
- frontend build
- backend checks
- API tests

The exact commands will be documented as the project develops.

---

# 21. API Development

API implementations must follow:

docs/api-contract.md

Do not silently change:

- endpoint paths
- HTTP methods
- required fields
- response structures
- authentication requirements
- workflow semantics

Contract changes require coordination.

---

# 22. Database Development

Database changes must follow:

docs/database-schema.md

Database migrations must be used once the migration framework
is established.

Do not manually modify another developer's local database schema
without documenting the change.

---

# 23. ML Development

ML services must follow:

docs/ml-contract.md

Models must document:

- inputs
- outputs
- units
- prediction horizon
- confidence
- model version
- timestamp
- fallback behavior

---

# 24. Realtime Development

Realtime functionality must follow:

docs/realtime-events.md

WebSocket events are delivery mechanisms.

The database remains the source of truth.

---

# 25. Integration Failures

If a service is unavailable:

- return a controlled error
- use documented fallback behavior where applicable
- do not silently fabricate authoritative data
- log the failure appropriately

---

# 26. Development Principle

Prefer:

Simple
→ Testable
→ Maintainable
→ Integratable

over:

Complex
→ Unnecessary
→ Difficult to maintain

---

# 27. Current Development Milestone

The first integration target is:

Farmer Login
→ Procurement Request
→ Centre Recommendation
→ Slot
→ Token

The complete queue, procurement, payment, notification and ML
features will be integrated incrementally.

---

# 28. Environment Change Rule

If a developer needs to change:

- Node version
- Python version
- Docker configuration
- database version
- Redis version
- shared environment variables
- required dependency

the change must be communicated to affected teams and reflected
in this document where appropriate.

---

# 29. Final Rule

Every developer should be able to clone the repository and,
after following this document, understand how the KISANQUEUE
development environment is intended to work.

Consistency across developers is more important than individual
local preferences.