#!/usr/bin/env python3
"""Find GWP tables that contradict the assessment report they NAME.

The test is deliberately not "is this number current". A hardcoded AR4 value is
frequently correct: the EU F-Gas Regulation mandates AR4, EU ETS moved to AR5 in
the 2023 amendment, and DEFRA and UNFCCC reporting use AR5. Telling those
projects their numbers are stale would be wrong, and wrong most of the time.

What IS checkable is a value sitting under a label that does not match it. Two
tests, both resting only on what the assessment reports published:

  MISLABEL     a field named ar5 holding the number AR4 published for that gas
  COLUMN_COPY  every row's ar6 equal to its ar5, in a file naming both

Neither compares against anyone's *current* corpus, which is the point. AR4
(2007), AR5 (2013) and AR6 (2021) are closed reports: their values do not
change, so a claim built only on them does not go stale. It also means this tool
never argues that its own number is the right one — it reports only that a file
disagrees with the report it cites.

  python3 gwp_basis_check.py FILE [FILE ...]
  python3 gwp_basis_check.py --self-test
  python3 gwp_basis_check.py --json FILE

Exit codes: 0 nothing found · 1 findings · 2 nothing was checkable.
"""
import argparse, json, re, sys
from pathlib import Path

HERE = Path(__file__).parent
REF = json.loads((HERE / "gwp_reference.json").read_text())
FROZEN = REF["values"]
EXCLUDE = REF["exclusions"]

# Every report this tool knows about comes from the reference file, never from
# code. Adding AR7 must be a data change: drop its values into gwp_reference.json
# and everything below — the field patterns, the header matcher, the comparison
# order — widens on its own. Hardcoding the list in six places is how a tool like
# this rots the first time the science moves.
BASES = REF["bases"]                      # e.g. ["ar4", "ar5", "ar6"], in order
_DIGITS = "".join(sorted(b[-1] for b in BASES))
_AR = rf"ar[{_DIGITS}]"


def consecutive_pairs():
    """Adjacent report pairs, oldest first — the copy that actually happens is
    from the previous report into the current column."""
    return [(BASES[i], BASES[i + 1]) for i in range(len(BASES) - 1)]


def coincides(gas, a, b):
    """Two reports publishing the same number for a gas. Such a cell is correct
    under either label, so it can never support the mislabel test. Computed from
    the data rather than listed, so it cannot drift away from it."""
    v = FROZEN.get(gas, {})
    x, y = v.get(a), v.get(b)
    return x is not None and y is not None and abs(float(x) - float(y)) < 0.051


def excluded(gas, basis):
    return basis in EXCLUDE.get(gas, [])


# Gas naming. Longest first and anchored: 'hfc-23' is a substring of 'hfc-236cb',
# and 'fossil' of 'carbon dioxide (fossil)'. Getting this wrong produces
# confident false positives, which is the failure that matters here.
SPECIAL = {
    "ch4nonfossil": "CH4_biogenic", "ch4biogenic": "CH4_biogenic",
    "methanenonfossil": "CH4_biogenic", "ch4fossil": "CH4_fossil",
    "methanefossil": "CH4_fossil", "co2": "CO2", "carbondioxide": "CO2",
    "n2o": "N2O", "nitrousoxide": "N2O", "sf6": "SF6", "nf3": "NF3",
}


# Alternate spellings come from the reference too, so adding one is a data
# change. A gas the tool cannot name is a gas it silently ignores.
ALIAS = {}
for _gas, _names in REF.get("aliases", {}).items():
    for _n in _names:
        ALIAS[re.sub(r"[\s_\-–]+", "", _n.lower())] = _gas


def canon(raw):
    """Map a written gas name onto a reference key, or None.

    Bare 'CH4' returns None on purpose. AR6 publishes 27.0 for non-fossil, 29.8
    for fossil and 27.9 origin-agnostic, so an unqualified methane row cannot be
    judged without knowing which was meant."""
    s = re.sub(r"[\s_\-–]+", "", (raw or "").lower())
    if re.match(r"hfo1234", s):
        s = s.replace("hfo", "hfc")
    if s in SPECIAL:
        return SPECIAL[s]
    if s in ALIAS:
        return ALIAS[s]
    for gas in sorted(FROZEN, key=len, reverse=True):
        g = re.sub(r"[\s_\-]+", "", gas.lower())
        if s == g:
            return gas
        tail = re.sub(r"^(hfc|pfc|hcfc|hfo|r)", "", g)
        if tail and s in (tail, "r" + tail, "hfc" + tail, "pfc" + tail):
            return gas
    return None


