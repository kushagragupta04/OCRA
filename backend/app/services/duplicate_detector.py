import re
from typing import List, Tuple, Optional, Dict, Any
from app.adapters import JiraAdapter, get_jira_adapter
from app.schemas.jira import JiraIssue


class DuplicateDetector:
    @staticmethod
    def compute_similarity(text1: str, text2: str) -> float:
        """
        Computes normalized Jaccard token and character bigram similarity between two text strings.
        """
        if not text1 or not text2:
            return 0.0

        def tokenize(text: str) -> set:
            cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
            tokens = [t for t in cleaned.split() if len(t) > 2 and t not in {"the", "and", "for", "with", "add", "set"}]
            return set(tokens)

        set1 = tokenize(text1)
        set2 = tokenize(text2)

        if not set1 or not set2:
            return 0.0

        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        jaccard = intersection / union if union > 0 else 0.0

        # Substring boost if one is a clean subset of the other
        t1_clean = " ".join(sorted(list(set1)))
        t2_clean = " ".join(sorted(list(set2)))
        if t1_clean in t2_clean or t2_clean in t1_clean:
            jaccard = max(jaccard, 0.85)

        return round(jaccard, 2)

    @classmethod
    async def evaluate_proposed_create(
        cls,
        summary: str,
        description: Optional[str],
        project_key: str = "PAY",
        jira: Optional[JiraAdapter] = None
    ) -> Tuple[str, Optional[JiraIssue], float]:
        """
        Searches existing Jira issues in project and classifies duplicate status:
        - NO_MATCH (< 0.50)
        - POSSIBLE_DUPLICATE (0.50 - 0.79)
        - STRONG_DUPLICATE (>= 0.80)
        """
        adapter = jira or get_jira_adapter()
        
        # Search candidate issues in project
        existing_issues = await adapter.search_issues(f"project = {project_key}", limit=50)

        best_score = 0.0
        best_match: Optional[JiraIssue] = None

        for issue in existing_issues:
            # Score against summary and description
            sim_summary = cls.compute_similarity(summary, issue.summary)
            sim_desc = cls.compute_similarity(description or "", issue.description or "")
            score = max(sim_summary, (sim_summary * 0.7 + sim_desc * 0.3))

            if score > best_score:
                best_score = score
                best_match = issue

        if best_score >= 0.80:
            return "STRONG_DUPLICATE", best_match, best_score
        elif best_score >= 0.50:
            return "POSSIBLE_DUPLICATE", best_match, best_score
        else:
            return "NO_MATCH", None, best_score
