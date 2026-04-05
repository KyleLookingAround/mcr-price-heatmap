"""
Tests for pipeline/aggregate.py

Covers: extract_district, filter_gm, apply_filters, make_history,
        compute_delta12m, aggregate_group, build_output.
"""
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from aggregate import (
    extract_district,
    filter_gm,
    apply_filters,
    make_history,
    compute_delta12m,
    aggregate_group,
    build_output,
    GM_PREFIXES,
    GM_WA_DISTRICTS,
    PTYPE_MAP,
)


# ─── Helpers ────────────────────────────────────────────────────────────────

def make_df(**kwargs):
    """Build a minimal DataFrame with sensible defaults for testing."""
    n = len(next(iter(kwargs.values())))
    defaults = {
        "postcode":       ["M20 2LN"] * n,
        "price":          [250000] * n,
        "date":           [pd.Timestamp("2024-06-01")] * n,
        "property_type":  ["S"] * n,
        "new_build":      ["N"] * n,
        "ppd_category":   ["A"] * n,
        "record_status":  ["A"] * n,
    }
    defaults.update(kwargs)
    return pd.DataFrame(defaults)


# ─── extract_district ────────────────────────────────────────────────────────

class TestExtractDistrict:
    def test_standard_postcode(self):
        s = pd.Series(["M20 2LN"])
        assert extract_district(s).iloc[0] == "M20"

    def test_two_char_area(self):
        s = pd.Series(["SK4 1AB"])
        assert extract_district(s).iloc[0] == "SK4"

    def test_uppercases_result(self):
        s = pd.Series(["m20 2ln"])
        assert extract_district(s).iloc[0] == "M20"

    def test_strips_whitespace(self):
        s = pd.Series(["  OL1 2AB  "])
        assert extract_district(s).iloc[0] == "OL1"

    def test_multiple_postcodes(self):
        s = pd.Series(["M1 1AA", "BL3 2BC", "WA14 5DE"])
        result = extract_district(s)
        assert list(result) == ["M1", "BL3", "WA14"]

    def test_single_char_area(self):
        s = pd.Series(["M1 1AA"])
        assert extract_district(s).iloc[0] == "M1"


# ─── filter_gm ──────────────────────────────────────────────────────────────

class TestFilterGM:
    def _df(self, postcodes):
        n = len(postcodes)
        return pd.DataFrame({
            "postcode":      postcodes,
            "price":         [200000] * n,
            "date":          [pd.Timestamp("2024-01-01")] * n,
            "property_type": ["S"] * n,
            "new_build":     ["N"] * n,
            "ppd_category":  ["A"] * n,
            "record_status": ["A"] * n,
        })

    def test_keeps_m_prefix(self):
        df = self._df(["M20 2LN", "M14 5AB"])
        result = filter_gm(df)
        assert len(result) == 2

    def test_keeps_sk_prefix(self):
        df = self._df(["SK4 1AB"])
        result = filter_gm(df)
        assert len(result) == 1

    def test_keeps_ol_prefix(self):
        df = self._df(["OL1 2AB"])
        result = filter_gm(df)
        assert len(result) == 1

    def test_keeps_bl_prefix(self):
        df = self._df(["BL3 4CD"])
        result = filter_gm(df)
        assert len(result) == 1

    def test_keeps_wn_prefix(self):
        df = self._df(["WN1 2EF"])
        result = filter_gm(df)
        assert len(result) == 1

    def test_keeps_gm_wa_districts(self):
        for district in GM_WA_DISTRICTS:
            df = self._df([f"{district} 1AB"])
            result = filter_gm(df)
            assert len(result) == 1, f"Expected {district} to be included"

    def test_excludes_non_gm_wa_district(self):
        # WA1 (Warrington) is not in GM_WA_DISTRICTS
        df = self._df(["WA1 1AB"])
        result = filter_gm(df)
        assert len(result) == 0

    def test_excludes_london_postcode(self):
        df = self._df(["SW1A 1AA"])
        result = filter_gm(df)
        assert len(result) == 0

    def test_mixed_postcodes(self):
        df = self._df(["M20 2LN", "SW1A 1AA", "SK4 1AB", "WA1 1AB"])
        result = filter_gm(df)
        assert len(result) == 2  # M20, SK4

    def test_adds_district_column(self):
        df = self._df(["M20 2LN"])
        result = filter_gm(df)
        assert "district" in result.columns

    def test_district_column_values(self):
        df = self._df(["M20 2LN", "SK4 1AB"])
        result = filter_gm(df)
        assert set(result["district"]) == {"M20", "SK4"}


