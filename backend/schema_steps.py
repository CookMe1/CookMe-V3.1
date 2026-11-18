"""Read recipe steps out of schema.org `recipeInstructions`, whatever shape a site uses:
a string, a list of strings, HowToStep objects, HowToSection groups, an ItemList, or one nested object."""
import html
import re


def _clean(text) -> str:
    text = re.sub(r"</?(?:p|br|li|ul|ol|div)\b[^>]*>", " ", str(text), flags=re.I)   # block tags break words
    text = html.unescape(re.sub(r"<[^>]+>", "", text))                         # inline tags (b, i, a) vanish
    return re.sub(r"\s+", " ", text).strip()


def extract_steps(raw) -> list:
    steps = []

    def walk(node):
        if node is None:
            return
        if isinstance(node, str):
            parts = [p for p in re.split(r"\n+", node) if p.strip()]
            steps.extend(c for c in (_clean(p) for p in parts) if c)
        elif isinstance(node, list):
            for n in node:
                walk(n)
        elif isinstance(node, dict):
            kids = node.get("itemListElement") or node.get("steps")
            if kids:                      # a section or list: read its steps, not its field names
                walk(kids)
                return
            text = node.get("text") or node.get("name") or ""
            c = _clean(text)
            if c:
                steps.append(c)

    walk(raw)
    return steps
