from __future__ import annotations


def build_cover_letter(company: str, role: str, highlights: list[str]) -> str:
    lines = [
        f"Dear Hiring Team at {company},",
        "",
        f"I am excited to apply for the {role} role.",
    ]
    for h in highlights[:3]:
        lines.append(f"- {h}")
    lines.extend(["", "Sincerely,", "Candidate"])
    return "\n".join(lines)
