"""Measure real LLM bonus decisions through the actual ResumeEvaluator.

Usage: python benchmark/run_real_scoring.py --per-group 5 --controls 20 --out real_results.jsonl
Interrupted runs resume from the output file. Uses DEFAULT_MODEL from your .env.
"""

import argparse, collections, json, pathlib, random, re, sys

root = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(root), str(root.parent)]
import cases_heldout, cases_nearword
from bonus_verifier import (
    VERIFIED_KEYS,
    apply_bonus_verification,
    recover_missed_bonuses,
)
from evaluator import ResumeEvaluator
from models import build_evaluation_model
from roles import load_role

BASES = [
    "Name: A. Kumar\nB.Tech Computer Science, 2027\nSkills: Python, SQL, React\nProjects: Inventory API with FastAPI and Postgres; chat app with WebSockets.",
    "Name: R. Sharma\nB.E. Electronics, 2026\nSkills: Java, Spring Boot, MySQL\nProjects: Library management system; expense tracker Android app.",
    "Name: S. Reddy\nB.Tech Information Technology, 2027\nSkills: TypeScript, Next.js, Docker\nProjects: Portfolio generator; image classifier deployed on Vercel.",
    "Name: P. Nair\nB.Tech Computer Engineering, 2026\nSkills: C++, Go, Redis\nProjects: Key-value store; URL shortener with caching.",
    "Name: M. Khan\nB.Tech Computer Science, 2027\nExperience: Software intern at a Series A startup, 3 months.\nOpen source: 2 docs PRs to a small CLI.\nAwards: 2nd place in college hackathon; 4-star CodeChef.\nProjects: Summer of learning blog; startup landing page template.",
    "Name: T. Iyer\nB.E. Information Science, 2026\nExperience: Backend intern at an early-stage fintech company.\nLeadership: President of the coding club; organised a 200-person hackathon.\nProjects: Payment gateway clone; Google Maps based delivery tracker.",
    "Name: L. Das\nB.Tech Electronics, 2027\nExperience: Google Developer Student Club lead.\nOpen source: active on GitHub, 300 contributions this year.\nAwards: Rank 120 in LeetCode Weekly Contest; Hacktoberfest finisher.\nProjects: Engineer productivity dashboard; first-year course planner.",
    "Name: V. Rao\nB.Tech Data Science, 2026\nExperience: Data intern at a 50-person startup, worked with the founders on metrics.\nAwards: Top 5% in Kaggle competition; winner of a campus coding contest.\nProjects: Resume parser; Girls in Tech volunteer website.",
]


OTHER_TRUE = {
    "gsoc": r"google summer of code|\bgsoc\b",
    "girl_script": r"girl\s?script summer of code|\bgssoc\b",
}


def build_runs(per_group, controls, seed):
    rng = random.Random(seed)
    groups = collections.defaultdict(list)
    for case in cases_heldout.CASES + cases_nearword.CASES:
        groups[case[:2]].append(case)
    runs = [
        {
            "id": f"control-{i}",
            "key": None,
            "label": "control",
            "rank": None,
            "text": BASES[i % len(BASES)],
        }
        for i in range(controls)
    ]
    for (key, label), cases in sorted(groups.items()):
        for n, case in enumerate(rng.sample(cases, min(per_group, len(cases)))):
            runs.append(
                {
                    "id": f"{key}-{label}-{n}",
                    "key": key,
                    "label": label,
                    "rank": case[3] if len(case) > 3 else None,
                    "text": f"{BASES[n % len(BASES)]}\nExperience and awards: {case[2]}",
                }
            )
    return runs


def score_once(evaluator, run):
    evaluation = evaluator.evaluate_resume(run["text"])
    items = evaluation.bonus_points.items
    before = {k: getattr(items, k).points for k in VERIFIED_KEYS}
    verdicts = {v.key: v for v in apply_bonus_verification(evaluation, run["text"])}
    recovered = [
        v.key for v in recover_missed_bonuses(evaluation, run["text"], evaluator.role)
    ]
    return {
        **run,
        "before": before,
        "rank_correction": evaluator.rank_correction,
        "recovered": recovered,
        "verdicts": {
            k: {"grade": v.grade, "score": v.score, "action": v.action}
            for k, v in verdicts.items()
        },
    }


def award_is_true(row, key):
    """Target claims use their label. Any other bonus is false unless the line truly earns it."""
    if key == row["key"]:
        return row["label"] == "supported"
    line = row["text"].split("awards: ")[-1]
    return bool(key in OTHER_TRUE and re.search(OTHER_TRUE[key], line, re.I))


def summarize(rows):
    out = collections.Counter()
    for r in rows:
        if r.get("error"):
            out["errors"] += 1
            continue
        out["scored"] += 1
        if r.get("rank_correction"):
            out["rank corrections"] += 1
        if r["label"] == "supported" and not r["before"][r["key"]]:
            out["valid claims missed by model"] += 1
        for k in r.get("recovered", []):
            out[
                f"recovered: {'valid' if r['key'] and award_is_true(r, k) else 'false'}"
            ] += 1
        for k in VERIFIED_KEYS:
            if r["before"][k]:
                truth = "valid" if r["key"] and award_is_true(r, k) else "false"
                out[f"{truth} awards"] += 1
                out[f"{truth}: {r['verdicts'][k]['action']}"] += 1
    return dict(sorted(out.items()))


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--per-group", type=int, default=5)
    a.add_argument("--controls", type=int, default=20)
    a.add_argument("--seed", type=int, default=7)
    a.add_argument("--out", default="real_results.jsonl")
    a.add_argument("--model", default=None, help="Model name from providers.json")
    args = a.parse_args()
    role = load_role("software_engineering_intern")
    options = {"model_name": args.model} if args.model else {}
    evaluator = ResumeEvaluator(role, build_evaluation_model(role), **options)
    evaluator.verify_bonuses = False
    path = pathlib.Path(args.out)
    rows = (
        [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()]
        if path.exists()
        else []
    )
    done = {r["id"] for r in rows}
    runs = [
        r
        for r in build_runs(args.per_group, args.controls, args.seed)
        if r["id"] not in done
    ]
    for i, run in enumerate(runs, 1):
        try:
            row = score_once(evaluator, run)
        except Exception as e:
            row = {**run, "error": str(e)[:200]}
        rows.append(row)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        print(
            f"{i}/{len(runs)} {run['id']} {'ERROR' if row.get('error') else 'ok'}",
            flush=True,
        )
    print(json.dumps(summarize(rows), indent=2))


if __name__ == "__main__":
    main()
