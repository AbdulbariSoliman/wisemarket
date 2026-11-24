import re
from typing import List


# "May contain traces of ..." and shared-facility statements (EN/DE/FR/IT).
# Shared by the parser (to keep the statement as one item) and the matcher
# (to ignore it for diet verdicts, but keep it for allergen / gluten warnings).
TRACE_PATTERN = re.compile(
    r"(peut contenir|peux contenir|peuvent contenir|peut aussi contenir|traces? (?:de|d'|éventuelles)|"
    r"fabriqué dans un atelier|fabriqué dans une usine|"
    r"may contain|may also contain|traces? of|"
    r"made in a factory|produced in a factory|made in a facility|produced in a facility|"
    r"kann spuren|kann .{0,40}?enthalten|spuren von|"
    r"hergestellt in einem betrieb|in einem betrieb hergestellt|"
    r"può contenere|tracce di|prodotto in uno stabilimento)",
    re.IGNORECASE,
)


class IngredientParser:
    """
    Parse raw ingredient label text into a normalized flat list.

    Version 1 goals:
    - lowercase
    - split outside parentheses
    - extract sub-ingredients
    - remove percentages and simple weights
    - normalize E-numbers
    - preserve order
    - deduplicate without losing order
    """

    def __init__(self) -> None:
        self.e_number_pattern = re.compile(
            r"\bE[\s-]?(\d{3,4}[a-z]?)\b",
            re.IGNORECASE,
        )
        self.trace_pattern = TRACE_PATTERN
        self.junk_pattern = re.compile(
            r"\d+\s?(%|g|kg|mg|ml|l|cl|dl)",
            re.IGNORECASE,
        )

    def _split_outside_parentheses(self, text: str) -> List[str]:
        parts: List[str] = []
        current: List[str] = []
        depth = 0

        for ch in text:
            if ch in "([{":
                depth += 1
                current.append(ch)
            elif ch in ")]}":
                depth = max(0, depth - 1)
                current.append(ch)
            elif ch in ",;" and depth == 0:
                part = "".join(current).strip()
                if part:
                    parts.append(part)
                current = []
            else:
                current.append(ch)

        tail = "".join(current).strip()
        if tail:
            parts.append(tail)

        return parts

    def _extract_parentheses_content(self, text: str) -> List[str]:
        results: List[str] = []
        stack = []
        start = None

        for i, ch in enumerate(text):
            if ch in "([{":
                if not stack:
                    start = i + 1
                stack.append(ch)
            elif ch in ")]}" and stack:
                stack.pop()
                if not stack and start is not None:
                    results.append(text[start:i].strip())
                    start = None

        return results

    def _normalize_token(self, item: str) -> str:
        item = item.lower().strip()

        # Remove parenthesized content from the main token
        item = re.sub(r"[\(\[\{][^)\]}]*[\)\]\}]", "", item).strip()
        item = item.strip("()[]{} ")

        # Normalize E-numbers: E 322 / E-322 -> e322
        item = self.e_number_pattern.sub(lambda m: f"e{m.group(1).lower()}", item)

        # Remove simple percentages / weights
        item = self.junk_pattern.sub("", item)

        # Remove formatting artifacts
        item = item.replace("*", " ").replace(".", " ")

        # Collapse whitespace
        item = re.sub(r"\s+", " ", item).strip()

        return item

    def _split_trace_statement(self, text: str):
        """Split 'may contain traces of ...' off the ingredient list."""
        m = self.trace_pattern.search(text)
        if not m:
            return text, ""
        return text[: m.start()], text[m.start():]

    def normalize(self, raw_text: str) -> List[str]:
        if not raw_text or not raw_text.strip():
            return []

        # Open Food Facts marks allergens like _blé_ / _milk_
        raw_text = raw_text.replace("_", " ")
        # OCR often reads a lower-case "l" as a capital "I" ("SeeIachsfiIet")
        raw_text = re.sub(r"(?<=[a-zäöüßéèàç])I(?=[a-zäöüßéèàç])", "l", raw_text)
        # "œuf" and "oeuf" are the same word
        raw_text = raw_text.replace("œ", "oe").replace("Œ", "Oe")

        # Keep a "may contain ..." statement as ONE item, so it can be
        # recognised as a trace warning instead of real ingredients.
        raw_text, trace_text = self._split_trace_statement(raw_text)

        main_parts = self._split_outside_parentheses(raw_text)
        nested_parts = self._extract_parentheses_content(raw_text)

        combined: List[str] = []
        combined.extend(main_parts)
        if trace_text.strip():
            combined.append(re.sub(r"[()\[\]{}]", " ", trace_text))

        for nested in nested_parts:
            combined.extend(self._split_outside_parentheses(nested))

        cleaned: List[str] = []
        seen = set()

        for item in combined:
            norm = self._normalize_token(item)
            if norm and len(norm) > 1 and norm not in seen:
                seen.add(norm)
                cleaned.append(norm)

        return cleaned
