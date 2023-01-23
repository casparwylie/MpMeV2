const artistListContainer = document.getElementById('artist-list');
const trackListContainer = document.getElementById('track-list');

function loadArtists(source) {
  artistListContainer.replaceChildren();
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
  for (var element of document.getElementById('artist-list').children) {
    element.classList.remove('artist-selected');
  }
  evt.target.classList.add('artist-selected');
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

eel.expose(updateDisk)
function updateDisk(name) {
  loadArists('local');
}

loadArtists('local');