# --- shape 1: a record carrying a gas name plus AR-labelled fields -----------
FIELD = re.compile(
    rf"\b(?:gwp[_\s]*)?({_AR})(?:[_\s]*(?:gwp|100|value|100yr|_100yr|gwp100))*\b"
    r"\s*[:=]\s*(?:Decimal\s*\(\s*)?['\"]?(-?\d[\d,]*(?:\.\d+)?)['\"]?", re.I)
NAME = re.compile(r"(?:name|label|gas|species|refrigerant|key)\s*[:=]\s*"
                  r"['\"]([^'\"]{1,40})['\"]", re.I)

# --- shape 2: one map per report, keyed by gas ------------------------------
BASIS_MAP = re.compile(
    rf"\b(?:const\s+|let\s+|var\s+)?([A-Za-z_]*{_AR}[A-Za-z_]*)\s*(?::[^=]{{0,40}})?=\s*"
    r"\{([^{}]{0,4000})\}", re.I)
ENTRY = re.compile(r"['\"]([A-Za-z0-9 _\-]{1,30})['\"]\s*:\s*(-?\d[\d,]*(?:\.\d+)?)")

# --- shape 3: tables, HTML / markdown / CSV ---------------------------------
# The basis lives in the COLUMN HEADER and the gas in a cell of the same row.
# Never infer from proximity: a comparison page legitimately puts AR4, AR5 and
# AR6 within a few characters of each other, so a window scan produces confident
# nonsense. Map the header, then read down the column.
BASIS_IN_HEADER = re.compile(rf"\bar\s*-?\s*([{_DIGITS}])\b", re.I)
NUMCELL = re.compile(r"^\s*[~<>≈]?\s*(-?\d[\d,   ]*(?:\.\d+)?)\s*$")


def basis_maps(text):
    found = {}
    for m in BASIS_MAP.finditer(text):
        b = re.search(_AR, m.group(1), re.I)
        if not b:
            continue
        basis = b.group(0).lower()
        for em in ENTRY.finditer(m.group(2)):
            gas_raw, num = em.group(1), em.group(2)
            gas = canon(gas_raw)
            if not gas:
                continue
            try:
                val = float(num.replace(",", ""))
                entry_line = text[:m.start(2) + em.start()].count("\n") + 1
                found.setdefault((gas_raw, gas), {})[basis] = (val, entry_line)
            except ValueError:
                pass
    out = []
    for (raw, gas), b_dict in found.items():
        vals = {b: val for b, (val, _) in b_dict.items()}
        lines = {b: ln for b, (_, ln) in b_dict.items()}
        if vals:
            out.append((raw, gas, vals, lines))
    return out


def _basis_of_header(cell):
    m = BASIS_IN_HEADER.search(re.sub(r"<[^>]+>", " ", cell or ""))
    return f"ar{m.group(1)}" if m else None


def _grids_html(text):
    for tbl in re.finditer(r"<table\b.*?</table>", text, re.S | re.I):
        rows = list(re.finditer(r"<tr\b.*?</tr>", tbl.group(0), re.S | re.I))
        grid = []
        for r in rows:
            cells = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip()
                     for c in re.findall(r"<t[dh]\b.*?</t[dh]>", r.group(0), re.S | re.I)]
            row_line = text[:tbl.start() + r.start()].count("\n") + 1
            grid.append((cells, row_line))
        if grid:
            yield grid


def _grids_markdown(text):
    block = []
    lines = text.splitlines()
    for idx, line in enumerate(lines + [""]):
        line_num = idx + 1
        if line.strip().startswith("|") and line.count("|") >= 3:
            block.append(([c.strip() for c in line.strip().strip("|").split("|")], line_num))
        else:
            if len(block) >= 2:
                grid = [(r, ln) for r, ln in block
                        if not all(re.fullmatch(r":?-{2,}:?", c or "") for c in r)]
                if grid:
                    yield grid
            block = []


def _grids_csv(text, path=""):
    if not str(path).lower().endswith((".csv", ".tsv")):
        return
    sep = "\t" if str(path).lower().endswith(".tsv") else ","
    lines = text.splitlines()[:4000]
    grid = []
    for idx, l in enumerate(lines):
        if l.strip():
            cells = [c.strip().strip('"') for c in l.split(sep)]
            grid.append((cells, idx + 1))
    if len(grid) >= 2 and len(grid[0][0]) >= 2:
        yield grid