# ─── apply_filters ───────────────────────────────────────────────────────────

class TestApplyFilters:
    def test_removes_deletions(self):
        df = make_df(record_status=["A", "D", "A"])
        result = apply_filters(df, exclude_new_builds=False, exclude_cat_b=False)
        assert len(result) == 2

    def test_removes_category_b_when_flag_set(self):
        df = make_df(ppd_category=["A", "B", "A"])
        result = apply_filters(df, exclude_new_builds=False, exclude_cat_b=True)
        assert len(result) == 2

    def test_keeps_category_b_when_flag_not_set(self):
        df = make_df(ppd_category=["A", "B", "A"])
        result = apply_filters(df, exclude_new_builds=False, exclude_cat_b=False)
        assert len(result) == 3

    def test_removes_new_builds_when_flag_set(self):
        df = make_df(new_build=["N", "Y", "N"])
        result = apply_filters(df, exclude_new_builds=True, exclude_cat_b=False)
        assert len(result) == 2

    def test_keeps_new_builds_when_flag_not_set(self):
        df = make_df(new_build=["N", "Y", "N"])
        result = apply_filters(df, exclude_new_builds=False, exclude_cat_b=False)
        assert len(result) == 3

    def test_removes_unknown_property_types(self):
        df = make_df(property_type=["D", "S", "T", "F", "O", "U"])
        result = apply_filters(df, exclude_new_builds=False, exclude_cat_b=False)
        assert set(result["property_type"]) == {"D", "S", "T", "F"}

    def test_removes_null_postcodes(self):
        df = make_df(postcode=["M20 2LN", None, ""])
        result = apply_filters(df, exclude_new_builds=False, exclude_cat_b=False)
        assert len(result) == 1

    def test_removes_prices_below_minimum(self):
        df = make_df(price=[10000, 10001, 250000])
        result = apply_filters(df, exclude_new_builds=False, exclude_cat_b=False)
        # price=10000 is NOT > 10000, so it's excluded
        assert all(result["price"] > 10_000)

    def test_removes_prices_above_maximum(self):
        df = make_df(price=[250000, 10_000_000, 9_999_999])
        result = apply_filters(df, exclude_new_builds=False, exclude_cat_b=False)
        assert all(result["price"] < 10_000_000)

    def test_all_filters_combined(self):
        df = pd.DataFrame({
            "postcode":      ["M20 2LN", "M20 2LN", "M20 2LN"],
            "price":         [250000,     250000,    250000],
            "date":          [pd.Timestamp("2024-01-01")] * 3,
            "property_type": ["S",         "S",       "S"],
            "new_build":     ["N",         "Y",       "N"],     # row 1 excluded
            "ppd_category":  ["A",         "A",       "B"],     # row 2 excluded
            "record_status": ["A",         "A",       "A"],
        })
        result = apply_filters(df, exclude_new_builds=True, exclude_cat_b=True)
        assert len(result) == 1


# ─── make_history ────────────────────────────────────────────────────────────

