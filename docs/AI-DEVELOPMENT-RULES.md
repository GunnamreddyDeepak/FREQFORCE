# KISANQUEUE — AI DEVELOPMENT RULES

Version: 1.0
Status: Active
Project: KISANQUEUE
SIH Problem Statement: 26032

---

# 1. PURPOSE

This document defines how AI coding assistants must operate while
developing KISANQUEUE.

AI assistants are engineering agents working under the KISANQUEUE
architecture.

They must optimize for:

- System correctness
- Integration consistency
- SIH alignment
- Real-world feasibility
- Security
- Maintainability
- Simplicity

They must NOT optimize for feature count or unnecessary technical
complexity.

---

# 2. PROJECT IDENTITY

KISANQUEUE is an:

> Intelligent Procurement Centre Orchestration Platform

Core workflow:

Registration
→ Slot Booking
→ Centre Recommendation
→ Real-Time Queue
→ Notifications
→ Procurement Tracking
→ Payment Tracking

KISANQUEUE is not simply a farmer booking application.

Its purpose is to coordinate:

- Farmer demand
- Procurement-centre capacity
- Queue pressure
- Processing throughput
- Procurement workflow
- Payment visibility
- Government operational monitoring

Core principle:

> ML predicts. Rules decide.

---

# 3. SYSTEM ARCHITECTURE

KISANQUEUE contains three separate user-facing portals:

1. Farmer Portal
2. Centre Operator Portal
3. Government Control Tower

Shared platform:

React Portals
→ FastAPI Backend
→ PostgreSQL + PostGIS
→ Redis
→ WebSockets
→ AI/ML Services
→ Decision/Recommendation Engine

The backend is the single source of truth.

Frontend applications must never directly access PostgreSQL.

---

# 4. DOCUMENTATION IS THE SOURCE OF TRUTH

Before implementing a feature, AI agents must inspect the relevant
documentation under:

docs/

Important documents include:

- architecture.md
- database-schema.md
- api-contract.md
- data-dictionary.md
- ml-contract.md
- realtime-events.md
- security.md
- integration-rules.md
- development-environment.md
- cross-team-dependencies.md
- AI-DEVELOPMENT-RULES.md

If existing documentation conflicts with a proposed implementation:

DO NOT silently change the architecture.

Identify the conflict and escalate it to the
Architecture/Integration Lead.

---

# 5. AI AGENT ROLE

Each AI assistant represents a specialized engineering role.

AI must remain within its assigned responsibility.

Roles:

- Architecture / Integration
- Backend / Database
- Data Engineering / GIS
- AI / ML
- Frontend
- QA / DevOps / Security

An AI agent must not independently take ownership of another team's
module.

Cross-team changes require coordination.

---

# 6. CORE ENGINEERING PRINCIPLES

## 6.1 Backend is the source of truth

Authoritative business decisions must happen in the backend.

Frontend code must not independently determine:

- Procurement eligibility
- Centre capacity
- Procurement rates
- Payment state
- Workflow authorization
- Final recommendation decisions

Frontend may display decisions returned by the backend.

---

## 6.2 ML predicts. Rules decide.

Machine learning may provide predictions such as:

- Demand forecast
- Processing time
- Waiting time / ETA
- Centre overload probability
- Anomaly detection

Deterministic rules control:

- Eligibility
- Authorization
- Hard capacity constraints
- Commodity compatibility
- Workflow transitions
- Procurement rules
- Quality/rate rules
- Payment state transitions
- Audit requirements

ML predictions must never override hard constraints.

---

# 7. CENTRE RECOMMENDATION

Centre recommendation must not simply select the nearest centre.

The recommendation pipeline should consider:

1. Eligibility
2. Operational status
3. Commodity compatibility
4. Capacity feasibility
5. Queue pressure
6. Predicted ETA
7. Distance

Feasibility must be evaluated before scoring.

Recommendations should be explainable.

Example:

A farther centre may be recommended if the nearest centre
cannot efficiently handle the farmer's requested quantity.

---

# 8. QUANTITY-AWARE CAPACITY

Procurement quantity matters.

A request for:

10 qtl

is not operationally equivalent to:

70 qtl

Capacity and workload calculations must account for quantity.

Do not build a recommendation system that only considers:

- Distance
- Number of farmers
- Simple booking counts

---

# 9. PROCUREMENT WORKFLOW

The authoritative workflow is:

REQUESTED
→ ELIGIBILITY_CHECKED
→ CENTRE_RECOMMENDED
→ SLOT_CONFIRMED
→ TOKEN_GENERATED
→ CHECKED_IN
→ WEIGHED
→ QUALITY_TESTED
→ BILLED
→ PAYMENT_INITIATED
→ PAYMENT_COMPLETED

Possible exception states/events include:

