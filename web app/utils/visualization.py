"""
Responsible for: building Plotly figure objects.
All methods receive plain Python data and return go.Figure instances.
"""

import plotly.graph_objects as go

_PALETTE = ['#764ba2', '#f0c040', '#9b6fc5', '#4a2d6b', '#d4a017', '#c084f5', '#1a1a2e', '#6b6b8a']

_LAYOUT_BASE = dict(
    template='plotly_white',
    height=400,
    plot_bgcolor='#faf8fc',
    paper_bgcolor='#22222e',
    xaxis=dict(gridcolor='#e8e0f0', linecolor='#c5c5d8'),
    yaxis=dict(gridcolor='#e8e0f0', linecolor='#c5c5d8'),
)


class ChartBuilder:
    """
    Factory for all Plotly charts used in the application.

    Usage:
        charts = ChartBuilder()
        fig = charts.time_series({'NDVI': {'2024-01-01': 0.4, ...}}, 'NDVI', 'Value')
        st.plotly_chart(fig)
    """

    def time_series(
        self,
        data: dict[str, dict[str, float]],
        title: str,
        y_label: str = 'Value',
    ) -> go.Figure:
        """
        Line chart with markers for one or more index time series.

        Args:
            data:    {series_name: {date_str: value}}
            title:   Chart title.
            y_label: Y-axis label.
        """
        fig = go.Figure()
        for i, (name, values) in enumerate(data.items()):
            color = _PALETTE[i % len(_PALETTE)]
            fig.add_trace(go.Scatter(
                x=list(values.keys()),
                y=list(values.values()),
                mode='lines+markers',
                name=name,
                line=dict(width=3, color=color),
                marker=dict(size=8, color=color),
            ))
        fig.update_layout(
            title=title,
            xaxis_title='Date',
            yaxis_title=y_label,
            hovermode='x unified',
            **_LAYOUT_BASE,
        )
        return fig

    def before_after_bars(
        self,
        before_values: list[float],
        after_values: list[float],
        index_name: str,
    ) -> go.Figure:
        """
        Grouped bar chart comparing Before vs After statistics.

        Args:
            before_values: [median, std, min, max] for the earlier image.
            after_values:  [median, std, min, max] for the later image.
            index_name:    Used in title and y-axis label.
        """
        categories = ['Median', 'Std Dev', 'Min', 'Max']
        fig = go.Figure(data=[
            go.Bar(
                name='Before',
                x=categories,
                y=before_values,
                marker_color='#9b6fc5',
                marker_line=dict(color='#764ba2', width=1),
            ),
            go.Bar(
                name='After',
                x=categories,
                y=after_values,
                marker_color='#f0c040',
                marker_line=dict(color='#d4a017', width=1),
            ),
        ])
        fig.update_layout(
            title=f'{index_name} Comparison: Before vs After',
            barmode='group',
            yaxis_title=f'{index_name} Value',
            legend=dict(bgcolor='#f3edf9', bordercolor='#c5c5d8', borderwidth=1),
            **_LAYOUT_BASE,
        )
        return fig

    def multi_index_bars(
        self,
        data: dict[str, float],
        title: str = 'Multi-Index Comparison',
    ) -> go.Figure:
        """
        Single bar per index showing its median value.

        Args:
            data:  {index_name: median_value}
            title: Chart title.
        """
        n = len(data)
        fig = go.Figure(data=[
            go.Bar(
                x=list(data.keys()),
                y=list(data.values()),
                marker=dict(
                    color=[_PALETTE[i % len(_PALETTE)] for i in range(n)],
                    line=dict(color='#4a2d6b', width=1),
                ),
            )
        ])
        fig.update_layout(
            title=title,
            xaxis_title='Spectral Index',
            yaxis_title='Value',
            **_LAYOUT_BASE,
        )
        return fig

    def heatmap(
        self,
        matrix: list[list[float]],
        x_labels: list[str],
        y_labels: list[str],
        title: str = 'Correlation Heatmap',
    ) -> go.Figure:
        fig = go.Figure(data=go.Heatmap(
            z=matrix,
            x=x_labels,
            y=y_labels,
            colorscale='RdBu',
            zmid=0,
        ))
        fig.update_layout(title=title, template='plotly_white', height=500)
        return fig