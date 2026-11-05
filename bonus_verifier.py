"""Graded, near-wording evidence check for LLM-awarded bonus claims.

Three layers, cheapest first:
1. Near-term match: exact aliases plus fuzzy matching for typos and spacing.
2. Meaning grade: sentence similarity to qualifying and non-qualifying examples.
3. Safe action: remove only when no evidence or a hard fact fails. Uncertain wording
   goes to human review, so context alone never takes points from a candidate.
"""

from dataclasses import dataclass
import re

from models import _allowed_bonus_points as allowed_bonus_points
from rapidfuzz import fuzz

try:
    import spacy

    NLP = spacy.load("en_core_web_md")
except (ImportError, OSError):
    NLP = None  # Meaning grade is skipped; weak matches go to human review.

SPLIT = re.compile(r"(?<=[.!?])\s+|\n+|;\s*")
ROLE = r"(engineer|developer)"
ORD = r"(first|second|third|fourth|fifth|1st|2nd|3rd|\d+th)"

TERMS = {
    "gsoc": ["google summer of code", "gsoc", "g soc", "google soc"],
    "girl_script": [
        "girl script summer of code",
        "girlscript summer of code",
        "gssoc",
        "gs soc",
        "girlscript soc",
    ],
    "orchestrate": ["hackerrank orchestrate", "hacker rank orchestrate"],
}
PATTERNS = {
    "founder": rf"\bco ?found(er|ed)\b|\bfound(er|ed)\b|\bfounding (ceo|partner)\b|\bco owner\b|\bowner\b.*\b(pvt|ltd|inc|llp|startup)\b|\b(pvt|ltd|inc|llp|startup)\b.*\bceo\b|\bceo\b.*\b(pvt|ltd|inc|llp|startup)\b|\bstarted\b.*\b(pvt|ltd|inc|llp|startup|technologies)\b",
    "early_engineer": rf"\bfounding( [\w]+){{0,2}} {ROLE}\b|\b(very )?first( [\w]+){{0,2}} {ROLE}\b|\bfirst engineering hire\b|\b{ORD} {ROLE}\b|\b(engineer|developer|employee) (no )?\d+\b|\bfirst \d+ (engineers|employees)\b|\binitial \d+ engineers\b|\bearly hire\b|\bearly employee\b",
}
POSITIVE = {
    "gsoc": [
        "contributor in Google Summer of Code",
        "selected as a GSoC student developer",
        "GSoC mentor for an open source organisation",
    ],
    "girl_script": [
        "contributor in Girl Script Summer of Code",
        "GSSoC project admin",
        "GSSoC mentor and contributor",
    ],
    "founder": [
        "founder and CEO of a technology startup",
        "co-founder of a funded company",
        "started a company with paying customers",
    ],
    "early_engineer": [
        "founding engineer at a seed stage startup",
        "one of the first engineers at a startup",
        "early employee and software engineer at a startup",
    ],
}
NEGATIVE = {
    "gsoc": [
        "applied to the program but was not selected",
        "attended a talk about the program",
        "preparing to apply next year",
        "wrote a blog with tips for applicants",
    ],
    "girl_script": [
        "applied to the program but was not selected",
        "attended a community meetup",
        "planning to join next year",
        "volunteered at an event",
    ],
    "founder": [
        "intern at a startup",
        "founder of a college club",
        "personal side project",
        "worked with the founders",
    ],
    "early_engineer": [
        "intern at a startup",
        "student in a college team",
        "engineer at a large company",
        "attended a talk by an engineer",
    ],
}
PARTICIPATION = re.compile(
    r"\b(contribut\w+|mentor|mentee|student|developer|scholar|participa\w+|selected|accepted"
    r"|project admin|completed|finished|passed)\b",
    re.I,
)
COMPANY = re.compile(
    r"\b(startup|company|pvt|ltd|inc|llc|llp|private limited|technologies|labs|studios|robotics|analytics)\b",
    re.I,
)
FOUNDER_CONTEXT = {
    "blog",
    "personal",
    "channel",
    "portfolio",
    "project",
    "app",
    "tool",
    "dream",
    "aspiring",
    "magazine",
    "fund",
}
HARD_INTENT = re.compile(
    r"\b(waitlisted|rejected|inspired by|helped|registered interest|applied to|applied for|not selected"
    r"|friend'?s|reviewer for)\b",
    re.I,
)
CONTEXT = {
    "club",
    "society",
    "council",
    "chapter",
    "university",
    "college",
    "intern",
    "aspiring",
    "mentor",
    "alumnus",
    "alumni",
}
MENTOR_ROLE = re.compile(r"\bmentor\b(?! ?ed)", re.I)
INTENT = {
    "apply",
    "prepare",
    "plan",
    "hope",
    "attend",
    "watch",
    "reject",
    "aspire",
    "register",
    "wish",
    "organise",
    "organize",
    "compare",
    "review",
}
ORCHESTRATE = re.compile(r"\bhacker ?rank orchestrate\b", re.I)
RANK_LABELLED = re.compile(
    r"\b(?:rank(?:ed)?|air|position|number)\s*[:#]?\s*#?(\d{1,5})\b", re.I
)
RANK_ORDINAL = re.compile(
    r"\b(?:placed|ranked|finished|secured)\s+(\d{1,5})(?:st|nd|rd|th)\b"
    r"|\b(\d{1,5})(?:st|nd|rd|th)\s+(?:rank|place|overall)\b",
    re.I,
)
GAP_BEFORE = re.compile(
    r"^(?:\s|,|:|-|\||\(|\)|in|at|the|on|rank|place|worldwide|overall|global|among|finalist)*$",
    re.I,
)
RIVALS = re.compile(
    r"\b(codeforces|leetcode|codechef|icpc|college|gate|atcoder|kaggle)\b", re.I
)


