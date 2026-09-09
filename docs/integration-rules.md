# KISANQUEUE Integration Rules

## Version

v1.0

## Purpose

This document defines the rules that all KISANQUEUE development teams
must follow when building, integrating, testing, and modifying the system.

The objective is to ensure that independently developed modules work
together without breaking the overall architecture.

---

# 1. Core Architecture Principle

KISANQUEUE follows:

Frontend
→ API
→ FastAPI Backend
→ PostgreSQL/PostGIS

with Redis, AI/ML services, notification services, and external
integrations connected through defined backend interfaces.

The backend is the single source of truth.

---

# 2. System Boundaries

The system contains three independent user-facing applications:

1. Farmer Portal
2. Centre Operator Portal
3. Government Control Tower

They must remain separate applications.

They communicate with the backend through APIs.

No portal may directly access another portal's internal code or database.

---

# 3. Backend Is the Single Source of Truth

The backend owns:

- Authentication
- Authorization
- Procurement workflow
- Capacity rules
- Slot validation
- Token generation
- Queue state
- Procurement state
- Quality/rate logic
- Billing
- Payment state
- Notifications
- Audit records
- Centre assignment decisions

Frontend applications only display and submit information.

Frontend code must not become the authoritative source for business rules.

---

# 4. Frontend Integration Rules

Frontend applications must:

- communicate through documented APIs
- validate basic user input for usability
- handle loading states
- handle API errors
- handle network failures
- display backend-provided state
- respect user permissions

Frontend applications must NOT:

- connect directly to PostgreSQL
- connect directly to Redis
- modify database records directly
- generate authoritative token numbers
- calculate authoritative procurement rates
- decide procurement workflow transitions
- bypass backend authorization
- implement duplicate business rules as the source of truth

Client-side validation is allowed for user experience.

Server-side validation is mandatory.

---

# 5. Farmer Portal Boundary

The Farmer Portal may access only farmer-authorized information.

It may:

- create procurement requests
- view own requests
- view recommendations
- confirm slots
- view own token
- view own queue/status information
- view procurement status
- view bill/payment status
- receive notifications

It must not expose:

- other farmers' personal information
- government administrative controls
- unrestricted centre management
- internal system audit data
- unauthorized operational data

---

# 6. Centre Operator Portal Boundary

The Centre Operator Portal must operate within the permissions of
the authenticated centre/operator.

It may:

- view assigned centre queue
- check in farmers
- record weighments
- record quality results
- generate/confirm bills where authorized
- view applicable configured rates
- update permitted operational states
- view centre exceptions

It must not:

- access arbitrary centres
- change government configuration
- bypass workflow validation
- directly modify payment completion state
- modify audit records
- access data outside its authorization scope

---

# 7. Government Control Tower Boundary

The Government Control Tower provides authorized network/district-level
operational visibility.

It may access:

- centre status
- centre capacity
- queue information
- procurement information
- forecasts
- overload risk
- exceptions
- payment status
- operational analytics
- authorized audit information

Government actions must still pass through backend authorization
and validation.

The Control Tower is an operational decision-support interface,
not a replacement for the transactional backend.

---

# 8. Database Rule

PostgreSQL is the transactional source of truth.

PostGIS is used for geographic data and spatial queries.

Redis is used for:

- caching
- rapidly changing operational state
- realtime support
- temporary data where appropriate

Redis must not become the authoritative permanent source of
transactional procurement data.

---

# 9. Database Access Rule

Only backend services may directly access the transactional database.

Frontend:

NO

AI/ML:

NO direct transactional database writes

External services:

NO direct database access

Backend:

YES

AI/ML services receive data through defined service/API interfaces.

---

# 10. Workflow State Rule

Procurement workflow state transitions must be controlled by the backend.

Normal lifecycle:

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

A frontend must never directly set a workflow state.

Every critical transition must:

1. Validate the current state.
2. Validate the requested transition.
3. Check authorization.
4. Persist the change.
5. Record an audit event where required.
6. Notify affected systems/users where required.

---

# 11. AI/ML Integration Rule

## ML predicts. Rules decide.

AI/ML may provide:

- demand forecasts
- processing-time predictions
- queue/ETA predictions
- overload predictions
- confidence scores
- model metadata

AI/ML must NOT independently:

- approve procurement
- bypass capacity constraints
- authorize users
- change payment states
- override hard eligibility rules
- directly modify transactional workflow state

ML output is advisory input to the decision engine.

---

# 12. Recommendation Engine Rule

Centre recommendation must follow:

Request
→ Eligibility
→ Operational availability
→ Commodity compatibility
→ Capacity feasibility
→ Prediction/ETA
→ Distance
→ Ranking
→ Recommendation

Hard feasibility constraints must be checked before ranking.

A centre that cannot accept the request must not be recommended
merely because it is closer.

Recommendation results should provide an explanation when practical.

Example:

"North Centre recommended because it has sufficient capacity
and lower predicted queue pressure."

---

# 13. Quantity-Aware Capacity Rule

Capacity decisions must consider the farmer's requested quantity.

Example:

10 qtl and 70 qtl must not be treated as identical workloads.

