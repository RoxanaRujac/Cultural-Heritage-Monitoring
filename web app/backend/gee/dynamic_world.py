

import geemap
import ee

class DynamicWorldClassifier:
    """Wrapper around geemap's Dynamic World functions"""
    
    def __init__(self):
        pass
    
    @staticmethod
    def get_timeseries(geometry, start_date, end_date):
        """Get Dynamic World timeseries"""
        return geemap.dynamic_world_timeseries(
            geometry,
            start_date,
            end_date,
            return_type="class"
        )
    
    @staticmethod
    def get_composite(images):
        """Get mode composite"""
        return images.mode()