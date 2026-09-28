# Smart Timetable Optimizer

A one-week MVP that uses PostgreSQL, FastAPI, SQLAlchemy, Alembic, React, and Google OR-Tools CP-SAT to generate conflict-free college timetables.

## Project Status

Initial project scaffold only. Database models, migrations, API endpoints, optimizer logic, dataset, and frontend timetable UI will be added incrementally.

## Planned Structure

- `backend/`: FastAPI application, database integration, optimizer, and tests
- `frontend/`: React + Vite application
- `scripts/`: small project utility scripts

## Planned Development Order

1. Configure PostgreSQL and SQLAlchemy.
2. Add database models and the first Alembic migration.
3. Add validation and a small demo dataset.
4. Implement the isolated OR-Tools optimizer.
5. Add FastAPI generation and retrieval endpoints.
6. Build the React timetable view.