Recommendation logic should consider:

- current load
- available capacity
- requested quantity
- expected arrivals
- processing throughput
- predicted utilization

Capacity rules are deterministic.

ML may predict future demand or processing behavior.

---

# 14. Procurement Rate Rule

Procurement rates must be controlled by the backend.

Rates must NOT be hardcoded in:

- React
- mobile frontend
- static frontend configuration
- ML models

The backend must provide the applicable configured rate.

Quality/rate changes must flow consistently through:

Quality Test
→ Applicable Rate
→ Bill
→ Payment
→ Government View
→ Audit

Any official procurement rules/rates must come from an
authorized source/configuration.

Demo-only values must be clearly labelled as demo configuration.

---

# 15. Payment Integration Rule

Payment status is controlled by the backend/payment integration layer.

Possible prototype states:

PENDING
→ INITIATED
→ PROCESSING
→ COMPLETED

or:

PENDING
→ INITIATED
→ PROCESSING
→ FAILED

The prototype must not claim live PFMS, NPCI, banking, or DBT
integration unless an actual authorized integration exists.

Payment providers must be accessed through an adapter/integration layer.

Business logic must not be tightly coupled to a specific provider.

---

# 16. Notification Integration Rule

Notifications must follow:

Backend Event
→ Notification Service
→ SMS/Web/PWA Delivery

Frontend applications must not directly call the SMS provider.

Notification events may include:

- SLOT_CONFIRMED
- SLOT_CHANGED
- SLOT_REMINDER
- TOKEN_GENERATED
- CENTRE_DELAY
- CENTRE_REASSIGNED
- PROCUREMENT_COMPLETED
- PAYMENT_INITIATED
- PAYMENT_COMPLETED
- ACTION_REQUIRED

The notification provider must be replaceable through an adapter.

---

# 17. Realtime Integration Rule

Realtime updates use backend-controlled events.

Examples:

- QUEUE_UPDATED
- FARMER_CHECKED_IN
- WEIGHMENT_COMPLETED
- QUALITY_UPDATED
- CENTRE_LOAD_CHANGED
- CENTRE_DELAYED
- SLOT_CHANGED
- PAYMENT_UPDATED

WebSockets may be used for realtime delivery.

The database remains the source of truth.

A lost WebSocket event must not corrupt the underlying transaction.

Clients should be able to refresh/re-fetch current state.

---

# 18. GIS Integration Rule

PostGIS is responsible for geographic operations.

GIS/data services may provide:

- centre coordinates
- farmer/request location
- distance calculations
- geographic filtering
- district/region relationships

Distance must not be calculated independently in multiple
frontend applications.

The backend should provide authoritative distance values used
for recommendation.

---

# 19. Data Integration Rule

Official or authorized data is preferred.

Data sources must be documented.

For every external/official dataset, record:

- source organization
- source URL/API
- fields used
- update frequency
- geographic coverage
- time coverage
- access/license information
- ingestion method

Synthetic/demo data may be used during development when real data
is unavailable.

Synthetic data must be explicitly labelled.

Synthetic data must not be presented as official government data.

---

# 20. AI/ML Data Boundary

AI/ML teams must receive documented data inputs.

Every model interface should define:

- input fields
- output fields
- units
- prediction horizon
- confidence representation
- model version
- timestamp
- fallback behavior

Example:

Input:
quantity, queue_size, throughput, commodity

Output:
estimated_wait_minutes, confidence, model_version

ML services must have a deterministic fallback when the model
is unavailable.

---

# 21. API Contract Rule

All teams must use:

docs/api-contract.md

as the shared API contract.

Before creating a new shared endpoint:

1. Check whether an existing endpoint already solves the requirement.
2. Discuss the requirement with the architecture/integration lead.
3. Update the API contract if required.
4. Implement the endpoint.
5. Add tests.
6. Update consumers if necessary.

No team should silently change a shared API.

---

# 22. Breaking Changes

A breaking change includes:

- removing an endpoint
- changing HTTP method
- changing required request fields
- changing response structure
- changing authentication requirements
- changing workflow semantics
- changing field meaning
- changing units

Breaking changes require:

- architecture review
- affected-team discussion
- contract update
- implementation update
- consumer update
- testing

Prefer backward-compatible changes where possible.

---

# 23. Error Handling

All APIs should return predictable errors.

Frontend applications must not assume every request succeeds.

At minimum, handle:

- 400 Bad Request
- 401 Unauthorized
- 403 Forbidden
- 404 Not Found
- 409 Conflict
- 422 Validation Error
- 500 Internal Server Error
- network timeout/failure

Business errors should use documented error codes.

---

# 24. Authentication and Authorization

Authentication verifies identity.

Authorization verifies permission.

Never treat authentication as authorization.

Example:

A valid centre operator token does NOT automatically grant
access to every procurement centre.

Resource-level authorization must be enforced by the backend.

---

# 25. Sensitive Data Rule

Do not expose unnecessary sensitive information.

Full Aadhaar numbers must not be stored or returned.

Use only the minimum identity information required for the workflow.

Secrets/API keys/passwords must never be committed to Git.

