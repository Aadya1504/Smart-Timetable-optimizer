"""Pydantic response schemas for the timetable API."""

from pydantic import BaseModel


class TimetableAssignmentResponse(BaseModel):
    course_id: int
    room_id: int
    time_slot_id: int
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

