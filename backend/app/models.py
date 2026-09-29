"""SQLAlchemy models for the timetable optimizer MVP."""

from datetime import datetime, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Faculty(Base):
    __tablename__ = "faculty"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    courses: Mapped[list["Course"]] = relationship(back_populates="faculty")
    availability: Mapped[list["FacultyAvailability"]] = relationship(
        back_populates="faculty",
        cascade="all, delete-orphan",
    )


class Room(Base):
    __tablename__ = "rooms"
    __table_args__ = (
        CheckConstraint("capacity > 0", name="ck_rooms_capacity_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)

    availability: Mapped[list["RoomAvailability"]] = relationship(
        back_populates="room",
        cascade="all, delete-orphan",
    )
    timetable_entries: Mapped[list["TimetableEntry"]] = relationship(
        back_populates="room"
    )


class TimeSlot(Base):
    __tablename__ = "time_slots"
    __table_args__ = (
        UniqueConstraint(
            "day_of_week",
            "slot_number",
            name="uq_time_slots_day_slot",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day_of_week: Mapped[str] = mapped_column(String(20), nullable=False)
    slot_number: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_undesirable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    faculty_availability: Mapped[list["FacultyAvailability"]] = relationship(
        back_populates="time_slot",
        cascade="all, delete-orphan",
    )
    room_availability: Mapped[list["RoomAvailability"]] = relationship(
        back_populates="time_slot",
        cascade="all, delete-orphan",
    )
    timetable_entries: Mapped[list["TimetableEntry"]] = relationship(
        back_populates="time_slot"
    )


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (
        CheckConstraint(
            "sessions_per_week > 0",
            name="ck_courses_sessions_positive",
        ),
        CheckConstraint(
            "enrollment > 0",
            name="ck_courses_enrollment_positive",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    faculty_id: Mapped[int] = mapped_column(
        ForeignKey("faculty.id"),
        nullable=False,
    )
    student_group: Mapped[str] = mapped_column(String(100), nullable=False)
    sessions_per_week: Mapped[int] = mapped_column(Integer, nullable=False)
    enrollment: Mapped[int] = mapped_column(Integer, nullable=False)

    faculty: Mapped[Faculty] = relationship(back_populates="courses")
    timetable_entries: Mapped[list["TimetableEntry"]] = relationship(
        back_populates="course"
    )


class FacultyAvailability(Base):
    __tablename__ = "faculty_availability"

    faculty_id: Mapped[int] = mapped_column(
        ForeignKey("faculty.id"),
        primary_key=True,
    )
    time_slot_id: Mapped[int] = mapped_column(
        ForeignKey("time_slots.id"),
        primary_key=True,
    )
    is_available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    faculty: Mapped[Faculty] = relationship(back_populates="availability")
    time_slot: Mapped[TimeSlot] = relationship(
        back_populates="faculty_availability"
    )


class RoomAvailability(Base):
    __tablename__ = "room_availability"

    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id"),
        primary_key=True,
    )
    time_slot_id: Mapped[int] = mapped_column(
        ForeignKey("time_slots.id"),
        primary_key=True,
    )
    is_available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    room: Mapped[Room] = relationship(back_populates="availability")
    time_slot: Mapped[TimeSlot] = relationship(
        back_populates="room_availability"
    )


class TimetableRun(Base):
    __tablename__ = "timetable_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    objective_value: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    entries: Mapped[list["TimetableEntry"]] = relationship(
        back_populates="timetable_run",
        cascade="all, delete-orphan",
    )


class TimetableEntry(Base):
    __tablename__ = "timetable_entries"
    __table_args__ = (
        UniqueConstraint(
            "timetable_run_id",
            "course_id",
            "session_number",
            name="uq_entries_run_course_session",
        ),
        UniqueConstraint(
            "timetable_run_id",
            "room_id",
            "time_slot_id",
            name="uq_entries_run_room_slot",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timetable_run_id: Mapped[int] = mapped_column(
        ForeignKey("timetable_runs.id"),
        nullable=False,
    )
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id"),
        nullable=False,
    )
    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id"),
        nullable=False,
    )
    time_slot_id: Mapped[int] = mapped_column(
        ForeignKey("time_slots.id"),
        nullable=False,
    )
    session_number: Mapped[int] = mapped_column(Integer, nullable=False)

    timetable_run: Mapped[TimetableRun] = relationship(
        back_populates="entries"
    )
    course: Mapped[Course] = relationship(back_populates="timetable_entries")
    room: Mapped[Room] = relationship(back_populates="timetable_entries")
    time_slot: Mapped[TimeSlot] = relationship(
        back_populates="timetable_entries"
    )

