"""
Land Cover Change Detection & Transition Analysis
Track how land cover classes transform over time
"""

import ee
import pandas as pd
import plotly.graph_objects as go
from typing import Dict, List, Tuple
from backend.gee.dynamic_world import DynamicWorldClassifier, DW_CLASSES, DW_NAMES


class LandCoverChangeAnalyzer:
    """
    Analyze transitions between land cover classes over time
    Identify critical changes affecting heritage sites
    """

    def __init__(self):
        self.classifier = DynamicWorldClassifier()

    def detect_transitions(self,
                           before_classification: ee.Image,
                           after_classification: ee.Image,
                           geometry: ee.Geometry,
                           min_area_km2: float = 0.01) -> Dict:
        """
        Detect all class transitions and their extents

        Args:
            before_classification: Earlier classification
            after_classification: Later classification
            geometry: Area of interest
            min_area_km2: Minimum area threshold to report

        Returns:
            Dictionary with transition matrix and statistics
        """
        change_data = self.classifier.detect_class_change(
            before_classification,
            after_classification,
            geometry
        )

        # Filter by minimum area
        filtered_transitions = {
            trans: stats for trans, stats in change_data['transitions'].items()
            if stats['area_km2'] >= min_area_km2
        }

        change_data['transitions'] = filtered_transitions

        return change_data

    def identify_critical_changes(self,
                                  before_stats: Dict,
                                  after_stats: Dict) -> List[Dict]:
        """
        Identify changes that threaten heritage sites
        Priority: Built-up increases, Forest loss, Water changes

        Args:
            before_stats: Statistics from earlier classification
            after_stats: Statistics from later classification

        Returns:
            List of critical changes sorted by severity
        """
        critical_changes = []

        # Monitor these classes for heritage threat
        threat_classes = {
            'Built-up': {'direction': 'increase', 'weight': 10, 'threshold': 2},
            'Bare': {'direction': 'increase', 'weight': 8, 'threshold': 3},
            'Water': {'direction': 'increase', 'weight': 7, 'threshold': 2},
            'Flooded': {'direction': 'increase', 'weight': 9, 'threshold': 1},
            'Trees': {'direction': 'decrease', 'weight': 6, 'threshold': 5},
        }

        for class_name, threat_info in threat_classes.items():
            before_pct = before_stats.get(class_name, {}).get('percentage', 0)
            after_pct = after_stats.get(class_name, {}).get('percentage', 0)
            change = after_pct - before_pct

            # Check if change crosses threshold and is in threat direction
            if threat_info['direction'] == 'increase':
                if change > threat_info['threshold']:
                    critical_changes.append({
                        'class': class_name,
                        'change': change,
                        'before': before_pct,
                        'after': after_pct,
                        'severity': 'critical' if change > 10 else 'warning',
                        'weight': threat_info['weight']
                    })
            else:  # decrease
                if change < -threat_info['threshold']:
                    critical_changes.append({
                        'class': class_name,
                        'change': change,
                        'before': before_pct,
                        'after': after_pct,
                        'severity': 'critical' if abs(change) > 10 else 'warning',
                        'weight': threat_info['weight']
                    })

        # Sort by weight/severity
        critical_changes.sort(key=lambda x: abs(x['change']) * x['weight'], reverse=True)

        return critical_changes

    def get_transition_matrix(self,
                              before_classification: ee.Image,
                              after_classification: ee.Image,
                              geometry: ee.Geometry) -> pd.DataFrame:
        """
        Create detailed transition matrix showing class-to-class changes

        Args:
            before_classification: Earlier classification
            after_classification: Later classification
            geometry: Area of interest

        Returns:
            DataFrame with transition matrix (rows=from, cols=to)
        """
        # Create transition code: from_class * 10 + to_class
        before_int = before_classification.toInt()
        after_int = after_classification.toInt()
        transition = before_int.multiply(10).add(after_int)

        # Get histogram
        histogram = transition.reduceRegion(
            reducer=ee.Reducer.frequencyHistogram(),
            geometry=geometry,
            scale=10,
            maxPixels=1e9
        )

        hist_dict = histogram.getInfo()

        # Build matrix
        matrix_data = {}

        if 'label' in hist_dict and isinstance(hist_dict['label'], dict):
            for code_str, count in hist_dict['label'].items():
                try:
                    code = int(code_str)
                    from_class = code // 10
                    to_class = code % 10

                    from_name = DW_CLASSES.get(from_class, {}).get('name', f'Class_{from_class}')
                    to_name = DW_CLASSES.get(to_class, {}).get('name', f'Class_{to_class}')

                    if from_name not in matrix_data:
                        matrix_data[from_name] = {}

                    matrix_data[from_name][to_name] = {
                        'pixels': count,
                        'area_km2': round((count * 10 * 10) / 1e6, 3)
                    }

                except (ValueError, TypeError):
                    continue

        # Convert to DataFrame for easier handling
        all_classes = set()
        for from_dict in matrix_data.values():
            all_classes.update(from_dict.keys())
        all_classes.update(matrix_data.keys())
        all_classes = sorted(list(all_classes))

        # Create matrix with all classes
        matrix_dict = {}
        for from_class in all_classes:
            matrix_dict[from_class] = {}
            for to_class in all_classes:
                if from_class in matrix_data and to_class in matrix_data[from_class]:
                    matrix_dict[from_class][to_class] = matrix_data[from_class][to_class]['pixels']
                else:
                    matrix_dict[from_class][to_class] = 0

        return pd.DataFrame(matrix_dict).fillna(0).astype(int)

    def create_sankey_transitions(self,
                                  transition_data: Dict,
                                  min_pixels: int = 100) -> go.Figure:
        """
        Create Sankey diagram showing class transitions

        Args:
            transition_data: Dictionary with transition information
            min_pixels: Minimum pixels to show transition

        Returns:
            Plotly Sankey figure
        """
        transitions = transition_data.get('transitions', {})

        # Parse transitions for Sankey
        source = []
        target = []
        value = []
        colors = []

        for trans_str, stats in transitions.items():
            if stats['pixels'] >= min_pixels:
                from_class, to_class = trans_str.split(' → ')

                source.append(from_class)
                target.append(to_class)
                value.append(stats['pixels'])

                # Color based on from_class
                from_id = next((i for i, c in DW_CLASSES.items() if c['name'] == from_class), 0)
                colors.append(f"rgba({int(DW_CLASSES[from_id]['hex'][:2], 16)}, "
                              f"{int(DW_CLASSES[from_id]['hex'][2:4], 16)}, "
                              f"{int(DW_CLASSES[from_id]['hex'][4:6], 16)}, 0.4)")

        # Map class names to indices
        all_nodes = sorted(list(set(source + target)))
        source_idx = [all_nodes.index(s) for s in source]
        target_idx = [all_nodes.index(t) for t in target]

        # Node colors
        node_colors = []
        for node in all_nodes:
            class_id = next((i for i, c in DW_CLASSES.items() if c['name'] == node), 0)
            node_colors.append(f"#{DW_CLASSES[class_id]['hex']}")

        fig = go.Figure(data=[go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color='black', width=0.5),
                label=all_nodes,
                color=node_colors
            ),
            link=dict(
                source=source_idx,
                target=target_idx,
                value=value,
                color=colors
            )
        )])

        fig.update_layout(
            title="Land Cover Transitions",
            font=dict(size=11),
            height=500,
            template='plotly_white'
        )

        return fig

    def analyze_trend(self,
                      time_series_df: pd.DataFrame,
                      target_classes: List[str] = None) -> Dict:
        """
        Analyze trends in land cover changes over time

        Args:
            time_series_df: DataFrame with temporal class statistics
            target_classes: Classes to analyze (None = all)

        Returns:
            Dictionary with trend statistics
        """
        if target_classes is None:
            target_classes = [c for c in DW_NAMES if c in time_series_df.columns]

        trends = {}

        for class_name in target_classes:
            if class_name not in time_series_df.columns:
                continue

            values = time_series_df[class_name].dropna()

            if len(values) < 2:
                continue

            # Calculate trend
            x = range(len(values))
            y = values.values

            # Linear regression
            coeffs = np.polyfit(x, y, 1)
            slope = coeffs[0]
            intercept = coeffs[1]

            # Calculate correlation
            from scipy.stats import linregress
            if len(x) > 1:
                slope_stats, intercept_stats, r_value, p_value, std_err = linregress(x, y)
            else:
                slope_stats = r_value = p_value = 0

            trends[class_name] = {
                'slope': slope,
                'trend': 'increasing' if slope > 0 else 'decreasing' if slope < 0 else 'stable',
                'r_squared': r_value ** 2,
                'p_value': p_value,
                'significant': p_value < 0.05,
                'initial': y[0] if len(y) > 0 else 0,
                'final': y[-1] if len(y) > 0 else 0,
                'change': y[-1] - y[0] if len(y) > 1 else 0
            }

        return trends

    def get_vulnerable_transitions(self,
                                   before_classification: ee.Image,
                                   after_classification: ee.Image,
                                   geometry: ee.Geometry) -> List[Dict]:
        """
        Identify transitions most damaging to heritage sites

        Returns sorted list of dangerous transitions
        """
        # Define dangerous transitions
        dangerous = [
            ('Trees', 'Built-up'),  # Forest loss to urban
            ('Trees', 'Bare'),  # Forest to bare soil
            ('Grass', 'Built-up'),  # Natural to urban
            ('Water', 'Bare'),  # Water loss
            ('Grass', 'Bare'),  # Vegetation loss
            ('Cropland', 'Built-up'),  # Agricultural to urban
        ]

        change_data = self.classifier.detect_class_change(
            before_classification,
            after_classification,
            geometry
        )

        vulnerable = []

        for from_class, to_class in dangerous:
            trans_key = f"{from_class} → {to_class}"
            if trans_key in change_data['transitions']:
                stats = change_data['transitions'][trans_key]
                vulnerable.append({
                    'from': from_class,
                    'to': to_class,
                    'area_km2': stats['area_km2'],
                    'pixels': stats['pixels'],
                    'severity': 'critical' if stats['area_km2'] > 0.5 else 'warning'
                })

        return sorted(vulnerable, key=lambda x: x['area_km2'], reverse=True)


# Helper for trend calculation
import numpy as np