"""Compare bonus-claim checks on labeled cases. Usage: run_benchmark.py [dev|heldout]"""
import pathlib, sys, time
root = pathlib.Path(__file__).resolve().parent
sys.path[:0] = [str(root), str(root.parent)]
from bonus_verifier import verify_claim

# Keywords copied from PR #329 BONUS_KEYWORD_MAP; #242's list behaves the same on these cases.
PR329 = {"gsoc": ["google summer of code", "gsoc"],
         "girl_script": ["girl script summer of code", "girlscript", "gssoc"],
         "founder": ["founder", "co-founder", "cofounder"]}


def v(c):
    return verify_claim(c[0], c[2], c[3] if len(c) > 3 else None)


def keyword(c):
    words = PR329.get(c[0])
    return "keep" if words is None or any(w in c[2].lower() for w in words) else "remove"


def report(cases):
    bad = [c for c in cases if c[1] == "unsupported"]
    good = [c for c in cases if c[1] == "supported"]
    print(f"{'method':<18}{'false auto-kept':>17}{'valid auto-removed':>20}{'sent to review':>16}")
    for name, fn in [("keyword PR #329", keyword), ("graded v2", lambda c: v(c).action)]:
        fk = sum(fn(c) == "keep" for c in bad); vr = sum(fn(c) == "remove" for c in good)
        rv = sum(fn(c) == "review" for c in cases)
        print(f"{name:<18}{f'{fk}/{len(bad)}':>17}{f'{vr}/{len(good)}':>20}{f'{rv}/{len(cases)}':>16}")


split = sys.argv[1] if len(sys.argv) > 1 else "dev"
cases = __import__(f"cases_{split}").CASES
report(cases)
print("\nserious errors:")
for c in cases:
    r = v(c)
    if (c[1] == "supported" and r.action == "remove") or (c[1] == "unsupported" and r.action == "keep"):
        print(f"  [{c[0]}|{c[1]}|{r.grade} {r.score}] {c[2]!r}")
t = time.perf_counter()
_ = [v(c) for c in cases]
print(f"\nspeed: {(time.perf_counter()-t)/len(cases)*1000:.2f} ms per claim")
