import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1. Setup and Configuration

    In this first block of the notebook we import the needed libraries, define constants, and create and set up the DuckDB connection to the Overture bucket.

    ### 1.1 What each import is needed for

    * `marimo`: Markdown cells
    * `duckdb`: Embedded analytical database used to query Overture GeoParquet directly from S3
    * `geopandas`: Reading the NUTS GeoPackage, transforming CRS, handling Overture geometries, calculating centroids, writing GeoParquet
    * `numpy`: Masking arrays, nodata handling, raster statistics
    * `pandas`: Tabular summary data
    * `rasterio`: Remote access to CHIRPS COGs, and raster subsetting and georeferencing
    * `rowcol`: Converting centroid coordinates into raster row/column indices
    * `from_bounds`: Calculating raster window corresponding to the Sicily bbox for CHIRPS subsetting
    """)
    return


@app.cell
def _():
    import marimo as mo
    import duckdb
    import geopandas as gpd
    import numpy as np
    import pandas as pd
    import rasterio
    from rasterio.transform import rowcol
    from rasterio.windows import from_bounds

    return duckdb, from_bounds, gpd, mo, np, pd, rasterio, rowcol


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 1.2 Parameters, data sources, and paths

    Here, we keep all parameters, data sources and paths within a centralized configuration cell. Avoiding spreading these definitions through the notebook allows for better adaptability and readability. Two types of constants are defined:
    1. **User-configurable parameters**
    * The code of the NUTS region to be used as AOI
    * The range of months to be considered as an agricultural season
    * The range of CHIRPS years for which the analysis should be carried out
    * The range of years that constitutes the analysis baseline
    * The range of years for which the rainfall anomalies are to be calculated in relation to the baseline
    2. **Data sources and paths**
    * The Overture S3 region
    * Location of the NUTS GeoPackage
    * S3 path to the Overture land-cover dataset
    * URL to the CHIRPS COG mirror
    * Output path for the agricultural polygons
    * Output path for the processed rainfall anomalies
    * Output path for the summary statistics table
    """)
    return


@app.cell
def _():
    # User-configurable parameters
    AOI_NUTS_CODE = "ITG1"
    MONTHS = range(3,10)
    YEARS = range(1991, 2026)
    BASELINE_YEARS = range (1991, 2021)
    TARGET_YEARS = range(2021, 2026)

    # Data sources and paths
    S3_REGION = "us-west-2"
    NUTS_GPKG = "data/raw/NUTS_RG_01M_2024_3035.gpkg"
    OVERTURE_S3_PATH = "s3://overturemaps-us-west-2/release/2026-07-22.0/theme=base/type=land_cover/*"
    CHIRPS_COG_BASE_URL = "https://data.chc.ucsb.edu/products/CHIRPS/v3.0/monthly/global/cogs"
    AGRI_POLYGON_OUTPUT_PATH = "data/raw/agri_polygons.parquet"
    PROCESSED_OUTPUT_PATH = "data/processed/agricultural_rainfall_anomalies.parquet"
    SUMMARY_OUTPUT_PATH = "data/processed/rainfall_deficit_summary.csv"
    return (
        AGRI_POLYGON_OUTPUT_PATH,
        AOI_NUTS_CODE,
        BASELINE_YEARS,
        CHIRPS_COG_BASE_URL,
        MONTHS,
        NUTS_GPKG,
        OVERTURE_S3_PATH,
        PROCESSED_OUTPUT_PATH,
        S3_REGION,
        SUMMARY_OUTPUT_PATH,
        TARGET_YEARS,
        YEARS,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 1.3 How the duckdb setup works

    First, we create an in-process DuckDB database connection. In-process means that it runs inside the same process as this Python file and that there is no separate database server process. Since we don't provide a database path, the DuckDB instance is in-memory, meaning we don't create a persistent .duckdb database file. In-memory is what we want for this project since we use DuckDB solely as a query enginge and not as persistent storage.

    Then, we install and load two DuckDB extensions that we need in order to access geometry functions and access remote files (HTTP/S3).

    Lastly, we configure the S3 region for the Overture release, which is hosted in us-west-2.

    One thing to note here is that there is two different DuckDB interfaces involved in this setup: the Python API and the SQL engine. For some SQL functionalities (e.g. installing and loading extensions) DuckDB provides dedicated Python API methods, while others (e.g. S3 config) are sent to the DuckDB SQL engine as SQL statements (i.e., via `execute()`).
    """)
    return


@app.cell
def _(S3_REGION, duckdb):
    # Create database connection
    con = duckdb.connect()

    # Install and load extensions
    con.install_extension("spatial")
    con.load_extension("spatial")

    con.install_extension("httpfs")
    con.load_extension("httpfs")

    # Configure S3 region
    con.execute(f"SET s3_region='{S3_REGION}'")
    return (con,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2. Defining the Area of Interest

    In this second block of the notebook, we extract the definition of our AOI from the NUTS (nomenclature of territorial units for statistics) regions via its unique _NUTS_ID_. The latest NUTS dataset (as of now 2024) in _01M_ scale is retrieved from [eurostat](https://ec.europa.eu/eurostat/web/gisco/geodata/statistical-units/territorial-units-statistics) as GeoPackage, and is provided in the repository under [finalProj/app/data/raw](https://github.com/MarkusTomio/applicationDevelopment/tree/main/finalProj/app/data/raw).


    **How the AOI definition is implemented**

    First, we read the provided NUTS GeoPackage (EPSG:3035) into a `GeoDataFrame`. A `GeoDataFrame` is a tabular data structure from `GeoPandas`, whith an added geometry column (stored as a `GeoSeries`, which in turn uses `Shapely` for handling spatial data types) and the CRS stored in its metadata. It behaves like an "ordinary" data table, where rows represent features and the columns hold their attributes.

    Second, we create a boolean mask with the NUTS 2 identifier for Sicily ("ITG1") and assign the result to a new independent `GeoDataFrame` with `.copy()`.

    Third, we transform the AOI from its native EPSG:3035 into EPSG:4326, as Overture and CHIRPS data are georeferenced in that CRS.

    Fourth, we extract the bounding box (bbox) of the AOI using `geopandas.GeoSeries.total_bounds`, which returns a tuple containing minx, miny, maxx, maxy values for the bounds of the series as a whole. The bbox is later used to reduce the Overture query and to calculate the CHIRPS raster window.

    Lastly, we take the actual geometry of the AOI (Sicily / NUTS region ITG1) and convert it into `Well-Known Binary` (WKB). This is needed for querying the Overture features not only for the AOIs rectangular bbox, but for explicitly ensuring they intersect the actual AOI geometry.

    More information on how the bbox and WKB geometry get used for querying / subsetting are given in the respective blocks below.
    """)
    return


