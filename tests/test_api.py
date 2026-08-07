"""
Basic test suite covering signup/login, movie CRUD, and the booking +
payment flow. Run with the API up:
    pytest tests/test_api.py -v
"""

import httpx
import pytest
import random
import string

BASE_URL = "http://localhost:8001"
ADMIN_SECRET = "change-this-secret-for-creating-admin-accounts"  # matches .env.example


def _random_email(prefix: str) -> str:
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"{prefix}_{suffix}@example.com"


@pytest.fixture
def client():
    return httpx.Client(base_url=BASE_URL, timeout=10)


@pytest.fixture
def admin_token(client):
    email = _random_email("admin")
    client.post(
        "/auth/register-admin",
        json={"name": "Admin", "email": email, "password": "adminpass123", "admin_secret": ADMIN_SECRET},
    )
    resp = client.post("/auth/login", json={"email": email, "password": "adminpass123"})
    return resp.json()["access_token"]


@pytest.fixture
def customer_token(client):
    email = _random_email("customer")
    client.post("/auth/register", json={"name": "Customer", "email": email, "password": "custpass123"})
    resp = client.post("/auth/login", json={"email": email, "password": "custpass123"})
    return resp.json()["access_token"]


def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200


def test_customer_signup_and_login(client):
    email = _random_email("newuser")
    resp = client.post("/auth/register", json={"name": "New User", "email": email, "password": "pass12345"})
    assert resp.status_code == 201
    assert resp.json()["role"] == "customer"

    login_resp = client.post("/auth/login", json={"email": email, "password": "pass12345"})
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()
    assert "refresh_token" in login_resp.json()


def test_admin_registration_requires_correct_secret(client):
    email = _random_email("fakeadmin")
    resp = client.post(
        "/auth/register-admin",
        json={"name": "Fake Admin", "email": email, "password": "pass12345", "admin_secret": "wrong-secret"},
    )
    assert resp.status_code == 403


def test_refresh_token_rotation(client):
    email = _random_email("refreshuser")
    client.post("/auth/register", json={"name": "Refresh User", "email": email, "password": "pass12345"})
    login_resp = client.post("/auth/login", json={"email": email, "password": "pass12345"})
    old_refresh = login_resp.json()["refresh_token"]

    refresh_resp = client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert refresh_resp.status_code == 200
    assert "access_token" in refresh_resp.json()

    # Using the same (now-rotated) refresh token again must fail
    reuse_resp = client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert reuse_resp.status_code == 401


def test_movie_crud_requires_admin(client, admin_token, customer_token):
    # Customer cannot create a movie
    resp = client.post(
        "/movies",
        json={"title": "Test Movie", "duration_minutes": 120, "genre": "Action", "language": "English"},
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert resp.status_code == 403

    # Admin can
    resp = client.post(
        "/movies",
        json={"title": "Test Movie", "duration_minutes": 120, "genre": "Action", "language": "English"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    movie_id = resp.json()["id"]

    # Anyone can read
    get_resp = client.get(f"/movies/{movie_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "Test Movie"


def test_full_booking_and_payment_flow(client, admin_token, customer_token):
    # Set up: movie -> theatre -> screen -> seats -> show
    movie_resp = client.post(
        "/movies",
        json={"title": "Booking Flow Movie", "duration_minutes": 100, "genre": "Drama", "language": "English"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    movie_id = movie_resp.json()["id"]

    theatre_resp = client.post(
        "/theatres",
        json={"name": "Test Theatre", "city": "Testville"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    theatre_id = theatre_resp.json()["id"]

    screen_resp = client.post(
        "/screens",
        json={"theatre_id": theatre_id, "name": "Screen 1"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    screen_id = screen_resp.json()["id"]

    seats_resp = client.post(
        f"/screens/{screen_id}/seats/generate",
        json={"rows": 2, "seats_per_row": 4, "premium_rows": 1},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert seats_resp.status_code == 201
    seat_id = seats_resp.json()[0]["id"]

    show_resp = client.post(
        "/shows",
        json={"movie_id": movie_id, "screen_id": screen_id, "show_time": "2026-12-25T18:00:00Z", "price": "250.00"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert show_resp.status_code == 201
    show_id = show_resp.json()["id"]

    # Book the seat
    booking_resp = client.post(
        "/bookings",
        json={"show_id": show_id, "seat_ids": [seat_id]},
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert booking_resp.status_code == 201
    booking_id = booking_resp.json()["bookings"][0]["id"]
    assert booking_resp.json()["bookings"][0]["status"] == "pending"

    # Seat should now show as unavailable
    availability_resp = client.get(f"/shows/{show_id}/seats")
    seat_status = next(s for s in availability_resp.json() if s["seat_id"] == seat_id)
    assert seat_status["is_available"] is False

    # A second attempt to book the SAME seat must be rejected
    duplicate_resp = client.post(
        "/bookings",
        json={"show_id": show_id, "seat_ids": [seat_id]},
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert duplicate_resp.status_code == 409

    # Pay for it successfully
    payment_resp = client.post(
        "/payments",
        json={"booking_id": booking_id, "simulate_failure": False},
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert payment_resp.status_code == 201
    assert payment_resp.json()["status"] == "success"

    # Cancel it, which should free the seat again
    cancel_resp = client.post(f"/bookings/{booking_id}/cancel", headers={"Authorization": f"Bearer {customer_token}"})
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"

    availability_resp_2 = client.get(f"/shows/{show_id}/seats")
    seat_status_2 = next(s for s in availability_resp_2.json() if s["seat_id"] == seat_id)
    assert seat_status_2["is_available"] is True


def test_payment_failure_releases_seat(client, admin_token, customer_token):
    movie_resp = client.post(
        "/movies",
        json={"title": "Failure Test Movie", "duration_minutes": 90, "genre": "Comedy", "language": "English"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    movie_id = movie_resp.json()["id"]
    theatre_resp = client.post(
        "/theatres", json={"name": "Fail Theatre", "city": "Failtown"}, headers={"Authorization": f"Bearer {admin_token}"}
    )
    screen_resp = client.post(
        "/screens",
        json={"theatre_id": theatre_resp.json()["id"], "name": "Screen F"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    screen_id = screen_resp.json()["id"]
    seats_resp = client.post(
        f"/screens/{screen_id}/seats/generate",
        json={"rows": 1, "seats_per_row": 2, "premium_rows": 0},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    seat_id = seats_resp.json()[0]["id"]
    show_resp = client.post(
        "/shows",
        json={"movie_id": movie_id, "screen_id": screen_id, "show_time": "2026-12-26T18:00:00Z", "price": "200.00"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    show_id = show_resp.json()["id"]

    booking_resp = client.post(
        "/bookings",
        json={"show_id": show_id, "seat_ids": [seat_id]},
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    booking_id = booking_resp.json()["bookings"][0]["id"]

    payment_resp = client.post(
        "/payments",
        json={"booking_id": booking_id, "simulate_failure": True},
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert payment_resp.json()["status"] == "failed"

    # Seat should be free again since the booking was auto-cancelled
    availability_resp = client.get(f"/shows/{show_id}/seats")
    seat_status = next(s for s in availability_resp.json() if s["seat_id"] == seat_id)
    assert seat_status["is_available"] is True
