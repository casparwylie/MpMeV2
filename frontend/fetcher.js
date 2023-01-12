
const fetcherContainer = document.getElementById('fetcher-container');
const fetcherRowContainer = document.getElementById('fetcher-track-rows');
const fetchSubmit = document.getElementById('fetcher-submit');
const fetcherShowOption = document.getElementById('fetch-option')

function getFetcherData(lock) {
  const rows = document.getElementsByClassName('fetcher-row');
  data = [];
  for (row of rows) {
    artist = row.children[0].value;
    title = row.children[1].value;
    data.push([artist, title, row.getAttribute('ref')]);
  }
  return data;
}

function addFetcherRow() {
  const id = fetcherRowContainer.children.length + 1;
  const container = document.createElement('div');
  const artistName = document.createElement('input');
  const title = document.createElement('input');

  artistName.placeholder = 'Artist...';
  artistName.className = 'i-1 fetcher-input';
  title.className = 'i-1 fetcher-input';
  title.placeholder = 'Title...';
  title.addEventListener('keypress', (evt) => {
    if (evt.key == 'Enter') { evt.preventDefault(); addFetcherRow(); }
  });

  container.className = 'fetcher-row';
  container.setAttribute('ref', id.toString())
  container.appendChild(artistName);
  container.appendChild(title);
  fetcherRowContainer.appendChild(container);
}

eel.expose(updateFetcherTrackStatus);
function updateFetcherTrackStatus(fetcher_id, mood) {
  const pbar = document.getElementById('fetcher-track-pbar-' + fetcher_id);
  pbar.className = 'progress-bar ' + mood;
}

eel.expose(updateFetcherTrackProgress);
function updateFetcherTrackProgress(fetcher_id, percent) {
  const pbar = document.getElementById('fetcher-track-pbar-' + fetcher_id);
  pbar.style = 'width: ' + percent;
}


function replaceFetcherRowWithProgress(row, data) {
  row.replaceChildren();
  const progressContainer = document.createElement('div');
  const progressBar = document.createElement('div');

  progressContainer.className = 'progress-container';
  progressContainer.innerHTML = data.artist + ' - ' + data.title;
  progressContainer.appendChild(progressBar);

  progressBar.id = 'fetcher-track-pbar-' + data.fetcher_id.toString();
  progressBar.className = 'progress-bar';

  row.appendChild(progressContainer);
}

function submitFetcher() {
  const rows = document.getElementsByClassName('fetcher-row');
  var data = [];
  var rowsToDelete = [];
  for (var row of rows) {
    const artist = row.children[0].value;
    const title = row.children[1].value;
    if (!artist || !title) {
      rowsToDelete.push(row);
    } else {
      data.push({
        artist: artist,
        title: title,
        fetcher_id: row.getAttribute('ref'),
      });
      replaceFetcherRowWithProgress(row, data[data.length - 1]);
    }
  }
  if (data.length) {
    for (var row of rowsToDelete) {
      row.remove();
    }
    fetchSubmit.style = 'display: none';
    eel.fetch_tracks(data)((_) => {browser.loadArtists();});
  }
}

function showFetcher() {
  fetchSubmit.style = 'display: block';
  fetcherRowContainer.replaceChildren();
  addFetcherRow();
  fetcherContainer.style = 'display: block';
}


fetchSubmit.addEventListener('click', submitFetcher);
fetcherShowOption.addEventListener('click', showFetcher);
