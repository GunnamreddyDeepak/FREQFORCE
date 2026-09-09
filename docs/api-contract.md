# KISANQUEUE API Contract

## Version

v1.0

## Purpose

This document defines the API contract between KISANQUEUE portals,
backend services, AI/ML services, database services, notification services,
and external integrations.

The backend is the single source of truth.

Frontend applications must not directly access the database.

---

# 1. API Base

Development:

/api/v1

Example:

http://localhost:8000/api/v1

Production URL will be configured separately.

---

# 2. Authentication

Authentication mechanism:

JWT-based authentication.

Every protected API must validate:

- JWT token
- User identity
- User role
- Resource ownership
- Permission for requested operation

Roles:

- FARMER
- CENTRE_OPERATOR
- GOVERNMENT

---

# 3. Standard Response Principles

Successful responses must return JSON.

Errors must return a consistent structure.

Example:

{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Quantity must be greater than zero"
  }
}

---

# 4. Authentication APIs

## POST /api/v1/auth/login

Purpose:

Authenticate a user and return an access token.

Request:

{
  "mobile": "string",
  "password": "string"
}

Response:

{
  "access_token": "string",
  "token_type": "bearer",
  "user": {
    "user_id": "uuid",
    "role": "FARMER"
  }
}

Allowed roles:

FARMER
CENTRE_OPERATOR
GOVERNMENT

---

# 5. Farmer APIs

## POST /api/v1/procurement-requests

Purpose:

Create a new farmer procurement request.

Role:

FARMER

Request:

{
  "commodity_id": "uuid",
  "quantity_qtl": 70,
  "preferred_date": "2026-09-12",
  "preferred_start_time": "09:30",
  "preferred_end_time": "11:30"
}

Validation:

- commodity_id must exist
- quantity_qtl must be greater than 0
- preferred date must be valid
- preferred start time must be before end time
- farmer must be authenticated

Response:

{
  "request_id": "uuid",
  "status": "REQUESTED"
}

---

## GET /api/v1/procurement-requests/{request_id}

Purpose:

Retrieve procurement request status.

Roles:

- FARMER
- CENTRE_OPERATOR
- GOVERNMENT

Access rules:

- Farmer can access only their own request.
- Centre operator can access requests assigned to their centre.
- Government can access authorized district/network requests.

Response:

{
  "request_id": "uuid",
  "commodity_id": "uuid",
  "quantity_qtl": 70,
  "preferred_date": "2026-09-12",
  "preferred_start_time": "09:30",
  "preferred_end_time": "11:30",
  "status": "REQUESTED"
}

---

# 6. Centre Recommendation APIs

## POST /api/v1/recommendations

Purpose:

Recommend the most suitable procurement centre for a farmer request.

Role:

FARMER

The recommendation process must evaluate feasibility before ranking.

Evaluation order:

1. Centre operational status
2. Commodity compatibility
3. Capacity feasibility
4. Predicted queue/ETA
5. Distance
6. Overall score

The recommendation engine may use:

- deterministic rules
- demand prediction
- ETA prediction
- capacity information
- geographic distance

ML predictions must not override hard business constraints.

Request:

{
  "request_id": "uuid"
}

Response:

{
  "request_id": "uuid",
  "recommended_centre": {
    "centre_id": "uuid",
    "name": "North Procurement Centre",
    "distance_km": 5.4,
    "estimated_wait_minutes": 12,
    "projected_utilization_percent": 48
  },
  "alternatives": [
    {
      "centre_id": "uuid",
      "name": "South Procurement Centre",
      "distance_km": 21.5,
      "estimated_wait_minutes": 78,
      "projected_utilization_percent": 68
    }
  ],
  "reason": "Recommended because the centre has sufficient capacity and lower predicted queue pressure."
}

---

# 7. Slot APIs

## POST /api/v1/slots

Purpose:

Confirm a procurement slot.

Role:

FARMER

Request:

{
  "request_id": "uuid",
  "centre_id": "uuid",
  "slot_start": "2026-09-12T09:30:00",
  "slot_end": "2026-09-12T11:30:00"
}

Backend must verify:

- request belongs to authenticated farmer
- centre is operational
- commodity is accepted
- capacity is available
- slot is valid
- request has not already been confirmed

Response:

{
  "slot_id": "uuid",
  "request_id": "uuid",
  "centre_id": "uuid",
  "slot_start": "2026-09-12T09:30:00",
  "slot_end": "2026-09-12T11:30:00",
  "status": "CONFIRMED"
}

---

# 8. Token APIs

## POST /api/v1/tokens

Purpose:

Generate a procurement token after slot confirmation.