@dataclass(frozen=True)
class Verdict:
    key: str
    score: int
    grade: str
    action: str
    evidence: str


def _norm(text):
    return re.sub(r"\s+", " ", re.sub(r"[-_'’#.]", " ", text.lower())).strip()


def near_match(key, clause):
    """Return 0-1 strength for how closely the clause names the qualifying thing."""
    norm = _norm(clause)
    if key in PATTERNS:
        return 1.0 if re.search(PATTERNS[key], norm) else 0.0
    best = 0.0
    for term in TERMS[key]:
        if re.search(rf"\b{re.escape(term)}\b", norm):
            return 1.0
        if len(term) > 8:
            best = max(best, fuzz.partial_ratio(term, norm) / 100)
    if key == "gsoc" and "summer of code" in norm and "google" in norm:
        return 0.95
    if key == "girl_script" and "summer of code" in norm and "girl" in norm:
        return 0.95
    return best if best >= 0.9 else 0.0


_cache = {}


def _doc(text):
    return _cache.setdefault(text, NLP(text))


def meaning_margin(key, clause):
    if NLP is None:
        return -0.1
    doc = _doc(clause)
    sim = lambda items: max(doc.similarity(_doc(t)) for t in items)
    return sim(POSITIVE[key]) - sim(NEGATIVE[key])


def _blocked(clause, key=None):
    if key == "founder":
        words = set(re.findall(r"[a-z]+", clause.lower()))
        if words & FOUNDER_CONTEXT:
            return True
        clause = re.sub(r"\bregistered\b", "", clause, flags=re.I)
    if HARD_INTENT.search(clause):
        return True
    if NLP is None:
        words = set(re.findall(r"[a-z]+", clause.lower()))
        return bool(
            words
            & (
                INTENT
                | CONTEXT
                | {"applied", "not", "planning", "attended", "rejected"}
            )
        )
    doc = _doc(clause)
    return (
        any(t.dep_ == "neg" for t in doc)
        or any(t.pos_ == "VERB" and t.lemma_.lower() in INTENT for t in doc)
        or any(t.lemma_.lower() in CONTEXT for t in doc)
    )


def _grade(score):
    if score >= 80:
        return "A", "keep"
    if score >= 60:
        return "B", "keep"
    if score >= 40:
        return "C", "review"
    return "F", "remove"


def stated_rank(clause):
    """Return the Orchestrate rank stated in one clause, or None."""
    mention = ORCHESTRATE.search(clause)
    if not mention or RIVALS.search(clause):
        return None
    ranks = []
    for pattern in (RANK_LABELLED, RANK_ORDINAL):
        for match in pattern.finditer(clause):
            number = int(next(g for g in match.groups() if g))
            before = match.end() <= mention.start()
            if before and not GAP_BEFORE.match(clause[match.end() : mention.start()]):
                continue
            ranks.append(number)
    return min(ranks) if ranks else None


def orchestrate_rank(text):
    """Return the best Orchestrate rank stated anywhere in the source text."""
    clauses = [c.strip() for c in SPLIT.split(text or "") if c.strip()]
    ranks = [r for r in map(stated_rank, clauses) if r is not None]
    for first, second in zip(clauses, clauses[1:]):
        if ORCHESTRATE.search(first) and not ORCHESTRATE.search(second):
            joined = stated_rank(f"{first} {second}")
            if joined is not None and len(second) < 25:
                ranks.append(joined)
    return min(ranks) if ranks else None


