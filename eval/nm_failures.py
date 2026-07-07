import json, glob

files = sorted(glob.glob("eval/results/run_20260706T014533_r*.json"))
for f in files:
    d = json.load(open(f))
    nm = [e for e in d["entries"] if e["slice"] == "near_miss" and not e["correct"]]
    rid = f.split("_r")[-1].split(".")[0]
    print(f"run {rid}: {len(nm)} fails")
    for e in nm:
        det = str(e.get("detail", ""))[:120]
        print(f"  {e['id']}: expected={e['expected_spec_type']} got={e['got_spec_type']} detail={det}")
    print()