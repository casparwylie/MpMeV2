const syncAllDevicesOption = document.getElementById('sync-all-option');
const artistListContainer = document.getElementById('artist-list');
const trackListContainer = document.getElementById('track-list');
const deviceListContainer = document.getElementById('device-list');
const loadingIcon = document.getElementById('loading');


syncAllDevicesOption.addEventListener('click', (evt) => {
  show_element(loadingIcon);
  eel.sync_all()(() => {
    hide_element(loadingIcon);
  })
})

eel.expose(loadArtists)
function loadArtists(source) {
  artistListContainer.replaceChildren();
  trackListContainer.replaceChildren();
  show_element(loadingIcon);
  eel.load_artists(source)((results) => {
    hide_element(loadingIcon);
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
  eel.load_tracks(source, artist)((results) => {
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
  for (var element of deviceListContainer.children) {
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
  if (names.length > 1) {
    show_element(syncAllDevicesOption);
  } else {
    hide_element(syncAllDevicesOption);
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


eel.get_device_names()((results) => {
  updateDevices(results);
  const device = deviceListContainer.children[0];
  selectDevice(device);
});
