"""
Responsible for: submitting GEE batch export tasks to Drive or Cloud Storage.
"""

import ee
from config.settings import EXPORT_FOLDER


class GEEExporter:
    """
    Wraps ee.batch.Export calls for images and tables.

    Usage:
        exporter = GEEExporter()
        task = exporter.image_to_drive(image, aoi, 'NDVI_2024')
        # task.status() to poll
    """

    def image_to_drive(
        self,
        image: ee.Image,
        geometry: ee.Geometry,
        description: str,
        folder: str = EXPORT_FOLDER,
        scale: int = 10,
    ) -> ee.batch.Task:
        task = ee.batch.Export.image.toDrive(
            image=image,
            description=description,
            folder=folder,
            region=geometry,
            scale=scale,
            crs='EPSG:4326',
            maxPixels=1e13,
            fileFormat='GeoTIFF',
        )
        task.start()
        return task

    def table_to_drive(
        self,
        features: ee.FeatureCollection,
        description: str,
        folder: str = EXPORT_FOLDER,
        file_format: str = 'CSV',
    ) -> ee.batch.Task:
        task = ee.batch.Export.table.toDrive(
            collection=features,
            description=description,
            folder=folder,
            fileFormat=file_format,
        )
        task.start()
        return task

    def image_to_cloud_storage(
        self,
        image: ee.Image,
        bucket: str,
        file_prefix: str,
        geometry: ee.Geometry,
        scale: int = 10,
    ) -> ee.batch.Task:
        task = ee.batch.Export.image.toCloudStorage(
            image=image,
            description=file_prefix,
            bucket=bucket,
            fileNamePrefix=file_prefix,
            region=geometry,
            scale=scale,
            maxPixels=1e13,
        )
        task.start()
        return task