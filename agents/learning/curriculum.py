"""Curriculum tracking -- Learning Division, AI Empire University.

Structural tracking only, seeded directly from Mohamed's own curriculum
document (2026-08-03) -- fully deterministic, no LLM anywhere in this
file. Actual lecture/lesson content generation is deliberately NOT
built here (his own explicit choice) -- he supplies real lesson
material himself via the existing PASTE/URL/VIDEO ingestion commands
(agents/learning/telegram_listener.py), tagged with the subject name as
category, which then goes through the already-working Ollama flashcard
pipeline. This file only tracks WHERE he is in the 6-phase structure and
lets him mark a subject complete to advance.
"""

from datetime import UTC

CURRICULUM_SEED = [
    {
        "phase_number": 1,
        "name": "Foundation Studies",
        "goal": "Build a strong engineering foundation.",
        "subjects": [
            "Computer Fundamentals",
            "Linux",
            "Networking",
            "Python",
            "Bash",
            "Git & GitHub",
            "SQL Fundamentals",
            "Mathematics for Computing",
        ],
        "projects": ["Linux administration", "Python automation", "Networking exercises", "Git portfolio"],
        "assessments": ["Theory", "Practical labs", "Weekly quizzes", "Monthly projects"],
    },
    {
        "phase_number": 2,
        "name": "Software Engineering",
        "goal": "Become a professional software engineer.",
        "subjects": [
            "Object-Oriented Programming",
            "Data Structures",
            "Algorithms",
            "Databases",
            "REST APIs",
            "FastAPI",
            "Testing",
            "Clean Code",
            "Design Patterns",
            "Secure Coding",
        ],
        "projects": [
            "Backend APIs",
            "Authentication systems",
            "Automation tools",
            "CLI applications",
            "Database applications",
        ],
        "assessments": None,
    },
    {
        "phase_number": 3,
        "name": "Cybersecurity Foundations",
        "goal": "Understand how to build and defend secure systems.",
        "subjects": [
            "Linux Security",
            "Windows Security",
            "Networking Security",
            "Cryptography",
            "Web Security",
            "Authentication",
            "Authorization",
            "Identity Management",
            "Digital Forensics",
            "Incident Response",
            "Security Operations Center Concepts",
            "Cloud Security Fundamentals",
        ],
        "projects": [
            "System hardening",
            "Log analysis",
            "Threat detection exercises",
            "Security monitoring",
            "Guided labs in authorized practice environments",
        ],
        "assessments": None,
    },
    {
        "phase_number": 4,
        "name": "Artificial Intelligence",
        "goal": "Become an AI Engineer.",
        "subjects": [
            "Machine Learning",
            "Deep Learning",
            "Computer Vision",
            "Natural Language Processing",
            "Large Language Models",
            "PyTorch",
            "Prompt Engineering",
            "Embeddings",
            "Retrieval-Augmented Generation (RAG)",
        ],
        "projects": [
            "Spam detection",
            "Log anomaly detection",
            "Image classification",
            "Document intelligence",
            "AI assistants",
        ],
        "assessments": None,
    },
    {
        "phase_number": 5,
        "name": "AI-Powered Cybersecurity",
        "goal": "Combine AI with cybersecurity.",
        "subjects": [
            "AI for Security Operations",
            "Threat Detection using Machine Learning",
            "Security Automation",
            "AI Security",
            "Prompt Injection",
            "LLM Security",
            "Model Security",
            "AI Agent Security",
            "Threat Intelligence",
            "AI Risk Assessment",
        ],
        "projects": [
            "AI Security Assistant",
            "Security Chatbot",
            "Threat Intelligence Platform",
            "Log Analysis AI",
            "Security Dashboard",
            "Security Automation Workflows",
        ],
        "assessments": None,
    },
    {
        "phase_number": 6,
        "name": "Production Engineering",
        "goal": "Deploy secure AI systems professionally.",
        "subjects": [
            "Docker",
            "Kubernetes",
            "Cloud Fundamentals",
            "CI/CD",
            "Monitoring",
            "Logging",
            "Identity & Access Management",
            "Production Deployment",
        ],
        "projects": [
            "Deploy AI applications",
            "Secure cloud applications",
            "Production monitoring",
            "End-to-end engineering project",
        ],
        "assessments": None,
    },
]


