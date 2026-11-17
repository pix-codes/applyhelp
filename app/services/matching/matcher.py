
from app.models import CandidateProfile, Job
from app.utils.normalization import normalize_string


class JobMatcher:
    """
    Deterministic matching engine between candidate profile and a vacancy.
    Evaluates:
    1. Technical skill overlap
    2. Role & title suitability
    3. Geographic eligibility (Nepal priority)
    4. Seniority / Experience fit
    """

    @staticmethod
    def calculate_match(candidate: CandidateProfile, job: Job) -> tuple[float, list[str]]:
        reasons: list[str] = []
        score = 0.0

        # 1. Geographic Eligibility (Weight: 35%)
        if job.nepal_eligible:
            score += 35.0
            reasons.append("Eligible for candidates located in Nepal (+35%)")
        elif job.geographic_eligibility == "Worldwide":
            score += 30.0
            reasons.append("Worldwide remote vacancy (+30%)")
        elif job.geographic_eligibility == "Unknown":
            score += 10.0
            reasons.append("Geographic eligibility is unspecified/unknown (+10%)")
        else:
            reasons.append(f"Restricted geographic eligibility: {job.location_restrictions} (0%)")

        # 2. Skill Overlap (Weight: 40%)
        candidate_skills = {s.lower().strip() for s in (candidate.technical_skills or [])}
        job_skills = {s.skill_name.lower().strip() for s in (job.skills or [])}

        # Also search job description for candidate skills if job has few declared skills
        desc_lower = (job.description or "").lower()
        matched_skills = set()

        for c_skill in candidate_skills:
            if c_skill in job_skills or (len(c_skill) > 2 and c_skill in desc_lower):
                matched_skills.add(c_skill)

        if candidate_skills:
            skill_ratio = len(matched_skills) / min(len(candidate_skills), 8)
            skill_score = min(skill_ratio * 40.0, 40.0)
            score += skill_score
            if matched_skills:
                reasons.append(f"Matching technical skills: {', '.join(sorted(matched_skills))} (+{round(skill_score, 1)}%)")
        else:
            score += 15.0

        # 3. Title / Role Suitability (Weight: 25%)
        pref_titles = [normalize_string(t) for t in (candidate.preferred_job_titles or [])]
        job_title_norm = normalize_string(job.title)

        title_matched = False
        for pt in pref_titles:
            if pt and (pt in job_title_norm or job_title_norm in pt):
                title_matched = True
                break

        if title_matched:
            score += 25.0
            reasons.append("Matches preferred job title profile (+25%)")
        else:
            # Partial match on words (e.g. 'engineer', 'backend')
            common_words = set(job_title_norm.split()) & {"engineer", "developer", "backend", "fullstack", "platform"}
            if common_words:
                score += 15.0
                reasons.append(f"Related engineering discipline: {', '.join(common_words)} (+15%)")
            else:
                score += 5.0

        final_score = min(round(score, 1), 100.0)
        return final_score, reasons
