"""Run the timetable optimizer against the current database contents."""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.database import SessionLocal  # noqa: E402
from backend.app.optimizer import generate_timetable  # noqa: E402


def main() -> None:
    db = SessionLocal()
    try:
        result = generate_timetable(db)

        print(f"Solver status: {result.status}")
        print(f"Feasible: {result.feasible}")
        print(f"Assignments generated: {len(result.assignments)}")
        print("Assignments:")
        for assignment in result.assignments:
            print(
                "  "
                f"course_id={assignment.course_id}, "
                f"session_number={assignment.session_number}, "
                f"room_id={assignment.room_id}, "
                f"time_slot_id={assignment.time_slot_id}"
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()