def seed_curriculum() -> dict:
    """One-time setup -- inserts all 6 phases + subjects from
    CURRICULUM_SEED. Safe to call again (checks for existing phases
    first, won't duplicate)."""
    from shared.scoped_db import get_scoped_client

    client = get_scoped_client("learning_agent")
    existing = client.table("curriculum_phases").select("phase_number").execute()
    if existing.data:
        return {"seeded": False, "reason": f"Already seeded ({len(existing.data)} phase(s) exist)."}

    for phase_data in CURRICULUM_SEED:
        phase = (
            client.table("curriculum_phases")
            .insert(
                {
                    "phase_number": phase_data["phase_number"],
                    "name": phase_data["name"],
                    "goal": phase_data["goal"],
                    "projects": phase_data["projects"],
                    "assessments": phase_data["assessments"],
                }
            )
            .execute()
            .data[0]
        )

        for i, subject_name in enumerate(phase_data["subjects"]):
            client.table("curriculum_subjects").insert(
                {
                    "phase_id": phase["id"],
                    "name": subject_name,
                    "sequence_order": i,
                }
            ).execute()

    return {"seeded": True, "phases": len(CURRICULUM_SEED)}


def get_current_subject() -> dict:
    """The current subject is simply the first non-completed subject in
    phase/sequence order -- no separate pointer to keep in sync, just
    derived from real status each time."""
    from shared.scoped_db import get_scoped_client

    client = get_scoped_client("learning_agent")
    phases = client.table("curriculum_phases").select("*").order("phase_number").execute().data
    for phase in phases:
        subjects = (
            client.table("curriculum_subjects")
            .select("*")
            .eq("phase_id", phase["id"])
            .neq("status", "completed")
            .order("sequence_order")
            .limit(1)
            .execute()
            .data
        )
        if subjects:
            return {"found": True, "phase": phase, "subject": subjects[0]}
    return {"found": False}


def start_current_subject() -> dict:
    """Marks the current subject in_progress (if not_started) and
    stamps started_at -- doesn't error if already in_progress."""
    current = get_current_subject()
    if not current["found"]:
        return {"ok": False, "reason": "No subjects remaining -- curriculum complete, or not seeded yet."}

    subject = current["subject"]
    if subject["status"] == "not_started":
        from datetime import datetime

        from shared.scoped_db import get_scoped_client

        get_scoped_client("learning_agent").table("curriculum_subjects").update(
            {
                "status": "in_progress",
                "started_at": datetime.now(UTC).isoformat(),
            }
        ).eq("id", subject["id"]).execute()

    return {"ok": True, "phase": current["phase"], "subject": subject}


def mark_current_subject_complete() -> dict:
    from datetime import datetime

    from shared.scoped_db import get_scoped_client

    current = get_current_subject()
    if not current["found"]:
        return {"ok": False, "reason": "No current subject to complete."}

    get_scoped_client("learning_agent").table("curriculum_subjects").update(
        {
            "status": "completed",
            "completed_at": datetime.now(UTC).isoformat(),
        }
    ).eq("id", current["subject"]["id"]).execute()

    next_current = get_current_subject()
    return {"ok": True, "completed_subject": current["subject"]["name"], "next": next_current}


def get_progress_summary() -> dict:
    from shared.scoped_db import get_scoped_client

    client = get_scoped_client("learning_agent")
    all_subjects = client.table("curriculum_subjects").select("status").execute().data
    total = len(all_subjects)
    completed = sum(1 for s in all_subjects if s["status"] == "completed")

    current = get_current_subject()
    return {
        "total_subjects": total,
        "completed_subjects": completed,
        "percent_complete": round(100 * completed / total, 1) if total else 0,
        "current_phase": current["phase"]["name"] if current["found"] else None,
        "current_subject": current["subject"]["name"] if current["found"] else None,
    }
