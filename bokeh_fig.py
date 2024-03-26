from bokeh.plotting import figure, show
import bokeh.plotting as bkp
from bokeh.models.tools import (
    PanTool, WheelZoomTool, BoxZoomTool, ResetTool,
    HoverTool, SaveTool, BoxSelectTool, LassoSelectTool,
    PointDrawTool, PolyDrawTool, PolyEditTool, TapTool
)
from bokeh.models import ColumnDataSource


class BokehFig:
    """Custom Bokeh plot with custom defaults properties and methods"""

    def __init__(self, webgl=True, *args, **kwargs):
        #  Setup figure and data sources for drawn points and polys
        self.f = figure(*args, **kwargs)
        self.drawn_points_data = ColumnDataSource(data=dict(x=[], y=[]))
        self.drawn_points = self.f.scatter(x='x', y='y', source=self.drawn_points_data, size=10, color='blue')
        self.drawn_polys_data = ColumnDataSource(data=dict(xs=[], ys=[]))
        self.drawn_polys_vertex_data = ColumnDataSource(data=dict(x=[], y=[]))
        self.drawn_polys_vertex = self.f.scatter(x='x', y='y', source=self.drawn_polys_vertex_data, size=20,
                                                 color='red', marker='x')
        self.drawn_polys = self.f.patches(xs='xs', ys='ys', source=self.drawn_polys_data, color='blue')

        # Define tools
        self.pan_tool = PanTool()
        self.wheel_zoom_tool = WheelZoomTool()
        self.box_zoom_tool = BoxZoomTool()
        self.reset_tool = ResetTool()
        self.hover_tool = HoverTool()
        self.save_tool = SaveTool()
        self.box_select_tool = BoxSelectTool()
        self.lasso_select_tool = LassoSelectTool()
        self.point_draw_tool = PointDrawTool(renderers=[self.drawn_points])
        self.poly_draw_tool = PolyDrawTool(renderers=[self.drawn_polys])
        self.poly_edit_tool = PolyEditTool(renderers=[self.drawn_polys], vertex_renderer=self.drawn_polys_vertex)
        self.tap_tool = TapTool()

        # List of tools to pass to figure object
        tool_list = [
            self.pan_tool,
            self.wheel_zoom_tool,
            self.box_zoom_tool,
            self.reset_tool,
            self.hover_tool,
            self.save_tool,
            self.box_select_tool,
            self.lasso_select_tool,
            self.point_draw_tool,
            self.poly_draw_tool,
            self.poly_edit_tool,
            self.tap_tool
        ]
        self.f.sizing_mode = 'stretch_both'
        self.f.output_backend = 'webgl' if webgl is True else None
        self.f.tools = tool_list
        self.f.toolbar.active_scroll = self.wheel_zoom_tool
        self.f.toolbar.logo = None  # Remove Bokeh logo from toolbar

        #  Setup default axes properties
        axis_props = {
            'axis_line_width': 2,
            'major_label_text_font_size': '16px'
        }
        self.f.xaxis.update(**axis_props)
        self.f.yaxis.update(**axis_props)


    def show(self):
        return bkp.show(self.f)

    def line(self, *args, **kwargs):
        return self.f.line(*args, **kwargs)


if __name__ == "__main__":
    fig = BokehFig()
    fig.f.line(x=[1, 2, 3], y=[1, 6, 8])
    fig.show()
