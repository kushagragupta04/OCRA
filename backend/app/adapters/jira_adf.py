from typing import Dict, Any, List, Optional


class JiraADFBuilder:
    """
    Constructs Atlassian Document Format (ADF) JSON structures
    for rich issue descriptions, evidence quotes, and audit comments.
    """

    @staticmethod
    def doc(content: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "version": 1,
            "type": "doc",
            "content": content
        }

    @staticmethod
    def paragraph(text: str, marks: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        text_node = {"type": "text", "text": text}
        if marks:
            text_node["marks"] = marks
        return {
            "type": "paragraph",
            "content": [text_node]
        }

    @staticmethod
    def heading(text: str, level: int = 3) -> Dict[str, Any]:
        return {
            "type": "heading",
            "attrs": {"level": level},
            "content": [{"type": "text", "text": text}]
        }

    @staticmethod
    def blockquote(text: str, cite: Optional[str] = None) -> Dict[str, Any]:
        content = [{"type": "text", "text": f'"{text}"'}]
        if cite:
            content.append({
                "type": "text",
                "text": f" — {cite}",
                "marks": [{"type": "em"}]
            })
        return {
            "type": "blockquote",
            "content": [{
                "type": "paragraph",
                "content": content
            }]
        }

    @staticmethod
    def panel(text: str, panel_type: str = "info") -> Dict[str, Any]:
        """panel_type can be: info, note, warning, success, error"""
        return {
            "type": "panel",
            "attrs": {"panelType": panel_type},
            "content": [{
                "type": "paragraph",
                "content": [{"type": "text", "text": text}]
            }]
        }

    @classmethod
    def build_action_description(
        cls,
        summary: str,
        description: Optional[str],
        meeting_title: str,
        evidence_items: List[Dict[str, Any]],
        confidence: float,
        reason: str
    ) -> Dict[str, Any]:
        blocks = []
        
        # Main description
        if description:
            blocks.append(cls.paragraph(description))
        else:
            blocks.append(cls.paragraph(summary))

        # Panel header for OCRA Traceability
        blocks.append(cls.panel(
            f"🤖 Created automatically by OCRA Engineering Agent from meeting: {meeting_title} (Confidence: {int(confidence * 100)}%)",
            "info"
        ))

        # Rationale
        blocks.append(cls.heading("Meeting Rationale & Context", level=3))
        blocks.append(cls.paragraph(reason))

        # Evidence blockquotes
        if evidence_items:
            blocks.append(cls.heading("Meeting Evidence & Excerpts", level=4))
            for ev in evidence_items:
                time_str = f"{ev.get('start_ms', 0) // 1000}s - {ev.get('end_ms', 0) // 1000}s"
                blocks.append(cls.blockquote(
                    ev.get("evidence_text", ""),
                    f"Timestamp: {time_str}"
                ))

        return cls.doc(blocks)

    @classmethod
    def build_comment_adf(
        cls,
        comment_text: str,
        meeting_title: Optional[str] = None,
        evidence_quote: Optional[str] = None,
        timestamp_str: Optional[str] = None
    ) -> Dict[str, Any]:
        blocks = [cls.paragraph(comment_text)]
        if evidence_quote:
            blocks.append(cls.blockquote(
                evidence_quote,
                f"Source: {meeting_title or 'Engineering Sync'} ({timestamp_str or 'Recorded'})"
            ))
        return cls.doc(blocks)

    @classmethod
    def build_conflict_comment(
        cls,
        new_decision: str,
        evidence_text: str,
        meeting_title: str,
        reviewer: Optional[str] = None
    ) -> Dict[str, Any]:
        blocks = [
            cls.panel(
                "⚠️ Scope Change / Decision Update flagged by OCRA from engineering meeting discussion.",
                "warning"
            ),
            cls.heading("New Engineering Decision:", level=3),
            cls.paragraph(new_decision),
            cls.heading("Meeting Excerpt & Evidence:", level=4),
            cls.blockquote(evidence_text, f"Meeting: {meeting_title}"),
        ]
        if reviewer:
            blocks.append(cls.paragraph(f"Reviewed & Approved by: {reviewer}", marks=[{"type": "em"}]))
        return cls.doc(blocks)
