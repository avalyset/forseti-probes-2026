"""Regresjonstest: check_packs maa fange 130 030 i commit 32c494f av nav_aap,
og maa ikke melde hoytillits-AVVIK mot upstream/dev.

Kjor:  python -I test_check_packs.py
"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def run(ref):
    subprocess.run([sys.executable, "-I", os.path.join(ROOT, "check_packs.py"), ref],
                   cwd=ROOT, check=True, capture_output=True, text=True)
    safe = "".join(c if c.isalnum() else "_" for c in ref)
    return json.load(open(os.path.join(ROOT, f"check_{safe}.json")))


def main():
    fails = []

    d = run("32c494f")
    hits = [r for r in d["rows"] if r["value"] == 130030.0]
    if not hits:
        fails.append("32c494f: 130 030 ble IKKE fanget")
    elif hits[0]["verdict"] not in ("AVVIK", "MISTANKE"):
        fails.append(f"32c494f: 130 030 fanget, men som {hits[0]['verdict']}")
    else:
        print(f"OK  32c494f: 130 030 fanget som {hits[0]['verdict']}")
        print(f"    {hits[0]['detail']}")

    d2 = run("upstream/dev")
    n_avvik = d2["counts"]["AVVIK"]
    if n_avvik:
        fails.append(f"upstream/dev: {n_avvik} hoytillits-AVVIK, ventet 0")
    else:
        print(f"OK  upstream/dev: 0 hoytillits-AVVIK  "
              f"(OK {d2['counts']['OK']}, MISTANKE {d2['counts']['MISTANKE']}, "
              f"UKJENT {d2['counts']['UKJENT']}, UTELATT {d2['counts']['UTELATT']})")
    for r in d2["rows"]:
        if r["verdict"] == "MISTANKE":
            print(f"    kjent falsk positiv: {r['value']:.0f} i {r['pack']} "
                  f"- scenario-internt hypotetisk belop")

    if fails:
        print("\nFEILET:")
        for f in fails:
            print("  -", f)
        return 1
    print("\nalle tester bestatt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
