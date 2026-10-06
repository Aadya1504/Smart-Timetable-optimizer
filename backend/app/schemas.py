"""Pydantic response schemas for the timetable API."""

from datetime import time

from pydantic import BaseModel


class TimetableAssignmentResponse(BaseModel):
    course_id: int
    course_code: str
    course_name: str
    faculty_id: int
    faculty_name: str
    room_id: int
    room_name: str
    time_slot_id: int
    day_of_week: str
    start_time: time
    end_time: time
    session_number: int


class GenerateTimetableResponse(BaseModel):
    timetable_run_id: int
    solver_status: str
    assignment_count: int
    assignments: list[TimetableAssignmentResponse]


class TimetableRunResponse(BaseModel):
    timetable_run_id: int
    status: str
    objective_value: float | None = None
    assignment_count: int
    assignments: list[TimetableAssignmentResponse]

