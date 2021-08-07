from functions import (
    create_colorscale,
    generate_counts,
    filter_dataframe,
    add_china_to_hk,
)

import pandas as pd
import numpy as np
import ast
import os
import time

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

import plotly.express as px
import plotly.io as pio
import plotly.graph_objects as go

from plexapi.myplex import MyPlexAccount

# Customise plotly theme
pio.templates["custom"] = pio.templates["plotly"]
pio.templates["custom"]["layout"]["paper_bgcolor"] = "rgba(255,255,255,0.00)"
pio.templates["custom"]["layout"]["plot_bgcolor"] = "rgba(255,255,255,0.05)"
pio.templates["custom"]["layout"]["font_color"] = "white"
pio.templates["custom"]["layout"]["colorway"] = ("yellow",)
pio.templates.default = "custom"

# Load Data
test = True
if test == True:
    metadata = pd.read_csv("test.csv")
    metadata["genres"] = metadata["genres"].apply(ast.literal_eval)
    metadata["countries"] = metadata["countries"].apply(ast.literal_eval)
    metadata["actors"] = metadata["actors"].apply(ast.literal_eval)
    metadata["directors"] = metadata["directors"].apply(ast.literal_eval)
else:
    pass
metadata["countries"] = metadata["countries"].apply(add_china_to_hk)

# Initialise Plotly Dash
app = dash.Dash(__name__)
server = app.server
# Dash layout
app.layout = html.Div(
    children=[
        html.H1("Plex Library Stats"),
        html.Div(
            children=[
                html.Div(
                    id="initial_loading",
                    className="lds-dual-ring",
                ),
            ],
            className="container",
        ),
        html.Div(
            style={"display": "none"},
            id="main",
            children=[
                html.Button(
                    "Reset Filters",
                    id="reset_filters",
                    className="container",
                ),
                html.Div(
                    children=[
                        dcc.Graph(
                            id="year_bar_chart",
                            # figure=fig,
                            className="eight columns",
                        ),
                        dcc.Graph(
                            id="rating_table",
                            config={"displayModeBar": False},
                            className="four columns",
                        ),
                    ],
                    className="row",
                ),
                html.Div(
                    children=[
                        dcc.Graph(id="genre_bar_chart", className="six columns"),
                        dcc.Graph(id="country_choropleth", className="six columns"),
                    ],
                    className="row",
                ),
                html.Div(
                    children=[
                        dcc.Graph(
                            id="popular_actor_bar",
                            className="six columns",
                        ),
                        dcc.Graph(
                            id="popular_director_bar",
                            className="six columns",
                        ),
                    ],
                    className="row",
                ),
                dcc.Graph(id="ratings_histogram"),
                dcc.Graph(id="popular_actor_bar_animated", style={"display": "none"}),
            ],
        ),
    ]
)

# Callbacks to handle interactivity and cross-fitlering

# Movies per Year bar chart
@app.callback(
    Output("year_bar_chart", "figure"),
    [
        Input("reset_filters", "n_clicks"),
        Input("popular_director_bar", "selectedData"),
        Input("popular_actor_bar", "selectedData"),
        Input("country_choropleth", "selectedData"),
        Input("genre_bar_chart", "selectedData"),
        Input("ratings_histogram", "selectedData"),
    ],
)
def draw_year_chart(x, directors, actors, countries, genres, ratings):

    df = filter_dataframe(
        metadata,
        ["directors", "actors", "countries", "genres", "rating"],
        [directors, actors, countries, genres, ratings],
    )
    year_counts = generate_counts(df["year"])
    year_bar_chart = px.bar(
        y=year_counts.values(),
        x=year_counts.keys(),
        title="Movies per Year",
        labels={"x": "count", "y": "year"},
    )
    year_bar_chart.update_layout(
        margin=dict(
            r=0,
        ),
        xaxis_tickformat="d",
        clickmode="event+select",
    )
    return year_bar_chart


