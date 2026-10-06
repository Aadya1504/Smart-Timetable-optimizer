import { Fragment, useState } from "react";

const weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];

function formatTime(value) {
  const [hourValue, minuteValue] = value.split(":");
  const hour = Number(hourValue);
  const suffix = hour >= 12 ? "PM" : "AM";
  const displayHour = hour % 12 || 12;
  return `${displayHour}:${minuteValue} ${suffix}`;
}

function getTimeSlots(assignments) {
  const uniqueSlots = new Map();

  assignments.forEach((assignment) => {
    const key = `${assignment.start_time}-${assignment.end_time}`;
    uniqueSlots.set(key, {
      key,
      startTime: assignment.start_time,
      endTime: assignment.end_time,
    });
  });

  return [...uniqueSlots.values()].sort((first, second) =>
    first.startTime.localeCompare(second.startTime),
  );
}

function App() {
  const [isGenerating, setIsGenerating] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  async function handleGenerateTimetable() {
    setIsGenerating(true);
    setResult(null);
    setError("");

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/timetable/generate",
        {
          method: "POST",
        },
      );
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "The timetable could not be generated.");
      }

      setResult(data);
    } catch (requestError) {
      setError(
        requestError.message ||
          "Unable to connect to the timetable generation service.",
      );
    } finally {
      setIsGenerating(false);
    }
  }

  return (
    <main style={styles.page}>
      <section style={styles.container}>
        <header style={styles.header}>
          <p style={styles.eyebrow}>ACADEMIC PLANNING</p>
          <h1 style={styles.title}>Smart Timetable Optimizer</h1>
          <p style={styles.subtitle}>
            Generate conflict-free academic timetables with intelligent
            scheduling constraints.
          </p>
        </header>

        <section style={styles.cardGrid}>
          <article style={styles.card}>
            <div style={styles.iconCircle}>01</div>
            <h2 style={styles.cardTitle}>Regular Timetable</h2>
            <p style={styles.cardDescription}>
              Generate a complete timetable using courses, faculty
              availability, rooms, and time slots.
            </p>
            <button
              type="button"
              style={styles.button}
              onClick={handleGenerateTimetable}
              disabled={isGenerating}
            >
              {isGenerating ? "Generating..." : "Generate Timetable"}
            </button>
          </article>

          <article style={styles.card}>
            <div style={styles.iconCircle}>02</div>
            <h2 style={styles.cardTitle}>Extra Class Scheduling</h2>
            <p style={styles.cardDescription}>
              Find an available room and time slot for an additional class.
            </p>
            <button type="button" style={styles.button}>
              Schedule Extra Class
            </button>
          </article>
        </section>

        {error && <p style={styles.error}>{error}</p>}

        {result && (
          <section style={styles.resultPanel}>
            <div style={styles.resultHeader}>
              <div>
                <p style={styles.resultEyebrow}>GENERATION COMPLETE</p>
                <h2 style={styles.resultTitle}>Timetable Result</h2>
              </div>
              <span style={styles.status}>{result.solver_status}</span>
            </div>

            <div style={styles.summaryGrid}>
              <div>
                <span style={styles.summaryLabel}>Run ID</span>
                <strong style={styles.summaryValue}>
                  {result.timetable_run_id}
                </strong>
              </div>
              <div>
                <span style={styles.summaryLabel}>Assignments</span>
                <strong style={styles.summaryValue}>
                  {result.assignment_count}
                </strong>
              </div>
            </div>

            <div style={styles.timetableScroll}>
              <div
                style={{
                  ...styles.timetableGrid,
                  gridTemplateColumns: `180px repeat(${weekdays.length}, minmax(160px, 1fr))`,
                }}
              >
                <div style={styles.timetableHeader}>Time</div>
                {weekdays.map((day) => (
                  <div key={day} style={styles.timetableHeader}>
                    {day}
                  </div>
                ))}

                {getTimeSlots(result.assignments).map((slot) => (
                  <Fragment key={slot.key}>
                    <div key={`${slot.key}-label`} style={styles.timeCell}>
                      <strong>{formatTime(slot.startTime)}</strong>
                      <span>to {formatTime(slot.endTime)}</span>
                    </div>

                    {weekdays.map((day) => {
                      const cellAssignments = result.assignments.filter(
                        (assignment) =>
                          assignment.day_of_week === day &&
                          assignment.start_time === slot.startTime &&
                          assignment.end_time === slot.endTime,
                      );

                      return (
                        <div
                          key={`${slot.key}-${day}`}
                          style={styles.timetableCell}
                        >
                          {cellAssignments.length === 0 ? (
                            <span style={styles.emptyCell}>-</span>
                          ) : (
                            cellAssignments.map((assignment) => (
                              <div
                                key={`${assignment.course_id}-${assignment.session_number}`}
                                style={styles.classBlock}
                              >
                                <strong style={styles.courseCode}>
                                  {assignment.course_code}
                                </strong>
                                <span style={styles.courseName}>
                                  {assignment.course_name}
                                </span>
                                <span style={styles.classMeta}>
                                  {assignment.faculty_name}
                                </span>
                                <span style={styles.classMeta}>
                                  {assignment.room_name}
                                </span>
                              </div>
                            ))
                          )}
                        </div>
                      );
                    })}
                  </Fragment>
                ))}
              </div>
            </div>
          </section>
        )}
      </section>
    </main>
  );
}

