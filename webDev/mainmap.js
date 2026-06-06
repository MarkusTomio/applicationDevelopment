let initialZoomLevel = 10;
let initialCenter = [1588911.734653, 6026906.806230];
// Define source of features for vector layer suited for editing
let pointFeatures = new ol.source.Vector();
// Define measuring state
let measuring = false;
// Define measuring points
let measuringPoint1 = null;
let measuringPoint2 = null;

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
    view.setZoom(zoom - 1);
};

document.getElementById('zoom-in').onclick = function() {
    var view = map.getView();
    var zoom = view.getZoom();
    view.setZoom(zoom + 1);
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
    if(measuringPoint1 == null) {
        measuringPoint1 = e.coordinate;
    } else {
        measuringPoint2 = e.coordinate;
        measuring = false;
    }
});

document.getElementById('measure').onclick = function() {
    measuring = true;
    alert("Measurement mode: click two points on the map.");
}