def reconcile_ranked_bonus(evaluation_dict, source_text, role):
    """Set the Orchestrate rank and points from the source text, before validation.

    The model often returns a rank and points that disagree, which would otherwise fail
    the whole evaluation. A rank stated in the resume decides the tier; without one the
    bonus is 0, so ranks from other contests cannot qualify.
    Returns the model's original item when it was changed, otherwise None.
    """
    rule = next((r for r in role.bonus_rules if r["key"] == "orchestrate"), None)
    items = (evaluation_dict.get("bonus_points") or {}).get("items") or {}
    item = items.get("orchestrate")
    if rule is None or not isinstance(item, dict):
        return None
    rank = orchestrate_rank(source_text)
    tier = next(
        (
            t
            for t in rule["tiers"]
            if rank is not None and t["min_rank"] <= rank <= t["max_rank"]
        ),
        None,
    )
    resolved = (tier["points"], rank) if tier else (0, None)
    if (item.get("points"), item.get("rank")) == resolved:
        return None
    original = dict(item)
    item["points"], item["rank"] = resolved
    item["evidence"] = f"Rank taken from the resume. {item.get('evidence', '')}".strip()
    return original


def _score(key, clause, rank):
    strength = near_match(key, clause)
    if not strength:
        return 0
    if key == "orchestrate":
        return (
            90
            if rank is not None and stated_rank(clause) == rank and rank <= 500
            else 10
        )
    score = 60 + int(max(-20, min(30, meaning_margin(key, clause) * 200)))
    if strength < 1:
        score -= 5
    blocked = bool(HARD_INTENT.search(clause)) or (
        _blocked(clause, key) and not MENTOR_ROLE.search(clause)
    )
    if key == "founder" and not COMPANY.search(clause):
        blocked = True
    if blocked:
        return min(score, 55)
    if key in TERMS and PARTICIPATION.search(clause):
        score = max(score, 80 if strength == 1 else 65)
    return max(score, 40)


def verify_claim(key, text, rank=None):
    """Grade one awarded bonus against resume and GitHub text."""
    best, proof = 0, ""
    for clause in (c.strip() for c in SPLIT.split(text or "")):
        if clause:
            score = _score(key, clause, rank)
            if score > best:
                best, proof = score, clause
    if key == "orchestrate" and best < 40:
        joined = " ".join(c.strip() for c in SPLIT.split(text or ""))
        best = max(best, _score(key, joined, rank))
    grade, action = _grade(best)
    return Verdict(key, best, grade, action, proof)


VERIFIED_KEYS = ("gsoc", "girl_script", "orchestrate", "founder", "early_engineer")


def recover_missed_bonuses(evaluation, source_text, role):
    """Award a bonus the model missed when the resume shows grade A evidence.

    Uses the lowest qualifying points, leaving any higher judgement to a human.
    Orchestrate is handled by reconcile_ranked_bonus.
    """
    items = getattr(getattr(evaluation, "bonus_points", None), "items", None)
    recovered = []
    if items is None:
        return recovered
    for rule in role.bonus_rules:
        key = rule["key"]
        if key not in VERIFIED_KEYS or key == "orchestrate":
            continue
        item = getattr(items, key)
        if item.points:
            continue
        verdict = verify_claim(key, source_text)
        if verdict.grade == "A":
            item.points = min(p for p in allowed_bonus_points(rule) if p > 0)
            item.evidence = f"Recovered from resume: {verdict.evidence}"
            recovered.append(verdict)
    return recovered


def apply_bonus_verification(evaluation, source_text):
    """Check awarded bonuses in place and return one verdict per awarded claim.

    Claims graded F lose their points. Claims graded C keep them and are marked for review.
    Portfolio, LinkedIn, and blog bonuses are outside this check.
    """
    bonus = getattr(evaluation, "bonus_points", None)
    items = getattr(bonus, "items", None)
    verdicts = []
    if items is None:
        return verdicts
    for key in VERIFIED_KEYS:
        item = getattr(items, key, None)
        if item is None or not item.points:
            continue
        verdict = verify_claim(key, source_text, getattr(item, "rank", None))
        verdicts.append(verdict)
        if verdict.action == "remove":
            item.evidence = (
                f"Removed: no supporting evidence found. LLM said: {item.evidence}"
            )
            item.points = 0
            if hasattr(item, "rank"):
                item.rank = None
        elif verdict.action == "review":
            item.evidence = f"Needs human review ({verdict.score}/100). {item.evidence}"
    return verdicts