- SLOT_CHANGED
- CENTRE_DELAYED
- CENTRE_FULL
- FARMER_NO_SHOW
- QUALITY_EXCEPTION
- WEIGHMENT_EXCEPTION
- PAYMENT_FAILED
- CANCELLED
- SYSTEM_ERROR

Do not invent arbitrary workflow states.

Every authoritative state transition must be:

- Authorized
- Validated
- Timestamped
- Audited

---

# 10. DATA RULES

Prefer official or authorized data sources.

For every external data source, document where possible:

- Organization
- Source
- URL
- Available fields
- Update frequency
- Geographic coverage
- Access/license
- Intended usage

Synthetic/demo data is allowed during development.

However:

> Synthetic data must never be presented as real government data.

Clearly label synthetic datasets.

Do not scrape random sources merely to make the project appear
data-driven.

---

# 11. SENSITIVE DATA

Do not store full Aadhaar numbers.

Do not expose sensitive farmer information unnecessarily.

Do not place:

- Secrets
- API keys
- Passwords
- Tokens
- Private credentials

inside source code.

Use environment configuration.

Never commit `.env`.

---

# 12. MONEY AND QUANTITY

Money must use decimal-safe representations.

Do not use floating-point arithmetic for authoritative monetary
calculations.

Quantity must be represented in:

qtl

Procurement rates must NOT be hardcoded in frontend applications.

Rates must originate from backend-controlled configuration/rules.

---

# 13. TIME AND TIMESTAMPS

Use ISO-compatible timestamps.

Distinguish between:

- Scheduled slot time
- Actual check-in time
- Actual weighing time
- Actual quality-test time
- Actual billing time
- Payment initiation time
- Payment completion time

Do not overwrite scheduled time with operational event time.

---

# 14. EXTERNAL INTEGRATIONS

External systems must be isolated behind adapters/interfaces.

Examples:

Payment Integration Layer

Notification/SMS Provider Adapter

Official Data Adapter

Do not tightly couple core business logic to a single external provider.

Do not claim that a government/bank/payment integration is live unless
it is actually integrated and authorized.

Prototype simulations must be clearly labelled.

---

# 15. REALTIME SYSTEM

Redis may be used for:

- Cache
- Live operational state
- Short-lived data
- Realtime coordination

WebSockets may be used for realtime updates.

Examples:

- QUEUE_UPDATED
- FARMER_CHECKED_IN
- WEIGHMENT_COMPLETED
- QUALITY_UPDATED
- CENTRE_LOAD_CHANGED
- CENTRE_DELAYED
- SLOT_CHANGED
- PAYMENT_UPDATED

PostgreSQL remains the authoritative persistent source of truth.

Realtime systems must not become the authoritative database.

---

# 16. FRONTEND RULES

Frontend applications must:

- Consume backend APIs
- Validate user input
- Display loading states
- Display errors
- Display empty states
- Handle network failures
- Use responsive layouts
- Respect RBAC boundaries

Frontend must NOT:

- Access the database directly
- Make authoritative procurement decisions
- Hardcode procurement rates
- Implement duplicate backend business rules
- Change workflow state without backend authorization

Mock data may be used temporarily.

Mock data must be isolated behind an API/service adapter.

---

# 17. API RULES

The API contract is defined in:

docs/api-contract.md

Do not invent endpoints when an existing contract already provides
the required functionality.

Do not silently rename:

- Endpoints
- Request fields
- Response fields
- Enum values
- Workflow states
- Event names

Breaking API changes require discussion and approval.

---

# 18. DATABASE RULES

PostgreSQL is the transactional source of truth.

Database schema changes must be coordinated with:

- Backend owner
- Architecture/Integration Lead
- Any affected team

Use migrations.

Do not manually modify production-like databases without a migration.

Avoid unnecessary tables.

Avoid duplicate representations of the same authoritative data.

---

# 19. ML RULES

Do not build sophisticated ML merely to claim AI.

Before selecting a model, determine:

1. Is ML actually needed?
2. Is usable data available?
3. What is the baseline?
4. What metric measures success?
5. How will predictions be evaluated?
6. How will confidence be represented?
7. How will model versions be tracked?

Start with simple, interpretable baselines.

If sufficient data does not exist:

> Say so.

Do not fabricate training performance.

Do not report fake accuracy.

---

# 20. AI EXPLAINABILITY

Where AI predictions influence operational planning, expose
appropriate metadata such as:

- Prediction
- Confidence
- Model version
- Prediction timestamp

AI predictions are advisory unless explicitly defined otherwise.

Final operational decisions must follow deterministic business rules.

---

# 21. SECURITY

Never trust the frontend for authorization.

The backend must enforce:

- Authentication
- Authorization
- Role boundaries
- Resource ownership
- Input validation

Roles:

FARMER
CENTRE_OPERATOR
GOVERNMENT

A farmer must not access another farmer's private data.

