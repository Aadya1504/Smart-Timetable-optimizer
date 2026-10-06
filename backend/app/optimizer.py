"""CP-SAT timetable optimizer.

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
    objective_value: float | None = None
    message: str | None = None


# Larger weights express stronger preferences in the objective function.
COURSE_DAY_REWARD = 100
COURSE_SAME_DAY_PENALTY = 80
CONSECUTIVE_COURSE_PENALTY = 20
GROUP_DAY_REWARD = 12
GROUP_SAME_DAY_PENALTY = 6
GROUP_GAP_PENALTY = 8


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
    course_slot_variables: dict[tuple[int, int], list[cp_model.IntVar]] = {}
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
                    course_slot_variables.setdefault(
                        (course.id, time_slot.id), []
                    ).append(variable)
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

    objective_terms = []
    slots_by_day: dict[str, list[TimeSlot]] = {}
    for time_slot in time_slots:
        slots_by_day.setdefault(time_slot.day_of_week, []).append(time_slot)
    for day_slots in slots_by_day.values():
        day_slots.sort(key=lambda slot: slot.slot_number)

    # Presence variables let the objective reason about a course being used
    # on a day or in a period, independently of its selected room.
    course_slot_used: dict[tuple[int, int], cp_model.IntVar] = {}
    course_day_used: dict[tuple[int, str], cp_model.IntVar] = {}

    for course in courses:
        for time_slot in time_slots:
            slot_variables = course_slot_variables.get(
                (course.id, time_slot.id), []
            )
            slot_used = model.NewBoolVar(
                "course_{}_slot_{}_used".format(course.id, time_slot.id)
            )
            if slot_variables:
                model.AddMaxEquality(slot_used, slot_variables)
            else:
                model.Add(slot_used == 0)
            course_slot_used[(course.id, time_slot.id)] = slot_used

        for day, day_slots in slots_by_day.items():
            day_slot_used = [
                course_slot_used[(course.id, time_slot.id)]
                for time_slot in day_slots
            ]
            day_used = model.NewBoolVar(
                "course_{}_day_{}_used".format(course.id, day)
            )
            model.AddMaxEquality(day_used, day_slot_used)
            course_day_used[(course.id, day)] = day_used
            objective_terms.append(COURSE_DAY_REWARD * day_used)

            sessions_on_day = []
            for time_slot in day_slots:
                sessions_on_day.extend(
                    course_slot_variables.get(
                        (course.id, time_slot.id), []
                    )
                )
            same_day_excess = model.NewIntVar(
                0,
                course.sessions_per_week,
                "course_{}_day_{}_excess".format(course.id, day),
            )
            model.Add(
                same_day_excess == sum(sessions_on_day) - day_used
            )
            objective_terms.append(
                -COURSE_SAME_DAY_PENALTY * same_day_excess
            )

        # Penalize consecutive periods occupied by the same course.
        for day, day_slots in slots_by_day.items():
            for earlier_slot, later_slot in zip(day_slots, day_slots[1:]):
                earlier_used = course_slot_used[
                    (course.id, earlier_slot.id)
                ]
                later_used = course_slot_used[(course.id, later_slot.id)]
                consecutive = model.NewBoolVar(
                    "course_{}_{}_{}_consecutive".format(
                        course.id,
                        earlier_slot.id,
                        later_slot.id,
                    )
                )
                model.Add(consecutive <= earlier_used)
                model.Add(consecutive <= later_used)
                model.Add(consecutive >= earlier_used + later_used - 1)
                objective_terms.append(
                    -CONSECUTIVE_COURSE_PENALTY * consecutive
                )

    # The same presence variables are used to spread each group's workload
    # over weekdays and to identify empty periods inside a group schedule.
    groups = sorted({course.student_group for course in courses})
    group_slot_used: dict[tuple[str, int], cp_model.IntVar] = {}
    group_day_used: dict[tuple[str, str], cp_model.IntVar] = {}

    for group in groups:
        for time_slot in time_slots:
            slot_variables = group_slot_variables.get(
                (group, time_slot.id), []
            )
            slot_used = model.NewBoolVar(
                "group_{}_slot_{}_used".format(group, time_slot.id)
            )
            if slot_variables:
                model.AddMaxEquality(slot_used, slot_variables)
            else:
                model.Add(slot_used == 0)
            group_slot_used[(group, time_slot.id)] = slot_used

        for day, day_slots in slots_by_day.items():
            day_slot_used = [
                group_slot_used[(group, time_slot.id)]
                for time_slot in day_slots
            ]
            day_used = model.NewBoolVar(
                "group_{}_day_{}_used".format(group, day)
            )
            model.AddMaxEquality(day_used, day_slot_used)
            group_day_used[(group, day)] = day_used
            objective_terms.append(GROUP_DAY_REWARD * day_used)

            classes_on_day = []
            for time_slot in day_slots:
                classes_on_day.extend(
                    group_slot_variables.get(
                        (group, time_slot.id), []
                    )
                )
            same_day_excess = model.NewIntVar(
                0,
                sum(
                    course.sessions_per_week
                    for course in courses
                    if course.student_group == group
                ),
                "group_{}_day_{}_excess".format(group, day),
            )
            model.Add(same_day_excess == sum(classes_on_day) - day_used)
            objective_terms.append(-GROUP_SAME_DAY_PENALTY * same_day_excess)

        for day, day_slots in slots_by_day.items():
            for index in range(1, len(day_slots) - 1):
                current_slot = group_slot_used[(group, day_slots[index].id)]
                before_slots = [
                    group_slot_used[(group, slot.id)]
                    for slot in day_slots[:index]
                ]
                after_slots = [
                    group_slot_used[(group, slot.id)]
                    for slot in day_slots[index + 1 :]
                ]

                has_class_before = model.NewBoolVar(
                    "group_{}_{}_{}_before".format(
                        group,
                        day,
                        index,
                    )
                )
                has_class_after = model.NewBoolVar(
                    "group_{}_{}_{}_after".format(
                        group,
                        day,
                        index,
                    )
                )
                model.AddMaxEquality(has_class_before, before_slots)
                model.AddMaxEquality(has_class_after, after_slots)

                gap = model.NewBoolVar(
                    "group_{}_{}_{}_gap".format(group, day, index)
                )
                model.AddBoolAnd(
                    [has_class_before, has_class_after, current_slot.Not()]
                ).OnlyEnforceIf(gap)
                model.AddBoolOr(
                    [
                        has_class_before.Not(),
                        has_class_after.Not(),
                        current_slot,
                        gap,
                    ]
                )
                objective_terms.append(-GROUP_GAP_PENALTY * gap)

    # Maximize the weighted schedule quality score while keeping all hard
    # constraints above mandatory.
    if objective_terms:
        model.Maximize(sum(objective_terms))

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
            objective_value=None,
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
        objective_value=solver.ObjectiveValue(),
    )

