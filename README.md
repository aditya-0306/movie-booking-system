# 🎬 Movie Ticket Booking Backend

A production-style movie ticket booking API built with **FastAPI, PostgreSQL, and Redis** — designed around the classic backend interview problem: guaranteeing that two users can never book the same seat, even under simultaneous concurrent requests.

This isn't a CRUD tutorial clone. The system is built around a layered architecture (routers → services → repositories → models) and demonstrates real backend engineering concerns: concurrency-safe transactions, JWT refresh token rotation, role-based authorization, Redis caching, and global rate limiting.

---

## 🌐 Live Demo

Try it live: **https://movie-booking-system-53u1.onrender.com/docs**

⚠️ Hosted on a free tier — the first request may take 30-60 seconds to wake up if it's been idle. Use the **Authorize** button in Swagger to log in and test protected endpoints directly in the browser.

---

## ✨ Features

- **JWT authentication** with short-lived access tokens + rotating refresh tokens (a stolen refresh token is only usable once)
- **Role-based authorization** — admin vs customer, enforced via a reusable dependency
- **Concurrency-safe seat booking** — a database-level constraint guarantees no double-booking is possible, even under real simultaneous requests (see below)
- **All-or-nothing multi-seat booking** — booking 3 seats either reserves all 3 or none, never a partial/confusing booking
- **Mock payment gateway** — simulates success/failure, correctly releases the seat when payment fails
- **Redis caching** — movie listings and show details, cache-aside pattern with explicit invalidation on writes
- **Global rate limiting** — Redis sliding-window algorithm, applied as middleware across every route
- **Pagination, filtering, and search** on movies and shows
- **Global exception handling** — consistent JSON error format across the whole API
- **Request logging middleware**
- **Alembic migrations** — schema is version-controlled, not just `create_all()`
- **Fully containerized** — one command spins up the API, PostgreSQL, and Redis together

---

## 🏗️ Architecture

```
routers/       -> HTTP layer only: parses requests, calls services, returns responses
services/      -> business rules and orchestration
repositories/  -> data access layer, isolates all raw SQLAlchemy queries
models/        -> SQLAlchemy ORM models
schemas/       -> Pydantic request/response contracts
middleware/    -> logging, rate limiting, global exception handling
dependencies/  -> reusable FastAPI dependencies (auth, pagination)
```

Each layer only talks to the layer directly below it — routers never touch the database directly, and services never build HTTP responses. This keeps business logic testable independently of the web framework.

---

## 🔒 The Core Engineering Decision: Preventing Double-Booking

This is the single most important design choice in the project, and the one worth understanding in depth.

**The naive approach** — check if a seat is booked, then insert a booking if it's free — has a race condition: two requests can both pass the "is it free?" check before either one commits its booking.

**A common "fix"** is `SELECT ... FOR UPDATE` to lock the seat row before booking it. But this has a subtle gap: **row locking only works on rows that already exist.** The very first booking attempt for a seat has no existing row to lock, so two simultaneous *first* attempts can still both slip through.

**The actual fix used here:** a **partial unique index** on the `bookings` table:

```sql
CREATE UNIQUE INDEX uq_active_booking_per_seat_per_show
ON bookings (show_id, seat_id)
WHERE status != 'cancelled';
```

This tells PostgreSQL itself: *never allow two non-cancelled booking rows for the same seat on the same show — no exceptions, no timing gaps.* When two requests race to book the same seat, PostgreSQL guarantees exactly one `INSERT` succeeds and the other raises an `IntegrityError`, which the booking service catches and turns into a clean `409 Conflict`. The database becomes the single source of truth for seat availability, not application code that can have timing bugs.

This is proven under real concurrent load in `tests/load_test_booking.py` — see the Testing section below.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| API Framework | FastAPI |
| Database | PostgreSQL + SQLAlchemy 2.0 |
| Migrations | Alembic |
| Cache / Rate Limiter | Redis |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Containerization | Docker + docker-compose |
| Testing | pytest + httpx (async concurrency load testing) |

---

## 🚀 Getting Started

### Prerequisites
- Docker & Docker Compose installed

### Run it

```bash
git clone https://github.com/aditya-0306/movie-booking-system.git
cd movie-booking-system
cp .env.example .env
docker-compose up --build
```