def tables(text, path=""):
    out = []
    for grid in (list(_grids_html(text)) + list(_grids_markdown(text))
                 + list(_grids_csv(text, path))):
        header = grid[0][0]
        cols = {}
        for i, c in enumerate(header):
            b = _basis_of_header(c)
            if b:
                cols[i] = b
        if not cols:
            continue
        for row, row_line in grid[1:]:
            if len(row) < 2:
                continue
            gas = nm = None
            for c in row:
                if c and not NUMCELL.match(c):
                    g = canon(re.sub(r"\(.*?\)", "", c).strip())
                    if g:
                        gas, nm = g, c.strip()
                        break
            if not gas:
                continue
            vals = {}
            for i, b in cols.items():
                if i < len(row):
                    m = NUMCELL.match(row[i])
                    if m:
                        try:
                            vals[b] = float(re.sub(r"[,   ]", "", m.group(1)))
                        except ValueError:
                            pass
            if vals:
                out.append((nm, gas, vals, row_line))
    return out


def records(text):
    out = []
    offset = 0
    for block in re.split(r"[{}]", text):
        nm = NAME.search(block)
        if nm:
            gas = canon(nm.group(1))
            if gas:
                vals = {}
                lines = {}
                name_line = text[:offset + nm.start()].count("\n") + 1
                for fm in FIELD.finditer(block):
                    basis = fm.group(1).lower()
                    num = fm.group(2)
                    try:
                        vals[basis] = float(num.replace(",", ""))
                        lines[basis] = text[:offset + fm.start()].count("\n") + 1
                    except ValueError:
                        pass
                if vals:
                    lines["_default"] = name_line
                    out.append((nm.group(1), gas, vals, lines))
        offset += len(block) + 1
    out.extend(basis_maps(text))
    return out


def check(path):
    text = Path(path).read_text(errors="replace")
    recs = records(text) + tables(text, str(path))
    findings = []

    for item in recs:
        raw, gas, vals = item[0], item[1], item[2]
        line_info = item[3] if len(item) > 3 else None
        for basis, v in vals.items():
            if excluded(gas, basis):
                continue
            ref = FROZEN.get(gas, {}).get(basis)
            if ref is None or abs(v - float(ref)) < 0.051:
                continue
            for other in BASES:
                if other == basis or excluded(gas, other):
                    continue
                ov = FROZEN.get(gas, {}).get(other)
                if ov is None or coincides(gas, basis, other):
                    continue
                if abs(v - float(ov)) < 0.051:
                    line = (line_info.get(basis) or line_info.get("_default")) if isinstance(line_info, dict) else line_info
                    f = {"type": "MISLABEL", "gas": raw, "canonical": gas,
                         "labelled": basis, "value": v,
                         "actually": other, "expected": ref}
                    if line is not None:
                        f["line"] = line
                    findings.append(f)
                    break

    for a, b in consecutive_pairs():
        pairs = [(item[1], item[2], item[3] if len(item) > 3 else None) for item in recs
                 if a in item[2] and b in item[2]
                 and not coincides(item[1], a, b)
                 and FROZEN.get(item[1], {}).get(a) is not None
                 and FROZEN.get(item[1], {}).get(b) is not None]
        if len(pairs) >= 3 and all(abs(v[a] - v[b]) < 0.051 for _, v, _ in pairs):
            first_line = None
            for _, _, l in pairs:
                if isinstance(l, dict):
                    first_line = l.get(b) or l.get(a) or l.get("_default")
                elif l is not None:
                    first_line = l
                if first_line is not None:
                    break
            f = {"type": "COLUMN_COPY", "a": a, "b": b, "rows": len(pairs),
                 "gases": sorted({g for g, _, _ in pairs})}
            if first_line is not None:
                f["line"] = first_line
            findings.append(f)
    return recs, findings


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if not args.files:
        ap.print_help()
        return 0

    unparsed, total, out = 0, 0, []
    for path in args.files:
        recs, findings = check(path)
        total += len(findings)
        out.append({"file": str(path), "records": len(recs), "findings": findings})
        if args.json:
            continue
        print(f"\n=== {path}  ({len(recs)} labelled gas records) ===")
        if not recs:
            # NOT the same as clean. A checker that understood nothing and
            # reported green is worse than one that reports red: it retires the
            # question. Say so, and exit non-zero so a caller cannot mistake it.
            print("  NOT CHECKED — no gas table in a shape this tool parses.")
            print("  Shapes read: a record with a gas name plus "
                  f"{'/'.join(BASES)} fields; a per-report map keyed by gas;")
            print("  and HTML, markdown or CSV tables whose COLUMN HEADER names a report.")
            unparsed += 1
            continue
        if not findings:
            print("  clean — every labelled cell matches the report it names")
        for f in findings:
            loc = f"line {f['line']}: " if f.get("line") is not None else ""
            if f["type"] == "MISLABEL":
                print(f"  MISLABEL    {loc}{f['gas']:14} field '{f['labelled']}' = {f['value']:g}"
                      f"  -> that is {f['actually'].upper()}'s value;"
                      f" {f['labelled'].upper()} published {f['expected']:g}")
            else:
                print(f"  COLUMN_COPY {loc}every {f['b']} equals its {f['a']} across "
                      f"{f['rows']} rows where the reports differ "
                      f"({', '.join(f['gases'][:5])}{'…' if len(f['gases']) > 5 else ''})")
    if args.json:
        print(json.dumps({"reference_version": REF.get("version"),
                          "bases": BASES, "results": out}, indent=1))
    elif unparsed:
        print(f"\n{unparsed} file(s) NOT CHECKED. Absence of a finding there is "
              f"absence of a reading, not evidence of correctness.")
    if total:
        return 1
    return 2 if unparsed else 0


