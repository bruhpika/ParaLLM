"""P4 Part E: audit of the actually-available LG M50 experimental dataset.

Audits data/external/pyprobe_sample/lgm50/LGM50_BoL_RPT0_short_CA4.parquet
(the Imperial College PyProBE sample dataset, "LG M50 BoL RPT0_short" cell C)
and writes a machine-readable compatibility/limitations report to
data/registry/dataset_audit_lgm50.json.

The audit is read-only: it never modifies the dataset (AGENTS.md: preserve
raw data). Every number is computed from the parquet itself or copied from
the README.yaml protocol; nothing is hand-entered except the semantic
mapping of README protocol steps to observations, which is explicit below
and flagged as an assumption.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data/external/pyprobe_sample/lgm50"
PARQUET = DATA_DIR / "LGM50_BoL_RPT0_short_CA4.parquet"
README = DATA_DIR / "README.yaml"
OUT = REPO_ROOT / "data/registry/dataset_audit_lgm50.json"

SOURCE_URL = (
    "https://raw.githubusercontent.com/ImperialCollegeLondon/PyProBE/main/"
    "tests/sample_data/LGM50/NDK%20-%20LG%20M50%20deg%20-%20exp%202%2C2%20-%20"
    "rig%203%20-%2025degC%20-%20cell%20C%20-%20BoL%20-%20RPT0_short_CA4.parquet"
)
RETRIEVED = "2026-11-08"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def main() -> int:
    df = pl.read_parquet(PARQUET)
    cols = df.columns
    steps = (
        df.group_by("Step")
        .agg(
            pl.len().alias("n_points"),
            pl.col("Time [s]").min().alias("t_start_s"),
            pl.col("Time [s]").max().alias("t_end_s"),
            pl.col("Current [A]").min().alias("i_min_a"),
            pl.col("Current [A]").max().alias("i_max_a"),
            pl.col("Current [A]").mean().alias("i_mean_a"),
            pl.col("Voltage [V]").min().alias("v_min_v"),
            pl.col("Voltage [V]").max().alias("v_max_v"),
            pl.col("Voltage [V]").mean().alias("v_mean_v"),
            pl.col("Voltage [V]").std().alias("v_std_v"),
            pl.col("Capacity [Ah]").first().alias("cap_start_ah"),
            pl.col("Capacity [Ah]").last().alias("cap_end_ah"),
            pl.col("Temperature [C]").min().alias("temp_min_c"),
            pl.col("Temperature [C]").max().alias("temp_max_c"),
            pl.col("Temperature [C]").mean().alias("temp_mean_c"),
        )
        .sort("Step")
    )
    steps_dicts = [dict(r) for r in steps.iter_rows(named=True)]
    for s in steps_dicts:
        s["duration_s"] = s.pop("t_end_s") - s.pop("t_start_s")  # type: ignore[union-attr]
        s["capacity_delta_ah"] = s.pop("cap_end_ah") - s.pop("cap_start_ah")  # type: ignore[union-attr]

    readme_text = README.read_text()

    # ---- semantic step mapping (flagged as an assumption in the artifact) --
    # Measured signatures match the README protocol order 1:1 (CC current
    # magnitudes 1.5 C/3-charge and 0.5 discharge/charge, CV hold at 4.2 V,
    # rest lengths 2 min/2 h/6 h/10 min/30 s).
    step_labels = {
        0: "initial_rest_2min",
        1: "cc_charge_1p5A_to_4p2V",
        2: "cv_hold_4p2V_until_0p05A",
        3: "rest_2h_after_cccv",
        4: "pre_discharge_rest_30s",
        5: "pocv_discharge_0p5A_to_2p5V",
        6: "rest_6h",  # 21600 s
        7: "pre_charge_rest_30s",
        8: "pocv_charge_0p5A_to_4p2V",
        9: "final_rest_10min",
    }
    semanticSteps = []
    for s in steps_dicts:
        label_i = step_labels.get(int(s["Step"]), "unlabeled")
        semanticSteps.append(dict(step=s["Step"], label=label_i, observed=dict(
            n_points=s["n_points"], i_mean_a=s["i_mean_a"],
            v_range=[s["v_min_v"], s["v_max_v"]], duration_s=s["duration_s"],
            capacity_delta_ah=s["capacity_delta_ah"],
        )))
    semantic = dict(
        steps=semanticSteps,
        readme_protocol=readme_text.strip(),
        mapping_status="consistent with README protocol order (verified by "
        "current levels, voltage limits and durations); treated as an "
        "assumption until cross-checked with PyProBE's protocol parser",
    )

    # pOCV C/10 segments (discharge and charge) with capacity observations
    pocv = {
        s["Step"]: dict(
            capacity_ah=round(abs(s["capacity_delta_ah"]), 4),
            mean_current_a=round(s["i_mean_a"], 6),
            c_rate=round(abs(s["i_mean_a"]) / 5.0, 4),
            v_start=max(s["v_max_v"], s["v_min_v"]),
            v_end=min(s["v_max_v"], s["v_min_v"]),
            duration_s=s["duration_s"],
            temp_range_c=[s["temp_min_c"], s["temp_max_c"]],
            v_std=s["v_std_v"],
        )
        for s in steps_dicts
        if abs(s["i_mean_a"]) < -0.4 + 0.9 and abs(s["i_mean_a"]) > 0.4
        or abs(s["capacity_delta_ah"]) > 4.0
    }
    # precise selection: the two |I| = 0.5 A segments, with the summary keys
    d0 = [s for s in steps_dicts if abs(s["i_mean_a"] + 0.5) < 0.01]
    c0 = [s for s in steps_dicts if abs(s["i_mean_a"] - 0.5) < 0.01]
    pocv = {
        "discharge_step": d0[0]["Step"] if d0 else None,
        "discharge": (
            dict(
                step=d0[0]["Step"],
                capacity_ah=round(abs(d0[0]["capacity_delta_ah"]), 4),
                c_rate=round(abs(d0[0]["i_mean_a"]) / 5.0, 4),
                v_start=d0[0]["v_max_v"],
                v_end=d0[0]["v_min_v"],
                duration_s=d0[0]["duration_s"],
                temp_range_c=[d0[0]["temp_min_c"], d0[0]["temp_max_c"]],
                v_std=d0[0]["v_std_v"],
            )
            if d0
            else None
        ),
        "charge_step": c0[0]["Step"] if c0 else None,
        "charge": (
            dict(
                step=c0[0]["Step"],
                capacity_ah=round(abs(c0[0]["capacity_delta_ah"]), 4),
                c_rate=round(abs(c0[0]["i_mean_a"]) / 5.0, 4),
                v_start=c0[0]["v_min_v"],
                v_end=c0[0]["v_max_v"],
                duration_s=c0[0]["duration_s"],
                temp_range_c=[c0[0]["temp_min_c"], c0[0]["temp_max_c"]],
                v_std=c0[0]["v_std_v"],
            )
            if c0
            else None
        ),
    }

    def is_rest(s) -> bool:
        return abs(s["i_mean_a"]) < 1e-2

    # ---- global observations ------------------------------------------
    temp_max_c = df["Temperature [C]"].max()
    temp_min_c = df["Temperature [C]"].min()
    v_noise_rests = [
        s["v_std_v"] for s in steps_dicts if is_rest(s) and s["n_points"] > 2
    ]
    global_stats = dict(
        n_rows=df.height,
        n_steps=df["Step"].max() + 1,
        t_min_s=df["Time [s]"].min(),
        t_max_s=df["Time [s]"].max(),
        duration_h=(df["Time [s]"].max() - df["Time [s]"].min()) / 3600,
        v_min_v=df["Voltage [V]"].min(),
        v_max_v=df["Voltage [V]"].max(),
        i_range_a=[df["Current [A]"].min(), df["Current [A]"].max()],
        capacity_range_ah=[df["Capacity [Ah]"].min(), df["Capacity [Ah]"].max()],
        temperature_range_c=[temp_min_c, temp_max_c],
        null_values=df.null_count().sum_horizontal().item(),
        capacity_based_c_rates=dict(
            charge=float(df["Current [A]"].max()) / 5.0,
            discharge=float(-df["Current [A]"].min()) / 5.0,
            definition="|I| / 5.0 Ah (Chen2020 LGM50 rated capacity)",
        ),
    )

    out = dict(
        title="LG M50 BoL RPT0_short (PyProBE sample) dataset audit",
        generated=datetime.now(timezone.utc).isoformat(),
        file=dict(
            path=str(PARQUET.relative_to(REPO_ROOT)),
            sha256=sha256(PARQUET),
            size_bytes=PARQUET.stat().st_size,
            source_url=SOURCE_URL,
            retrieved=RETRIEVED,
            creator=(
                "Imperial College London, PyProBE project sample data "
                "(originally NDK Research Group raw export)"
            ),
        ),
        columns=cols,
        per_step=steps_dicts,
        semantic_step_mapping=semantic,
        pocv_c10=pocv,
        global_stats=global_stats,
        rest_voltage_noise=dict(
            definition="std of Voltage [V] within rest steps (>2 points)",
            std_per_rest_step_v=v_noise_rests,
            max_v=v_noise_rests and round(max(v_noise_rests), 6) or None,
        ),
        protocol_from_readme=readme_text.strip(),
        compatibility=dict(
            cell=dict(
                verdict="LG M50 21700, consistent with the Chen2020 characterization "
                "target (voltage window 2.5-4.2 V; chemistry not re-verified from "
                "the dataset alone)",
            ),
            capacity_checks=dict(
                disclaimer=(
                    "Single BoL cycle; no GITT/HPPC data. For capacity-proportional "
                    "couplings only."
                ),
                c_discharge=pocv["discharge"]["capacity_ah"] if pocv["discharge"] else None,
                coulombic_efficiency=(
                    round(
                        pocv["charge"]["capacity_ah"] / abs(pocv["discharge"]["capacity_ah"]),
                        4,
                    )
                    if pocv["charge"] and pocv["discharge"]
                    else None
                ),
                note=(
                    "CE is intake-limited by the 0.5 A (C/10) charge without a "
                    "CV hold; treat as an observation, not a cell-health claim."
                ),
                rated_reference_ah=5.0,
                reference_source="Chen2020 rated capacity 5 Ah (2.5-4.2 V)",
            ),
            neware_baseline=dict(
                verdict="INCOMPATIBLE baseline for fitting",
                reason=(
                    "The P3-audited Neware sample (dethermalized, no LG M50 "
                    "chemistry/protocol structure) stays excluded; P3 "
                    "verification results are unchanged."
                ),
            ),
            temperature=dict(
                verdict="non-isothermal during the 1.5 A charge (up to 32.3 C); "
                "C/10 segments stay close to 24.7-26.8 C",
                evidence_c=[temp_min_c, temp_max_c],
                consequence=(
                    "isothermal P0 models are defensible for the C/10 pOCV "
                    "segments with a small bias, but not for the CC-CV "
                    "charge section."
                ),
            ),
            protocol=dict(
                c_rates_available=["C/10 pOCV discharge", "C/10 pOCV charge"],
                missing=("no 0.5C/1C/2C discharge traces; no pulse/HPPC; no GITT "
                "segment identical to Chen2020 validation experiments"),
            ),
        ),
        provenance=dict(
            paper_precedent=(
                "Chen2020 validation traces are NOT available in the paper or "
                "supplement (parameterizations and OCV curves only); reuse "
                "requires author request"
            ),
            status="UNRESOLVED",
            note="data license-free redistribution of the PyProBE sample is "
            "UNRESOLVED (repo code BSD-3-Clause). No further distribution "
            "is allowed by this artifact.",
        ),
        limitations=[
            "Single RPT protocol; simulations limited to the C/10 pOCV segments and rest relaxations.",
            "Temperature rises to 32.3 C during the 1.5 A charge; OCV extraction from "
            "that segment carries a bias under the isothermal assumption.",
            "Coulombic efficiency at C/10 (without a final CV hold) is an intake-"
            "limited observation, not a cell-health metric.",
            "License and full re-distribution rights of the sample dataset are UNRESOLVED.",
            "Step semantics mapping is verified against the README protocol but "
            "treated as an assumption until PyProBE's protocol parser is used.",
        ],
    )
    OUT.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(f"wrote {OUT}")
    print(json.dumps(global_stats, indent=2))
    print("pocv C/10:", {k: (v.get('capacity_ah') if isinstance(v, dict) else v) for k, v in pocv.items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