class TestMakeHistory:
    def _grp(self, dates, prices):
        return pd.DataFrame({"date": pd.to_datetime(dates), "price": prices})

    def test_returns_list_of_length_months(self):
        grp = self._grp(["2024-06-01", "2024-07-01"], [200000, 210000])
        history = make_history(grp, months=36)
        assert len(history) == 36

    def test_non_null_values_are_ints(self):
        grp = self._grp(["2024-06-01", "2024-07-01"], [200000, 210000])
        history = make_history(grp, months=12)
        non_null = [v for v in history if v is not None]
        assert all(isinstance(v, int) for v in non_null)

    def test_missing_months_are_none(self):
        # Only one month has data; the rest should be None
        grp = self._grp(["2024-06-15"], [200000])
        history = make_history(grp, months=36)
        none_count = sum(1 for v in history if v is None)
        assert none_count == 35  # 35 months are empty

    def test_latest_month_uses_median(self):
        # Two sales in same month at 200k and 300k → median = 250k
        grp = self._grp(["2024-06-01", "2024-06-15"], [200000, 300000])
        history = make_history(grp, months=1)
        assert history[-1] == 250000

    def test_custom_months_count(self):
        grp = self._grp(["2024-06-01", "2024-07-01"], [200000, 210000])
        history = make_history(grp, months=6)
        assert len(history) == 6


# ─── compute_delta12m ────────────────────────────────────────────────────────

class TestComputeDelta12m:
    REF_DATE = pd.Timestamp("2024-12-31")

    def _grp(self, dates, prices):
        return pd.DataFrame({"date": pd.to_datetime(dates), "price": prices})

    def test_returns_none_when_insufficient_recent_sales(self):
        # Only 3 recent sales (< 5 required)
        dates = ["2024-10-01", "2024-11-01", "2024-12-01"]
        prior = ["2023-01-01"] * 10
        all_dates = dates + prior
        prices = [300000] * 3 + [280000] * 10
        grp = self._grp(all_dates, prices)
        result = compute_delta12m(grp, self.REF_DATE)
        assert result is None

    def test_returns_none_when_insufficient_prior_sales(self):
        # 10 recent but only 3 prior
        recent = ["2024-10-01"] * 10
        prior = ["2023-06-01"] * 3
        prices = [300000] * 13
        grp = self._grp(recent + prior, prices)
        result = compute_delta12m(grp, self.REF_DATE)
        assert result is None

    def test_returns_positive_delta_for_price_rise(self):
        # Prior 12m: median 200k, Recent 12m: median 220k → +10%
        recent = [self.REF_DATE - timedelta(days=i * 20) for i in range(10)]
        prior  = [self.REF_DATE - timedelta(days=400 + i * 20) for i in range(10)]
        recent_prices = [220000] * 10
        prior_prices  = [200000] * 10
        dates = [str(d.date()) for d in recent + prior]
        prices = recent_prices + prior_prices
        grp = self._grp(dates, prices)
        result = compute_delta12m(grp, self.REF_DATE)
        assert result is not None
        assert result == pytest.approx(10.0, abs=0.1)

    def test_returns_negative_delta_for_price_fall(self):
        # Prior 12m: median 220k, Recent 12m: median 200k → ≈ -9.09%
        recent = [self.REF_DATE - timedelta(days=i * 20) for i in range(10)]
        prior  = [self.REF_DATE - timedelta(days=400 + i * 20) for i in range(10)]
        dates = [str(d.date()) for d in recent + prior]
        prices = [200000] * 10 + [220000] * 10
        grp = self._grp(dates, prices)
        result = compute_delta12m(grp, self.REF_DATE)
        assert result is not None
        assert result == pytest.approx(-9.09, abs=0.1)

    def test_result_is_rounded_to_2dp(self):
        recent = [self.REF_DATE - timedelta(days=i * 20) for i in range(10)]
        prior  = [self.REF_DATE - timedelta(days=400 + i * 20) for i in range(10)]
        dates = [str(d.date()) for d in recent + prior]
        prices = [213333] * 10 + [200000] * 10
        grp = self._grp(dates, prices)
        result = compute_delta12m(grp, self.REF_DATE)
        assert result is not None
        assert result == round(result, 2)


# ─── aggregate_group ─────────────────────────────────────────────────────────

