# KISANQUEUE V2 — Realtime Events Contract

## 1. Purpose

This document defines the realtime event contract used by KISANQUEUE V2.

Realtime communication is used to notify connected clients about operational changes without requiring continuous polling.

Primary technologies:

- FastAPI
- WebSockets
- Redis Pub/Sub or equivalent event broker

PostgreSQL remains the authoritative source of truth.

---

# 2. Core Principle

```text
Operational Action
       ↓
FastAPI Backend
       ↓
PostgreSQL
       ↓
Operational Event
       ↓
Redis
       ↓
WebSocket
       ↓
Authorized Client