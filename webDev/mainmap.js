let initialZoomLevel = 10;
let initialCenter = [1588911.734653, 6026906.806230];
// Define source of features for vector layer suited for editing
let pointFeatures = new ol.source.Vector();
// Define measuring state
let measuring = false;
// Define measuring points
let measureP1 = null;
let measureP2 = null;

var distance;

let mapObjectInput = {
        layers: [
          new ol.layer.Tile({
            source: new ol.source.OSM()
          }),
          // Vector data for client side rendering
          // Takes our pointFeatures as source
          new ol.layer.Vector({
            source: pointFeatures,
            // Change default style for better visibility
            style: new ol.style.Style({
                image: new ol.style.Circle({
                    radius: 6,
                    fill: new ol.style.Fill({
                        color: 'red'
                    }),
                    stroke: new ol.style.Stroke({
                    color: 'black',
                    width: 2
                    })
                })
            })
          })
        ],
        target: 'map',
        view: new ol.View({
          center: initialCenter,
          zoom: initialZoomLevel
        })
      };

var map = new ol.Map(mapObjectInput);

document.getElementById('zoom-out').onclick = function() {
    var view = map.getView();
    var zoom = view.getZoom();
    view.animate({zoom: zoom - 1});    
    //view.setZoom(zoom - 1);
};

document.getElementById('zoom-in').onclick = function() {
    var view = map.getView();
    var zoom = view.getZoom();
    view.animate({zoom: zoom + 1}); 
    //view.setZoom(zoom + 1);
};

document.getElementById('reset').onclick = function() {
    var view = map.getView();
    view.animate({zoom: initialZoomLevel}, {center: initialCenter});
};

document.getElementById('left').onclick = function() {
    var view = map.getView();
    var currentCenter = view.getCenter();
    view.animate({center: [currentCenter[0] - 100000, currentCenter[1]]});
};

document.getElementById('right').onclick = function() {
    var view = map.getView();
    var currentCenter = view.getCenter();
    view.animate({center: [currentCenter[0] + 100000, currentCenter[1]]});
};

document.getElementById('up').onclick = function() {
    var view = map.getView();
    var currentCenter = view.getCenter();
    view.animate({center: [currentCenter[0], currentCenter[1] + 100000]});
};

document.getElementById('down').onclick = function() {
    var view = map.getView();
    var currentCenter = view.getCenter();
    view.animate({center: [currentCenter[0], currentCenter[1] - 100000]});
};

map.on('click', function(e) {
    // If measuring is not active do nothing
    if (!measuring) {
        return;
    }

    // Define new point feature with last click coordinate
    var measurePoints = new ol.Feature({
        geometry: new ol.geom.Point(e.coordinate)
    });
    
    // Add the feature to the point features source,
    // which is then rendered client side (see MapObjectInput)
    pointFeatures.addFeature(measurePoints);

    // If first point is still null, assign it clicked coordinate
    // If it's not null, we know first one is recorded and assign clicked coordinate to second one
    if(measureP1 == null) {
        measureP1 = e.coordinate;
        return;
    } else {
        measureP2 = e.coordinate;

        // Transform points to geographic coordinates, i.e. lonlat
        var measureP1geo = ol.proj.transform (
            measureP1,
            'EPSG:3857',
            'EPSG:4326'
        );

        var measureP2geo = ol.proj.transform (
            measureP2,
            'EPSG:3857',
            'EPSG:4326'
        );

        // Define sphere on which to measure the distance
        // From ol.Sphere docs: radius equal to semi-major axis of WGS84 ellipsoid
        var sphere = new ol.Sphere(6378137);

        // Calculate haversine distance between points
        distance = sphere.haversineDistance(measureP1geo, measureP2geo);

        // Set status to normal
        measuring = false;
        // Set points to null for subsequent measurement
        measureP1 = null;
        measureP2 = null;

        // Display measurement results on page
        document.getElementById('measureStatus').innerHTML = 
        "Geographical distance between first and second point is measured at: " + 
        Math.floor(distance/1000) + "km " + 
        (distance%1000).toFixed(2) + "m (" +
        distance.toFixed(2) + "m).";
        return;
    }
});

document.getElementById('measure').onclick = function() {
    // Initiate measurement status
    measuring = true;
    // Empty features source, i.e. from previous measurement
    pointFeatures.clear();
    // Display measurement status and instructions on page
    document.getElementById('measureStatus').innerHTML = "Measurement mode: click two points on the map.";
}