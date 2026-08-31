import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1. Setup and Configuration

    In this first block of the notebook we import the needed libraries and configure constants.

    ### 1.1 What each import is needed for

    * `marimo`: Markdown cells and marimo UI elements
    * `geopandas`: Reading the processed GeoParquet
    * `matplotlib`: Access colormaps
    * `pyplot`: Legend plotting
    * `numpy`: Work on anomaly arrays and color range percentiles
    * `pandas`: Read the summary CSV
    * `Map`, `SolidPolygonLayer`: Display polygons and interactive map
    * `apply_continuous_cmap`: Converting normalized anomaly values into RGBA using Matplotlib colormap
    * `Normalize`: Transformation of physical range anomaly values into normalized 0 ... 1 values
    """)
    return


@app.cell
def _():
    import marimo as mo
    import geopandas as gpd
    import matplotlib as mpl
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd

    from lonboard import Map, SolidPolygonLayer
    from lonboard.colormap import apply_continuous_cmap
    from matplotlib.colors import Normalize

    return (
        Map,
        Normalize,
        SolidPolygonLayer,
        apply_continuous_cmap,
        gpd,
        mo,
        mpl,
        np,
        pd,
        plt,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 1.2 Data sources and paths

    * Path to the processed rainfall anomalies
    * Path to the summary statistics table
    * Range of the target years
    """)
    return


@app.cell
def _():
    PROCESSED_DATA_PATH = "data/processed/agricultural_rainfall_anomalies.parquet"
    SUMMARY_DATA_PATH = "data/processed/rainfall_deficit_summary.csv"

    TARGET_YEARS = range(2021, 2026)
    return PROCESSED_DATA_PATH, SUMMARY_DATA_PATH, TARGET_YEARS


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2. Loading processed data

    Here we read the two processed outputs from the rdas_processing notebook into a GDF and DF respectively.
    """)
    return


@app.cell
def _(PROCESSED_DATA_PATH, SUMMARY_DATA_PATH, gpd, pd):
    # Read anomaly polygons
    agri_gdf = gpd.read_parquet(PROCESSED_DATA_PATH)

    # Read summary statistics
    summary_df = pd.read_csv(SUMMARY_DATA_PATH)
    return agri_gdf, summary_df


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3. Constructing the year selector

    Here, we prepare the `marimo.ui` dropdown-element that allows to interactively switch between years. We pass the target years in as values and set the default value to 2021. We do not display the dropdown yet, as it will be displayed near the map for better usability.
    """)
    return


@app.cell
def _(TARGET_YEARS, mo):
    year_selector = mo.ui.dropdown(options={str(year): year for year in TARGET_YEARS}, value="2021", label="Year")
    return (year_selector,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 4. Prepare selected-year data

    First we read the year value of the dropdown element, and construct the corresponding anomaly column name. Everytime the dropdown value changes, all cells depending on that value are rerun. This is what allows our marimo notebook to act as an interactive explorer.

    Then we prepare the GDF that we will pass into the `lonboard.Map` as a `lonboard.SolidPolygonLayer`. Therefore, we first create a smaller copy of the original GDF, that only holds the relevant columns. Then we explicitly store the anomaly column as a NumPy array, which we will need later for coloring. The two lambda functions are there to format the values appropriately for the map pop-ups: We create two new columns that format the anomaly to two decimal places and handle nodata values, and convert square meters into square kilometers, also limiting the value to two decimal places. Lastly, we drop the unformatted columns, as we do not want / need them anymore.
    """)
    return


@app.cell
def _(year_selector):
    # Read dropdown value
    selected_year = year_selector.value

    # Construct according column name
    anomaly_column = f"anomaly_{selected_year}"
    return anomaly_column, selected_year


@app.cell
def _(agri_gdf, anomaly_column, pd):
    # Copy subset of anomaly polygons GDF
    map_gdf = agri_gdf[["geometry","area_m2", anomaly_column]].copy()

    # Store anomaly column as NumPy array
    anomaly_values = map_gdf[anomaly_column].to_numpy()

    # Add formatted pop-up columns
    map_gdf["Anomaly [mm]"] = map_gdf[anomaly_column].apply(
        lambda x: f"{x:.2f}" if pd.notna(x) else "No data"
    )

    map_gdf["Area [km²]"] = map_gdf["area_m2"].apply(
        lambda x: f"{x / 1_000_000:.2f}"
    )

    # Drop redundant unformatted columns
    map_gdf = map_gdf.drop(columns=[anomaly_column, "area_m2"])
    return anomaly_values, map_gdf


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 5. Common color scale

    In this fifth block, we establish one common color scale across all five target years. For that, we first create a list containing the names of all anomaly columns. Then, we select those columns from the original GDF, convert them into a NumPy array, and flatten them into a single sequence using `.ravel()`. This allows us to work on the whole range of values at once. Next, we calculate the 95th percentile of this range based on all non-nodata values, which we use for color stretching to reduce the influence of extreme values. The sign is ignored via `np.abs()`. With this we can create our normalizer (`matplotlib.colors.Normalize()`), to which we pass the 95th percentile with negative sign as vmin and with positive sign as vmax, and enable clipping to force all values to lie within 0 and 1. We define the normalizer here once and reuse / call it for the polygon coloring and the legend display.
    """)
    return


