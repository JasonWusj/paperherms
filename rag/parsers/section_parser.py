from __future__ import annotations

import re

from rag.models import PaperSection


SECTION_ALIASES = {
    "abstract": "Abstract",
    "introduction": "Introduction",
    "background": "Background",
    "related work": "Related Work",
    "method": "Method",
    "methods": "Method",
    "methodology": "Method",
    "approach": "Method",
    "experiments": "Experiments",
    "experiment": "Experiments",
    "experimental setup": "Experiments",
    "results": "Results",
    "discussion": "Discussion",
    "limitations": "Limitations",
    "limitation": "Limitations",
    "conclusion": "Conclusion",
    "conclusions": "Conclusion",
    "references": "References",
}


class SectionParser:
    _heading_re = re.compile(
        r"^\s*(?:(?P<num>\d+(?:\.\d+)*)\.?\s+)?(?P<title>"
        r"Abstract|Introduction|Background|Related Work|Method|Methods|Methodology|Approach|"
        r"Experiments?|Experimental Setup|Results|Discussion|Limitations?|Conclusions?|References"
        r")\s*$",
        re.IGNORECASE,
    )

    def parse(self, text: str) -> list[PaperSection]:
        lines = text.splitlines()
        headings: list[tuple[int, str, int]] = []

        for index, line in enumerate(lines):
            match = self._heading_re.match(line.strip())
            if match:
                title = SECTION_ALIASES[match.group("title").lower()]
                level = match.group("num").count(".") + 1 if match.group("num") else 1
                headings.append((index, title, level))

        if not headings:
            content = "\n".join(line.rstrip() for line in lines).strip()
            return [PaperSection(title="Full Text", content=content)] if content else []

        sections: list[PaperSection] = []
        for position, (line_index, title, level) in enumerate(headings):
            next_index = headings[position + 1][0] if position + 1 < len(headings) else len(lines)
            content = "\n".join(lines[line_index + 1 : next_index]).strip()
            if content:
                sections.append(PaperSection(title=title, content=content, level=level))
        return sections
