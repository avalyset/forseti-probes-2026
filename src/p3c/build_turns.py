"""Brukerturene per svar. Ingen modellkjoring - bare lesing av transkriptene."""
import json, os, sys
from pathlib import Path
HOME = Path.home()
sys.path.insert(0, "/Volumes/Vault/forseti/p3/src")
from build_data import run_files, answer_of          # noqa: E402
import yaml                                           # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
decl = yaml.safe_load((HOME / "ClaudeWork/decision-probe/factcheck/expected_facts.yaml").read_text())
ids = {sc["id"] for sc in decl["scenarios"]}
out = {}
for path, meta in run_files():
    for res in json.loads(Path(path).read_text()).get("results") or []:
        if res.get("scenario_name") not in ids or not answer_of(res):
            continue
        conv = res.get("conversation") or []
        users = [m.get("content") or "" for m in conv if m.get("role") == "user"]
        out[f"{res['scenario_name']}|{meta['target']}|{meta['judge']}|{meta['run']}"] = users
json.dump(out, open(ROOT / "data" / "user_turns.json", "w"), ensure_ascii=False, indent=1)
n = [len(v) for v in out.values()]
print(f"{len(out)} svar, brukerturer per svar: {min(n)}-{max(n)} (median {sorted(n)[len(n)//2]})")
