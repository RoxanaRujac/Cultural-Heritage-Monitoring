"""
Responsible for: rendering styled HTML metric cards in Streamlit.
"""

import streamlit as st


class MetricCards:
    """
    Renders colourful summary cards using st.markdown + HTML.
    Each card shows a label and a bold value.

    Usage:
        cards = MetricCards()
        with st.columns(3) as cols:
            cards.render_in_column(cols[0], 'Site', 'Alba Iulia', gradient='purple')
            cards.render_in_column(cols[1], 'Images', '24 scenes', gradient='pink')
            cards.render_in_column(cols[2], 'Time Span', '730 days', gradient='blue')
    """

    _GRADIENTS = {
        'purple': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        'pink':   'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
        'blue':   'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
        'green':  'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
        'orange': 'linear-gradient(135deg, #f7971e 0%, #ffd200 100%)',
    }

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
        bg = self._GRADIENTS.get(gradient, self._GRADIENTS['purple'])
        with col:
            st.markdown(f"""
            <div style='background:{bg}; padding:20px; border-radius:10px; color:white;'>
                <h4 style='margin:0; color:white;'>{icon} {label}</h4>
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