A centre operator must not automatically access unrelated centre
operations.

Government users may have network-level operational visibility
according to authorization.

---

# 22. GIT RULES

Branches:

main
develop
feature/*

Workflow:

develop
→ feature/*
→ implementation
→ tests
→ commit
→ Pull Request
→ review
→ develop

Rules:

- main = stable
- develop = integration
- feature/* = individual work

Do not:

- Work directly on main
- Force-push shared branches
- Commit secrets
- Commit `.venv`
- Commit `node_modules`
- Commit local databases
- Modify another team's feature without coordination

---

# 23. CODE QUALITY

Prefer:

- Small functions
- Clear names
- Typed interfaces where appropriate
- Reusable services
- Testable components
- Explicit error handling
- Clear separation of responsibilities

Avoid:

- Giant files
- Copy-pasted logic
- Hidden global state
- Magic numbers
- Hardcoded configuration
- Unnecessary abstractions
- Premature optimization

---

# 24. AI IMPLEMENTATION PROCESS

Before coding:

1. Read relevant documentation.
2. Inspect existing code.
3. Identify dependencies.
4. Identify shared interfaces.
5. Identify risks.
6. Propose the smallest reasonable implementation.

Then:

7. Implement incrementally.
8. Run tests.
9. Check integration impact.
10. Review the diff.
11. Report changes.
12. Prepare commit.

AI must not blindly generate large unrelated codebases.

---

# 25. WHEN AI MUST STOP AND ASK

AI must stop and ask the Architecture/Integration Lead when:

- API contract must change
- Database contract affecting other modules must change
- Workflow states must change
- Realtime event contracts must change
- ML input/output contract must change
- Authentication architecture must change
- RBAC boundaries must change
- External integration architecture must change
- Shared configuration changes are required
- A new cross-team dependency is introduced

---

# 26. LOCAL VS SHARED DECISIONS

AI may make local implementation decisions when they do not affect
other modules.

Example:

Choosing how to organize internal helper functions.

AI must escalate shared decisions.

Example:

Changing:

GET /api/v1/procurement-requests

to:

GET /api/v1/farmer/requests

This is a shared API decision and must be discussed.

---

# 27. FEATURE DISCIPLINE

Do not add features simply because they sound impressive.

Unapproved examples include:

- Chatbot
- Blockchain
- Facial recognition
- Cryptocurrency
- Unnecessary IoT
- Social features
- Random AI insights
- Decorative analytics

Every feature must answer:

1. What real problem does this solve?
2. How does it support SIH26032?
3. Who uses it?
4. What data does it require?
5. What operational benefit does it provide?
6. What complexity does it introduce?

If the benefit is weak, recommend not implementing it.

---

# 28. TESTING REQUIREMENTS

Every feature must include appropriate tests.

At minimum consider:

- Valid input
- Invalid input
- Missing input
- Unauthorized access
- Wrong role
- Boundary values
- Duplicate requests
- Network failure
- Database failure
- External-service failure
- Invalid workflow transition

Tests must reflect actual project rules.

Do not write tests merely to increase test count.

---

# 29. AI RESPONSE FORMAT

For significant development tasks, the AI agent should report:

## Understanding

What the task means.

## Relevant Rules

Which KISANQUEUE rules apply.

## Files Affected

Which files will change.

## Implementation Plan

The smallest appropriate implementation.

## Changes

What was implemented.

## Tests

What was tested and the result.

## Integration Impact

Whether another team is affected.

## Risks

Potential issues.

## Human Review

What the teammate must inspect.

## Commit

Suggested Git commit message.

---

# 30. HUMAN RESPONSIBILITY

AI generates and modifies code.

The human teammate remains responsible for:

- Reviewing changes
- Running tests
- Understanding the implementation
- Checking requirements
- Reporting conflicts
- Creating commits
- Opening pull requests
- Communicating blockers

AI output must never be merged blindly.

---

# 31. ARCHITECTURE AUTHORITY

The Architecture/Integration Lead is responsible for resolving
cross-team architectural conflicts.

When two modules require incompatible approaches:

Do not independently choose one.

Escalate.

The goal is not:

"Make my module work."

The goal is:

"Make KISANQUEUE work as one system."

---

# 32. DEFINITION OF DONE

A feature is not complete merely because the code runs.

A feature is considered ready when:

- Requirement is satisfied
- Relevant documentation is followed
- API contracts are respected
- Security boundaries are respected
- Tests pass
- Errors are handled
- Integration impact is understood
- No secrets are committed
- Git changes are reviewable
- Human teammate has reviewed the implementation

---

# 33. FINAL PRINCIPLE

KISANQUEUE follows:

> Innovation + Real-world Workability + SIH Alignment
> > Feature Count

And:

> ML predicts. Rules decide.

And most importantly:

> Build ONE coherent KISANQUEUE system,
> not six independent AI-generated projects.