"""
The single most important test in this project.

Fires many simultaneous booking requests at the SAME seat for the SAME show,
from different users, all at once. If the concurrency-safety design (the
partial unique index on bookings) is working correctly, EXACTLY ONE request
should succeed and every other one should get a clean 409 Conflict -- never
two successful bookings for the same seat.

Run with the API already up:
    python tests/load_test_booking.py
"""

import asyncio
import random
import string
import httpx

BASE_URL = "http://localhost:8001"
ADMIN_SECRET = "change-this-secret-for-creating-admin-accounts"
CONCURRENT_USERS = 15


def _random_email(prefix: str) -> str:
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"{prefix}_{suffix}@example.com"


async def setup_show_and_seat(client: httpx.AsyncClient) -> tuple[int, int]:
    """Creates a movie, theatre, screen, one seat, and one show. Returns (show_id, seat_id)."""
    admin_email = _random_email("loadtest_admin")
    await client.post(
        "/auth/register-admin",
        json={"name": "Load Test Admin", "email": admin_email, "password": "adminpass123", "admin_secret": ADMIN_SECRET},
    )
    login = await client.post("/auth/login", json={"email": admin_email, "password": "adminpass123"})
    admin_token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    movie = await client.post(
        "/movies",
        json={"title": "Concurrency Test Movie", "duration_minutes": 120, "genre": "Action", "language": "English"},
        headers=headers,
    )
    theatre = await client.post("/theatres", json={"name": "Load Test Theatre", "city": "Loadtown"}, headers=headers)
    screen = await client.post(
        "/screens", json={"theatre_id": theatre.json()["id"], "name": "Screen LT"}, headers=headers
    )
    screen_id = screen.json()["id"]
    seats = await client.post(
        f"/screens/{screen_id}/seats/generate",
        json={"rows": 1, "seats_per_row": 1, "premium_rows": 0},
        headers=headers,
    )
    seat_id = seats.json()[0]["id"]

    show = await client.post(
        "/shows",
        json={
            "movie_id": movie.json()["id"],
            "screen_id": screen_id,
            "show_time": "2026-12-31T20:00:00Z",
            "price": "300.00",
        },
        headers=headers,
    )
    return show.json()["id"], seat_id


async def attempt_booking(client: httpx.AsyncClient, show_id: int, seat_id: int, user_index: int) -> tuple[int, int]:
    email = _random_email(f"loadtest_user{user_index}")
    await client.post("/auth/register", json={"name": f"User {user_index}", "email": email, "password": "pass12345"})
    login = await client.post("/auth/login", json={"email": email, "password": "pass12345"})
    token = login.json()["access_token"]

    response = await client.post(
        "/bookings",
        json={"show_id": show_id, "seat_ids": [seat_id]},
        headers={"Authorization": f"Bearer {token}"},
    )
    return user_index, response.status_code


async def main():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        print(f"Setting up one show with exactly ONE seat...")
        show_id, seat_id = await setup_show_and_seat(client)
        print(f"Show ID: {show_id}, Seat ID: {seat_id}")
        print(f"Firing {CONCURRENT_USERS} simultaneous booking requests for that single seat...\n")

        tasks = [attempt_booking(client, show_id, seat_id, i) for i in range(CONCURRENT_USERS)]
        results = await asyncio.gather(*tasks)

        successful = [r for r in results if r[1] == 201]
        conflicts = [r for r in results if r[1] == 409]
        other = [r for r in results if r[1] not in (201, 409)]

        print(f"Total concurrent requests: {CONCURRENT_USERS}")
        print(f"Successful bookings (201): {len(successful)}")
        print(f"Correctly rejected (409):  {len(conflicts)}")
        print(f"Unexpected status codes:   {len(other)} -> {other}")

        print()
        if len(successful) == 1 and len(conflicts) == CONCURRENT_USERS - 1:
            print("✅ PASS: Exactly one booking succeeded. No double-booking occurred under concurrent load.")
        else:
            print("❌ FAIL: Expected exactly 1 success and the rest conflicts. Double-booking may have occurred!")


if __name__ == "__main__":
    asyncio.run(main())
