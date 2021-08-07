import pandas as pd

### Funtions
def list_item_isin_list(list1: list, list2: list):
    for i in list1:
        if i in list2:
            return True
    return False


def filter_dataframe(
    original: pd.DataFrame,
    columns: list,
    conditions: list,
):
    """Filter dataframe with multiple conditions

    Args:
        original (pd.DataFrame): Orignal DataFrame to be fitlered
        columns (list): List of columns to be filtered. E.g ["Year"]
        conditions (list): Filter conditions for columns. E.g [[2010, 2015]]

    Returns:
        [pd.DataFrame]: Filtered DataFrame
    """
    filter_method = {
        "year": None,
        "directors": "overlap",
        "actors": "overlap",
        "countries": "overlap",
        "genres": "overlap",
        "rating": None,
    }

    for column, condition in zip(columns, conditions):
        if condition != None:
            if column == "countries":
                points = [point["location"] for point in condition["points"]]
            elif column == "rating":
                points = [point["x"] for point in condition["points"]]
                min_rating = min(points) - 0.16
                max_rating = max(points) + 0.06
                points = [round(min_rating * 10), round(max_rating * 10)]
                points = [i / 10 for i in range(points[0], points[1] + 1)]
            else:
                points = [point["label"] for point in condition["points"]]

            if filter_method[column] == "overlap":
                original = original[
                    original[column].apply(list_item_isin_list, list2=points)
                ]
            else:
                original = original[original[column].isin(points)]
    return original


def create_colorscale(x: list):
    """Custom colour scale that works with huge outliers

    Args:
        x (list): List of numeric numbers
    Returns:
        [list]: List that can be used as plotly colorscale
    """
    summary = pd.Series(x).describe()
    # If no values return basic colourscale
    if summary["count"] == 0:
        return [[0, "RGB(255, 255, 204)"], [1, "RGB(128, 0, 38)"]]
    maximum = summary["max"]
    colours = [
        [0, "RGB(255, 255, 204)"],
        [summary["25%"] / maximum / 2, "RGB(255, 237, 160)"],
        [summary["25%"] / maximum, "RGB(254, 217, 118)"],
        [summary["50%"] / maximum, "RGB(254, 178, 76)"],
        [summary["75%"] / maximum, "RGB(253, 141, 60)"],
        [(summary["75%"] / maximum + 1) / 2, "RGB(227, 26, 28)"],
        [1, "RGB(128, 0, 38)"],
    ]
    return colours


def generate_counts(x: pd.Series, n_keep: int = None, sort: bool = False):
    """Create dictionary from a pandas series showing item counts

    Args:
        x (pd.Series): pandas Series to generate counts

    Returns:
        [dict]: Count of all values in pandas Series
    """
    if type(x) == pd.Series:
        counts = x.value_counts()
        if n_keep != None:
            counts = counts[0:n_keep]
        return counts.to_dict()

    count = {}
    for row in x:
        for item in row:
            if item in count:
                count[item] = count[item] + 1
            else:
                count[item] = 1
    return count


def hover(df: pd.DataFrame, year: int):
    """Create hover text for a plotly bar chart

    Args:
        df (pd.DataFrame): pandas Dataframe
        year (int): year to subset
    Returns:
        [str]: hover data as string
    """
    year_slice = (
        df[df["year"] == year].sort_values("rating", ascending=False)["title"].to_list()
    )
    if len(year_slice) < 5:
        return year_slice
    else:
        return year_slice[0:5]


def extract_from_library(library):
    """Get data about each plex item

    Args:
        library (list): list of plex movies

    Returns:
        [list]: list of rows to crate pandas DataFrame
    """
    rows = []
    for i in library:
        rows.append({
            "title": i.title,
            "year": i.year,
            "rating": i.audienceRating,
            "genres": [genre.tag for genre in i.genres],
            "countries": [country.tag for country in i.countries],
            "actors": [actor.tag for actor in i.actors],
            "directors": [director.tag for director in i.directors],
            "studio": i.studio,
            "bitrate": i.media[0].bitrate,
            "release_date": i.originallyAvailableAt,
        })
    return rows


# Map Hong Kong to china. todo: seperate hong kong in map
def add_china_to_hk(x):
    if "Hong Kong" in x:
        if "China" not in x:
            x.append("China")
    return x