CASES = [
    # Positives ------------------------------------------------------------
    ("AR4 blends under an AR6 heading (the shape found on our own page 551)",
     "<table><tr><th>Gas</th><th>AR4 GWP-100</th><th>AR6 GWP-100</th></tr>"
     "<tr><td>HFC-410A</td><td>2,088</td><td>2,088</td></tr>"
     "<tr><td>HFC-404A</td><td>3,922</td><td>3,922</td></tr></table>", "html", "MISLABEL", True),
    ("an ar6 column copied from ar5", """
      { name: 'HFC-134a', gwp_ar4: 1430, gwp_ar5: 1300, gwp_ar6: 1300 }
      { name: 'HFC-410A', gwp_ar4: 2088, gwp_ar5: 1923, gwp_ar6: 1923 }
      { name: 'HFC-32',   gwp_ar4: 675,  gwp_ar5: 677,  gwp_ar6: 677  }
      { name: 'HFC-125',  gwp_ar4: 3500, gwp_ar5: 3170, gwp_ar6: 3170 }
    """, "ts", "COLUMN_COPY", True),
    ("a per-report map with one AR4 value in the AR5 map",
     'GWP_AR5 = {"R410A": 1924, "R32": 675}', "py", "MISLABEL", True),
    # Negatives — these are what keep the tool trustworthy ------------------
    ("a correct three-report table", """
      { name: 'HFC-134a', gwp_ar4: 1430, gwp_ar5: 1300, gwp_ar6: 1530 }
      { name: 'HFC-32',   gwp_ar4: 675,  gwp_ar5: 677,  gwp_ar6: 771  }
      { name: 'HFC-125',  gwp_ar4: 3500, gwp_ar5: 3170, gwp_ar6: 3740 }
    """, "ts", None, False),
    ("EU F-Gas, where AR4 is mandated by law", """
      { name: 'HFC-410A', ar4: 2088 }
      { name: 'HFC-404A', ar4: 3922 }
      { name: 'HFC-134a', ar4: 1430 }
    """, "ts", None, False),
    ("the two contested figures — must never fire", """
      { name: 'SF6',        gwp_ar4: 22800, gwp_ar5: 23500, gwp_ar6: 24300 }
      { name: 'CH4 fossil', gwp_ar4: 25,    gwp_ar5: 30,    gwp_ar6: 29.8  }
    """, "ts", None, False),
    ("CO2, identical under every report", """
      { name: 'CO2', gwp_ar4: 1, gwp_ar5: 1, gwp_ar6: 1 }
      { name: 'CO2', gwp_ar4: 1, gwp_ar5: 1, gwp_ar6: 1 }
      { name: 'CO2', gwp_ar4: 1, gwp_ar5: 1, gwp_ar6: 1 }
    """, "ts", None, False),
    ("HFC-507A, whose AR4 and AR5 are legitimately both 3,985",
     "{ name: 'HFC-507A', gwp_ar4: 3985, gwp_ar5: 3985, gwp_ar6: 4775 }", "ts", None, False),
    ("bare CH4, which AR6 publishes three ways — unjudgeable",
     "{ name: 'CH4', gwp_ar5: 28, gwp_ar6: 27.9 }", "ts", None, False),
]


