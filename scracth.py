from bokeh.io import show
from bokeh.models import ColumnDataSource, PolyDrawTool, PolyEditTool
from bokeh.plotting import figure

# Create initial data for polygons
xs = [[1, 3, 2], [3, 4, 6, 6]]
ys = [[4, 6, 8], [7, 8, 7, 5]]

source = ColumnDataSource(data=dict(xs=xs, ys=ys))

# Create a new plot
p = figure(title="PolyDraw and PolyEdit Example")
p.x_range.start, p.x_range.end = 0, 10
p.y_range.start, p.y_range.end = 0, 10

# Add patches renderer to the figure
renderer = p.patches('xs', 'ys', source=source, fill_color='blue', line_width=2)

# Initialize and add the PolyDraw and PolyEdit tools
draw_tool = PolyDrawTool(renderers=[renderer])
edit_tool = PolyEditTool(renderers=[renderer])
p.add_tools(draw_tool, edit_tool)
p.toolbar.active_tap = edit_tool

# Show the plot
show(p)
