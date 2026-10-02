"""Database seeding script with idempotent sample data insertion."""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import DB_PATH, logger
from src.database import get_db_connection, init_db

# Fictional sample projects
SAMPLE_PROJECTS = [
    {
        "name": "Cloud Infrastructure Modernization",
        "description": "Migrate on-premise compute resources to automated Kubernetes clusters.",
    },
    {
        "name": "Customer Portal Redesign",
        "description": "Revamp customer self-service dashboard with modern UI and responsive layouts.",
    },
    {
        "name": "Real-time Analytics Engine",
        "description": "Build streaming pipeline for operational metrics and incident alerting.",
    },
]

# Fictional sample tasks
SAMPLE_TASKS = [
    {
        "title": "Provision staging Kubernetes cluster",
        "description": "Configure Terraform manifests and bootstrap EKS cluster with security policies.",
        "status": "completed",
        "priority": "high",
        "due_date": "2025-01-15",
        "project_name": "Cloud Infrastructure Modernization",
    },
    {
        "title": "Implement automated database backups",
        "description": "Set up nightly snapshots with point-in-time recovery and retention policies.",
        "status": "in_progress",
        "priority": "urgent",
        "due_date": "2025-02-01",  # Past date (overdue)
        "project_name": "Cloud Infrastructure Modernization",
    },
    {
        "title": "Audit IAM permissions and roles",
        "description": "Review least-privilege access for all service accounts and API tokens.",
        "status": "pending",
        "priority": "medium",
        "due_date": "2026-11-20",
        "project_name": "Cloud Infrastructure Modernization",
    },
    {
        "title": "Design responsive navigation bar",
        "description": "Create accessible component adhering to WCAG 2.1 AA specifications.",
        "status": "completed",
        "priority": "medium",
        "due_date": "2025-03-10",
        "project_name": "Customer Portal Redesign",
    },
    {
        "title": "Build user profile preferences page",
        "description": "Allow customers to manage notification channels and two-factor authentication.",
        "status": "in_progress",
        "priority": "high",
        "due_date": "2026-10-15",
        "project_name": "Customer Portal Redesign",
    },
    {
        "title": "Integrate payment history export",
        "description": "Support PDF and CSV download options for billing invoices.",
        "status": "pending",
        "priority": "low",
        "due_date": "2026-12-01",
        "project_name": "Customer Portal Redesign",
    },
    {
        "title": "Benchmark Kafka message throughput",
        "description": "Stress-test event brokers with 50,000 events/second ingest simulation.",
        "status": "pending",
        "priority": "urgent",
        "due_date": "2025-02-10",  # Past date (overdue)
        "project_name": "Real-time Analytics Engine",
    },
    {
        "title": "Construct latency monitoring dashboard",
        "description": "Visualize p95 and p99 query latency metrics in Grafana.",
        "status": "pending",
        "priority": "high",
        "due_date": None,
        "project_name": "Real-time Analytics Engine",
    },
    {
        "title": "Conduct security vulnerability scan",
        "description": "Run static code analysis and dependency audits across all repositories.",
        "status": "pending",
        "priority": "medium",
        "due_date": "2026-11-05",
        "project_name": None,  # Unassigned task
    },
]


def seed_db(database_path=None) -> None:
    """Seed the database idempotently with fictional project and task records."""
    target_path = database_path or DB_PATH
    init_db(target_path)

    with get_db_connection(target_path) as conn:
        with conn:
            # 1. Seed projects idempotently
            project_id_map = {}
            for proj in SAMPLE_PROJECTS:
                existing = conn.execute(
                    "SELECT id FROM projects WHERE name = ?", (proj["name"],)
                ).fetchone()
                if existing:
                    project_id_map[proj["name"]] = existing["id"]
                else:
                    cur = conn.execute(
                        "INSERT INTO projects (name, description) VALUES (?, ?)",
                        (proj["name"], proj["description"]),
                    )
                    project_id_map[proj["name"]] = cur.lastrowid
                    logger.info(f"Inserted project: '{proj['name']}'")

            # 2. Seed tasks idempotently
            for tsk in SAMPLE_TASKS:
                existing_task = conn.execute(
                    "SELECT id FROM tasks WHERE title = ?", (tsk["title"],)
                ).fetchone()

                if existing_task:
                    task_id = existing_task["id"]
                else:
                    cur = conn.execute(
                        """
                        INSERT INTO tasks (title, description, status, priority, due_date)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (tsk["title"], tsk["description"], tsk["status"], tsk["priority"], tsk["due_date"]),
                    )
                    task_id = cur.lastrowid
                    logger.info(f"Inserted task: '{tsk['title']}' (ID: {task_id})")

                # Associate with project if specified
                proj_name = tsk.get("project_name")
                if proj_name and proj_name in project_id_map:
                    proj_id = project_id_map[proj_name]
                    rel_exists = conn.execute(
                        "SELECT 1 FROM task_projects WHERE task_id = ? AND project_id = ?",
                        (task_id, proj_id),
                    ).fetchone()
                    if not rel_exists:
                        conn.execute(
                            "INSERT INTO task_projects (task_id, project_id) VALUES (?, ?)",
                            (task_id, proj_id),
                        )
                        logger.info(f"Linked task ID {task_id} to project ID {proj_id}")


def main() -> None:
    """Run seed script."""
    logger.info(f"Seeding database at: {DB_PATH}")
    try:
        seed_db(DB_PATH)
        print(f"Sample data successfully seeded into: {DB_PATH}")
    except Exception as exc:
        print(f"Error seeding database: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
