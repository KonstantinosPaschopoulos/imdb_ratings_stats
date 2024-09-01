import pandas as pd
import plotly.express as px
from typing import Annotated
from fastapi import FastAPI, Request, File, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import logging
import os

app = FastAPI()
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)

logging.basicConfig(level=logging.INFO)

REQUIRED_COLUMNS = ["Year", "Directors", "Your Rating", "Genres", "IMDb Rating"]


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(name="index.html", context={"request": request})


@app.post("/upload", response_class=HTMLResponse)
def upload(file: Annotated[UploadFile, File()], request: Request):
    if file.content_type != "text/csv":
        logging.error("Uploaded file is not a CSV.")
        return templates.TemplateResponse(
            name="form.html",
            context={"request": request, "error": "Wrong input format."},
        )

    try:
        df = pd.read_csv(file.file)
    except pd.errors.EmptyDataError:
        logging.error("CSV file is empty.")
        return templates.TemplateResponse(
            name="form.html",
            context={"request": request, "error": "CSV file is empty or unreadable."},
        )
    except pd.errors.ParserError:
        logging.error("Error parsing CSV file.")
        return templates.TemplateResponse(
            name="form.html",
            context={"request": request, "error": "Error parsing the CSV file."},
        )
    except Exception as e:
        logging.error(f"Error reading CSV file: {e}")
        return templates.TemplateResponse(
            name="form.html",
            context={"request": request, "error": "Error reading the CSV file."},
        )

    if not all(col in df.columns for col in REQUIRED_COLUMNS):
        return templates.TemplateResponse(
            name="form.html",
            context={"request": request, "error": "CSV file missing required columns."},
        )

    figures = [
        _get_bar_fig(
            df, "Year", "Number of Movies/Shows", "Number of ratings by year of release"
        ),
        _get_director_fig(df),
        _get_bar_fig(
            df, "Your Rating", "Number of ratings", "Your ratings distribution"
        ),
        _get_genre_fig(df),
        _get_bar_fig(
            df, "IMDb Rating", "Number of ratings", "IMDb ratings distribution"
        ),
        _get_rating_difference_histogram(df),
    ]

    figures_html = "".join(
        [fig.to_html(include_plotlyjs=False, full_html=False) for fig in figures]
    )

    return templates.TemplateResponse(
        name="figures.html",
        context={
            "request": request,
            "ratings_count": len(df),
            "figures_html": figures_html,
        },
    )


def _get_bar_fig(df: pd.DataFrame, column: str, y_label: str, title: str) -> px.bar:
    """Helper function to generate a bar plot from a given column."""
    counts = df[column].value_counts().sort_index()
    return px.bar(
        counts,
        x=counts.index,
        y=counts.values,
        labels={"x": column, "y": y_label},
        title=title,
    )


def _get_director_fig(df: pd.DataFrame) -> px.bar:
    df = df.copy()
    df["Directors"] = df["Directors"].str.split(",")
    df = df.explode("Directors").rename(columns={"Directors": "Director"})
    top_directors = df["Director"].value_counts().head(15).sort_values(ascending=True)

    return px.bar(
        top_directors,
        x=top_directors.values,
        y=top_directors.index,
        orientation="h",
        labels={"x": "Number of Movies/Shows", "y": "Director"},
        title="Top 15 Directors by Number of ratings",
    )


def _get_genre_fig(df: pd.DataFrame) -> px.bar:
    df = df.copy()
    df["Genres"] = df["Genres"].str.split(", ")
    df = df.explode("Genres").rename(columns={"Genres": "Genre"})
    top_genres = df["Genre"].value_counts().head(10).sort_values(ascending=True)

    return px.bar(
        top_genres,
        x=top_genres.values,
        y=top_genres.index,
        orientation="h",
        labels={"x": "Number of ratings", "y": "Genre"},
        title="Top 10 genres by Number of ratings",
    )


def _get_rating_difference_histogram(df: pd.DataFrame) -> px.histogram:
    df["Rating Difference"] = df["Your Rating"] - df["IMDb Rating"]
    fig = px.histogram(
        df,
        x="Rating Difference",
        nbins=30,
        labels={"Rating Difference": "Difference (Your Rating - IMDb Rating)"},
        title="Histogram of Differences Between Your Ratings and IMDb Ratings",
    )
    fig.update_layout(yaxis_title="Number of Movies/Shows")
    return fig
