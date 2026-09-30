"""Insert a small, repeatable demo dataset for the timetable optimizer."""

import sys
from datetime import time
from pathlib import Path

from sqlalchemy import select


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.database import SessionLocal  # noqa: E402
from backend.app.models import (  # noqa: E402
    Course,
    Faculty,
    FacultyAvailability,
    Room,
    RoomAvailability,
    TimeSlot,
)


FACULTY_DATA = [
    ("Aarav Mehta", "aarav.mehta@example.edu"),
    ("Ananya Rao", "ananya.rao@example.edu"),
    ("Kabir Sharma", "kabir.sharma@example.edu"),
    ("Meera Iyer", "meera.iyer@example.edu"),
    ("Rohan Kapoor", "rohan.kapoor@example.edu"),
    ("Sana Khan", "sana.khan@example.edu"),
    ("Vikram Nair", "vikram.nair@example.edu"),
    ("Ishita Sen", "ishita.sen@example.edu"),
    ("Dev Malhotra", "dev.malhotra@example.edu"),
]

ROOM_DATA = [
    ("A-101", 40),
    ("A-102", 50),
    ("B-201", 60),
    ("B-202", 75),
    ("Lab-1", 35),
    ("Lab-2", 45),
]

COURSE_DATA = [
    ("CS301", "Data Structures", "aarav.mehta@example.edu", "CSE-3A", 3, 38),
    ("CS302", "Database Systems", "ananya.rao@example.edu", "CSE-3A", 3, 36),
    ("CS303", "Computer Networks", "kabir.sharma@example.edu", "CSE-3A", 2, 35),
    ("CS304", "Operating Systems", "meera.iyer@example.edu", "CSE-3A", 3, 40),
    ("CS305", "Web Engineering", "rohan.kapoor@example.edu", "CSE-3A", 2, 32),
    ("CS306", "Software Testing", "sana.khan@example.edu", "CSE-3A", 2, 30),
    ("CS307", "Algorithms", "vikram.nair@example.edu", "CSE-3B", 3, 42),
    ("CS308", "Information Security", "ishita.sen@example.edu", "CSE-3B", 2, 34),
    ("CS309", "Artificial Intelligence", "dev.malhotra@example.edu", "CSE-3B", 3, 40),
    ("CS310", "Computer Architecture", "aarav.mehta@example.edu", "CSE-3B", 2, 38),
    ("CS311", "Cloud Computing", "ananya.rao@example.edu", "CSE-3B", 2, 36),
    ("CS312", "Human Computer Interaction", "kabir.sharma@example.edu", "CSE-3B", 2, 30),
    ("CS313", "Linear Algebra", "meera.iyer@example.edu", "CSE-4A", 3, 45),
    ("CS314", "Probability and Statistics", "rohan.kapoor@example.edu", "CSE-4A", 2, 43),
    ("CS315", "Distributed Systems", "sana.khan@example.edu", "CSE-4A", 3, 35),
    ("CS316", "Compiler Design", "vikram.nair@example.edu", "CSE-4A", 2, 32),
    ("CS317", "Machine Learning", "ishita.sen@example.edu", "CSE-4B", 3, 44),
    ("CS318", "Mobile Application Development", "dev.malhotra@example.edu", "CSE-4B", 2, 30),
]

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
PERIODS = [
    (time(9, 0), time(10, 0)),
    (time(10, 0), time(11, 0)),
    (time(11, 0), time(12, 0)),
    (time(13, 0), time(14, 0)),
    (time(14, 0), time(15, 0)),
]

FACULTY_UNAVAILABLE = {
    "aarav.mehta@example.edu": {("Monday", 1), ("Wednesday", 1)},
    "meera.iyer@example.edu": {("Tuesday", 4), ("Thursday", 4)},
    "sana.khan@example.edu": {("Monday", 5), ("Friday", 5)},
}

ROOM_UNAVAILABLE = {
    "A-102": {("Tuesday", 4), ("Tuesday", 5)},
    "B-201": {("Friday", 1), ("Friday", 2)},
    "Lab-1": {("Wednesday", 4), ("Wednesday", 5)},
}


def get_or_create_faculty(session) -> tuple[dict[str, Faculty], int]:
    faculty_by_email = {}
    inserted = 0

    for name, email in FACULTY_DATA:
        faculty = session.scalar(
            select(Faculty).where(Faculty.email == email)
        )
        if faculty is None:
            faculty = Faculty(name=name, email=email)
            session.add(faculty)
            session.flush()
            inserted += 1
        faculty_by_email[email] = faculty

    return faculty_by_email, inserted