class TestAggregateGroup:
    REF_DATE = pd.Timestamp("2024-12-31")

    def _grp(self, n, price=250000):
        dates = [self.REF_DATE - timedelta(days=i * 10) for i in range(n)]
        return pd.DataFrame({
            "date":  pd.to_datetime([str(d.date()) for d in dates]),
            "price": [price] * n,
        })

    def test_returns_none_when_below_min_sales(self):
        grp = self._grp(19)
        assert aggregate_group(grp, self.REF_DATE, min_sales=20) is None

    def test_returns_dict_when_at_min_sales(self):
        grp = self._grp(20)
        result = aggregate_group(grp, self.REF_DATE, min_sales=20)
        assert result is not None
        assert isinstance(result, dict)

    def test_dict_has_required_keys(self):
        grp = self._grp(20)
        result = aggregate_group(grp, self.REF_DATE, min_sales=20)
        assert set(result.keys()) == {"median", "count", "delta12m", "history"}

    def test_median_is_correct(self):
        grp = self._grp(20, price=300000)
        result = aggregate_group(grp, self.REF_DATE, min_sales=20)
        assert result["median"] == 300000

    def test_count_matches_group_size(self):
        grp = self._grp(25)
        result = aggregate_group(grp, self.REF_DATE, min_sales=20)
        assert result["count"] == 25

    def test_history_is_list(self):
        grp = self._grp(20)
        result = aggregate_group(grp, self.REF_DATE, min_sales=20)
        assert isinstance(result["history"], list)

    def test_median_is_int(self):
        grp = self._grp(20)
        result = aggregate_group(grp, self.REF_DATE, min_sales=20)
        assert isinstance(result["median"], int)


# ─── build_output ────────────────────────────────────────────────────────────

class TestBuildOutput:
    def _full_df(self, district="M20", n=40):
        """Create a realistic DataFrame for one district with enough sales."""
        ref = pd.Timestamp("2024-12-31")
        dates = [ref - timedelta(days=i * 8) for i in range(n)]
        return pd.DataFrame({
            "district":      [district] * n,
            "postcode":      [f"{district} 1AA"] * n,
            "price":         [250000 + i * 1000 for i in range(n)],
            "date":          pd.to_datetime([str(d.date()) for d in dates]),
            "property_type": (["S"] * (n // 2) + ["F"] * (n // 2)),
            "ptype_name":    (["semi"] * (n // 2) + ["flat"] * (n // 2)),
            "new_build":     ["N"] * n,
            "ppd_category":  ["A"] * n,
            "record_status": ["A"] * n,
        })

    def test_includes_district_with_enough_sales(self):
        df = self._full_df("M20", n=40)
        result = build_output(df, min_sales=20)
        assert "M20" in result

    def test_excludes_district_below_min_sales(self):
        df = self._full_df("M20", n=10)
        result = build_output(df, min_sales=20)
        assert "M20" not in result

    def test_district_entry_has_all_key(self):
        df = self._full_df("M20", n=40)
        result = build_output(df, min_sales=20)
        assert "all" in result["M20"]

    def test_all_entry_has_required_keys(self):
        df = self._full_df("M20", n=40)
        result = build_output(df, min_sales=20)
        assert set(result["M20"]["all"].keys()) == {"median", "count", "delta12m", "history"}

    def test_property_types_included_when_above_threshold(self):
        df = self._full_df("M20", n=60)  # 30 semi + 30 flat, threshold = 60//3 = 20
        result = build_output(df, min_sales=60)
        # min_sales//3 = 20, each type has 30 → should be included
        assert "semi" in result["M20"] or "flat" in result["M20"]

    def test_multiple_districts(self):
        df1 = self._full_df("M20", n=40)
        df2 = self._full_df("M14", n=40)
        df = pd.concat([df1, df2], ignore_index=True)
        result = build_output(df, min_sales=20)
        assert "M20" in result
        assert "M14" in result

    def test_count_matches_total_sales(self):
        df = self._full_df("M20", n=40)
        result = build_output(df, min_sales=20)
        assert result["M20"]["all"]["count"] == 40
