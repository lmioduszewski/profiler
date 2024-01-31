import geopandas.sindex
import shapely as shp
import geopandas as gpd
import pandas as pd
import qgis.gui as gui
import qgis.core as core
import qgis.PyQt.QtWidgets as w


class SpatialIndex:

    def __init__(
            self,
            iface,
            layers: list = None,
    ):
        """
        Create a QgsSpatialIndex for the selected QgsVectorLayers.
        :param layers: list of QgsVectorLayers. A spatial index will be created for all layers
        """
        self.iface = iface
        self.layers = layers
        self.reference_geometry = None
        self.spatial_indexes = None

    @property
    def spatial_indexes(self):
        return self._spatial_indexes

    @spatial_indexes.setter
    def spatial_indexes(self, value):
        spatial_indexes = self.create_spatial_indexes(value)
        self._spatial_indexes = spatial_indexes

    def create_spatial_indexes(
            self,
            _
    ):
        try:
            spatial_indexes = {layer: core.QgsSpatialIndex(layer.getFeatures()) for layer in self.layers}
        except ValueError:
            print('layers provided are not valid QgsVectorLayers')
            spatial_indexes = None
        return spatial_indexes

    def get_nearby_features_ids(self, reference_geometry=None):
        """
        Function to get the feature ids of features that intersect the
        :return:
        """
        ids = {}
        if reference_geometry is None:
            return
        for layer, spatial_index in self.spatial_indexes.items():
            ids[layer.name()] = []
            ids_in_bounding_box = spatial_index.intersects(reference_geometry.boundingBox())
            for fid in ids_in_bounding_box:
                feature = layer.getFeature(fid)
                if feature.geometry().intersects(reference_geometry):
                    ids[layer.name()].append(fid)
            core.QgsProject.instance().mapLayersByName(layer.name())[0].selectByIds(ids[layer.name()])
        return ids