The API will be live at **http://localhost:8001**
Interactive API docs (Swagger UI): **http://localhost:8001/docs**

> **Note:** this project's ports are intentionally offset (API `8001`, Postgres `5433`, Redis `6380`) so it can run at the same time as the URL Shortener project (`8000`/`5432`/`6379`) on the same machine without conflicts. Just run `docker-compose up --build` in both project folders — each has its own isolated containers and database.

### Authenticating in Swagger UI
Click the **Authorize** button and log in with your email/password directly there — under the hood this calls a dedicated `/auth/token` endpoint built for Swagger's OAuth2 flow (kept separate from the regular JSON `/auth/login` used by real API clients). Once authorized, Swagger automatically attaches your token to every "Try it out" request. Use an **admin** account to test admin-only endpoints like creating movies or theatres.

### Apply database migrations
The app auto-creates tables on first boot for convenience, but the "real" schema history lives in Alembic. To apply migrations explicitly (recommended once containers are up):
```bash
docker-compose exec api alembic upgrade head
```

---

## 📖 API Overview

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| POST | `/auth/register` | Register a customer account | No |
| POST | `/auth/register-admin` | Register an admin (requires bootstrap secret) | No |
| POST | `/auth/login` | Login, returns access + refresh token | No |
| POST | `/auth/refresh` | Rotate refresh token for a new pair | No |
| GET/POST/PUT/DELETE | `/movies` | Movie catalog (mutations admin-only) | Mixed |
| GET/POST/PUT/DELETE | `/theatres` | Theatre management | Mixed |
| POST | `/screens` | Create a screen under a theatre | Admin |
| POST | `/screens/{id}/seats/generate` | Bulk-generate a seat grid | Admin |
| GET/POST/PUT/DELETE | `/shows` | Show scheduling | Mixed |
| GET | `/shows/{id}/seats` | Real-time seat availability | No |
| POST | `/bookings` | Book one or more seats (concurrency-safe) | Yes |
| GET | `/bookings/me` | Booking history | Yes |
| POST | `/bookings/{id}/cancel` | Cancel a booking, frees the seat | Yes |
| POST | `/payments` | Mock payment (supports simulated failure) | Yes |

Full request/response examples are in the Postman collection at `postman/Movie_Booking_API.postman_collection.json`.

---

## 🧪 Testing

### Functional tests
```bash
pytest tests/test_api.py -v
```
Covers auth, role enforcement, the full booking→payment→cancel lifecycle, and payment failure correctly releasing the seat.

### Concurrency proof (the important one)
```bash
python tests/load_test_booking.py
```
Fires 15 simultaneous booking requests, from 15 different users, at the exact same seat. Expected result: **exactly 1 succeeds, 14 correctly rejected with 409** — proving the double-booking guarantee holds under real concurrent load, not just sequential testing.

**Verified output (ran locally via `tests/load_test_booking.py`):**
```
Total concurrent requests: 15
Successful bookings (201): 1
Correctly rejected (409):  14
Unexpected status codes:   0 -> []

✅ PASS: Exactly one booking succeeded. No double-booking occurred under concurrent load.
```

---

## 🎯 Other Key Engineering Decisions

- **Refresh tokens are stored hashed**, not in plaintext — mirrors how passwords are handled, so a leaked database dump doesn't hand out usable tokens directly.
- **Refresh token rotation**: each refresh token is single-use. Using an old, already-rotated token is rejected, limiting the damage window of a stolen token.
- **All-or-nothing batch booking**: reserving multiple seats happens inside one transaction with per-seat savepoints — if any seat in the batch is taken, the entire batch rolls back rather than leaving the user with a confusing partial booking.
- **Cache invalidation over cache updates**: writes invalidate the relevant cache keys rather than trying to patch cached data in place — simpler to reason about correctly.
- **Admin accounts require a bootstrap secret**, not open self-registration, since public admin signup would be a critical security flaw.

---

## 📌 Possible Future Improvements

- Seat-hold with auto-expiry (reserve a seat for 10 minutes during checkout, auto-release if payment isn't completed)
- Real payment gateway integration (Stripe/Razorpay) behind the same interface
- WebSocket-based live seat-map updates
- Admin analytics dashboard (revenue, occupancy rates)

---

## 📄 License

MIT
