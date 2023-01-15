import eel
from dataclasses import dataclass
import subprocess
import youtube_dl
import platform
import eyed3
import threading
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
PLATFORM = platform.platform()
IGNORE_DISKS = {'Macintosh HD'}
MAC_VOLUMES_DIR = '/Volumes'
LINUX_MOUNT_DIR = '/mnt'
MAC_PLATFORM_PART = 'macOS'
LINUX_PLATFORM_PART = 'Linux'

UNSUPPORTED_OS_MSG = 'OS not supported'



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

  def __init__(self, name, path):
    eel.expose('get_artists_' + name)(self.get_artists)
    eel.expose('get_tracks_by_artist_' + name)(self.get_tracks_by_artist)
    print(name)
    self.name = name
    self.path = path

  def load_all_data(self, verbose=False):
    if verbose:
      mprint(f'Loading all data from {self.name}...', 'normal')
    try:
      self.tracks = []
      filenames = [
        item for item in os.listdir(self.path)
        if item.endswith('.' + AUDIO_FORMAT)
      ]
      for fname in filenames:
        eyed3_file = eyed3.load(os.path.join(self.path, fname))
        if eyed3_file and (not eyed3_file.tag.artist) and eyed3_file.tag.album:
          eyed3_file.tag.artist = eyed3_file.tag.album
          eyed3_file.tag.title = fname.split(',')[0]

        if eyed3_file and eyed3_file.tag.artist and eyed3_file.tag.title:
          self.tracks.append(
            Track(artist=eyed3_file.tag.artist, title=eyed3_file.tag.title)
          )
        else:
          self.report_mystery_file(fname)
      if verbose:
        mprint(f'Successfully loaded data from {self.name}!', 'good')
    except Exception as error:
      mprint(str(error), 'bad')

  def report_mystery_file(self, name):
    ...

  def get_artists(self):
    # Consider improving performance
    self.load_all_data()
    return sorted({track.artist for track in self.tracks})

  def get_tracks_by_artist(self, artist):
    # Consider improving performance
    return sorted(track.title for track in self.tracks if track.artist == artist)


def _fetch_tracks(data):
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

@eel.expose
def fetch_tracks(data):
  threading.Thread(target=_fetch_tracks, args=(data,)).start()


class DeviceManager:

  def __init__(self):
    self.available_disks = []
    self.selected_disk = None
    self.data_manager = DataManager('device', path='')

  @property
  def device_location_path(self):
    if MAC_PLATFORM_PART in PLATFORM:
      return MAC_VOLUMES_DIR
    raise Exception(UNSUPPORTED_OS_MSG)

  def find_disks(self):
    available_disks = set(os.listdir(self.device_location_path))
    return available_disks - IGNORE_DISKS

  def _poll_disks(self):
    while True:
      new_disks = self.find_disks()
      if self.selected_disk and self.selected_disk not in new_disks:
        self.selected_disk = None
        mprint('External disk removed', 'bad')
      if detected_diff := (new_disks - self.available_disks):
        mprint('External disk detected!', 'good')
        self.selected_disk = list(detected_diff)[0]
        self.read_disk()
        eel.updateDisk(self.selected_disk)
      self.available_disks = new_disks
      eel.sleep(1)

  def poll_disks(self):
    self.available_disks = self.find_disks()
    threading.Thread(target=self._poll_disks).start()

  def read_disk(self):
    if not self.selected_disk:
      raise Exception('Unexpected disk read')
    self.data_manager.path=os.path.join(
      self.device_location_path, self.selected_disk,
    )


def main():

  data_manager = DataManager(name='local', path=DATA_DIR)
  device_manager = DeviceManager()
  device_manager.poll_disks()

  eel.init('frontend')

  data_manager.load_all_data(verbose=True)

  eel.start('main.html')




if __name__ == "__main__":
  main()
