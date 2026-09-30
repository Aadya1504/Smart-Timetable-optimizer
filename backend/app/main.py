"""FastAPI application entry point."""

from fastapi import FastAPI

from .routes import router

app = FastAPI(title="Smart Timetable Optimizer")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(router)

