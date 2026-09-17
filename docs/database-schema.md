# KISANQUEUE V2 — Database Schema

## 1. Purpose

This document defines the authoritative relational data model for KISANQUEUE V2.

Database:

- PostgreSQL
- PostGIS extension for geospatial operations

PostgreSQL is the source of truth for operational state.

Application clients must never access PostgreSQL directly.

---

# 2. Design Principles

## 2.1 Relational source of truth

Operational entities are stored in normalized relational tables.

## 2.2 UUID primary identifiers

Externally exposed business entities should use UUID identifiers.

Examples:

- user_id
- farmer_id
- centre_id
- procurement_request_id
- slot_id
- token_id
- bill_id
- payment_id

## 2.3 Auditability

Important state changes must generate records in the operational event/audit system.

## 2.4 Idempotency

Operations that may be retried because of:

- network failure
- offline synchronization
- QR scanning
- API retries
- client timeout

must support idempotency.

## 2.5 Historical integrity

Operational records must not be silently overwritten when doing so would destroy historical truth.

For example:

- original requested quantity
- accepted quantity
- actual weighed quantity
- original slot
- changed slot
- payment transitions

must remain traceable.

---

# 3. Entity Overview

```text
USERS
  |
  +---- FARMERS
  |
  +---- CENTRE_OPERATORS
  |
  +---- GOVERNMENT_USERS

PROCUREMENT_CENTRES
  |
  +---- CENTRE_COMMODITIES
  |
  +---- CENTRE_CAPACITY
  |
  +---- SLOTS
  |
  +---- QUEUE_ENTRIES
  |
  +---- PROCUREMENT_REQUESTS
              |
              +---- TOKENS
              |
              +---- WEIGHMENTS
              |
              +---- QUALITY_TESTS
              |
              +---- BILLS
              |
              +---- PAYMENTS
              |
              +---- EXCEPTIONS
              |
              +---- NOTIFICATIONS
              |
              +---- OPERATIONAL_EVENTS

COMMODITIES
  |
  +---- PROCUREMENT_RATES

ML_PREDICTIONS