# Highest rated movies table
@app.callback(
    Output("rating_table", "figure"),
    [
        Input("year_bar_chart", "selectedData"),
        Input("popular_director_bar", "selectedData"),
        Input("popular_actor_bar", "selectedData"),
        Input("country_choropleth", "selectedData"),
        Input("genre_bar_chart", "selectedData"),
        Input("ratings_histogram", "selectedData"),
    ],
)
def items_per_year(years, directors, actors, countries, genres, ratings):

    df = filter_dataframe(
        metadata,
        ["year", "directors", "actors", "countries", "genres", "rating"],
        [years, directors, actors, countries, genres, ratings],
    )
    df = df.sort_values("rating", ascending=False).head(12)
    rating_table = go.Figure(
        go.Table(
            header=dict(values=["Title", "Rating"], fill_color="black"),
            cells=dict(
                values=[df["title"], df["rating"]],
                fill_color="black",
            ),
            columnwidth=[6, 1],
        ),
    )
    rating_table.update_layout(
        title_text="Highest rated",
        margin=dict(r=10, l=5, b=0),
    )
    return rating_table


# Count of Genres bar chart
@app.callback(
    Output("genre_bar_chart", "figure"),
    [
        Input("year_bar_chart", "selectedData"),
        Input("popular_director_bar", "selectedData"),
        Input("popular_actor_bar", "selectedData"),
        Input("country_choropleth", "selectedData"),
        Input("ratings_histogram", "selectedData"),
    ],
)
def draw_genre_chart(years, directors, actors, countries, ratings):

    df = filter_dataframe(
        metadata,
        ["year", "directors", "actors", "countries", "rating"],
        [years, directors, actors, countries, ratings],
    )

    genre_count = generate_counts(df["genres"].explode())

    genre_counts_bar = px.bar(
        x=genre_count.values(),
        y=genre_count.keys(),
        labels={"x": "count", "y": "genre"},
        title="Count of Genres",
    )
    genre_counts_bar.update_yaxes(categoryorder="total ascending")
    genre_counts_bar.update_layout(
        yaxis=dict(dtick=1),
        xaxis_tickformat="d",
        margin=dict(r=0),
        clickmode="event+select",
    )
    return genre_counts_bar


# Country choropleth
@app.callback(
    Output("country_choropleth", "figure"),
    [
        Input("year_bar_chart", "selectedData"),
        Input("popular_director_bar", "selectedData"),
        Input("popular_actor_bar", "selectedData"),
        Input("genre_bar_chart", "selectedData"),
        Input("ratings_histogram", "selectedData"),
    ],
)
def draw_country_choropleth(years, directors, actors, genres, ratings):
    df = filter_dataframe(
        metadata,
        ["year", "directors", "actors", "genres", "rating"],
        [years, directors, actors, genres, ratings],
    )
    country_count = df["countries"].explode()
    country_count = generate_counts(country_count)
    choropleth = go.Figure(
        data=go.Choropleth(
            locationmode="country names",
            locations=list(country_count.keys()),
            z=list(country_count.values()),
            colorscale=create_colorscale(country_count),
            reversescale=False,
            colorbar_title="Count",
        )
    )
    choropleth.update_layout(
        title_text="Library items by country",
        geo=dict(
            showcoastlines=False,
        ),
        margin=dict(l=0),
        clickmode="event+select",
    )
    return choropleth


# Popular Actors bar chart
@app.callback(
    Output("popular_actor_bar", "figure"),
    [
        Input("year_bar_chart", "selectedData"),
        Input("popular_director_bar", "selectedData"),
        Input("country_choropleth", "selectedData"),
        Input("genre_bar_chart", "selectedData"),
        Input("ratings_histogram", "selectedData"),
    ],
)
def draw_popular_actor_bar(years, directors, countries, genres, ratings):
    df = filter_dataframe(
        metadata,
        ["year", "directors", "countries", "genres", "rating"],
        [years, directors, countries, genres, ratings],
    )
    actor_count = generate_counts(df["actors"].explode(), n_keep=10)

    actor_counts_bar = px.bar(
        x=actor_count.values(),
        y=actor_count.keys(),
        labels={"x": "count", "y": "actor"},
        title="Popular Actors",
    )
    actor_counts_bar.update_yaxes(categoryorder="total ascending")
    actor_counts_bar.update_layout(
        yaxis=dict(dtick=1),
        margin=dict(r=0),
        clickmode="event+select",
        xaxis_tickformat="d",
    )
    return actor_counts_bar