@app.cell
def _(AOI_NUTS_CODE, NUTS_GPKG, gpd):
    # Read NUTS GeoPackage
    nuts_3035 = gpd.read_file(NUTS_GPKG)

    # Copy AOI into independent GDF
    aoi_3035 = nuts_3035[nuts_3035['NUTS_ID'] == AOI_NUTS_CODE].copy()

    # Transform to EPSG:4326
    aoi_4326 = aoi_3035.to_crs(epsg=4326)

    # Extract AOI bbox values
    aoi_minx, aoi_miny, aoi_maxx, aoi_maxy = aoi_4326.total_bounds

    # Convert AOI geometry to WKB
    aoi_geom_wkb = aoi_4326.geometry.iloc[0].wkb
    return aoi_geom_wkb, aoi_maxx, aoi_maxy, aoi_minx, aoi_miny


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3. Overture agricultural polygon acquisition

    Now we query the Overture bucket to retrieve the agricultural polygons within the Sicily NUTS region.

    For that, we first define our query as a string, as it is part of the SQL structure. Question marks can be used as placeholders for query parameters, but file paths need different handling. The S3 path is passed into the query string for it to be present before / during execution, and the output path is given as a standard Python argument in the `to_parquet()` wrapper method. Expressed in natural language, the query says:

    > `Select` everything `From` the remote GeoParquet files on S3 `WHERE` the subtype is crop, that is within the bbox, and that intersects with the geometry of the AOI (reconstructing the geometry from the WKB).

    Notably, we first use a cheap bbox filter to narrow down the amount of data the intersects test needs to go through during the finer filtering.

    After the query is defined, `con.sql()` executes it with the passed in parameter and stores the resulting relation in a variable.

    Lastly, the relation is saved via `to_parquet()`, where DuckDB recognizes the geometry column and therefore keeps the geospatial metadata. This allows us to read it directly as a `GeoDataFrame` later.
    """)
    return


@app.cell
def _(
    AGRI_POLYGON_OUTPUT_PATH,
    OVERTURE_S3_PATH,
    aoi_geom_wkb,
    aoi_maxx,
    aoi_maxy,
    aoi_minx,
    aoi_miny,
    con,
):
    # Define query
    query = f"""
        SELECT *
        FROM read_parquet('{OVERTURE_S3_PATH}')
        WHERE
            subtype = 'crop'
            AND bbox.xmin <= ?
            AND bbox.xmax >= ?
            AND bbox.ymin <= ?
            AND bbox.ymax >= ?
            AND ST_INTERSECTS(
                ST_GeomFromWKB(?),
                geometry
            )
    """

    # Execute query with given parameters
    agri_relation = con.sql(query, params=[aoi_maxx, aoi_minx, aoi_maxy, aoi_miny, aoi_geom_wkb])

    # Save relation as GeoParquet
    agri_relation.to_parquet(AGRI_POLYGON_OUTPUT_PATH)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 4. CHIRPS acquisition and seasonal aggregation

    In this block we access the monthly CHIRPS precipitation rasters directly from the [USB Climate Hazard Center COG mirror](https://data.chc.ucsb.edu/products/CHIRPS/v3.0/monthly/global/cogs/), but only for the given years and months, and only for the the raster window corresponding to the AOI bbox. We also aggregate these monthly rasters to yearly / seasonal ones.

    The processing logic is wrapped in a function for the purposes of reusability and separation of concerns. We first create a dictionary `seasonal_rainfall` that will later be filled with years as keys and 2D arrays containing the summed seasonal precipitation. Also, we create an initially "empty" variable `window_transform`, which will store the affine transformation of the cropped Sicily raster window so that the NumPy arrays can be georeferenced. Then, we loop over the years, creating fresh list every time, allowing us to temporarily store individual monthly precipitation arrays and sum them up later. Inside sits a nested loop over the months: this is where the core of the acquisition sits. For each month, the corresponding URL is configured, and the remote COG is opened as a raster dataset. A `Rasterio` window is then constructed from the bbox values and the COGs transformation, telling `Rasterio` where the COG lies geographically. `src.read()` then actually reads the raster values from band 1 within the given window. During implementation it was found that `src.nodata` is not defined for the COGs, so we mask values equal to -9999 with `np.ma.masked_equal()`. This is neccessary, so that nodata is correctly ignored in later statistical calculations. We append the result to the temporary monthly list and check if `window_transform` already stores an actual value: which is _False_ for the first loop execution (-> affine transformation for cropped window get's stored via `src.window_transform()`) and _True_ for all subsequent runs (-> we can skip repeated assigning). Lastly, we sum the monthly arrays into one yearly / seasonal raster array per year, where _axis=0_ makes sure we sum across the first dimension (i.e., the values) and keep the row x columns structure in tact, making it a yearly / seasonal 2D raster (7 x rows x columns -> rows x columns). `.ma` makes sure the earlier created mask applies to the calculation.

    The next cell calls the function.
    """)
    return


