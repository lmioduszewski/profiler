"""from qgis.PyQt.QtWidgets import (
    QAction, QMessageBox, QDockWidget, QToolBar,
    QComboBox)"""
import math

import qgis.PyQt.QtWidgets as w
import qgis.gui as gui
import qgis.core as core
from qgis.PyQt.QtCore import Qt
import plotly.graph_objs as go
from . import gis_functions as gis
from qgis.PyQt.QtGui import QColor
import geopandas as gpd
import shapely as shp
from pathlib import Path
from ._figure import Fig


class XSectionPlugin(w.QWidget):
    def __init__(self, iface: gui.QgisInterface):
        super().__init__()
        self.iface = iface
        self.main_widget = w.QWidget()
        self.layout = w.QVBoxLayout(self.main_widget)
        self.profile_canvas = gui.QgsElevationProfileCanvas()
        self.open_action = w.QAction('X-sect', self.iface.mainWindow())
        self.toolbar = w.QToolBar(parent=self.main_widget)
        self.test_action = w.QAction(parent=self.toolbar)
        self.feature_identifier = gui.QgsMapToolIdentifyFeature(self.iface.mapCanvas())
        self.raster_combobox = w.QComboBox()
        self.tolerance_slider = w.QSlider()
        self.vector_list = w.QListWidget()
        self.selected_line: core.QgsFeature = None
        self.layer_for_selection: core.QgsMapLayer = None
        self.buffer_rubber_band: gui.QgsRubberBand = None
        self.buffer_geometry = None
        self.vector_list_selection = None
        self._nearby_features_as_ids= None
        self.dock_widget = w.QDockWidget(parent=self.profile_canvas)
        self.dock_widget.setWidget(self.main_widget)
        self._nearby_features_dict = None
        self.fig = Fig()

    def initGui(self):

        self.layout.addWidget(self.toolbar)
        self.add_button_to_toolbar(name='Select Line', callback_function=self.activate_select_line)
        self.feature_identifier.featureIdentified.connect(self.select_line_feature)
        self.add_button_to_toolbar(name='Plot Selected Line', callback_function=self.plot_selected_line)
        self.add_button_to_toolbar(name='Get Nearby Features', callback_function=self.get_nearby_features_dict)

        self.tolerance_slider.setOrientation(Qt.Orientation(1))  # 1 = horizontal
        self.toolbar.addWidget(self.tolerance_slider)
        self.tolerance_slider.sliderReleased.connect(self.on_tolerance_slider_release)

        self.layout.addWidget(self.raster_combobox)
        self.layout.addWidget(self.vector_list)
        self.vector_list.itemSelectionChanged.connect(self.check_vector_list_selection)

        self.iface.addToolBarIcon(self.open_action)
        self.open_action.triggered.connect(self.run)

    def unload(self):
        # remove selections
        selection = [item.text() for item in self.vector_list.selectedItems()]
        for vector_layer_name in selection:
            vector_layer = core.QgsProject.instance().mapLayersByName(vector_layer_name)[0]
            vector_layer.removeSelection()
        # Remove the toolbar icon
        self.iface.removeToolBarIcon(self.open_action)
        # Reset the map tool to the default (e.g., pan tool)
        if self.iface.mapCanvas().mapTool() == self.feature_identifier:
            self.iface.mapCanvas().unsetMapTool(self.feature_identifier)
        # Hide or close custom widgets or dockwidgets
        try:
            if self.main_widget.isVisible():
                self.main_widget.close()
        except ValueError:
            print('self.main_widget is not an object')
        # Delete actions or UI elements if needed
        del self.open_action
        if self.dock_widget:
            self.iface.removeDockWidget(self.dock_widget)
            self.dock_widget.deleteLater()
        del self.profile_canvas
        self.clear_rubber_band()
        del self.toolbar
        del self.main_widget
        del self.layout

    def run(self):
        self.iface.addDockWidget(Qt.BottomDockWidgetArea, self.dock_widget)
        self.tolerance_slider.setMinimum(0)
        self.tolerance_slider.setMaximum(500)
        self.tolerance_slider.setValue(100)
        self.vector_list.setSelectionMode(w.QAbstractItemView.SelectionMode(2))
        self.get_rasters_for_combobox()
        self.raster_combobox.setCurrentIndex(3)
        self.vector_list.setCurrentRow(0)
        self.activate_select_line()

    def add_button_to_toolbar(self, name: str = None, callback_function=None):
        """adds a button with 'name' that calls a 'callback_function to the main widget"""
        # define action
        action = w.QAction(text=name, parent=self.main_widget)
        # add it to the toolbar as a push button
        w.QPushButton.addAction(self.toolbar, action)
        # connect action to the callback function
        action.triggered.connect(callback_function)

    def get_rasters_for_combobox(self):
        """Populates the combo box with names of raster layers."""
        layers = core.QgsProject.instance().mapLayers().values()
        for layer in layers:
            if layer.type() == core.QgsMapLayer.RasterLayer:
                self.raster_combobox.addItem(layer.name(), layer)
            if layer.type() == core.QgsMapLayer.VectorLayer:
                self.vector_list.addItem(layer.name())

    def on_tolerance_slider_release(self):
        """what to do when the tolerance slider is moved then released"""
        if self.selected_line:
            self.draw_buffer()
        self.get_nearby_features_as_ids()

    def activate_select_line(self):
        self.feature_identifier.setLayer(self.iface.activeLayer())
        self.iface.mapCanvas().setMapTool(self.feature_identifier)

    def select_line_feature(self, feature: core.QgsFeature):
        self.layer_for_selection = self.iface.activeLayer()
        self.selected_line = feature
        feature_id = feature.id()
        self.layer_for_selection.selectByIds([feature_id])
        self.draw_buffer()
        self.get_nearby_features_as_ids()

    def plot_selected_line(self):
        x, z = self.get_profile_xz_from_QgsFeature(self.selected_line)
        print(f"plotting line: {self.selected_line.id()} | {self.iface.activeLayer().name()}")
        self.plot_fig(x, z)

    def get_nearby_features_as_ids(self) -> dict:
        """Method to get nearby features to the selected line. Various other methods call this
        to get nearby features when a gui element changes or is updated. That way
        self.nearby_features_as_ids will always return the nearby features based on the currently
        set parameters"""
        vector_layer_names_to_check = [item.text() for item in self.vector_list.selectedItems()]
        vector_layers_to_check = [self.get_layer_by_name(name) for name in vector_layer_names_to_check]
        spatial_index = gis.SpatialIndex(
            iface=self.iface,
            layers=vector_layers_to_check,
        )
        nearby_features_ids = spatial_index.get_nearby_features_ids(reference_geometry=self.buffer_geometry)
        self._nearby_features_as_ids = nearby_features_ids
        return nearby_features_ids

    def get_profile_xz_from_QgsFeature(self, feature: core.QgsFeature):
        try:
            feature_geometry_as_multipolyline = feature.geometry().asMultiPolyline()[0]
        except TypeError:
            print('feature cannot be converted to a MultiPolyline')
            return
        line = core.QgsLineString(feature_geometry_as_multipolyline)
        x, z = self.get_profile_xz(line=line)
        return x, z

    def plot_fig(self, x, z):
        # get nearby feature just in case
        self.get_nearby_features_dict()
        self.add_ground_line(x, z)
        self.add_nearby_explo_lines()
        # fig.write_image(Path().home().joinpath("output_xsection.pdf"), width=1500, height=750)
        # fig.write_html(Path().home().joinpath("output_xsection.html"), config={'scrollZoom': True})
        self.fig.show()

    def add_ground_line(self, x, z):
        self.fig.add_scattergl(
            x=x, y=z,
            hoverinfo='y',
            name='Ground Surface Elevation',
            mode='lines',
            line_color='brown'
        )

    def add_nearby_explo_lines(self, line_color='blue', line_width=2):
        for feature_name, feature_data_dict in self.nearby_features_dict.items():
            distance_along_line = feature_data_dict['distanceAlongLine']
            lidar_elevation = feature_data_dict['lidar']
            total_depth = feature_data_dict['ExploDepth']
            if type(total_depth) not in [float, int]:
                bottom_elevation = lidar_elevation
                total_depth = None
            else:
                bottom_elevation = lidar_elevation - total_depth
            if total_depth is None:
                self.fig.add_scattergl(
                    x=(distance_along_line,),
                    y=(lidar_elevation,),
                    name=feature_name
                )
            else:
                self.fig.add_scattergl(
                    mode='lines',
                    line_width=line_width,
                    line_color=line_color,
                    marker_symbol=1,
                    name=feature_name,
                    x=(distance_along_line, distance_along_line),
                    y=(lidar_elevation, bottom_elevation)
                )

    def get_elevation_of_QgsPointXY(
            self,
            dem_layer_name: str = None,
            point: core.QgsPointXY = None
    ):
        if dem_layer_name is None:
            dem_layer_name = self.raster_combobox.currentData().name()
        dem_layer = core.QgsProject.instance().mapLayersByName(dem_layer_name)[0]
        # Sample elevation
        elevation, success = dem_layer.dataProvider().sample(point, 1)
        if success:
            return elevation
        else:
            return print(f"Elevation data not available at {point}")

    def get_profile_xz(
            self,
            dem_layer_name: str = None,
            line: core.QgsLineString = None,
            num_points: int = 1000
    ) -> tuple:
        """
        This function needs some revisions
        :param dem_layer_name: name of raster layer that is the reference dem
        :param line: the profile line to get x, z coordinates, as a core.QgsLineString
        :param num_points: Number of points to interpolate (increase for higher resolution)
        :return: a tuple with an x-coordinate list and a z-coordinate list
        """
        if dem_layer_name is None:
            dem_layer_name = self.raster_combobox.currentData().name()
        dem_layer = core.QgsProject.instance().mapLayersByName(dem_layer_name)[0]

        # Transform context for CRS transformations
        transform_context = core.QgsCoordinateTransformContext()
        # CRS transformation from line CRS to DEM CRS
        # transform = core.QgsCoordinateTransform(line.crs(), dem_layer.crs(), transform_context)

        line_length = line.length()
        interval = line_length / num_points

        elevation_profile = []
        for i in range(num_points + 1):
            point_on_line = line.interpolatePoint(i * interval)
            # point_on_line = point_on_line.transform(ct=dem_layer.crs())
            # Transform point to DEM CRS if needed
            # point_on_dem = transform.transform(point_on_line)

            # Sample elevation
            elevation, success = dem_layer.dataProvider().sample(core.QgsPointXY(point_on_line), 1)
            if success:
                x = i * interval
                elevation_profile.append((x, elevation))
            else:
                print("Elevation data not available at", point_on_line)
                continue
        x = list(zip(*elevation_profile))[0]
        z = list(zip(*elevation_profile))[1]

        return x, z

    def draw_buffer(self):
        self.clear_rubber_band()
        geometry: core.QgsGeometry = self.selected_line.geometry()
        # Create a rubber band for line geometry, with red color
        self.buffer_rubber_band = gui.QgsRubberBand(self.iface.mapCanvas())
        self.buffer_rubber_band.setColor(QColor(255, 0, 0, 50))  # Red
        self.buffer_rubber_band.setWidth(2)  # Line width
        buffer = geometry.buffer(self.tolerance_slider.value(), segments=20)
        self.buffer_rubber_band.setToGeometry(buffer)
        self.buffer_geometry = buffer

    def clear_rubber_band(self):
        # Remove the existing rubber band if it exists
        if self.buffer_rubber_band:
            self.buffer_rubber_band.reset()
            self.buffer_rubber_band = None

    def get_nearby_features_dict(self):
        features = self.get_nearby_features_as_QgsFeatures()
        self._nearby_features_dict = {}
        for feature in features:
            field_names = feature.fields().names()
            if 'ExploName' in field_names:
                name = feature.attribute('ExploName')
            elif 'Name' in field_names:
                name = feature.attribute('ExploName')
            else:
                name = 'No Name'
                print('no valid name attribute found')
            if 'ExploDepth' in field_names:
                explo_depth = feature.attribute('ExploDepth')
            else:
                explo_depth = None
            d = self.get_distance_of_geometry_to_line_geometry(
                geometry_to_check=feature.geometry().centroid().asPoint())
            elevation = self.get_elevation_of_QgsPointXY(point=feature.geometry().asPoint())
            d['lidar'] = elevation
            d['ExploDepth'] = explo_depth
            self._nearby_features_dict[name] = d

    def get_layer_by_name(self, name: str):
        """
        Gets a reference to a layer in the currently active Qgis project by layer name
        :param name: the name of the layer to get
        :return: QgsMapLayer
        """
        layer = core.QgsProject.instance().mapLayersByName(name)[0]
        return layer

    def check_vector_list_selection(self):
        """Checks the current selection of the vector layer list relative to the old selection. If
        any of the vector layers are no longer selected, then their selection is removed. Then
        redetermine nearby features and update the vector layer selection list"""
        if self.vector_list_selection is None:
            self.vector_list_selection = self.vector_list.selectedItems()
            return self.get_nearby_features_as_ids()
        new_selection = [item.text() for item in self.vector_list.selectedItems()]
        for vector_layer_name in self.vector_list_selection:
            if vector_layer_name not in new_selection:
                print(f'new selection: {new_selection}')
                vector_layer = core.QgsProject.instance().mapLayersByName(vector_layer_name.text())[0]
                vector_layer.removeSelection()
                print(f'{vector_layer} not in the new selection')
                print('removed selection')
        self.get_nearby_features_as_ids()
        self.vector_list_selection = self.vector_list.selectedItems()
        return

    @property
    def nearby_features_as_ids(self):
        return self._nearby_features_as_ids

    @property
    def nearby_features_dict(self):
        return self._nearby_features_dict

    def get_nearby_features_as_QgsFeatures(self):
        """Iterates through self.nearby_features_as_ids which is a dict of layer names as keys and feature
        ids and values. Returns a list of QgsFeatures corresponding to the self.nearby_features_as_ids dict."""
        nearby_QgsFeatures = []
        for layer_name, feature_ids in self.nearby_features_as_ids.items():
            layer = self.get_layer_by_name(layer_name)
            for fid in feature_ids:
                feature = layer.getFeature(fid)
                nearby_QgsFeatures.append(feature)
        return nearby_QgsFeatures

    def get_distance_of_geometry_to_line_geometry(
            self,
            geometry_to_check: core.QgsPointXY,
            reference_geometry: core.QgsGeometry = None,
    ) -> dict:
        """
        Gets distance of a QgsGeometry to another reference QgsGeometry
        :param geometry_to_check: geometry to measure distance from
        :param reference_geometry: reference line geometry to measure distance to, must be a line geometry
        :return: dict with keys: 'Dist' - distance, 'minDistPoint' - point on reference geometry that is closest to the
        geometry to check, 'nextVertexIndex' - index of the next vertex after the closest segment. The vertex before the
        closest segment is always nextVertexIndex - 1, 'leftOrRightOfSegment' - indicates if the point is located on the
        left or right side of the geometry ( < 0 means left, > 0 means right, 0 indicates that the test was
        unsuccessful, e.g. for a point exactly on the line, 'distanceAlongLine' - distance along the length of the
        reference line to the point of closest distance to teh geometry_to_check.
        """
        if reference_geometry is None:
            reference_geometry = self.selected_line.geometry()
        (sqrDist,
         minDistPoint,
         nextVertexIndex,
         leftOrRightOfSegment) = reference_geometry.closestSegmentWithContext(geometry_to_check)
        distanceAlongLine = reference_geometry.lineLocatePoint(core.QgsGeometry.fromPointXY(minDistPoint))
        dist_dict = {
            'Dist': math.sqrt(sqrDist),
            'minDistPoint': minDistPoint,
            'nextVertexIndex': nextVertexIndex,
            'leftOrRightOfSegment': leftOrRightOfSegment,
            'distanceAlongLine': distanceAlongLine
        }
        return dist_dict

    def get_distance_of_point_along_line(
            self,
            reference_geometry: core.QgsGeometry = None,
            point_to_check: core.QgsGeometry = None
    ):
        """
        get distance along a line geometry to the closest point relative to another point (point_to_check)
        :param reference_geometry: if None is passed, will default to self.selected_line.geometry()
        :param point_to_check: must be a QgsGeometry of a QgsPointXY
        :return: distance along the reference line
        """
        if reference_geometry is None:
            reference_geometry = self.selected_line.geometry()
        distance_along_line = reference_geometry.lineLocatePoint(point_to_check)
        return distance_along_line
