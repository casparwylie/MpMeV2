class Browser {


  constructor() {
     this.artistListContainer = document.getElementById('artist-list');
     this.trackListContainer = document.getElementById('track-list');
  }

  loadArtists() {
    this.artistListContainer.replaceChildren();
    eel.get_artists_local()((results) => {
      for (var artistName of results) {
        const artistRow = document.createElement('div');
        artistRow.innerHTML = artistName;
        artistRow.className = 'artist-row';
        artistRow.addEventListener('click', (evt) => {this.selectArtist(evt, this)});
        this.artistListContainer.appendChild(artistRow);
      }
    });
  }

  selectArtist(evt, callback) {
    for (var element of document.getElementById('artist-list').children) {
      element.classList.remove('artist-selected');
    }
    evt.target.classList.add('artist-selected');
    callback.loadTracks(evt.target.innerHTML);
  }

  loadTracks(artist) {
    this.trackListContainer.replaceChildren();
    eel.get_tracks_by_artist_local(artist)((results) => {
      for (var trackName of results) {
        const trackRow = document.createElement('div');
        trackRow.innerHTML = trackName;
        trackRow.className = 'artist-row';
        this.trackListContainer.appendChild(trackRow);
      }
    });
  }
}

const browser = new Browser();
browser.loadArtists();
