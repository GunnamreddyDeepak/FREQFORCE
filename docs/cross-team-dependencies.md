# KISANQUEUE Cross-Team Dependency Matrix

## Version

v1.0

## Purpose

This document defines the dependencies and interfaces between
KISANQUEUE development teams.

The objective is to prevent teams from developing isolated modules
that cannot integrate with the overall system.

---

# 1. Team Structure

KISANQUEUE has six development responsibilities:

| Team | Responsibility |
|---|---|
| Architecture / Integration | Architecture, contracts, coordination, review |
| Backend + Database | APIs, business rules, persistence |
| Data + GIS | Data sources, pipelines, geographic operations |
| AI/ML | Prediction models and ML services |
| Frontend | Farmer, Operator, Government portals |
| QA + DevOps + Security | Testing, deployment, security, CI/CD |

---

# 2. High-Level Dependency Flow

```text
                    Architecture
                         │
                  Contracts / Rules
                         │
        ┌────────────────┼────────────────┐
        ↓                ↓                ↓
     Backend           Data             Frontend
        │                │                │
        │                ↓                │
        ├─────────────── ML ←─────────────┤
        │
        ├──────── Notification
        │
        ├──────── Payment Integration
        │
        ↓
       QA / DevOps / Security