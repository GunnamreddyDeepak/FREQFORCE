# KISANQUEUE V2 — API Contract

## 1. Contract Status

Version:

`v2.0`

Status:

`FOUNDATION CONTRACT`

Base path:

`/api/v1`

The API version remains `/v1` for backward compatibility while the internal architecture is upgraded to KISANQUEUE V2.

Breaking API changes require a new API version.

---

# 2. Core API Principles

1. Backend is the single source of truth.
2. Frontends never access PostgreSQL directly.
3. All business rules are enforced server-side.
4. Authentication and authorization are enforced server-side.
5. ML predictions cannot override hard constraints.
6. Financial calculations are performed by the backend.
7. Workflow transitions are controlled by the backend.
8. Retryable mutations support idempotency.
9. Realtime events supplement REST APIs.
10. Errors use stable machine-readable error codes.

---

# 3. Roles

Initial roles:

```text
FARMER
CENTRE_OPERATOR
GOVERNMENT