Use environment variables or approved secret management.

---

# 26. Timestamp Rule

All important operational events must record actual timestamps.

Examples:

- check-in time
- weighment time
- quality test time
- bill generation time
- payment initiation time
- payment completion time

Scheduled slot time and actual event time are different concepts.

Do not overwrite a scheduled slot with an actual operational timestamp.

---

# 27. Audit Rule

Important state changes must be auditable.

Audit information should include where appropriate:

- actor
- role
- action
- entity
- previous state
- new state
- timestamp
- request/correlation identifier

Audit records must not be editable through normal frontend workflows.

---

# 28. Service Communication Rule

Services must communicate through documented interfaces.

Do not create hidden dependencies such as:

- direct database access between teams
- undocumented shared files
- hardcoded localhost URLs
- frontend-to-ML direct database access
- frontend-to-SMS direct access

Configuration must use environment variables.

---

# 29. Environment Configuration

Environment-specific values must not be hardcoded.

Examples:

DATABASE_URL
REDIS_URL
JWT_SECRET
SMS_API_KEY
AI_SERVICE_URL

Use:

.env

for local secrets.

Use:

.env.example

for required configuration names without secrets.

---

# 30. Logging and Observability

Services should produce useful logs for:

- API failures
- authentication failures
- workflow errors
- integration failures
- notification failures
- ML failures
- database errors

Never log passwords, API keys, full Aadhaar numbers,
or unnecessary sensitive information.

---

# 31. Team Ownership Boundaries

## Architecture / Integration Lead

Owns:

- architecture
- shared contracts
- integration rules
- cross-team dependencies
- major interface changes
- architecture review
- final resolution of integration conflicts

## Backend + Database

Owns:

- FastAPI
- database
- business rules
- workflow
- authentication APIs
- persistence
- transactional integrity

## Data + GIS

Owns:

- data sources
- data pipelines
- data quality
- geographic data
- PostGIS support
- data dictionary

## AI/ML

Owns:

- model development
- model evaluation
- prediction services
- model versioning
- ML contracts

## Frontend

Owns:

- Farmer Portal
- Operator Portal
- Government Portal
- UI/UX
- API consumption
- client-side validation
- realtime display

## QA + DevOps + Security

Owns:

- automated testing
- integration testing
- CI/CD
- Docker/deployment
- security testing
- API testing
- environment validation

---

# 32. Code Ownership Rule

A developer must not make architectural changes affecting another
team without discussion.

Examples:

Frontend developer should not independently redesign an API.

ML developer should not independently change database schema.

Data developer should not change transactional workflow.

Backend developer should not silently change frontend contracts.

Cross-team changes require coordination.

---

# 33. Git Integration Rule

Development happens through:

feature branch
→ commit
→ push
→ Pull Request
→ code review
→ develop

Main is the stable branch.

No direct development on main.

No direct push to main.

Shared contract changes require appropriate review.

---

# 34. Pull Request Requirements

Every PR should contain:

- clear title
- description of change
- affected module
- related API/contract changes
- tests performed
- known limitations
- screenshots for significant UI changes where useful

Before merging:

- code builds
- tests pass
- no obvious security issue
- API contract remains compatible
- integration impact is understood

---

# 35. Code Review Focus

Architecture lead reviews for:

- architectural consistency
- API compatibility
- integration impact
- business-rule ownership
- security boundaries
- cross-team dependencies

Module owners review for:

- implementation correctness
- maintainability
- tests
- module-specific standards

Not every PR requires the architecture lead to inspect every line.

---

# 36. Definition of Done for Shared Features

A shared feature is not considered complete until:

1. API contract is defined.
2. Backend implementation exists.
3. Database changes are documented.
4. Frontend consumer is compatible.
5. Tests exist.
6. Authentication/authorization is verified.
7. Error cases are handled.
8. Audit requirements are satisfied where applicable.
9. Realtime/notification requirements are handled where applicable.
10. Documentation is updated.

---

# 37. Integration Priority

When there is a conflict between:

Feature Count
and
System Reliability

choose:

System Reliability.

When there is a conflict between:

Demo Complexity
and
Real-world Workability

choose:

Real-world Workability.

When there is a conflict between:

ML prediction
and
Hard business constraints

choose:

Hard business constraints.

---

# 38. Core Engineering Principle

KISANQUEUE is not built as a collection of disconnected features.

It is one coordinated system.

The target flow is:

Farmer
→ Procurement Request
→ Recommendation
→ Slot
→ Token
→ Queue
→ Procurement
→ Quality
→ Bill
→ Payment

with:

Government Visibility
+
Notifications
+
Audit
+
AI/ML Decision Support

around the same backend source of truth.

---

# 39. Final Rule

If a developer is unsure where a piece of logic belongs:

Ask:

"Who owns this decision?"

If it is a transactional/business decision:

Backend.

If it is a prediction:

AI/ML.

If it is presentation:

Frontend.

If it is geographic computation:

GIS/PostGIS/backend.

If it is external communication:

Integration/adapter layer.

If it is security authorization:

Backend/security layer.

If it affects multiple teams:

Architecture/integration review.