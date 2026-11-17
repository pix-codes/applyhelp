from app.models import CandidateProfile, Job, JobSkill
from app.services.matching.matcher import JobMatcher


def test_job_matcher_skill_and_nepal():
    candidate = CandidateProfile(
        full_name="Jane Doe",
        email="jane@example.com",
        location="Nepal",
        technical_skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
        preferred_job_titles=["Backend Engineer"],
    )

    job = Job(
        title="Senior Backend Engineer",
        description="Looking for Python and FastAPI expert to scale microservices",
        geographic_eligibility="Worldwide",
        nepal_eligible=True,
        skills=[JobSkill(skill_name="Python"), JobSkill(skill_name="Docker")],
    )

    score, reasons = JobMatcher.calculate_match(candidate, job)
    assert score >= 70.0
    assert any("Nepal" in r for r in reasons)
    assert any("Matching technical skills" in r for r in reasons)