const styles = {
  page: {
    minHeight: "100vh",
    backgroundColor: "#f4f7fb",
    color: "#172033",
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, sans-serif",
    padding: "64px 24px",
    boxSizing: "border-box",
  },
  container: {
    width: "100%",
    maxWidth: "1040px",
    margin: "0 auto",
  },
  header: {
    maxWidth: "680px",
    marginBottom: "40px",
  },
  eyebrow: {
    margin: "0 0 12px",
    color: "#4773b8",
    fontSize: "12px",
    fontWeight: 700,
    letterSpacing: "1.6px",
  },
  title: {
    margin: 0,
    fontSize: "clamp(32px, 5vw, 52px)",
    lineHeight: 1.1,
    letterSpacing: "0",
  },
  subtitle: {
    margin: "18px 0 0",
    color: "#5d6a7e",
    fontSize: "18px",
    lineHeight: 1.6,
  },
  cardGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
    gap: "20px",
  },
  card: {
    display: "flex",
    flexDirection: "column",
    alignItems: "flex-start",
    minHeight: "280px",
    padding: "28px",
    backgroundColor: "#ffffff",
    border: "1px solid #dfe6ef",
    borderRadius: "8px",
    boxShadow: "0 8px 24px rgba(34, 56, 86, 0.06)",
    boxSizing: "border-box",
  },
  iconCircle: {
    display: "grid",
    placeItems: "center",
    width: "40px",
    height: "40px",
    marginBottom: "24px",
    borderRadius: "50%",
    backgroundColor: "#e8f0fb",
    color: "#3765a5",
    fontSize: "12px",
    fontWeight: 700,
  },
  cardTitle: {
    margin: "0 0 12px",
    fontSize: "23px",
    lineHeight: 1.25,
  },
  cardDescription: {
    flex: 1,
    margin: 0,
    color: "#5d6a7e",
    fontSize: "15px",
    lineHeight: 1.65,
  },
  button: {
    marginTop: "28px",
    padding: "12px 18px",
    border: 0,
    borderRadius: "6px",
    backgroundColor: "#285b9f",
    color: "#ffffff",
    fontSize: "14px",
    fontWeight: 700,
    cursor: "pointer",
  },
  error: {
    margin: "24px 0 0",
    padding: "14px 16px",
    border: "1px solid #f2b8b5",
    borderRadius: "6px",
    backgroundColor: "#fff1f0",
    color: "#a33a34",
    fontSize: "14px",
  },
  resultPanel: {
    marginTop: "24px",
    padding: "28px",
    backgroundColor: "#ffffff",
    border: "1px solid #dfe6ef",
    borderRadius: "8px",
    boxShadow: "0 8px 24px rgba(34, 56, 86, 0.06)",
  },
  resultHeader: {
    display: "flex",
    alignItems: "flex-start",
    justifyContent: "space-between",
    gap: "16px",
  },
  resultEyebrow: {
    margin: "0 0 8px",
    color: "#4773b8",
    fontSize: "12px",
    fontWeight: 700,
    letterSpacing: "1.4px",
  },
  resultTitle: {
    margin: 0,
    fontSize: "24px",
  },
  status: {
    padding: "7px 10px",
    borderRadius: "999px",
    backgroundColor: "#e8f5ed",
    color: "#237044",
    fontSize: "12px",
    fontWeight: 700,
  },
  summaryGrid: {
    display: "flex",
    gap: "48px",
    margin: "24px 0",
    padding: "16px 0",
    borderTop: "1px solid #edf0f4",
    borderBottom: "1px solid #edf0f4",
  },
  summaryLabel: {
    display: "block",
    marginBottom: "6px",
    color: "#738096",
    fontSize: "12px",
    textTransform: "uppercase",
    letterSpacing: "0.8px",
  },
  summaryValue: {
    color: "#172033",
    fontSize: "20px",
  },
  timetableScroll: {
    width: "100%",
    overflowX: "auto",
    paddingBottom: "4px",
  },
  timetableGrid: {
    display: "grid",
    minWidth: "980px",
    borderTop: "1px solid #dfe6ef",
    borderLeft: "1px solid #dfe6ef",
  },
  timetableHeader: {
    padding: "13px 14px",
    backgroundColor: "#eef3f9",
    borderRight: "1px solid #dfe6ef",
    borderBottom: "1px solid #dfe6ef",
    color: "#3e5878",
    fontSize: "13px",
    fontWeight: 700,
  },
  timeCell: {
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    gap: "4px",
    padding: "12px 14px",
    backgroundColor: "#f8fafc",
    borderRight: "1px solid #dfe6ef",
    borderBottom: "1px solid #dfe6ef",
    color: "#34445c",
    fontSize: "13px",
  },
  timetableCell: {
    minHeight: "112px",
    padding: "8px",
    backgroundColor: "#ffffff",
    borderRight: "1px solid #dfe6ef",
    borderBottom: "1px solid #dfe6ef",
  },
  emptyCell: {
    display: "block",
    padding: "10px 6px",
    color: "#b1bac8",
    textAlign: "center",
  },
  classBlock: {
    display: "flex",
    flexDirection: "column",
    gap: "3px",
    padding: "10px",
    borderLeft: "3px solid #4773b8",
    borderRadius: "4px",
    backgroundColor: "#f1f6fd",
    color: "#26344a",
  },
  courseCode: {
    color: "#285b9f",
    fontSize: "14px",
  },
  courseName: {
    color: "#26344a",
    fontSize: "13px",
    lineHeight: 1.3,
  },
  classMeta: {
    color: "#617087",
    fontSize: "12px",
  },
};

export default App;