@app.cell
def _(from_bounds, np, rasterio):
    def acquire_chirps(base_url, months, years, xmin, ymin, xmax, ymax):

        # Initialize return values
        seasonal_rainfall = {}
        window_transform = None

        for year in years:
            # Initialize monthly arrays list
            monthly_arrays = []

            for month in months:
                # Construct month & year specific url 
                url = f"{base_url}/chirps-v3.0.{year}.{month:02d}.cog"

                # Open remote COG
                with rasterio.open(url) as src:
                    # Define raster window
                    window = from_bounds(xmin, ymin, xmax, ymax, transform=src.transform)

                    # Read remote COG within window
                    rainfall = src.read(1, window=window)
                    # Mask nodata
                    rainfall = np.ma.masked_equal(rainfall, -9999)

                    # Append to monthly array list
                    monthly_arrays.append(rainfall)

                    # Store affine transformation during first run
                    if window_transform is None:
                        window_transform = src.window_transform(window)

            # Calculate yearly rainfall and store in dict
            seasonal_rainfall[year] = np.ma.sum(monthly_arrays, axis=0)

        return seasonal_rainfall, window_transform

    return (acquire_chirps,)


@app.cell
def _(
    CHIRPS_COG_BASE_URL,
    MONTHS,
    YEARS,
    acquire_chirps,
    aoi_maxx,
    aoi_maxy,
    aoi_minx,
    aoi_miny,
):
    # Call the function and store return values
    seasonal_rainfall, chirps_transform = acquire_chirps(CHIRPS_COG_BASE_URL, MONTHS, YEARS, aoi_minx, aoi_miny, aoi_maxx, aoi_maxy)
    return chirps_transform, seasonal_rainfall


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 5. Calculating the historical baseline and rainfall anomalies

    The baseline calculation is best read inside-out. The list comprehension creates a list of rasters for all rasters within the baseline year range. We then (again with `.ma` for the same reason as above), average them along the year dimension (i.e., pixel by pixel). The explicit `axis=0` is needed because we are reducing dimensions. The result is one average value for the whole baseline.

    The anomalies are calculated for each set year by subtracting the baseline from each years rainfall. The anomalies are stored as a dictionary to retain the years as naturally fitting keys.
    """)
    return


@app.cell
def _(BASELINE_YEARS, TARGET_YEARS, np, seasonal_rainfall):
    # Calculate baseline
    baseline = np.ma.mean([seasonal_rainfall[year] for year in BASELINE_YEARS], axis=0)

    # Calculate anomalies
    anomalies = {year: seasonal_rainfall[year] - baseline for year in TARGET_YEARS}
    return (anomalies,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 6. Sampling rainfall anomalies at agricultural polygon centroids

    In this block of the notebook we derive the centroid positions of the agricultural polygons that we retrieved earlier in block 3 and attach their sampled anomaly values.

    First, we load the saved agricultural polygons into a geodataframe. Then, we calculate the centroids while temporarily transforming the gdf into EPSG:32633 for the calculation, which is a fitting UTM Zone (33N). This is necessary, because calculating them in longitude / latitude is not ideal and the transformation allows us to calculate them in the suitable projected CRS. The resulting `GeoSeries` points are transformed back into EPSG:4326 to match the CRS of the CHIRPS data.

    Second, we use `rasterio.transform.rowcol()`, which in this case transforms the given geographic centroid coordinates into raster array indices using the affine transformation of the earlier saved CHIRPS window. The result of `rowcol()` is two sequences that tell us within which row and column of the raster each centroid lies.

    Third, we need to create a binary mask that stores whether each centroid is spatially within the rasters. We read the list comprehension bottom up, starting with zipping the retrieved corresponding row and col valued into pairs. Then for each pair of centroid positions, we check if it falls within the shape of the anomaly rasters (`shape[0]` is the rows and `shape[1]` is the columns). As all raster arrays have the same dimension, we perform the check only on the "first" anomaly raster (in this case `TARGET_YEARS[0]` is the year 2021).

    Fourth, we iterate over our anomalies dictionary while tracking the key as year and the corresponding 2D array as anomaly, and initialize a numpy array filled with nan (not a number) in the length of the centroids `GeoSeries`.

    Fifth, we process each centroid position individually. `i` tracks the current position we are processing via the index it receives from `enumerate()`. `zip()` creates tuples for each centroid, storing its row and column index toghether with the corresponding validity boolean mask value. For each valid centroid, we retrieve its corresponding anomaly value, and if that value is not masked (i.e., if it is not a nodata cell), we insert it into the earlier created numpy array at its respective index position.

    Lastly, we add the sampled values per year as a new column to the agricultural polygons GDF. The result is a GDF of agricultural polygons in the AOI that hold their corresponding anomaly values per year as attributes.
    """)
    return


