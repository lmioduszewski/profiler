from pathlib import Path
import psycopg2
import pandas as pd
import shapely as shp
from plotly import graph_objects as go
# import webview
from plotly.subplots import make_subplots
import geopandas as gpd
import plotly
import pickle

data_dir = Path.cwd().joinpath('sample_data')


class Template:
    def __init__(self):

        # FIG TEMPLATE
        self._config = {
            'scrollZoom': True,
            'displaylogo': False
        }
        self.default_trace_colors = plotly.colors.DEFAULT_PLOTLY_COLORS
        self._trace_colors_dict = {}
        self._modebar = go.layout.Modebar(
            add=[
                'togglespikelines',
                'hovercompare',
                'togglehover',
                'drawline',
                'drawopenpath',
                'drawclosedpath',
                'drawcircle',
                'drawrect',
                'eraseshape',
                'hoverclosest',
            ]
        )
        self._xaxis_template = go.layout.XAxis(gridcolor='lightgray', griddash='dot')
        self._yaxis_template = go.layout.YAxis(gridcolor='lightgray', griddash='dot')
        self._font_template = go.layout.Font()

        self._template_layout = go.Layout(
            dragmode='pan',
            modebar=self._modebar,
            paper_bgcolor='white',
            plot_bgcolor='white',
            xaxis=self._xaxis_template,
            yaxis=self._yaxis_template,
        )
        self._template = go.layout.Template(layout=self._template_layout)
        self.layout = go.Layout(template=self._template)

        # to update subplot layout
        self._template_update_args = {
            'dragmode': 'pan',
            'modebar': self._modebar,
            'paper_bgcolor': 'white',
            'plot_bgcolor': 'white',
            'xaxis': {
                'showticklabels': True,
                'gridcolor': 'lightgray',
                'griddash': 'dot',
            },
            'xaxis2': {
                'showticklabels': True,
                'gridcolor': 'lightgray',
                'griddash': 'dot',
            },
            'yaxis': {
                'gridcolor': 'lightgray',
                'griddash': 'dot'
            },
            'yaxis2': {
                'gridcolor': 'lightgray',
                'griddash': 'dot'
            },
            'legend': {
                'x': -0.26,
                'y': 0.5
            },
        }

    def _get_colors_for_traces(self, names=None, color_list=None) -> dict:
        """
        Helper method to get color names for each trace being added to a fig.
        Returns a dictionary of names and colors. Can be used to sync colors between traces
        with certain names.
        :param names: iterable with names of traces
        :param color_list: list of eligible colors. Defaults to default plotly color list.
        :return: Dict where keys are names and values are CSS colors
        """
        if color_list is None:
            color_list = self.default_trace_colors
        if names is None:
            return self._trace_colors_dict
        trace_colors_dict = self._trace_colors_dict
        for idx, name in enumerate(names):
            if name in trace_colors_dict.keys():
                continue
            color = color_list[idx % len(color_list)]
            trace_colors_dict[name] = color
        return trace_colors_dict

    @staticmethod
    def create_hover(name_dict: dict = None):
        """
        Function to return a hover template for a Plotly figure
        :return: customdata, hovertemplate
        """
        names = list(name_dict.keys())
        lists = list(name_dict.values())
        list_len = len(lists[0])
        custom_data = []
        hover_template_list = []

        for i in range(list_len):
            this_list = [param[i] for param in lists]
            custom_data.append(this_list)

        for i, name in enumerate(names):
            if type(custom_data[0][i]) is float:
                hover_template_list.append(
                    f'<b>{name}: </b>%{{customdata[{i}]:.2f}}<br>'
                )
            else:
                hover_template_list.append(
                    f'<b>{name}: </b>%{{customdata[{i}]}}<br>'
                )
        hover_template_list.append('<extra></extra>')
        hover_template = ''.join(hover_template_list)

        return custom_data, hover_template


template = Template()


class BaseFig(go.Figure):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layout = template.layout
        self._config = {'scrollZoom': True}

    def show(self, renderer='browser', config=None, *args, **kwargs):
        if not config:
            config = self._config
        super().show(renderer=renderer, config=config, *args, **kwargs)


