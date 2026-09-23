# gwp-basis-check

**Check that a GWP value matches the IPCC assessment report it claims.** A linter for global warming potential (GWP-100) tables in carbon-accounting code — emission factors, refrigerant CO₂e values, GHG inventories. Catches an AR4 number sitting in a column labelled AR5.

```
$ gwp_basis_check.py factors/gwp.py

=== factors/gwp.py  (26 labelled gas records) ===
  MISLABEL    r-410a   field 'ar5' = 2088  -> that is AR4's value; AR5 published 1923
```

MIT · no dependencies · Python 3.9+ · the reference values are [published below](#what-gwp-100-value-does-each-ipcc-report-give)

---

## Why isn't an old GWP value simply wrong?

Because it usually isn't wrong. Every greenhouse gas has a multiplier saying how much warming it causes relative to CO₂, and each IPCC assessment report revises them. HFC-134a is **1,430** in AR4 (2007), **1,300** in AR5 (2013) and **1,530** in AR6 (2021).

Which one you must use depends on what you are reporting under:

| Framework | GWP set required |
|---|---|
| EU F-Gas Regulation (2024/573) | **AR4** — mandated |
| EU ETS | **AR5**, since the 2023/2122 amendment. The 2018/2066 release referenced AR4 |
| UNFCCC national inventories | **AR5** |
| UK DEFRA / DESNZ conversion factors | **AR5** |
| GHG Protocol | **AR5 or AR6**, stated by the reporter |
| IPCC AR6 (current science) | **AR6** |

So `1430` is correct — under AR4. It is a defect only when the code calls it AR5.

**This tool does not tell you your values are out of date.** It checks one thing: *does the value match the report the file itself names?*

## Which numbers get confused most often?

Blends. A blend's GWP is the mass-weighted average of its components, so it is **re-derived at every assessment report**. It is widely believed that blend values carry across unchanged — they do not, and one "AR-agnostic" figure ends up in all three columns.

| If you see | It is | Not |
|---|---|---|
| **R-410A = 2,088** | AR4 | AR5 is 1,923 · AR6 is 2,256 |
| **R-404A = 3,922** | AR4 | AR5 is 3,943 · AR6 is 4,728 |
| **R-407C = 1,774** | AR4 | AR5 is 1,624 · AR6 is 1,908 |
| **R-507A = 3,985** | AR4 *and* AR5 | AR6 is 4,775 |
| **HFC-134a = 1,430** | AR4 | AR5 is 1,300 · AR6 is 1,530 |
| **HFC-32 = 675** | AR4 | AR5 is 677 · AR6 is 771 |

In practice the pure compounds in a table are all correct and only the blends are wrong, which is exactly why nobody notices.

## What GWP-100 value does each IPCC report give?

These are the values the tool checks against, generated from [`gwp_reference.json`](./gwp_reference.json) so this table cannot drift from the code. GWP-100, as published by each report.

<!-- BEGIN GENERATED TABLES -->

**The Kyoto basket**

| Gas | IPCC AR4 (2007) | IPCC AR5 (2013) | IPCC AR6 (2021) |
|---|---|---|---|
| Carbon dioxide (CO₂) | 1 | 1 | 1 |
| Methane, fossil (CH₄) | 25 | 28 ‡ | 29.8 |
| Methane, non-fossil (CH₄) | 25 | 28 | 27 |
| Nitrogen trifluoride (NF₃) | 17,200 | 16,100 | 17,400 |
| Nitrous oxide (N₂O) | 298 | 265 | 273 |
| Sulphur hexafluoride (SF₆) | 22,800 | 23,500 | 25,200 ‡ |
| Sulphuryl fluoride (SO₂F₂) | — | 4,090 | 4,630 |

**Single-compound refrigerants and other fluorinated gases**

| Gas | IPCC AR4 (2007) | IPCC AR5 (2013) | IPCC AR6 (2021) |
|---|---|---|---|
| HFC-125 | 3,500 | 3,170 | 3,740 |
| HFC-134 | — | 1,120 | 1,260 |
| HFC-134a | 1,430 | 1,300 | 1,530 |
| HFC-143 | — | 328 | 364 |
| HFC-143a | 4,470 | 4,800 | 5,810 |
| HFC-152a | 124 | 138 | 164 |
| HFC-227ea | 3,220 | 3,350 | 3,600 |
| HFC-23 | 14,800 | 12,400 | 14,600 |
| HFC-236fa | 9,810 | 8,060 | 8,690 |
| HFC-245fa | 1,030 | 858 | 962 |
| HFC-32 | 675 | 677 | 771 |
| HFC-365mfc | 794 | 804 | 914 |
| HFC-41 | — | 116 | 135 |
| HFC-43-10mee | 1,640 | 1,650 | 1,600 |
| HFO-1234yf | — | — | 0.501 |
| HFO-1234ze | — | — | 1.37 |
| R-290 (propane) | — | — | 0.02 |

**Refrigerant blends — re-derived at every report, which is where most errors live**

| Gas | IPCC AR4 (2007) | IPCC AR5 (2013) | IPCC AR6 (2021) |
|---|---|---|---|
| R-404A | 3,922 | 3,943 | 4,728 |
| R-407A | 2,107 | 1,923 | 2,262 |
| R-407C | 1,774 | 1,624 | 1,908 |
| R-407F | 1,825 | 1,674 | 1,965 |
| R-410A | 2,088 | 1,923 | 2,256 |
| R-422D | 2,729 | 2,473 | 2,917 |
| R-448A | — | — | 1,494 |
| R-449A | — | — | 1,504 |
| R-450A | — | — | 643 |
| R-452A | — | — | 2,292 |
| R-454B | — | — | 531 |
| R-507A | 3,985 | 3,985 | 4,775 |
| R-513A | — | — | 673 |

**Perfluorocarbons**

| Gas | IPCC AR4 (2007) | IPCC AR5 (2013) | IPCC AR6 (2021) |
|---|---|---|---|
| PFC-116 (C₂F₆) | 12,200 | 11,100 | 12,400 |
| PFC-14 (CF₄) | 7,390 | 6,630 | 7,380 |
| PFC-218 (C₃F₈) | 8,830 | 8,900 | 9,290 |
| PFC-31-10 (C₄F₁₀) | 8,860 | 9,200 | 10,000 |
| PFC-318 (c-C₄F₈) | 10,300 | 9,540 | 10,200 |
| PFC-41-12 (C₅F₁₂) | 9,160 | 8,550 | 9,220 |
| PFC-51-14 (C₆F₁₄) | 9,300 | 7,910 | 8,620 |

‡ This tool will not judge a cell labelled with that report — see [what it will not judge](#what-will-it-refuse-to-judge).

<!-- END GENERATED TABLES -->

## How does it detect a problem?

| | |
|---|---|
| `MISLABEL` | a field named `ar5` holding the number AR4 published for that gas |
| `COLUMN_COPY` | every row's `ar6` equal to its `ar5`, in a file naming both |

## Why won't this go stale?

Both tests rest only on what the reports published, and **AR4, AR5 and AR6 are closed**. Their numbers will not change again. A check built on them stays valid without maintenance, and never has to argue that its own value is the right one — it reports only that a file disagrees with the report it cites.

## How do I run it?

```bash
curl -O https://raw.githubusercontent.com/greencalculus/gwp-basis-check/main/gwp_basis_check.py
curl -O https://raw.githubusercontent.com/greencalculus/gwp-basis-check/main/gwp_reference.json

python3 gwp_basis_check.py src/**/*.py            # or .ts .js .json .md .html .csv
python3 gwp_basis_check.py --json factors.py      # machine-readable
python3 gwp_basis_check.py --self-test
```

Exit codes: `0` nothing found · `1` findings · `2` nothing was checkable.

### Run it with pre-commit

Add this repository to a project's `.pre-commit-config.yaml`:

```yaml
- repo: https://github.com/greencalculus/gwp-basis-check
  rev: v1
  hooks:
    - id: gwp-basis-check
```

The hook considers common source, table and documentation formats. A finding
blocks the commit; `NOT CHECKED` does not, because most ordinary files do not
contain a labelled GWP table.

### Run it in GitHub Actions

Use the composite action with one or more space-separated paths or glob
patterns:

```yaml
- uses: greencalculus/gwp-basis-check@v1
  with:
    paths: 'src/**/*.py data/*.csv'
```

As with the hook, unmatched or unreadable shapes remain visibly `NOT CHECKED`
without failing unrelated CI; a finding or a genuine runtime failure still
fails the step.

## What file formats does it read?

- a record carrying a gas name plus `ar4`/`ar5`/`ar6` fields — JSON, TypeScript, Python, SQL seed rows
- one map per report, keyed by gas — `GWP_AR5 = {"R410A": 1924, ...}`
- HTML, markdown and CSV tables **whose column header names a report**

Tables are read by mapping the header and then reading down the column. Proximity scanning is deliberately not used: a comparison page legitimately puts AR4, AR5 and AR6 numbers within a few characters of each other, and a window scan produces confident nonsense.

## Why does it say "NOT CHECKED" instead of "clean"?

Because those are different answers. If no gas table in a readable shape is found, the tool says **NOT CHECKED** and exits 2. A checker that understood nothing and reported green is worse than one that reports red, because it retires the question. Absence of a finding there is absence of a reading.

## What will it refuse to judge?

Encoded in `gwp_reference.json` with a written reason for each:

| | |
|---|---|
| **SF₆ under AR6** | Sources disagree on what AR6 published — GHG Protocol v2.0 prints 24,300, IPCC AR6 Table 7.SM.7 gives 25,200. Neither can be called "the label's value". |
| **CH₄ fossil under AR5** | A convention, not a value. AR5 Table 8.7 publishes a single 28 regardless of origin; GHG Protocol applies a +2 oxidation adjustment to reach 30. DEFRA and UNFCCC use 28. |
| **HFO-1234yf under AR5** | AR5 published `<1` — a bound, not a number you can compare. |
| **Unqualified CH₄** | AR6 publishes 27.0 non-fossil, 29.8 fossil and 27.9 origin-agnostic. A bare methane row cannot be judged. |
| **HCFC-22** | No row in the reference, so the tool is blind to it. Published: AR4 1,810 / AR5 1,760 / AR6 1,960. |
| **SAR columns** | Out of scope. SAR and AR5 both give HFC-134a 1,300. |

Two of those exist because **GreenCalculus holds the contested position**. When a naive version of this tool was pointed at a US national laboratory's tooling, two of its three complaints were exactly these. Neither was the lab's error.

## What are its limits?

- **Precision is bought with recall.** A wrong number that matches no other report's value is not reported, because it cannot be *proven* mislabelled. Real errors are missed on purpose.
- **Coverage is the binding constraint.** In a scan of 1,071 files drawn from GitHub code search, only 17 were in a readable shape. Most files mentioning an assessment report are imports, prose or scenario names.
- **Tables naming their report in a section heading rather than a column header are not read.** See [#1](https://github.com/greencalculus/gwp-basis-check/issues/1) — wanted, but it has to be built without reintroducing proximity matching.

## Where do the numbers come from?

[`gwp_reference.json`](./gwp_reference.json) — 44 gases, pulled from the [GreenCalculus](https://greencalculus.com) keyless API and reconciled against *GHG Protocol, "Global Warming Potential Values", v2.0, August 2024*. The regeneration command is in the file.

**Adding AR7 later is a data change, not a code change.** Append it to `bases`, add its values, run `python3 render_tables.py`, and the field patterns, table-header matcher, comparison order and the tables above all widen on their own. CI asserts this.

## Why should I trust a tool from a vendor?

You shouldn't, on our say-so — which is why the method, the reference values and every exclusion are here to be argued with. GreenCalculus sells emission-factor data.

**The same method was first run against our own corpus. It found 66 wrong cells out of 407 checked**, including AR4 blend values printed under an AR6 heading on our single most-visited page. The root cause was the blend-invariance belief described above. This tool exists because we were not the exception to it.

CI runs the tool against this README, so the tables above are checked by the thing they document.

## Contributing

See the [open issues](https://github.com/greencalculus/gwp-basis-check/issues). The self-test is the safety net: nine cases, of which **six are negatives** — a correct three-report table, an EU F-Gas table (AR4 by law), the two contested figures, CO₂, HFC-507A and bare CH₄. A change that makes any of those fire sends a correction to someone who was right. CI runs them on Python 3.9, 3.11 and 3.13, and also asserts that adding a report stays a data-only change.

Related: [greencalculus-benchmark](https://github.com/greencalculus/greencalculus-benchmark) measures whether LLMs recall emission factors correctly — the same concern one layer out.

MIT.
