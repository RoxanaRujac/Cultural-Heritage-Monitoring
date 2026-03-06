"""
Visualization utilities for Heritage Site Monitoring System
"""

import plotly.graph_objects as go


def plot_time_series(data_dict, title, y_label):
    """
    Create time series plot for indicators

    Args:
        data_dict: Dictionary of {name: {date: value}}
        title: Chart title
        y_label: Y-axis label

    Returns:
        Plotly figure object
    """
    fig = go.Figure()

    colors = ['#764ba2', '#f0c040', '#9b6fc5', '#4a2d6b', '#d4a017', '#c084f5', '#1a1a2e', '#6b6b8a']
    for i, (name, values) in enumerate(data_dict.items()):
        fig.add_trace(go.Scatter(
            x=list(values.keys()),
            y=list(values.values()),
            mode='lines+markers',
            name=name,
            line=dict(width=3, color=colors[i % len(colors)]),
            marker=dict(size=8, color=colors[i % len(colors)])
        ))

    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title=y_label,
        hovermode='x unified',
        template='plotly_white',
        height=400,
        plot_bgcolor = '#faf8fc',
        paper_bgcolor = '#22222e',
        xaxis = dict(gridcolor='#e8e0f0', linecolor='#c5c5d8'),
        yaxis = dict(gridcolor='#e8e0f0', linecolor='#c5c5d8'),
    )

    return fig


def plot_change_detection(before_stats, after_stats, index_name):
    """
    Create comparative before/after visualization

    Args:
        before_stats: List of statistics before [mean, std, min, max]
        after_stats: List of statistics after [mean, std, min, max]
        index_name: Name of the spectral index

    Returns:
        Plotly figure object
    """
    categories = ['Mean', 'Std Dev', 'Min', 'Max']

    fig = go.Figure(data=[
        go.Bar(
            name='Before',
            x=categories,
            y=before_stats,
            marker_color='#9b6fc5',
            marker_line=dict(color='#764ba2', width=1)
        ),
        go.Bar(
        ),
        go.Bar(
            name='After',
            x=categories,
            y=after_stats,
            marker_color='#f0c040',
            marker_line=dict(color='#d4a017', width=1)
        )
    ])

    fig.update_layout(
        title=f'{index_name} Comparison: Before vs After',
        barmode='group',
        template='plotly_white',
        height=400,
        yaxis_title=f'{index_name} Value',
        plot_bgcolor='#faf8fc',
        paper_bgcolor='#22222e',
        xaxis=dict(gridcolor='#e8e0f0'),
        yaxis=dict(gridcolor='#e8e0f0'),
        legend=dict(bgcolor='#f3edf9', bordercolor='#c5c5d8', borderwidth=1)
    )

    return fig


def plot_multi_index_comparison(indices_data, title="Multi-Index Comparison"):
    """
    Create comparison chart for multiple indices

    Args:
        indices_data: Dictionary of {index_name: value}
        title: Chart title

    Returns:
        Plotly figure object
    """
    bar_colors = ['#764ba2', '#f0c040', '#9b6fc5', '#4a2d6b', '#d4a017', '#c084f5', '#1a1a2e', '#6b6b8a']
    n = len(indices_data)
    fig = go.Figure(data=[
        go.Bar(
            x=list(indices_data.keys()),
            y=list(indices_data.values()),
            marker=dict(
                color=[bar_colors[i % len(bar_colors)] for i in range(n)],
                line=dict(color='#4a2d6b', width=1)
            )
        )
    ])

    fig.update_layout(
        title=title,
        xaxis_title="Spectral Index",
        yaxis_title="Value",
        template='plotly_white',
        height=400,
        plot_bgcolor='#faf8fc',
        paper_bgcolor='#22222e',
        xaxis=dict(gridcolor='#e8e0f0'),
        yaxis=dict(gridcolor='#e8e0f0'),
    )

    return fig


def plot_heatmap(data_matrix, x_labels, y_labels, title="Correlation Heatmap"):
    """
    Create heatmap visualization

    Args:
        data_matrix: 2D array of values
        x_labels: Labels for x-axis
        y_labels: Labels for y-axis
        title: Chart title

    Returns:
        Plotly figure object
    """
    fig = go.Figure(data=go.Heatmap(
        z=data_matrix,
        x=x_labels,
        y=y_labels,
        colorscale='RdBu',
        zmid=0
    ))

    fig.update_layout(
        title=title,
        template='plotly_white',
        height=500
    )

    return fig


def plot_area_chart(data_dict, title, y_label):
    """
    Create area chart for temporal data

    Args:
        data_dict: Dictionary of {name: {date: value}}
        title: Chart title
        y_label: Y-axis label

    Returns:
        Plotly figure object
    """
    fig = go.Figure()

    for name, values in data_dict.items():
        fig.add_trace(go.Scatter(
            x=list(values.keys()),
            y=list(values.values()),
            mode='lines',
            name=name,
            fill='tonexty',
            line=dict(width=2)
        ))

    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title=y_label,
        template='plotly_white',
        height=400,
        hovermode='x unified'
    )

    return fig


def plot_box_plot(data_dict, title="Index Distribution"):
    """
    Create box plot for index distributions

    Args:
        data_dict: Dictionary of {index_name: [values]}
        title: Chart title

    Returns:
        Plotly figure object
    """
    fig = go.Figure()

    for name, values in data_dict.items():
        fig.add_trace(go.Box(
            y=values,
            name=name,
            boxmean='sd'
        ))

    fig.update_layout(
        title=title,
        yaxis_title="Value",
        template='plotly_white',
        height=400
    )

    return fig