@app.cell
def _(Normalize, TARGET_YEARS, agri_gdf, np):
    # Construct list of all anomaly columns
    anomaly_columns = [f"anomaly_{year}" for year in TARGET_YEARS]

    # Convert anomaly columns into a flattened sequence
    all_anomalies = agri_gdf[anomaly_columns].to_numpy().ravel()

    # Calculate 95th percentile as range of values to linearly map from 0 to 1
    color_limit = np.nanquantile(np.abs(all_anomalies), 0.95)

    # Map values within [vmin, vmax] lineraly to [0.0, 1.0], clip values outside [vmin, vmax] to 0 and 1
    normalizer = Normalize(vmin=-color_limit, vmax=color_limit, clip=True)
    return (normalizer,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 6. Convert anomalies to colors

    Now we can call the prepared normalizer on the anomaly values and then use `apply_continuous_cmap()` to turn the normalized values into RGBA colors. We use the diverging `matplotlib.colormaps` cmap "RdYlBu" and set the alpha channel fully opaque.
    """)
    return


@app.cell
def _(anomaly_values, apply_continuous_cmap, mpl, normalizer):
    # Call normalizer on anomaly values
    normalized_anomaly = normalizer(anomaly_values)

    # Turn normalized values into fully opaque, diverging Red-Yellow-Blue RGBA colors
    fill_colors = apply_continuous_cmap(normalized_anomaly, mpl.colormaps["RdYlBu"], alpha=1.0)
    return (fill_colors,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 7. Final visualization

    Here happens the final visualization and exploration of the processed data.

    The first thing displayed is the earlier prepared `year_selector`, which is a dropdown that let's users select the specific target year they would like to explore. Changing this triggers a chain of reactive cell re-runs and ends up in the corresponding year polygons to be loaded as the current map layer. The specific dependencies can be explored on the left hand side, when opening this notebook in Marimo:

    > year_selector -> selected_year -> anomaly_column -> map_gdf -> anomaly_values -> normalized_anomaly -> fill_colors

    and

    > map_gdf -> polygon_layer <- fill_colors

    The polygon layer then get's constructed via `SolidPolygonLayer.from_geopandas()`, which takes the map_gdf and the fill_colors as input. `auto_highlight=True` enables a visual pop-out of the polygon that the mouse hovers above. On-click pop-ups are enabled by default and were configured inside map_gdf previously in block 4. All that is left to then, is to pass the layer to a `lonboard.Map()` to display it.

    We additionally provide a legend, which is constructed as a plot. The plot figure and plotting area are constructed first, then a colorbar is added to the figure with the exact same normalizer and colormap that the data uses for coloring. We then put the colorbal into legend_ax, make it horizontal, and store it in the variable `colorbar`, before adding the explanatory lable and displaying it.

    Lastly, we subset the summary_df according to the selected_year and format the contents for display in markdown, allowing users to have some statistical context of the currently displayed target year.

    As these following cells are meant to be used interactively, their code is hidden inside Marimo to improve usability.
    """)
    return


@app.cell(hide_code=True)
def _(year_selector):
    # Display year_selector
    year_selector
    return


@app.cell(hide_code=True)
def _(Map, SolidPolygonLayer, fill_colors, map_gdf):
    # Construct the layer
    polygon_layer = SolidPolygonLayer.from_geopandas(map_gdf, get_fill_color=fill_colors, auto_highlight=True)

    # Pass the layer to the map
    rainfall_map = Map(polygon_layer)

    # Display the map
    rainfall_map
    return


@app.cell(hide_code=True)
def _(mpl, normalizer, plt):
    # Initialize the legend plot
    legend_fig, legend_ax = plt.subplots(figsize=(6, 0.6))

    # Build the colorbar
    colorbar = legend_fig.colorbar(
        mpl.cm.ScalarMappable(norm=normalizer,cmap=mpl.colormaps["RdYlBu"]),
        cax=legend_ax,
        orientation="horizontal",
    )

    # Set explanatory label
    colorbar.set_label("Seasonal rainfall anomaly [mm]")

    # Display the legend
    legend_fig
    return


@app.cell(hide_code=True)
def _(mo, selected_summary, selected_year):
    mo.md(f"""
    ## Summary for {selected_year}

    * **Mean anomaly:** {selected_summary["mean_anomaly_mm"]:.1f} mm
    * **Median anomaly:** {selected_summary["median_anomaly_mm"]:.1f} mm
    * **Polygons with rainfall deficit:** {int(selected_summary["deficit_polygon_count"]):,} ({selected_summary["deficit_polygon_share"]:.1%})
    * **Agricultural area with rainfall deficit:** {selected_summary["deficit_area_km2"]:.1f} km² ({selected_summary["deficit_area_share"]:.1%})
    """)
    return


@app.cell(hide_code=True)
def _(selected_year, summary_df):
    # Subset summary DataFrame for selected_year
    selected_summary = summary_df[summary_df["year"] == selected_year].iloc[0]
    return (selected_summary,)


if __name__ == "__main__":
    app.run()
