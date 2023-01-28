const artistListContainer = document.getElementById('artist-list');
const trackListContainer = document.getElementById('track-list');
const deviceListContainer = document.getElementById('device-list');

function loadArtists(source) {
  artistListContainer.replaceChildren();
  trackListContainer.replaceChildren();
  eel['get_artists_' + source]()((results) => {
    for (var artistName of results) {
      const artistRow = document.createElement('div');
      artistRow.innerHTML = artistName;
      artistRow.className = 'artist-row';
      artistRow.addEventListener('click', (evt) => {selectArtist(evt, source)});
      artistListContainer.appendChild(artistRow);
    }
  });
}

function selectArtist(evt, source) {
  select(evt.target, 'artist-selected', 'artist-list');
  loadTracks(evt.target.innerHTML, source);
}

function loadTracks(artist, source) {
  trackListContainer.replaceChildren();
  eel['get_tracks_by_artist_' + source](artist)((results) => {
    for (var trackName of results) {
      const trackRow = document.createElement('div');
      trackRow.innerHTML = trackName;
      trackRow.className = 'artist-row';
      trackListContainer.appendChild(trackRow);
    }
  });
}

eel.expose(updateDevices);
function updateDevices(names) {
  var selected;
  for (var element of document.getElementById('device-list').children) {
    if (element.classList.contains('device-selected')) {
      selected = element.innerHTML;
      break;
    }
  }
  deviceListContainer.replaceChildren();
  for (var name of names) {
    const device = document.createElement("div");
    device.className = "device-opt b-1";
    device.innerHTML = name;
    device.addEventListener('click', (evt) => {selectDevice(evt.target)});
    deviceListContainer.appendChild(device);
    if( name == selected ) {
      select(device, 'device-selected', 'device-list');
    }
  }
}


function select(target, selectClass, listId) {
  for (var element of document.getElementById(listId).children) {
    element.classList.remove(selectClass);
  }
  target.classList.add(selectClass);
}

eel.expose(selectDevice);
function selectDevice(target) {
  select(target, 'device-selected', 'device-list');
  loadArtists(target.innerHTML);
}


eel.get_inital_devices()((results) => {
  updateDevices(results);
  const device = document.getElementById('device-list').children[0];
  selectDevice(device);
});