Role:

FARMER

Request:

{
  "slot_id": "uuid"
}

Response:

{
  "token_id": "uuid",
  "token_number": "KQ-143",
  "status": "ACTIVE"
}

Token generation must happen through the backend.

Frontend must not generate token numbers.

---

## GET /api/v1/tokens/{token_id}

Purpose:

Retrieve token and current status.

Roles:

- FARMER
- CENTRE_OPERATOR
- GOVERNMENT

Response:

{
  "token_id": "uuid",
  "token_number": "KQ-143",
  "status": "ACTIVE",
  "centre_id": "uuid",
  "slot_start": "2026-09-12T09:30:00",
  "slot_end": "2026-09-12T11:30:00"
}

---

# 9. Queue APIs

## GET /api/v1/queue/{centre_id}

Purpose:

Retrieve the current operational queue for a procurement centre.

Roles:

- CENTRE_OPERATOR
- GOVERNMENT

Farmer-specific queue information should be exposed through
farmer-authorized endpoints only.

Response:

{
  "centre_id": "uuid",
  "queue_size": 12,
  "estimated_wait_minutes": 35,
  "status": "NORMAL",
  "last_updated": "2026-09-12T09:45:00Z"
}

Important:

Queue position is operational information.

Estimated waiting time is a prediction and is not a guaranteed waiting time.

---

# 10. Operator APIs

## POST /api/v1/queue/check-in

Purpose:

Check a farmer/token into the procurement centre.

Role:

CENTRE_OPERATOR

Request:

{
  "token_id": "uuid"
}

Response:

{
  "queue_entry_id": "uuid",
  "token_id": "uuid",
  "status": "CHECKED_IN",
  "checked_in_at": "2026-09-12T09:42:00Z"
}

---

## POST /api/v1/weighments

Purpose:

Record actual procurement quantity.

Role:

CENTRE_OPERATOR

Request:

{
  "token_id": "uuid",
  "actual_quantity_qtl": 68.5
}

Response:

{
  "weighment_id": "uuid",
  "actual_quantity_qtl": 68.5,
  "status": "COMPLETED"
}

---

## POST /api/v1/quality-tests

Purpose:

Record quality test results.

Role:

CENTRE_OPERATOR

Request:

{
  "token_id": "uuid",
  "quality_grade": "A",
  "quality_parameters": {}
}

Response:

{
  "quality_test_id": "uuid",
  "quality_grade": "A",
  "status": "COMPLETED"
}

---

# 11. Rate and Billing APIs

## GET /api/v1/procurement-rates

Purpose:

Retrieve the applicable configured procurement rate.

Roles:

- CENTRE_OPERATOR
- GOVERNMENT

The frontend must never hardcode procurement rates.

Rate calculation/configuration belongs to the backend.

---

## POST /api/v1/bills

Purpose:

Generate a procurement bill.

Role:

CENTRE_OPERATOR

Request:

{
  "token_id": "uuid"
}

Backend calculates:

actual quantity
×
applicable configured rate

Response:

{
  "bill_id": "uuid",
  "token_id": "uuid",
  "quantity_qtl": 68.5,
  "rate_per_qtl": 2183,
  "total_amount": 149535.50,
  "status": "GENERATED"
}

---

# 12. Payment APIs

## GET /api/v1/payments/{bill_id}

Purpose:

Retrieve payment status.

Roles:

- FARMER
- CENTRE_OPERATOR
- GOVERNMENT

Possible states:

- PENDING
- INITIATED
- PROCESSING
- COMPLETED
- FAILED

Response:

{
  "payment_id": "uuid",
  "bill_id": "uuid",
  "amount": 149535.50,
  "status": "COMPLETED",
  "updated_at": "2026-09-12T12:30:00Z"
}

Important:

The prototype may simulate payment status.

No live PFMS/NPCI/bank integration may be claimed unless an actual authorized integration exists.

---

# 13. Government APIs

## GET /api/v1/government/centres

Purpose:

Retrieve authorized procurement centre operational information.

Role:

GOVERNMENT

Response may include:

- centre status
- capacity
- current load
- queue size
- throughput
- predicted demand
- predicted utilization
- exceptions

---

## GET /api/v1/government/forecasts

Purpose:

Retrieve demand and overload predictions.

Role:

GOVERNMENT

Response:

{
  "centre_id": "uuid",
  "forecast_quantity_qtl": 850,
  "overload_probability": 0.82,
  "risk_level": "HIGH",
  "model_version": "baseline-v1"
}

ML output is advisory.

Hard operational decisions remain governed by deterministic rules.

---

# 14. Exception APIs