def get_or_create_rooms(session) -> tuple[dict[str, Room], int]:
    rooms_by_name = {}
    inserted = 0

    for name, capacity in ROOM_DATA:
        room = session.scalar(select(Room).where(Room.name == name))
        if room is None:
            room = Room(name=name, capacity=capacity)
            session.add(room)
            session.flush()
            inserted += 1
        rooms_by_name[name] = room

    return rooms_by_name, inserted


def get_or_create_time_slots(session) -> tuple[dict[tuple[str, int], TimeSlot], int]:
    slots_by_key = {}
    inserted = 0

    for day in DAYS:
        for slot_number, (start_time, end_time) in enumerate(PERIODS, start=1):
            key = (day, slot_number)
            slot = session.scalar(
                select(TimeSlot).where(
                    TimeSlot.day_of_week == day,
                    TimeSlot.slot_number == slot_number,
                )
            )
            if slot is None:
                slot = TimeSlot(
                    day_of_week=day,
                    slot_number=slot_number,
                    start_time=start_time,
                    end_time=end_time,
                    is_undesirable=slot_number == 5,
                )
                session.add(slot)
                session.flush()
                inserted += 1
            slots_by_key[key] = slot

    return slots_by_key, inserted


def insert_courses(session, faculty_by_email: dict[str, Faculty]) -> int:
    inserted = 0

    for code, name, faculty_email, group, sessions, enrollment in COURSE_DATA:
        course = session.scalar(select(Course).where(Course.code == code))
        if course is None:
            session.add(
                Course(
                    code=code,
                    name=name,
                    faculty_id=faculty_by_email[faculty_email].id,
                    student_group=group,
                    sessions_per_week=sessions,
                    enrollment=enrollment,
                )
            )
            inserted += 1

    return inserted


def insert_availability(
    session,
    faculty_by_email: dict[str, Faculty],
    rooms_by_name: dict[str, Room],
    slots_by_key: dict[tuple[str, int], TimeSlot],
) -> tuple[int, int]:
    faculty_inserted = 0
    room_inserted = 0

    for email, faculty in faculty_by_email.items():
        unavailable = FACULTY_UNAVAILABLE.get(email, set())
        for key, slot in slots_by_key.items():
            existing = session.get(
                FacultyAvailability,
                {
                    "faculty_id": faculty.id,
                    "time_slot_id": slot.id,
                },
            )
            if existing is None:
                session.add(
                    FacultyAvailability(
                        faculty_id=faculty.id,
                        time_slot_id=slot.id,
                        is_available=key not in unavailable,
                    )
                )
                faculty_inserted += 1

    for room_name, room in rooms_by_name.items():
        unavailable = ROOM_UNAVAILABLE.get(room_name, set())
        for key, slot in slots_by_key.items():
            existing = session.get(
                RoomAvailability,
                {
                    "room_id": room.id,
                    "time_slot_id": slot.id,
                },
            )
            if existing is None:
                session.add(
                    RoomAvailability(
                        room_id=room.id,
                        time_slot_id=slot.id,
                        is_available=key not in unavailable,
                    )
                )
                room_inserted += 1

    return faculty_inserted, room_inserted


def seed_data() -> None:
    session = SessionLocal()
    try:
        faculty_by_email, faculty_inserted = get_or_create_faculty(session)
        rooms_by_name, rooms_inserted = get_or_create_rooms(session)
        slots_by_key, slots_inserted = get_or_create_time_slots(session)
        courses_inserted = insert_courses(session, faculty_by_email)
        faculty_availability_inserted, room_availability_inserted = (
            insert_availability(
                session,
                faculty_by_email,
                rooms_by_name,
                slots_by_key,
            )
        )

        session.commit()
        print("Seed data completed successfully.")
        print(f"Faculty inserted: {faculty_inserted}")
        print(f"Courses inserted: {courses_inserted}")
        print(f"Rooms inserted: {rooms_inserted}")
        print(f"Time slots inserted: {slots_inserted}")
        print(
            "Faculty availability inserted: "
            f"{faculty_availability_inserted}"
        )
        print(
            "Room availability inserted: "
            f"{room_availability_inserted}"
        )
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_data()

