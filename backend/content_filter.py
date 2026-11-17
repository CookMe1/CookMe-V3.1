"""Blocks phone numbers, email addresses, web links, social handles and profanity
in anything users publish (public recipes, comments, replies).

Detection is deliberately a bit stricter than a plain regex: it also catches the usual
tricks (``name (at) gmail (dot) com``, ``0 7 7 0 0 ...``, ``f.u.c.k``, ``sh1t``,
spelled-out digits). It never inspects private data, only text a user chooses to publish.
"""
import re
import unicodedata

MESSAGES = {
    "phone": "Please don't include phone numbers.",
    "email": "Please don't include email addresses.",
    "link": "Please don't include web links or website names.",
    "handle": "Please don't include social media handles or ask people to contact you elsewhere.",
    "profanity": "That contains language we don't allow. Please reword it.",
}

_EMAIL = re.compile(r"[\w.+-]+\s*@\s*[\w-]+(?:\s*\.\s*[\w-]+)+")
_EMAIL_WORDS = re.compile(
    r"[\w.+-]+\s*(?:\(at\)|\[at\]|\{at\}|\bat\b)\s*[\w-]+\s*(?:\(dot\)|\[dot\]|\{dot\}|\bdot\b|\.)\s*[a-z]{2,}", re.I)
_TLDS = r"(?:com|net|org|io|co|uk|es|app|me|ly|info|biz|xyz|shop|store|link|tv|gl|be|to|fr|de|it|us|ca|au|in|pk|ae|online|site|blog|page)"
_LINK = re.compile(
    r"https?://|www\.|\b[a-z0-9-]{2,}\s*(?:\.|\(dot\)|\[dot\]|\bdot\b)\s*" + _TLDS + r"\b", re.I)
_HANDLE = re.compile(
    r"(?<![\w@])@\w{3,}|\b(?:whats\s*app|telegram|snap\s*chat|we\s*chat|viber|kik|dm\s+me|pm\s+me|"
    r"(?:message|contact|text|call|ring|add|follow)\s+me\b)", re.I)
_DIGIT_RUN = re.compile(r"\+?\(?\d(?:[\s.\-()/]{0,2}\d){7,}")
_NUM_WORDS = {"zero", "oh", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
              "double", "triple", "cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete",
              "ocho", "nueve"}

# English, Spanish, Hindi/Urdu. Whole words only (so "cocktail", "class", "scunthorpe" are fine).
_BAD = {
    "fuck", "fucks", "fucked", "fucker", "fuckers", "fucking", "motherfucker", "shit", "shits", "shitty",
    "bullshit", "bitch", "bitches", "bastard", "cunt", "cunts", "wanker", "twat", "prick", "asshole",
    "arsehole", "slut", "whore", "pussy", "nigger", "nigga", "faggot", "fag", "retard", "retarded",
    "paki", "spic", "chink", "kike", "tranny", "dickhead", "cum", "jizz", "porn", "porno", "nazi",
    "puta", "puto", "mierda", "joder", "coño", "cono", "cabron", "cabrón", "gilipollas", "hijoputa",
    "pendejo", "verga", "chingar", "maricon", "maricón", "polla", "capullo", "zorra",
    "madarchod", "bhenchod", "behenchod", "chutiya", "chutiye", "gandu", "harami", "haramzada",
    "randi", "bhosdike", "lauda", "lund", "kutta", "kamina", "kuttiya",
}
_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s", "!": "i", "€": "e"})


def _fold(text: str) -> str:
    t = unicodedata.normalize("NFKD", text)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return t.lower()


def _has_profanity(text: str) -> bool:
    t = _fold(text)
    words = re.findall(r"[^\W_]+(?:['’][^\W_]+)?", t)
    bad = {_fold(b) for b in _BAD}
    for w in words:
        if w in bad or w.translate(_LEET) in bad:
            return True
    # f.u.c.k / f u c k / f-u-c-k : runs of single letters joined together
    for m in re.finditer(r"(?:\b[^\W\d_][\s.\-_*]+){2,}[^\W\d_]\b", t):
        joined = re.sub(r"[^a-z]", "", m.group(0))
        if joined in bad or any(joined.endswith(b) and len(b) >= 4 for b in bad):
            return True
    # f*ck, sh!t, s**t : masked with symbols
    for w in re.findall(r"\S+", t):
        if re.search(r"[*#%]", w):
            stem = re.sub(r"[^a-z*#%]", "", w)
            for b in bad:
                if len(b) == len(stem) and len(b) >= 4 and all(s in "*#%" or s == c for s, c in zip(stem, b)):
                    return True
    return False


def _has_spoken_number(text: str) -> bool:
    run = 0
    for w in re.findall(r"[a-z]+", _fold(text)):
        run = run + 1 if w in _NUM_WORDS else 0
        if run >= 7:
            return True
    return False


def problems(text: str) -> list:
    """Return [{'code', 'message'}] for everything in ``text`` that may not be published."""
    if not text:
        return []
    found = []

    def add(code):
        found.append({"code": code, "message": MESSAGES[code]})

    if _EMAIL.search(text) or _EMAIL_WORDS.search(text):
        add("email")
    flat = re.sub(r"[​-‏⁠]", "", text)
    digits_hit = False
    for m in _DIGIT_RUN.finditer(flat):
        if sum(c.isdigit() for c in m.group(0)) >= 9 and "\n" not in m.group(0):
            digits_hit = True
    if digits_hit or _has_spoken_number(flat):
        add("phone")
    if _LINK.search(flat):
        add("link")
    if _HANDLE.search(flat):
        add("handle")
    if _has_profanity(flat):
        add("profanity")
    return found


def first_message(text: str):
    p = problems(text)
    return p[0]["message"] if p else None
