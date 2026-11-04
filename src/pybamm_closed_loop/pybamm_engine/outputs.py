"""Extraction of solution variables into plain numpy arrays.

Rules enforced here:
- Only variables that exist in the solution are extracted; anything else is
  reported as unavailable. Nothing is synthesised or interpolated silently.
- Particle concentration variables depend on both radial (r) and through-cell
  (x) coordinates; profiles are sampled at the mid-point of the relevant
  electrode at the requested times, and the sampling position is recorded.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

# Variable names that depend on (x, r, t) rather than a single spatial axis.
_PARTICLE_VARIABLE_MARKERS = ("particle concentration",)


@dataclass
class ProfileResult:
    """Spatial profile of one variable at several times."""

    variable: str
    coordinate_name: str  # e.g. "x [m]" or "r [m]"
    times_s: list[float]
    coordinates: np.ndarray  # 1D sampling grid
    values: np.ndarray  # shape (n_times, n_coordinates)
    note: str = ""
    metadata: dict = field(default_factory=dict)


@dataclass
class ExtractionResult:
    """Everything extracted from a solution, plus an honest report of what is missing."""

    series: dict[str, np.ndarray] = field(default_factory=dict)
    profiles: dict[str, ProfileResult] = field(default_factory=dict)
    unavailable_series: list[str] = field(default_factory=list)
    unavailable_profiles: list[str] = field(default_factory=list)

    @property
    def availability_report(self) -> dict:
        return {
            "series_extracted": sorted(self.series),
            "series_unavailable": sorted(self.unavailable_series),
            "profiles_extracted": sorted(self.profiles),
            "profiles_unavailable": sorted(self.unavailable_profiles),
        }


def _is_particle_variable(name: str) -> bool:
    return any(marker in name for marker in _PARTICLE_VARIABLE_MARKERS)


def extract_series(solution, names: list[str]) -> tuple[dict[str, np.ndarray], list[str]]:
    """Extract 1D time series; return (found, missing)."""
    found: dict[str, np.ndarray] = {}
    missing: list[str] = []
    time = np.asarray(solution.t, dtype=float)
    found["Time [s]"] = time
    for name in names:
        if name == "Time [s]":
            continue
        try:
            entries = np.asarray(solution[name].entries, dtype=float)
        except Exception:
            missing.append(name)
            continue
        if entries.ndim == 1 and entries.shape[0] == time.shape[0]:
            found[name] = entries
        else:
            missing.append(name)
    return found, missing


def _profile_time_indices(solution, fractions: list[float]) -> list[tuple[float, int]]:
    """Map requested fractions of the simulated span to (time, nearest index)."""
    time = np.asarray(solution.t, dtype=float)
    t_start, t_end = float(time[0]), float(time[-1])
    out: list[tuple[float, int]] = []
    for frac in fractions:
        t_target = t_start + frac * (t_end - t_start)
        idx = int(np.argmin(np.abs(time - t_target)))
        out.append((float(time[idx]), idx))
    return out


def extract_profile(
    solution, name: str, fractions: list[float]
) -> ProfileResult | None:
    """Extract one spatial profile at the requested time fractions.

    Returns None when the variable is not available in the solution.
    """
    try:
        var = solution[name]
    except Exception:
        return None

    time_points = _profile_time_indices(solution, fractions)

    if _is_particle_variable(name):
        # (r, t) variables; sample at the mid-plane of the owning electrode.
        mesh = var.mesh
        r_nodes = np.linspace(float(mesh.edges[0]), float(mesh.edges[-1]), 40)
        if "negative" in name:
            x_grid = solution["Negative electrode potential [V]"].mesh.edges
        else:
            x_grid = solution["Positive electrode potential [V]"].mesh.edges
        x_mid = 0.5 * (float(x_grid[0]) + float(x_grid[-1]))
        values = []
        for t, _ in time_points:
            vals = np.asarray(var(t=t, r=r_nodes, x=x_mid), dtype=float)
            values.append(np.asarray(vals).reshape(-1))
        return ProfileResult(
            variable=name,
            coordinate_name="r [m]",
            times_s=[t for t, _ in time_points],
            coordinates=r_nodes,
            values=np.vstack(values),
            note=f"radial profile at x = {x_mid:.3e} m (electrode mid-plane)",
            metadata={"x_sample_m": x_mid},
        )

    # 1D through-cell variable (electrolyte/electrode potential or concentration).
    mesh = var.mesh
    x_nodes = np.linspace(float(mesh.edges[0]), float(mesh.edges[-1]), 60)
    values = []
    for t, _ in time_points:
        vals = np.asarray(var(t=t, x=x_nodes), dtype=float)
        values.append(np.asarray(vals).reshape(-1))
    return ProfileResult(
        variable=name,
        coordinate_name="x [m]",
        times_s=[t for t, _ in time_points],
        coordinates=x_nodes,
        values=np.vstack(values),
        note="through-cell profile",
    )


def extract_all(solution, series_names: list[str], profile_names: list[str],
                fractions: list[float]) -> ExtractionResult:
    """Extract all requested series and profiles, reporting anything unavailable."""
    result = ExtractionResult()
    found, missing = extract_series(solution, series_names)
    result.series = found
    result.unavailable_series = missing
    for name in profile_names:
        prof = extract_profile(solution, name, fractions)
        if prof is None:
            result.unavailable_profiles.append(name)
        else:
            result.profiles[name] = prof
    return result
