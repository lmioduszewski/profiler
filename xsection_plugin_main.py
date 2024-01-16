"""from qgis.PyQt.QtWidgets import (
    QAction, QMessageBox, QDockWidget, QToolBar,
    QComboBox)"""
import qgis.PyQt.QtWidgets as w
import qgis.gui as gui
import qgis.core as core
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsProfileRequest
import plotly.graph_objs as go


class XSectionPlugin(w.QWidget):
    def __init__(self, iface: gui.QgisInterface):
        super().__init__()
        self.iface = iface
        self.profile_canvas = gui.QgsElevationProfileCanvas()
        self.main_widget = w.QWidget()
        self.dock_widget = w.QDockWidget(
            parent=self.profile_canvas
        )
        self.dock_widget.setWidget(self.main_widget)
        self.toolbar = w.QToolBar(parent=self.main_widget)
        self.open_action = w.QAction('X-sect', self.iface.mainWindow())
        self.feature_identifier = gui.QgsMapToolIdentifyFeature(self.iface.mapCanvas())
        self.raster_combobox = w.QComboBox()
        self.layout = w.QVBoxLayout(self.main_widget)

    def initGui(self):
        self.open_action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.open_action)
        self.add_button(name='Sel', callback_function=self.get_line)
        self.layout.addWidget(self.raster_combobox)
        self.layout.addWidget(self.toolbar)
        self.get_rasters_for_combobox()

    def unload(self):
        # Remove the toolbar icon
        self.iface.removeToolBarIcon(self.open_action)
        # Disconnect signal connections
        if hasattr(self, 'feature_identifier') and self.feature_identifier:
            try:
                self.feature_identifier.featureIdentified.disconnect(self.callback)
            except:
                pass
        # Reset the map tool to the default (e.g., pan tool)
        if self.iface.mapCanvas().mapTool() == self.feature_identifier:
            self.iface.mapCanvas().unsetMapTool(self.feature_identifier)
        # Hide or close custom widgets or dockwidgets
        if self.main_widget.isVisible():
            self.main_widget.close()
        # Delete actions or UI elements if needed
        del self.open_action
        if hasattr(self, 'toolbar'):
            del self.toolbar
        if hasattr(self, 'main_widget'):
            del self.main_widget

    def run(self):
        self.iface.addDockWidget(Qt.BottomDockWidgetArea, self.dock_widget)

    def get_line(self):
        self.feature_identifier.setLayer(self.iface.activeLayer())
        self.feature_identifier.featureIdentified.connect(self.callback)
        self.iface.mapCanvas().setMapTool(self.feature_identifier)

    def add_button(self, name: str = None, callback_function=None):
        """adds a button with 'name' that calls a 'callback_function to the main widget"""
        button = w.QAction(name, self.main_widget)
        self.toolbar.addAction(button)
        button.triggered.connect(callback_function)

    def callback(self, feature: core.QgsFeature):
        print(f"You clicked on feature {feature.id()}")
        feature_geometry = feature.geometry()
        print(type(feature_geometry.type()))
        print(self.iface.activeLayer().name())
        line = core.QgsLineString(feature_geometry.asMultiPolyline()[0])
        self.get_profile_xy(line=line)

    def get_rasters_for_combobox(self):
        """Populates the combo box with names of raster layers."""
        layers = core.QgsProject.instance().mapLayers().values()
        for layer in layers:
            if layer.type() == core.QgsMapLayer.RasterLayer:
                self.raster_combobox.addItem(layer.name(), layer)
                print(layer.name())

    def get_profile_xy(
            self,
            dem_layer_name: core.QgsRasterLayer = None,
            line=None,
            num_points: int = 500
    ):
        if dem_layer_name is None:
            dem_layer_name = self.raster_combobox.currentData().name()
        dem_layer = core.QgsProject.instance().mapLayersByName(dem_layer_name)[0]

        # Transform context for CRS transformations
        transform_context = core.QgsCoordinateTransformContext()
        # CRS transformation from line CRS to DEM CRS
        # transform = core.QgsCoordinateTransform(line.crs(), dem_layer.crs(), transform_context)

        # Number of points to interpolate (increase for higher resolution)
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
                # print("Elevation data not available at", point_on_line)
                continue

        fig = go.Figure()
        fig.add_scattergl(x=list(zip(*elevation_profile))[0],
                          y=list(zip(*elevation_profile))[1])
        fig.show(renderer='browser')
