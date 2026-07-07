import json, glob

files = sorted(glob.glob("eval/results/run_20260706T014533_r*.json"))
print(f"{len(files)} runs\n")

slices = {}
costs = []
for f in files:
    d = json.load(open(f))
    costs.append(d.get("estimated_cost_usd", 0))
    by_slice = {}
    for e in d["entries"]:
        s = e["slice"]
        if s not in by_slice:
            by_slice[s] = []
        by_slice[s].append(e["correct"])
    for s, vals in by_slice.items():
        if s not in slices:
            slices[s] = []
        slices[s].append(100 * sum(vals) / len(vals))

clar_rates = []
for f in files:
    d = json.load(open(f))
    clean = [e for e in d["entries"] if e["slice"] == "clean"]
    clar = sum(1 for e in clean if e["got_spec_type"] == "clarification")
    clar_rates.append(100 * clar / len(clean))

for s in ["clean", "near_miss", "multi_turn", "clarification", "adversarial"]:
    if s in slices:
        vals = slices[s]
        lo = min(vals)
        hi = max(vals)
        print(f"{s}: min={lo:.1f}% max={hi:.1f}% runs={len(vals)}")

print()
print(f"Clean clarification rate: min={min(clar_rates):.1f}% max={max(clar_rates):.1f}%")
print(f"Total cost: ${sum(costs):.2f}")
print()

adv = slices.get("adversarial", [])
clean = slices.get("clean", [])
nm = slices.get("near_miss", [])
g1 = "PASS" if all(a == 100 for a in adv) else "FAIL"
g2 = "PASS" if all(c >= 90 for c in clean) and all(n >= 90 for n in nm) else "FAIL"
g3 = "PASS" if all(r < 10 for r in clar_rates) else "FAIL"
print(f"GATE adversarial 100%:   {g1}")
print(f"GATE accuracy >=90%:     {g2}")
print(f"GATE clarification <10%: {g3}")
