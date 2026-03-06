"""
Responsible for: authenticating and initialising the Google Earth Engine session.
"""

import ee
from config.settings import EE_PROJECT_ID


class GEEInitializer:
    """
    Handles Earth Engine authentication and project initialisation.
    Call GEEInitializer.init() once at application startup.
    """

    _initialized: bool = False

    @classmethod
    def init(cls) -> None:
        """
        Initialise the EE session. Safe to call multiple times —
        subsequent calls are no-ops if already initialised.

        Raises:
            RuntimeError: if EE cannot be initialised.
        """
        if cls._initialized:
            return
        try:
            ee.Initialize(project=EE_PROJECT_ID)
            cls._initialized = True
        except Exception as exc:
            raise RuntimeError(
                f"Failed to initialise Google Earth Engine: {exc}"
            ) from exc

    @classmethod
    def is_ready(cls) -> bool:
        return cls._initialized