@app.cell
def _(AGRI_POLYGON_OUTPUT_PATH, gpd):
    # Read our agricultural polygons
    agri_gdf = gpd.read_parquet(AGRI_POLYGON_OUTPUT_PATH)
    return (agri_gdf,)


@app.cell
def _(TARGET_YEARS, agri_gdf, anomalies, chirps_transform, rowcol):
    # Calculate centroids of the polygons in appropriate projected CRS and transform back to common CRS
    centroids = (agri_gdf.to_crs(epsg=32633).centroid.to_crs(epsg=4326))

    # Get raster array indices from geographic centroid coordinates
    rows, cols = rowcol(chirps_transform, centroids.x, centroids.y)

    # Boolean mask for checking whether centroids lie within raster array shape
    valid = [
        0 <= row < anomalies[TARGET_YEARS[0]].shape[0]
        and 0 <= col < anomalies[TARGET_YEARS[0]].shape[1]
        for row, col in zip(rows, cols)
    ]
    return centroids, cols, rows, valid


@app.cell
def _(agri_gdf, anomalies, centroids, cols, np, rows, valid):
    # Loop over anomalies dict
    for year, anomaly in anomalies.items():
        # Initialize np array for storing sampled anomalies
        values = np.full(len(centroids), np.nan)

        # Loop over centroids while tracking index position and validity
        for i, (row, col, is_valid) in enumerate(zip(rows, cols, valid)):
            # Retrieve anomaly value if centroid position is valid
            if is_valid:
                value = anomaly[row, col]

                # Insert anomaly value into values if it's not masked as nodata
                if not np.ma.is_masked(value):
                    values[i] = value

        # Create new columns in GDF per year with corresponding sampled anomaly values
        agri_gdf[f"anomaly_{year}"] = values
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 7. Calculating agricultural area and storing the processed data

    In block seven of the notebook, we calulcate the area of each agricultural polygon and save the result locally.

    We first load an independent copy of the existing GDF, leaving us with a clean variable for subsequent processing. The, we store its transformed version in a new variable. The transformation into the projected CRS is necessary to calculate the areas in the square meters unit and append it to the GDF as a new column. Lastly, we write the resulting GDF to a GeoParquet at the defined output path, leaving out the internal Pandas row index via `index=False`.
    """)
    return


@app.cell
def _(PROCESSED_OUTPUT_PATH, agri_gdf):
    # Load fresh copy of our GDF
    processed_gdf = agri_gdf.copy()

    # Create a transformed version in projected CRS
    agri_utm = processed_gdf.to_crs(epsg=32633)

    # Calculate polygon areas and append to GDF as new column
    processed_gdf["area_m2"] = agri_utm.geometry.area

    # Save resulting GDF as GeoParquet
    processed_gdf.to_parquet(PROCESSED_OUTPUT_PATH, index=False)
    return (processed_gdf,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 8. Calculating yearly summary statistics

    In this final processing block of the notebook, we calculate yearly statistics for our calculated rainfall anomaly agricultural polygons. These statistics add conextual statistical value to the outcome.

    We first initialize an empty list that will hold a dictionary of summary statistics per year. Then we loop over the target years and construct the anomaly column name per year, and also generate boolean mask to ensure we (1) don't calculate statistics on nodata entries and (2) know where rainfall deficit is present. This is all we need to calculate the statistics. We now create an actual statistics dictionary per year, and append it to the list of dictionaries. A few things noteworthy for the statistics calculations:

    * `.loc` let's us select a specific column of the GDF. Combined with a binary mask, we ensure we only work on cells that fulfill the masking criterion (i.e., where the mask is of value _True_).
    * Calling `.sum()` on a mask returns the number / sum / amount of cells holding the value _True_.
    * Square meters are converted into square kilometers, as it is the more sensible / reasonable unit here.

    The key names and the rest of the statistical calculation should be self explanatory.

    Lastly, we store the list of dictionaries as an ordinary `Pandas DataFrame` so that it becomes tabular data and save it to the configured output path as `CSV`. We don't use a GDF, as we don't have geographic attributes here.
    """)
    return


