"""
Responsible for: rendering the spectral indices colour-scale legend.
"""

import streamlit as st
from config.indices_config import INDICES_CONFIG


class LegendWidget:
    """
    Renders expandable legend cards for selected spectral indices.

    Usage:
        legend = LegendWidget(config)
        legend.render()
    """

    def __init__(self, config: dict):
        self._config     = config
        self._custom_map = {c['name']: c for c in config.get('custom_indices', [])}

    def render(self) -> None:
        st.markdown('---')
        st.markdown('### Spectral Indices Guide')
        for idx in self._config['indices']:
            if idx in self._custom_map:
                self._render_custom_card(idx)
            elif idx in INDICES_CONFIG:
                self._render_predefined_card(idx)

    # ── Private ──────────────────────────────────────────────────────────────

    def _render_predefined_card(self, idx: str) -> None:
        idc = INDICES_CONFIG[idx]
        with st.expander(f"**{idx}** — {idc['name']}", expanded=False):
            col1, col2 = st.columns([1, 2])
            with col1:
                grad = self._gradient_css(idc['palette'])
                st.markdown(
                    f'<div style="background:linear-gradient(to right,{grad});height:16px;'
                    f'border-radius:4px;border:1px solid #ccc;"></div>'
                    f'<div style="display:flex;justify-content:space-between;font-size:11px;">'
                    f'<span>{idc["min"]}</span><span>{idc["max"]}</span></div>',
                    unsafe_allow_html=True,
                )
            with col2:
                st.markdown(idc.get('description', ''))
                st.caption(idc.get('heritage_use', ''))

    def _render_custom_card(self, idx: str) -> None:
        ci = self._custom_map[idx]
        with st.expander(f"**{idx}** — Custom Index", expanded=False):
            col1, col2 = st.columns([1, 2])
            with col1:
                formula = ci.get('formula', '')
                if formula in ('normalized_diff', 'ratio', 'difference'):
                    ops  = {'normalized_diff': '(A-B)/(A+B)', 'ratio': 'A/B', 'difference': 'A-B'}
                    expr = (
                        ops[formula]
                        .replace('A', ci.get('band_a', ''))
                        .replace('B', ci.get('band_b', ''))
                    )
                    st.code(expr)
                elif formula == 'expression':
                    st.code(ci.get('expression', ''))
                st.caption(f"Range: {ci.get('min', -1)} to {ci.get('max', 1)}")
            with col2:
                st.info(ci.get('description', 'User-defined custom spectral index.'))

    @staticmethod
    def _gradient_css(palette: list[str]) -> str:
        colors = ['#' + p if not p.startswith('#') else p for p in palette]
        return ', '.join(colors)