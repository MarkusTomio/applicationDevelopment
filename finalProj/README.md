# RDAS - Rainfall Deficit in Agricultural Areas of Sicily

The RDAS project provides a reproducible workflow for calculating and interactively exploring yearly seasonal anomalies for agricultural land-cover areas in Sicily (and with minimal adaption for any other NUTS region).

The project is made of two main components: a processing notebook (also executable as script, refer to corresponding section below for more information) and an interactive exploration notebook. The processing notebook does most of the heavy lifting, by combining CHIRPS precipitation data with Overture Map agricultural land-cover polygons. The explorer notebook is responsible for the visualization of the calculated anomalies for the year 2021-2025 relative to the 1991-2020 March-September baseline.

## Requirements

The project is intended to run inside Docker. Therefore, Docker is required.

All dependencies are managed inside the container.

All data is provided under app/data, even processed data since it is rather small.

## Usage

To start Marimo, run this from the repository root:

```bash
docker compose up --build
```

Then open:

```bash
http://localhost:8080
```

To run the processing workflow directly from the command line, run this from the repository root:

```bash
docker compose run --rm marimo-notebook pixi run python rdas_processing.py
```