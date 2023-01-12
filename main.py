import eel
from dataclasses import dataclass
import subprocess
import youtube_dl
import eyed3
import os

DATA_DIR = 'data'
RETRY_ATTEMPTS = 3
AUDIO_FORMAT = 'mp3'
YDL_BASE_OPTS = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    # May fix 403s according to https://stackoverflow.com/questions/32104702/youtube-dl-library-and-error-403-forbidden-when-using-generated-direct-link-by
    # 'cachedir': False,
}



def mprint(message, mood='normal'):
  eel.jsprint(message, mood)
  print('\n' + message)



class Track:

  def __init__(self, artist: str, title: str, fetcher_id: str = ''):
    self.title = title.lower().capitalize()
    self.artist = artist.lower().title()
    self.fetcher_id = fetcher_id

  @property
  def search_term(self):
    return f'{self.artist} {self.title}'

  @property
  def full_name(self):
    return f'{self.artist} - {self.title}'

  @property
  def file_name(self):
    return self.full_name

  @property
  def full_path(self):
    return os.path.join(DATA_DIR, f'{self.file_name}.{AUDIO_FORMAT}')

  def download_progress_hook(self, info):
    return eel.updateFetcherTrackProgress(self.fetcher_id, info.get('_percent_str', "100%"))

  def fetch(self):
    mprint(f'Fetching {self.full_name}...')
    eel.updateFetcherTrackStatus(self.fetcher_id, 'normal')
    for attempt in range(RETRY_ATTEMPTS):
      try:
        ydl_opts = YDL_BASE_OPTS | {
          'outtmpl': self.full_path.split('.')[0] + '.%(ext)s',
          'progress_hooks': [self.download_progress_hook],
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
          ydl.download([f'ytsearch:{self.search_term}'])
        mprint(f'Successfully fetched {self.full_name}', 'good')
        eel.updateFetcherTrackStatus(self.fetcher_id, 'good')
        break
      except Exception as error:
        mprint(f'Issue: {error}', 'bad')
        mprint(f'Retrying {attempt + 1}/{RETRY_ATTEMPTS}', 'bad')
    else:
      mprint('Unable to fetch song. Skipping...', 'bad')
      eel.updateFetcherTrackStatus(self.fetcher_id, 'bad')
      return
    return True

  def tag(self):
    eyed3_file = eyed3.load(self.full_path)
    eyed3_file.tag.artist = self.artist
    eyed3_file.tag.title = self.title
    eyed3_file.tag.save()


class DataManager:

  def __init__(self, name):
    eel.expose('get_artists_' + name)(self.get_artists)
    eel.expose('get_tracks_by_artist_' + name)(self.get_tracks_by_artist)
    eel.expose('load_all_data_' + name)(self.load_all_data)
    self.name = name

  def load_all_data(self, verbose=False):
    if verbose:
      mprint(f'Loading all data from {self.name}...', 'normal')
    try:
      self.tracks = []
      filenames = [
        item for item in os.listdir(DATA_DIR)
        if item.endswith('.' + AUDIO_FORMAT)
      ]
      for fname in filenames:
        eyed3_file = eyed3.load(os.path.join(DATA_DIR, fname))
        self.tracks.append(
          Track(artist=eyed3_file.tag.artist, title=eyed3_file.tag.title)
        )
      if verbose:
        mprint(f'Successfully loaded data from {self.name}!', 'good')
    except Exception as error:
      mprint(error, 'bad')

  def get_artists(self):
    return sorted({track.artist for track in self.tracks})

  def get_tracks_by_artist(self, artist):
    return sorted(track.title for track in self.tracks if track.artist == artist)



@eel.expose
def fetch_tracks(data):
  for item in data:
    if item['artist'].strip() and item['title'].strip():
      track = Track(
        title=item['title'],
        artist=item['artist'],
        fetcher_id=item['fetcher_id'],
      )
      track.fetch()
      track.tag()
  mprint('Finished fetching tracks!', 'normal')
  data_manager.load_all_data()


data_manager = DataManager('local')

def main():

  eel.init('frontend')

  data_manager.load_all_data(verbose=True)

  eel.start('main.html')




if __name__ == "__main__":
  main()
