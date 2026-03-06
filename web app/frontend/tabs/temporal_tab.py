"""
Responsible for: rendering the Temporal Analysis tab.
"""

import streamlit as st
import ee
from datetime import datetime, timedelta

from backend.gee.index_calculator import IndexCalculator
from backend.gee.statistics_calculator import StatisticsCalculator
from backend.db.db_connection import DBConnection
from backend.db.temporal_repository import TemporalRepository
from utils.date_utils import DateUtils
from utils.visualization import ChartBuilder


class TemporalTab:
    """
    Renders incremental temporal analysis:
    1. Reads already-cached data points from MySQL.
    2. Identifies GEE timestamps not yet in the DB.
    3. Processes only the gaps.
    4. Reloads the full range and plots it.

    Usage:
        tab = TemporalTab(results, db)
        tab.render()
    """

    def __init__(self, results: dict, db: DBConnection):
        self._config     = results['config']
        self._collection = results['collection']
        self._aoi        = results['aoi']
        self._calc       = IndexCalculator()
        self._stats_calc = StatisticsCalculator()
        self._repo       = TemporalRepository(db)
        self._charts     = ChartBuilder()

    def render(self) -> None:
        st.subheader('Incremental Temporal Analysis')

        for idx_name in self._config['indices']:
            st.write(f'### {idx_name} Evolution')
            self._render_index(idx_name)

    # ── Per-index rendering ──────────────────────────────────────────────────

    def _render_index(self, idx_name: str) -> None:
        site       = self._config['site_name']
        start_date = self._config['start_date']
        end_date   = self._config['end_date']

        # 1. Existing dates in DB
        existing_dates = self._repo.get_existing_dates(site, idx_name, start_date, end_date)

        # 2. All timestamps in GEE collection
        all_timestamps = self._collection.aggregate_array('system:time_start').getInfo()

        # 3. Only process dates missing from DB
        missing = [
            ts for ts in all_timestamps
            if DateUtils.from_timestamp_ms(ts).strftime('%Y-%m-%d') not in existing_dates
        ]

        if missing:
            bar = st.progress(0)
            extra = self._config.get('custom_indices', [])

            for i, ts in enumerate(missing):
                curr_dt  = DateUtils.from_timestamp_ms(ts)
                date_str = curr_dt.strftime('%Y-%m-%d')
                next_str = DateUtils.day_after(curr_dt)

                img = ee.Image(
                    self._collection.filterDate(date_str, next_str).first()
                )
                img_with_idx = self._calc.compute(img, extra_indices=extra)
                stats        = self._stats_calc.run(img_with_idx, self._aoi, idx_name)
                val          = stats.get(f'{idx_name}_median')

                if val is not None:
                    self._repo.save_point(site, idx_name, curr_dt.date(), val)

                bar.progress((i + 1) / len(missing))
            bar.empty()

        # 4. Reload full range from DB and plot
        df = self._repo.find_range(site, idx_name, start_date, end_date)

        if not df.empty:
            chart_data = {
                idx_name: dict(zip(df['analysis_date'].astype(str), df['value']))
            }
            fig = self._charts.time_series(
                chart_data,
                title=f'{idx_name} — {site}',
                y_label='Value',
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning(f'No temporal data available for {idx_name}.')