"""
Responsible for: rendering index description expanders in the sidebar.
"""

import streamlit as st
from config.indices_config import INDICES_CONFIG


class IndexDescription:
    """
    Renders a collapsed expander listing all available indices with their
    descriptions and heritage use notes.

    Usage:
        desc = IndexDescription(available_indices)
        desc.render()
    """

    def __init__(self, available_indices: list[str]):
        self._indices = available_indices

    def render(self) -> None:
        with st.expander('Index Descriptions', expanded=False):
            for idx in self._indices:
                if idx not in INDICES_CONFIG:
                    continue
                cfg = INDICES_CONFIG[idx]
                st.markdown(f"**{idx}** — {cfg['name']}")
                st.caption(f"{cfg['description']}  \n *{cfg['heritage_use']}*")
                st.markdown('---')