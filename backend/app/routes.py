"""FastAPI routes for timetable generation and retrieval."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .database import get_db
from .models import TimetableEntry, TimetableRun
from .optimizer import generate_timetable
from .schemas import (
    GenerateTimetableResponse,
    TimetableAssignmentResponse,
    TimetableRunResponse,
)


router = APIRouter()


def _assignment_response(entry: TimetableEntry) -> TimetableAssignmentResponse:
    return TimetableAssignmentResponse(
        course_id=entry.course_id,
        room_id=entry.room_id,
        time_slot_id=entry.time_slot_id,
        session_number=entry.session_number,
    )


@router.post(
    "/timetable/generate",
    response_model=GenerateTimetableResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_timetable_endpoint(
    db: Session = Depends(get_db),
) -> GenerateTimetableResponse:
    """Generate a timetable and save the successful result."""

    result = generate_timetable(db)
    if not result.feasible:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result.message or "No feasible timetable was found.",
        )

    try:
        timetable_run = TimetableRun(
            status=result.status,
            objective_value=None,
        )
        db.add(timetable_run)
        db.flush()

        entries = [
            TimetableEntry(
                timetable_run_id=timetable_run.id,
                course_id=assignment.course_id,
                room_id=assignment.room_id,
                time_slot_id=assignment.time_slot_id,
                session_number=assignment.session_number,
            )
            for assignment in result.assignments
        ]
        db.add_all(entries)
        db.commit()

        return GenerateTimetableResponse(
            timetable_run_id=timetable_run.id,
            solver_status=result.status,
            assignment_count=len(entries),
            assignments=[
                TimetableAssignmentResponse(
                    course_id=assignment.course_id,
                    room_id=assignment.room_id,
                    time_slot_id=assignment.time_slot_id,
                    session_number=assignment.session_number,
                )
                for assignment in result.assignments
            ],
        )
    except SQLAlchemyError:
        db.rollback()
        raise


@router.get(
    "/timetable/{run_id}",
    response_model=TimetableRunResponse,
)
def get_timetable(
    run_id: int,
    db: Session = Depends(get_db),
) -> TimetableRunResponse:
    """Retrieve a saved timetable run and its assignments."""

    timetable_run = db.get(TimetableRun, run_id)
    if timetable_run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Timetable run {run_id} was not found.",
        )

    entries = db.scalars(
        select(TimetableEntry)
        .where(TimetableEntry.timetable_run_id == run_id)
        .order_by(
            TimetableEntry.course_id,
            TimetableEntry.session_number,
        )
    ).all()

    return TimetableRunResponse(
        timetable_run_id=timetable_run.id,
        status=timetable_run.status,
        objective_value=timetable_run.objective_value,
        assignment_count=len(entries),
        assignments=[_assignment_response(entry) for entry in entries],
    )