## GET /api/v1/exceptions

Purpose:

Retrieve operational exceptions.

Roles:

- CENTRE_OPERATOR
- GOVERNMENT

Possible exception types:

- CENTRE_FULL
- CENTRE_DELAYED
- FARMER_NO_SHOW
- QUALITY_EXCEPTION
- WEIGHMENT_EXCEPTION
- PAYMENT_FAILED
- SYSTEM_ERROR

---

# 15. Notification APIs

## GET /api/v1/notifications

Purpose:

Retrieve notifications for the authenticated user.

Roles:

- FARMER
- CENTRE_OPERATOR
- GOVERNMENT

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

SMS delivery must happen through the backend Notification Service.

Frontend must not directly call the SMS provider.

---

# 16. Audit APIs

## GET /api/v1/audit-logs

Purpose:

Retrieve authorized audit records.

Role:

GOVERNMENT

Important operations must be audited.

Examples:

- request creation
- slot confirmation
- token generation
- check-in
- weighment
- quality update
- bill generation
- payment state change
- centre reassignment
- exception resolution

---

# 17. Error Codes

Standard error codes:

- INVALID_REQUEST
- UNAUTHORIZED
- FORBIDDEN
- NOT_FOUND
- CONFLICT
- CAPACITY_UNAVAILABLE
- CENTRE_UNAVAILABLE
- COMMODITY_NOT_ACCEPTED
- SLOT_UNAVAILABLE
- INVALID_STATE_TRANSITION
- PAYMENT_FAILED
- INTERNAL_ERROR

HTTP status codes should follow normal REST semantics.

---

# 18. Workflow State Rules

Procurement request lifecycle:

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

Exceptions may interrupt the normal lifecycle.

Possible exceptions:

- SLOT_CHANGED
- CENTRE_DELAYED
- CENTRE_FULL
- FARMER_NO_SHOW
- QUALITY_EXCEPTION
- WEIGHMENT_EXCEPTION
- PAYMENT_FAILED
- CANCELLED
- SYSTEM_ERROR

The frontend must never directly modify workflow states.

All critical transitions must be validated and authorized by the backend.

---

# 19. API Design Rules

1. Backend is the single source of truth.

2. Frontend applications must communicate through APIs.

3. Frontend must not access PostgreSQL directly.

4. Frontend must not contain authoritative business rules.

5. Procurement rates must not be hardcoded in frontend code.

6. ML predictions must be treated as predictions, not authoritative decisions.

7. Hard constraints must be enforced by backend rules.

8. Authentication and authorization are mandatory for protected endpoints.

9. Users may access only resources permitted by their role.

10. Critical workflow transitions must be validated by the backend.

11. Important operations must create audit records.

12. API changes must be discussed before breaking existing consumers.

13. Breaking API changes require a contract/version review.

14. All timestamps exchanged through APIs should use ISO 8601 format.

15. Monetary values must use decimal-safe representations.

16. Quantity must be represented explicitly in quintals where applicable.

17. Sensitive identity information must not be unnecessarily exposed through APIs.

18. Full Aadhaar numbers must not be stored or returned by APIs.

---

# 20. API Ownership

Backend Team:

- Implements API endpoints
- Validates requests
- Enforces business rules
- Handles authentication/authorization
- Persists data
- Maintains API documentation

Frontend Team:

- Consumes APIs
- Displays API results
- Handles loading/error states
- Does not duplicate authoritative business logic

Data/GIS Team:

- Provides normalized centre/geographic data
- Defines GIS-related data requirements
- Supports distance and geographic queries

AI/ML Team:

- Provides predictions through defined ML interfaces
- Provides model version and confidence where applicable
- Does not directly modify transactional procurement state

QA/DevOps/Security:

- Tests APIs
- Validates authorization
- Tests failure cases
- Validates deployment configuration
- Monitors API reliability

Architecture / Integration Lead:

- Owns API contract
- Resolves cross-team API conflicts
- Reviews breaking changes
- Approves major interface changes

---

# 21. Contract Change Process

Before changing an API:

1. Identify affected teams.
2. Discuss the change.
3. Update this document.
4. Update related schemas/contracts.
5. Update implementation.
6. Update tests.
7. Review the pull request.
8. Merge only after affected consumers are compatible.

No team should silently change a shared API contract.

---

# 22. Initial Vertical Slice

The first end-to-end transaction should support:

Farmer Login
→ Create Procurement Request
→ Centre Recommendation
→ Slot Confirmation
→ Token Generation

The backend must persist the transaction.

This vertical slice is the first integration milestone before implementing the complete queue/procurement/payment workflow.