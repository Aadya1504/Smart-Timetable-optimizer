"""Initial CP-SAT timetable optimizer.

This module only builds and solves the scheduling model. It does not create
database records, so a future API/service layer can decide how to persist a
successful result.
"""

from dataclasses import dataclass

from ortools.sat.python import cp_model
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import (
    Course,
    FacultyAvailability,
    Room,
    RoomAvailability,
    TimeSlot,
)


@dataclass(frozen=True)
class TimetableAssignment:
    """One scheduled course session returned by the solver."""

    course_id: int
    room_id: int
    time_slot_id: int
    session_number: int


@dataclass
class OptimizationResult:
    """The solver status and assignments produced by a solve attempt."""

    status: str
    feasible: bool
    assignments: list[TimetableAssignment]
    message: str | None = None


def generate_timetable(
    db: Session,
    time_limit_seconds: float = 10.0,
) -> OptimizationResult:
    """Generate a timetable from database data using CP-SAT.

    The function does not commit anything to the database. Missing
    availability rows are treated as unavailable, which avoids accidentally
    scheduling in a slot whose availability has not been defined.
    """

    courses = db.scalars(select(Course).order_by(Course.id)).all()
    rooms = db.scalars(select(Room).order_by(Room.id)).all()
    time_slots = db.scalars(select(TimeSlot).order_by(TimeSlot.id)).all()

    faculty_availability = {
        (row.faculty_id, row.time_slot_id): row.is_available
        for row in db.scalars(select(FacultyAvailability)).all()
    }
    room_availability = {
        (row.room_id, row.time_slot_id): row.is_available
        for row in db.scalars(select(RoomAvailability)).all()
    }

    model = cp_model.CpModel()

    # Each variable means: this course session uses this room in this slot.
    variables: dict[tuple[int, int, int, int], cp_model.IntVar] = {}
    course_session_variables: dict[
        tuple[int, int], list[cp_model.IntVar]
    ] = {}
    faculty_slot_variables: dict[tuple[int, int], list[cp_model.IntVar]] = {}
    room_slot_variables: dict[tuple[int, int], list[cp_model.IntVar]] = {}
    group_slot_variables: dict[tuple[str, int], list[cp_model.IntVar]] = {}

    for course in courses:
        for session_number in range(1, course.sessions_per_week + 1):
            session_key = (course.id, session_number)
            course_session_variables[session_key] = []

            for time_slot in time_slots:
                faculty_is_available = faculty_availability.get(
                    (course.faculty_id, time_slot.id),
                    False,
                )
                if not faculty_is_available:
                    continue

                for room in rooms:
                    room_is_available = room_availability.get(
                        (room.id, time_slot.id),
                        False,
                    )
                    if not room_is_available or room.capacity < course.enrollment:
                        continue

                    variable_key = (
                        course.id,
                        session_number,
                        room.id,
                        time_slot.id,
                    )
                    variable = model.NewBoolVar(
                        "course_{}_session_{}_room_{}_slot_{}".format(
                            course.id,
                            session_number,
                            room.id,
                            time_slot.id,
                        )
                    )
                    variables[variable_key] = variable
                    course_session_variables[session_key].append(variable)
                    faculty_slot_variables.setdefault(
                        (course.faculty_id, time_slot.id), []
                    ).append(variable)
                    room_slot_variables.setdefault(
                        (room.id, time_slot.id), []
                    ).append(variable)
                    group_slot_variables.setdefault(
                        (course.student_group, time_slot.id), []
                    ).append(variable)

    # Every course session must receive exactly one feasible assignment.
    for (course_id, session_number), session_variables in (
        course_session_variables.items()
    ):
        if not session_variables:
            return OptimizationResult(
                status="INFEASIBLE",
                feasible=False,
                assignments=[],
                message=(
                    "Course {} session {} has no feasible room/time-slot "
                    "assignment.".format(course_id, session_number)
                ),
            )
        model.Add(sum(session_variables) == 1)

    # A faculty member can teach at most one course in a time slot.
    for slot_variables in faculty_slot_variables.values():
        model.Add(sum(slot_variables) <= 1)

    # A room can host at most one course in a time slot.
    for slot_variables in room_slot_variables.values():
        model.Add(sum(slot_variables) <= 1)

    # A student group can attend at most one course in a time slot.
    for slot_variables in group_slot_variables.values():
        model.Add(sum(slot_variables) <= 1)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_seconds
    solver.parameters.num_search_workers = 1

    solver_status = solver.Solve(model)
    status_name = solver.StatusName(solver_status)
    feasible = solver_status in (
        cp_model.OPTIMAL,
        cp_model.FEASIBLE,
    )

    if not feasible:
        return OptimizationResult(
            status=status_name,
            feasible=False,
            assignments=[],
            message="The solver did not find a feasible timetable.",
        )

    assignments = []
    for (course_id, session_number, room_id, time_slot_id), variable in (
        variables.items()
    ):
        if solver.Value(variable) == 1:
            assignments.append(
                TimetableAssignment(
                    course_id=course_id,
                    room_id=room_id,
                    time_slot_id=time_slot_id,
                    session_number=session_number,
                )
            )

    assignments.sort(key=lambda assignment: (
        assignment.course_id,
        assignment.session_number,
    ))

    return OptimizationResult(
        status=status_name,
        feasible=True,
        assignments=assignments,
    )

