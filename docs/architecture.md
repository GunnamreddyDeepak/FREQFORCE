# KISANQUEUE V2 — System Architecture

## 1. Purpose

KISANQUEUE is an intelligent procurement-centre orchestration platform designed to reduce farmer waiting time, improve procurement-centre capacity utilization, provide operational visibility, and support cross-centre workload balancing.

The system is not merely a farmer booking application.

Its core responsibility is to coordinate:

- farmer procurement demand
- centre capacity
- procurement workflow
- queue state
- predicted processing time
- centre workload
- operational exceptions
- procurement and payment status

Core operating loop:

Predict → Schedule → Balance → Process → Track → Resolve

---

## 2. Architecture Principles

### 2.1 Backend is the source of truth

All authoritative business state is maintained by the backend and PostgreSQL.

Frontend applications must never directly modify the database.

Frontend applications communicate only through versioned backend APIs.

---

### 2.2 ML predicts, rules decide

Machine learning may provide predictions such as:

- demand forecast
- processing-time estimate
- queue ETA
- overload probability
- anomaly signals

ML predictions must not override hard business constraints.

Deterministic rules control:

- eligibility
- centre operational status
- commodity compatibility
- hard capacity limits
- authorization
- workflow transitions
- procurement rules
- quality/rate rules
- payment state transitions
- audit requirements

---

### 2.3 Feasibility before optimization

A centre must first be proven feasible before it participates in recommendation scoring.

Recommendation order:

1. Eligibility
2. Operational status
3. Commodity compatibility
4. Hard capacity feasibility
5. Predicted processing/ETA
6. Distance
7. Explainable score

An infeasible centre must never be selected merely because it has a high ranking score.

---

### 2.4 PostgreSQL is authoritative

PostgreSQL stores authoritative operational state.

Redis/WebSockets may be used for realtime delivery and caching but must not become the system of record.

---

### 2.5 Every operational transition is auditable

Important operational actions generate immutable events.

Examples:

- request created
- slot confirmed
- token generated
- farmer checked in
- weighing completed
- quality recorded
- bill generated
- payment state changed
- centre delay reported
- reassignment performed

---

## 3. High-Level Architecture

```text
                         KISANQUEUE V2
                              |
          +-------------------+-------------------+
          |                   |                   |
          v                   v                   v
   FARMER PORTAL       OPERATOR PORTAL      GOVERNMENT TOWER
          |                   |                   |
          +-------------------+-------------------+
                              |
                              v
                       FASTAPI BACKEND
                              |
          +-------------------+-------------------+
          |                   |                   |
          v                   v                   v
   PROCUREMENT SERVICE   DECISION ENGINE    WORKFLOW ENGINE
                              |                   |
                    +---------+---------+         |
                    |                   |         |
                    v                   v         |
                   ML                 RULES       |
              PREDICTIONS         ENFORCEMENT     |
                    |                   |         |
                    +---------+---------+---------+
                              |
                              v
                    POSTGRESQL + POSTGIS
                       SOURCE OF TRUTH
                              |
               +--------------+--------------+
               |              |              |
               v              v              v
             REDIS       AUDIT/EVENT LOG   EXTERNAL
          / WEBSOCKETS                     ADAPTERS
               |                             |
               v                     +-------+-------+
          REALTIME EVENTS             |       |       |
               |                     SMS   PAYMENT  GOV APIs
               v
        NOTIFICATION SERVICE