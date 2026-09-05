"""Check year boundaries, net/gross accounting and a complete annual solve."""
import numpy as np
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pypsa_sudan.reference import build_reference, annual_hydro_constraint, validate_reference

@pytest.fixture(scope="module")
def annual():
    n = build_reference()
    assert n.optimize(solver_name="highs", extra_functionality=annual_hydro_constraint,
                      solver_options={"threads": 1, "random_seed": 0}) == ("ok", "optimal")
    return n

def test_full_year_and_source_capacity():
    n = build_reference()
    assert len(n.snapshots) == 8760
    assert str(n.snapshots[0]) == "2022-01-01 00:00:00"
    assert str(n.snapshots[-1]) == "2022-12-31 23:00:00"
    assert n.generators.loc[["hydro", "combustible", "other"], "p_nom"].sum() == 4209
    assert n.meta["gross_category_rounding_difference_gwh"] == 1
    np.testing.assert_allclose(n.loads_t.p_set.sum(), [13261000, 3652000], atol=1e-5)
    assert len(n.links) == 0  # No 2024 corridor assumptions leak into this benchmark.

def test_annual_dispatch_accounting(annual):
    assert validate_reference(annual)["passed"]
    energy = annual.generators_t.p.sum()
    assert np.isclose(energy[["hydro", "combustible", "other"]].sum(), 16031000)
    assert np.isclose(energy.imports, 882000)
    # This regression also catches accidental omission of the scarce hydro budget.
    assert np.isclose(energy.hydro, annual.meta["hydro_budget_mwh"])
    assert energy.unserved < 1e-5

def test_reference_roundtrip(annual, tmp_path):
    import pypsa
    path = tmp_path / "reference.nc"
    annual.export_to_netcdf(path)
    loaded = pypsa.Network(path)
    assert loaded.meta["reference_year"] == 2022
    assert validate_reference(loaded)["passed"]
