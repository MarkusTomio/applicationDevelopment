let initialZoomLevel = 10;
let initialCenter = [1588911.734653, 6026906.806230];

let mapObjectInput = {
        layers: [
          new ol.layer.Tile({
            source: new ol.source.OSM()
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
    console.log(e);
});