# Popular Directors bar chart
@app.callback(
    Output("popular_director_bar", "figure"),
    [
        Input("year_bar_chart", "selectedData"),
        Input("popular_actor_bar", "selectedData"),
        Input("country_choropleth", "selectedData"),
        Input("genre_bar_chart", "selectedData"),
        Input("ratings_histogram", "selectedData"),
    ],
)
def draw_popular_director_chart(years, actors, countries, genres, ratings):
    # df = filter_dataframe(metadata, ["year"], [years])
    df = filter_dataframe(
        metadata,
        ["year", "actors", "countries", "genres", "rating"],
        [years, actors, countries, genres, ratings],
    )
    director_count = generate_counts(df["directors"].explode(), n_keep=10)

    director_counts_bar = px.bar(
        x=director_count.values(),
        y=director_count.keys(),
        labels={"x": "count", "y": "director"},
        title="Popular Directors",
    )
    director_counts_bar.update_yaxes(categoryorder="total ascending")
    director_counts_bar.update_layout(
        yaxis=dict(dtick=1),
        margin=dict(r=0),
        clickmode="event+select",
        xaxis_tickformat="d",
    )
    return director_counts_bar


# Ratings disribution histogram
@app.callback(
    Output("ratings_histogram", "figure"),
    [
        Input("year_bar_chart", "selectedData"),
        Input("popular_director_bar", "selectedData"),
        Input("popular_actor_bar", "selectedData"),
        Input("country_choropleth", "selectedData"),
        Input("genre_bar_chart", "selectedData"),
    ],
)
def draw_ratings_histogram(years, directors, actors, countries, genres):
    df = filter_dataframe(
        metadata,
        ["year", "directors", "actors", "countries", "genres"],
        [years, directors, actors, countries, genres],
    )
    ratings = df["rating"]
    ratings_histogram = go.Figure()
    ratings_histogram.add_trace(
        go.Histogram(x=ratings, xbins=dict(start=0, end=10, size=0.3))
    )
    ratings_histogram.update_layout(
        title="Rating Distribution", clickmode="event+select"
    )
    return ratings_histogram


@app.callback(
    [
        Output("popular_actor_bar_animated", "figure"),
        Output("initial_loading", "style"),
        Output("main", "style"),
    ],
    [
        Input("year_bar_chart", "selectedData"),
        Input("popular_director_bar", "selectedData"),
        Input("country_choropleth", "selectedData"),
    ],
)
def draw_popular_actor_animated(years, directors, countries):
    df = filter_dataframe(
        metadata,
        ["year", "directors", "countries"],
        [years, directors, countries],
    )
    df = df[["actors", "year", "title", "release_date"]].explode("actors")
    # Keep only top 10 actors
    top_ten_actors = df["actors"].value_counts()[0:10].index
    df = df[df["actors"].isin(top_ten_actors)]
    # Only keep years >1 actor worked
    valid_years = np.sort(df["year"].unique())

    running_total = {}
    for actor in top_ten_actors:
        running_total[actor] = 0
    running_total

    rows = []
    for year in valid_years:
        df_subset = df[df["year"] == year]
        for row in df_subset.itertuples():
            if row.actors in top_ten_actors:
                running_total[row.actors] += 1
        for actor in running_total:
            rows.append([year, actor, running_total[actor]])

    running_total_df = pd.DataFrame(rows, columns=["year", "actor", "running_count"])
    actors_animated = px.bar(
        running_total_df,
        x="running_count",
        y="actor",
        animation_frame="year",
        title="Running Total of Most Popular Actors",
    ).update_yaxes(categoryorder="total ascending")
    actors_animated.update_layout(
        xaxis_range=[0, max(running_total_df["running_count"])],
        margin=dict(r=0),
        clickmode="event+select",
    )
    return actors_animated, {"display": "none"}, {"display": "inline"}


# Handle button to reset all filters
@app.callback(
    [
        Output("year_bar_chart", "selectedData"),
        Output("popular_director_bar", "selectedData"),
        Output("popular_actor_bar", "selectedData"),
        Output("country_choropleth", "selectedData"),
        Output("ratings_histogram", "selectedData"),
    ],
    Input("reset_filters", "n_clicks"),
)
def reset_filters(x):
    return (None,) * 5


if __name__ == "__main__":
    app.run_server()

# To do
# Hong Kong to be seperated
# Hover displays examples of best movies