class Fig(BaseFig):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._subplot = None
        self.update_layout(template.layout)

    def subplot(self, *args, **kwargs):
        self._subplot = Subplot(*args, **kwargs)
        return self._subplot

    def add_to_subplot(self, subplot_fig: go.Figure, row: int, col: int):
        """Add go.Figure traces to a subplot figure

        Args:
            subplot_fig (make_subplots): subplot figure to add to
            row (int): row of subplot to add to
            col (int): column of subplot to add to
        """
        num_traces = range(len(self.data))
        subplot_fig.add_traces(
            list(self.data),
            rows=[row for i in num_traces],
            cols=[col for i in num_traces]
        )


class Subplot:

    def __init__(
            self,
            show_precip=False,
            show_map=False,
            show_flow=False,
            *args,
            **kwargs
    ):
        self._config = {'scrollZoom': True}
        self._subplot_titles = []
        self.titles = {
            'water levels': 'Water Level Data',
            'map': 'Monitoring Locations',
            'rain': 'Daily Rainfall',
            'flow': 'Stream Flow Data'
        }
        self.trace_specs = {
            'precip_color': 'blue',
            'precip_width': 1,
            'water_levels_width': 1.5
        }
        self._rows = None
        self._cols = None
        self._col_widths = None
        self._row_heights = None
        self._specs = None
        self.show_precip = show_precip
        self.show_map = show_map
        self.show_flow = show_flow
        self.fig = self.make(
            rows=self.num_rows,
            cols=self.num_cols,
            specs=self.specs,
            column_widths=self._col_widths,
            row_heights=self._row_heights,
            *args, *kwargs
        )
        self.apply_template_layout()

    @property
    def num_rows(self):
        if self._rows is None:
            self.num_rows = None
        return self._rows

    @num_rows.setter
    def num_rows(self, value=None):
        if self.show_precip and self.show_flow:
            rows = 3
            self._row_heights = [0.7, 0.1, 0.2]
            titles = ['water levels', 'rain', 'flow']
        elif self.show_precip or self.show_flow:
            rows = 2
            self._row_heights = [0.75, 0.25]
            titles = ['water levels']
            if self.show_precip:
                titles.append('rain')
            else:
                titles.append('flow')
        else:
            rows = 1
            self._row_heights = [1]
            titles = ['water levels']
        self._subplot_titles = [self.titles[title] for title in titles if title in self.titles]
        self._rows = rows

    @property
    def num_cols(self):
        if self._cols is None:
            self.num_cols = None
        return self._cols

    @num_cols.setter
    def num_cols(self, value=None):
        if self.show_map:
            cols = 2
            self._col_widths = [0.7, 0.3]
            self._subplot_titles.insert(1, self.titles['map'])

        else:
            cols = 1
            self._col_widths = [1]
        self._cols = cols

    @property
    def specs(self):
        if self._specs is None:
            self.specs = None
        return self._specs

    @specs.setter
    def specs(self, value=None):
        specs = []
        if self.show_map:
            rowspan = self.num_rows
            specs.append([{}, {'rowspan': rowspan, 'type': 'scattermapbox'}])
            for row in range(self._rows - 1):
                specs.append([{}, None])
        else:
            specs = None
        self._specs = specs

    def make(self, rows, cols, specs, column_widths, row_heights,
             horizontal_spacing=0.03,
             vertical_spacing=0.07,
             shared_xaxes=True
             ):
        return make_subplots(
            rows=rows,
            cols=cols,
            specs=specs,
            subplot_titles=self._subplot_titles,
            column_widths=column_widths,
            row_heights=row_heights,
            horizontal_spacing=horizontal_spacing,
            vertical_spacing=vertical_spacing,
            shared_xaxes=shared_xaxes
        )

    def add_trace(self, *args, **kwargs):
        return self.fig.add_trace(*args, **kwargs)

    def show(self, renderer='browser'):
        self.fig.show(config=template._config, renderer=renderer)

    def apply_template_layout(self):
        self.fig.update_layout(**template._template_update_args)

    def add_water_levels(self, df: pd.DataFrame = None, row=1, col=1, **kwargs):
        trace_names = df.columns[1:]
        trace_colors = template._get_colors_for_traces(trace_names)
        for idx, loc in enumerate(trace_names):
            self.add_trace(
                go.Scattergl(
                    x=list(df.iloc[:, 0]),
                    y=list(df.iloc[:, idx + 1]),
                    name=loc,
                    line_width=self.trace_specs['water_levels_width'],
                    line_color=trace_colors[loc],
                    marker_color=trace_colors[loc],
                    **kwargs
                ),
                row=row,
                col=col
            )
        self.fig.update_yaxes(
            title_text="Elevation (ft)",
            showticklabels=True,
            automargin=True,
            row=1,
            col=1)

    def add_precip(self, df: pd.DataFrame = None, row=2, col=1, cols_to_plot=None, type='bars', **kwargs):
        if cols_to_plot is None:
            columns = df.columns[1:]
        else:
            columns = df.columns[cols_to_plot:cols_to_plot + 1]
        if len(columns) > 1:
            self.fig.update_layout(barmode='group')
        for loc in columns:
            if type == 'bars':
                self.add_trace(
                    go.Bar(
                        x=list(df.iloc[:, 0]),
                        y=list(df.loc[:, loc]),
                        marker_color=self.trace_specs['precip_color'],
                        name=loc,
                        **kwargs
                    ),
                    row=row,
                    col=col
                )
            if type == 'lines':
                self.add_trace(
                    go.Scattergl(
                        x=list(df.iloc[:, 0]),
                        y=list(df.loc[:, loc]),
                        name=loc,
                        mode='lines',
                        line_color=self.trace_specs['precip_color'],
                        line_width=self.trace_specs['precip_width'],
                        **kwargs
                    ),
                    row=row,
                    col=col
                )
            self.fig.update_yaxes(
                title_text="Rainfall (in)",
                showticklabels=True,
                automargin=True,
                row=2,
                col=1
            )

    def add_map(self, locs: Path, loc_name_field='ExploName', row=1, col=2):
        gdf_locs = gpd.read_file(locs)
        map_center = shp.MultiPoint(gdf_locs.geometry).centroid
        map_center = dict(
            lat=map_center.y,
            lon=map_center.x
        )
        self.add_trace(
            go.Scattermapbox(
                lat=gdf_locs.geometry.y.to_list(),
                lon=gdf_locs.geometry.x.to_list(),
                mode='markers',
                text=gdf_locs.loc[:, loc_name_field],
                hovertemplate=gdf_locs.loc[:, loc_name_field] +
                              '<br>Lat: %{lat:.4f}<br>' +
                              'Lon: %{lon:.4f}<extra></extra>',
                showlegend=False,
            ),
            row=row,
            col=col
        )
        self.fig.update_layout(
            mapbox_style="open-street-map",
            mapbox_center=map_center,
            mapbox_zoom=13,
        )


def get_fig():
    logger_data = pd.read_excel(Path.cwd().joinpath('sample_data', 'logger_data.xlsx'))
    hand_data = pd.read_excel(Path.cwd().joinpath('sample_data', 'hand_data.xlsx'))
    precip_data = pd.read_excel(Path.cwd().joinpath('sample_data', 'rain_data.xlsx'))
    locs = Path().cwd().joinpath('sample_data', 'ten_trails_map_locs.shp')
    fig = Fig().subplot(show_precip=True, show_map=True)
    fig.add_map(locs)
    fig.add_water_levels(df=logger_data)
    fig.add_water_levels(df=hand_data, mode='markers', marker_size=5)
    fig.add_precip(precip_data, cols_to_plot=3, type='lines')

    # Save/pickle the fig
    with open(data_dir.joinpath('Ten_Trails.fig'), 'wb') as f:
        pickle.dump(fig.fig, f)

    return


if __name__ == '__main__':
    get_fig()
