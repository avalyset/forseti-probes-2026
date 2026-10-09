"""Les de atte pakkene med ast.literal_eval - ingen exec av pakkekode.
Kilde: upstream/dev @ 7a0877d, hentet til data/packs_src/.
"""
import ast, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "packs_src")
PACKS = ["nav_aap", "skatteetaten", "helfo", "lanekassen", "nb_kryss_ordning",
         "skatteetaten_legitimasjon", "toll_reisegodskvote", "arbeidstilsynet_arbeidstid"]


def load_pack(name):
    path = os.path.join(SRC, name + ".py")
    tree = ast.parse(open(path, encoding="utf-8").read(), filename=path)
    out = []
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id.endswith("_SCENARIOS"):
                out = ast.literal_eval(node.value)
    if not out:
        raise RuntimeError(f"fant ingen *_SCENARIOS i {name}")
    return out


def load_all():
    rows = []
    for p in PACKS:
        for i, s in enumerate(load_pack(p)):
            rows.append({"pack": p, "idx": i, "scenario": s})
    return rows


if __name__ == "__main__":
    rows = load_all()
    print(f"{len(rows)} scenarier fra {len(PACKS)} pakker")
    from collections import Counter
    print(Counter(r["pack"] for r in rows))
    keys = Counter()
    for r in rows:
        keys.update(r["scenario"].keys())
    print("felter:", dict(keys))