def check_reference():
    """The reference file is the whole ground truth, and it is hand-edited when a
    report is added. Verify its shape here so a malformed edit fails loudly
    rather than quietly narrowing what the tool can see."""
    errs = []
    if not BASES:
        errs.append("bases is empty")
    for b in BASES:
        if not re.fullmatch(r"ar\d", b):
            errs.append(f"base {b!r} is not of the form ar<digit>")
        if b not in REF.get("base_names", {}):
            errs.append(f"base {b!r} has no entry in base_names")
    for gas, v in FROZEN.items():
        for basis in v:
            if basis not in BASES:
                errs.append(f"{gas} carries {basis!r}, which is not in bases")
    for gas, bs in EXCLUDE.items():
        if gas not in FROZEN:
            errs.append(f"exclusion names unknown gas {gas!r}")
        for b in bs:
            if b not in BASES:
                errs.append(f"exclusion {gas}.{b} names an unknown report")
            if f"{gas}.{b}" not in REF.get("exclusion_reasons", {}):
                errs.append(f"exclusion {gas}.{b} has no written reason")
    seen = {}
    for gas, names in REF.get("aliases", {}).items():
        if gas not in FROZEN:
            errs.append(f"aliases name unknown gas {gas!r}")
        for n in names:
            k = re.sub(r"[\s_\-–]+", "", n.lower())
            if k in seen and seen[k] != gas:
                errs.append(f"alias {n!r} maps to both {seen[k]} and {gas}")
            seen[k] = gas
    # Every gas must be usable for at least one comparison, or it is dead weight
    # that silently narrows coverage.
    for gas, v in FROZEN.items():
        judgeable = [b for b in BASES if b in v and not excluded(gas, b)]
        if len(judgeable) < 1:
            errs.append(f"{gas} has no judgeable report left after exclusions")
    return errs


def self_test():
    import tempfile, os
    ok = True
    print("REFERENCE INTEGRITY")
    errs = check_reference()
    for e in errs:
        print(f"  FAIL {e}")
    if not errs:
        print(f"  ok — {len(FROZEN)} gases, bases {'/'.join(BASES)}, "
              f"{sum(len(v) for v in EXCLUDE.values())} exclusions each with a reason")
    ok &= not errs
    print("\nSELF-TEST\n")
    for label, body, ext, want_type, want_hit in CASES:
        with tempfile.NamedTemporaryFile("w", suffix="." + ext, delete=False) as fh:
            fh.write(body)
            tmp = fh.name
        _, findings = check(tmp)
        os.unlink(tmp)
        types = {f["type"] for f in findings}
        good = (bool(findings) == want_hit) and (want_type is None or want_type in types)
        ok &= good
        print(f"  [{'PASS' if good else 'FAIL'}] {label[:58]:60} "
              f"{'got ' + str(sorted(types)) if types else 'clean'}")

    # Line number assertion on a known finding
    known_body = (
        "// line 1\n"
        "// line 2\n"
        "const table = [\n"
        "  { name: 'HFC-410A', gwp_ar4: 2088, gwp_ar5: 2088 }\n"
        "];\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".ts", delete=False) as fh:
        fh.write(known_body)
        tmp = fh.name
    _, findings = check(tmp)
    os.unlink(tmp)
    mislabels = [f for f in findings if f["type"] == "MISLABEL"]
    line_ok = bool(mislabels and mislabels[0].get("line") == 4)
    ok &= line_ok
    print(f"  [{'PASS' if line_ok else 'FAIL'}] {'line number reported on a known finding':60} "
          f"{'got line ' + str(mislabels[0].get('line')) if mislabels else 'no findings'}")

    # Multiline record assertion: finding must report the line of the offending field, not the name
    multiline_body = (
        "const table = [\n"
        "  {\n"
        "    name: 'HFC-410A',\n"
        "    gwp_ar4: 2088,\n"
        "    gwp_ar5: 2088,\n"
        "  }\n"
        "];\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".ts", delete=False) as fh:
        fh.write(multiline_body)
        tmp = fh.name
    _, findings = check(tmp)
    os.unlink(tmp)
    mislabels = [f for f in findings if f["type"] == "MISLABEL"]
    multi_ok = bool(mislabels and mislabels[0].get("line") == 5)
    ok &= multi_ok
    print(f"  [{'PASS' if multi_ok else 'FAIL'}] {'line number points to offending field in multiline record':60} "
          f"{'got line ' + str(mislabels[0].get('line')) if mislabels else 'no findings'}")

    print(f"\nreference {REF.get('version')} · reports {'/'.join(b.upper() for b in BASES)}")
    print("ALL PASS" if ok else "FAILURES ABOVE")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