@app.cell
def _(SUMMARY_OUTPUT_PATH, TARGET_YEARS, pd, processed_gdf):
    # Initialize empty list
    summary_rows = []

    # Loop over target years
    for summary_year in TARGET_YEARS:
        # Construct this years anomaly column name
        anomaly_column = f"anomaly_{summary_year}"

        # Binary mask for location nodata anomaly values
        valid_mask = processed_gdf[anomaly_column].notna()
        # Binary mask for location polygons with rainfall deficit
        deficit_mask = processed_gdf[anomaly_column] < 0

        # Generate statistics dictionary for this year and append it to the list
        summary_rows.append({
            "year": summary_year,
            "mean_anomaly_mm": processed_gdf.loc[valid_mask, anomaly_column].mean(),
            "median_anomaly_mm": processed_gdf.loc[valid_mask, anomaly_column].median(),
            "deficit_polygon_count": deficit_mask.sum(),
            "deficit_polygon_share": deficit_mask.sum() / valid_mask.sum(),
            "deficit_area_km2": (processed_gdf.loc[deficit_mask, "area_m2"].sum() / 1_000_000),
            "deficit_area_share": (processed_gdf.loc[deficit_mask, "area_m2"].sum() / processed_gdf.loc[valid_mask, "area_m2"].sum())
        })

    # Store the list of dictionaries in a DataFrame
    summary = pd.DataFrame(summary_rows)

    # Save the DataFrame to CSV
    summary.to_csv(SUMMARY_OUTPUT_PATH, index=False)
    return


if __name__ == "__main__":
    app.run()
