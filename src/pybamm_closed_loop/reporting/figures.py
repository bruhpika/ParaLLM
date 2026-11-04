"""Publication-style figures for baseline simulation output.

Only extracted data is plotted; the figure set adapts to what is actually
available in a run (missing variables are skipped and noted).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def _profile_times_label(times_s: list[float]) -> list[str]:
    return [f"t = {t:.0f} s" for t in times_s]


def plot_voltage_current(series: dict[str, np.ndarray], out_path: str | Path) -> Path | None:
    """Voltage and current versus time."""
    if "Terminal voltage [V]" not in series:
        return None
    t = series.get("Time [s]")
    if t is None:
        return None
    fig, axes = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
    axes[0].plot(t, series["Terminal voltage [V]"], color="C0")
    axes[0].set_ylabel("Terminal voltage [V]")
    axes[0].grid(alpha=0.3)
    if "Current [A]" in series:
        axes[1].plot(t, series["Current [A]"], color="C3")
        axes[1].set_ylabel("Current [A]")
    else:
        axes[1].set_visible(False)
    axes[1].set_xlabel("Time [s]")
    axes[1].grid(alpha=0.3)
    fig.tight_layout()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def plot_concentration_profiles(
    series: dict[str, np.ndarray],
    profiles: dict,
    out_path: str | Path,
) -> Path | None:
    """Electrolyte and particle concentration behaviour.

    Layout: (1) electrolyte c(x) profiles, (2) negative and positive particle
    surface concentration versus time, (3) particle radial profiles.
    """
    has_electrolyte = "Electrolyte concentration [mol.m-3]" in profiles
    has_surf = (
        "X-averaged negative particle surface concentration [mol.m-3]" in series
        or "X-averaged positive particle surface concentration [mol.m-3]" in series
    )
    has_radial = (
        "Negative particle concentration [mol.m-3]" in profiles
        or "Positive particle concentration [mol.m-3]" in profiles
    )
    if not (has_electrolyte or has_surf or has_radial):
        return None

    n_rows = sum([has_electrolyte, has_surf, has_radial])
    fig, axes = plt.subplots(n_rows, 1, figsize=(8, 3 * n_rows), squeeze=False)
    axes = axes.ravel()
    idx = 0

    if has_electrolyte:
        prof = profiles["Electrolyte concentration [mol.m-3]"]
        for i, t in enumerate(prof.times_s):
            axes[idx].plot(prof.coordinates * 1e3, prof.values[i], label=f"t = {t:.0f} s")
        axes[idx].set_xlabel("x [mm]")
        axes[idx].set_ylabel("Electrolyte conc. [mol.m-3]")
        axes[idx].legend(fontsize=8)
        axes[idx].grid(alpha=0.3)
        idx += 1

    if has_surf:
        t = series.get("Time [s]")
        for name, color in [
            ("X-averaged negative particle surface concentration [mol.m-3]", "C0"),
            ("X-averaged positive particle surface concentration [mol.m-3]", "C1"),
        ]:
            if name in series:
                label = "neg. surface" if "negative" in name else "pos. surface"
                axes[idx].plot(t, series[name], color=color, label=label)
        axes[idx].set_xlabel("Time [s]")
        axes[idx].set_ylabel("Surface conc. [mol.m-3]")
        axes[idx].legend(fontsize=8)
        axes[idx].grid(alpha=0.3)
        idx += 1

    if has_radial:
        for name, color in [
            ("Negative particle concentration [mol.m-3]", "C0"),
            ("Positive particle concentration [mol.m-3]", "C1"),
        ]:
            if name not in profiles:
                continue
            prof = profiles[name]
            for i, t in enumerate(prof.times_s):
                axes[idx].plot(
                    prof.coordinates * 1e6,
                    prof.values[i],
                    color=color,
                    linestyle=["-", "--", ":"][i % 3],
                    label=f"{'neg' if 'Negative' in name else 'pos'}, t = {t:.0f} s",
                )
        axes[idx].set_xlabel("r [µm]")
        axes[idx].set_ylabel("Particle conc. [mol.m-3]")
        axes[idx].legend(fontsize=8)
        axes[idx].grid(alpha=0.3)
        idx += 1

    fig.tight_layout()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def plot_electrode_potentials(profiles: dict, out_path: str | Path) -> Path | None:
    """Electrode/electrolyte potentials and electrode OCP versus position."""
    wanted = [
        "Negative electrode potential [V]",
        "Positive electrode potential [V]",
        "Electrolyte potential [V]",
        "Negative electrode open-circuit potential [V]",
        "Positive electrode open-circuit potential [V]",
    ]
    available = [w for w in wanted if w in profiles]
    if not available:
        return None

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for name in ["Negative electrode potential [V]", "Positive electrode potential [V]", "Electrolyte potential [V]"]:
        if name not in profiles:
            continue
        prof = profiles[name]
        for i, t in enumerate(prof.times_s):
            axes[0].plot(
                prof.coordinates * 1e3,
                prof.values[i],
                linestyle=["-", "--", ":"][i % 3],
                label=f"{name.split(' [')[0]}, t = {t:.0f} s",
            )
    axes[0].set_xlabel("x [mm]")
    axes[0].set_ylabel("Potential [V]")
    axes[0].legend(fontsize=7)
    axes[0].grid(alpha=0.3)

    for name in ["Negative electrode open-circuit potential [V]", "Positive electrode open-circuit potential [V]"]:
        if name not in profiles:
            continue
        prof = profiles[name]
        for i, t in enumerate(prof.times_s):
            axes[1].plot(
                prof.coordinates * 1e3,
                prof.values[i],
                linestyle=["-", "--", ":"][i % 3],
                label=f"{name.split(' [')[0]}, t = {t:.0f} s",
            )
    axes[1].set_xlabel("x [mm]")
    axes[1].set_ylabel("OCP [V]")
    axes[1].legend(fontsize=7)
    axes[1].grid(alpha=0.3)

    fig.tight_layout()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def generate_all_figures(
    series: dict[str, np.ndarray],
    profiles: dict,
    figures_dir: str | Path,
) -> list[str]:
    """Generate the full baseline figure set; returns written paths."""
    figures_dir = Path(figures_dir)
    written: list[str] = []
    for fn, fname in [
        (lambda: plot_voltage_current(series, figures_dir / "01_voltage_current.png"), None),
        (lambda: plot_concentration_profiles(series, profiles, figures_dir / "02_concentrations.png"), None),
        (lambda: plot_electrode_potentials(profiles, figures_dir / "03_electrode_potentials.png"), None),
    ]:
        path = fn()
        if path is not None:
            written.append(str(path))
    return written
