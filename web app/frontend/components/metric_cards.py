"""
Responsible for: rendering styled HTML metric cards in Streamlit.
"""

import streamlit as st

off_white = '#f8f9fa'

class MetricCards:

    def render_in_column(
        self,
        col,
        label: str,
        value: str,
        icon: str = '',
        gradient: str = 'purple',
    ) -> None:
        """
        Render a single card inside a pre-created Streamlit column.

        Args:
            col:      A Streamlit column object (from st.columns()).
            label:    Card header text.
            value:    Bold value displayed below the label.
            icon:     Optional emoji prefix for the label.
            gradient: Key from _GRADIENTS (purple/pink/blue/green/orange).
        """
        bg = off_white
        with col:
            st.markdown(f"""
            <div style='background:{bg}; padding:20px; border-radius:10px; color:#2c3e50;'>
                <h4 style='margin:0; color:#2c3e50;'>{icon} {label}</h4>
                <p style='margin:10px 0 0 0; font-size:18px;'><strong>{value}</strong></p>
            </div>
            """, unsafe_allow_html=True)

    def render_stats_row(self, stats: dict, index_name: str) -> None:
        """
        Render a row of four st.metric widgets (mmedian / std / min / max).

        Args:
            stats:      Dict returned by StatisticsCalculator.run().
            index_name: Used to look up keys like 'NDVI_median'.
        """
        c1, c2, c3, c4 = st.columns(4)
        c1.metric('Median',          f"{stats.get(f'{index_name}_median',   0):.4f}")
        c2.metric('Std Deviation', f"{stats.get(f'{index_name}_stdDev', 0):.4f}")
        c3.metric('Minimum',       f"{stats.get(f'{index_name}_min',    0):.4f}")
        c4.metric('Maximum',       f"{stats.get(f'{index_name}_max',    0):.4f}")