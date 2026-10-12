import pandas as pd
import pytest

from hst_wfc3ir_ramp_linearity_audit.clustered_uncertainty import (
    exposure_balanced_bootstrap,
    per_exposure_summary,
    pixel_bootstrap,
)


def fixture():
    return pd.DataFrame(
        {
            "product_id": ["a", "a", "b", "b"],
            "late_to_early_rate_change": [-0.2, -0.1, 0.1, 0.2],
            "endpoint_fractional_residual": [0, 0, 0, 0],
            "max_fluence": [1, 2, 3, 4],
        }
    )


def test_bootstraps_are_reproducible_and_balanced():
    data = fixture()
    first = pixel_bootstrap(data.late_to_early_rate_change, draws=200, seed=2)
    assert first == pixel_bootstrap(data.late_to_early_rate_change, draws=200, seed=2)
    result = exposure_balanced_bootstrap(data, draws=200, seed=2)
    assert result["equal_exposure_point"] == pytest.approx(0)


def test_per_exposure_summary_preserves_exposures():
    result = per_exposure_summary(fixture())
    assert result.n.sum() == 4
    assert set(result.product_id) == {"a", "b"}
