import eel
from dataclasses import dataclass
import subprocess
import enum
import youtube_dl
import json
import platform
import eyed3
import threading
import os

DATA_DIR = 'data'
CACHE_FILENAME = '.__cache__.json'
UNKNOWN = '_UNKNOWN_'
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
IGNORE_USBS = {'Macintosh HD'}
MAC_VOLUMES_DIR = '/Volumes'
LINUX_MOUNT_DIR = '/mnt'
MAC_PLATFORM_PART = 'macOS'
LINUX_PLATFORM_PART = 'Linux'

UNSUPPORTED_OS_MSG = 'OS not supported'



def mprint(message, mood='normal'):
  eel.jsprint(message, mood)
  print('\n' + message)


class Cache:
  def __init__(self, cache_filename):
    self.cache_filename = cache_filename
    self._touch()
    self._data = {}

  def __enter__(self):
    with open(self.cache_filename, 'r') as cfile:
     self._data = json.load(cfile)
    return self

  def __exit__(self, *args):
    with open(self.cache_filename, 'w') as cfile:
      json.dump(self._data, cfile)

  def _touch(self):
    if not os.path.exists(self.cache_filename):
      with open(self.cache_filename, 'w') as cfile:
        json.dump({}, cfile)

  def get(self, key):
    return self._data.get(key)

  def set(self, key, value):
    self._data[key] = value


class Caches:
  Tracks = Cache(CACHE_FILENAME)


class Track:
  def __init__(self, artist: str, title: str, fetcher_id: str = ''):
    self.title = title
    self.artist = artist
    self.fetcher_id = fetcher_id

    if not self.is_lost:
      self.format_properties()

  def format_properties(self):
    self.format_artist()
    self.format_title()

  def format_artist(self):
    self.artist = self.artist.lower().title()

  def format_title(self):
    self.title = self.title.lower().capitalize()

  @property
  def is_lost(self):
    return self.artist == self.title == UNKNOWN

  @property
  def search_term(self):
    return f'{self.artist} {self.title}'

  @property
  def full_name(self):
    return f'{self.artist} - {self.title}'

  @property
  def file_name(self):
    return f'{self.full_name}.{AUDIO_FORMAT}'

  @property
  def full_path(self):
    return os.path.join(DATA_DIR, self.file_name)

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

  def tag(self, cache):
    eyed3_file = eyed3.load(self.full_path)
    eyed3_file.tag.artist = self.artist
    eyed3_file.tag.title = self.title
    eyed3_file.tag.save()
    self.cache(self.file_name, cache=cache)

  @classmethod
  def fetch_from_cache(cls, key, cache):
    item = cache.get(key)
    if item:
      return cls(artist=item['artist'], title=item['title'])

  @classmethod
  def fetch_from_file(cls, path):
    eyed3_file = eyed3.load(path)
    if (
      eyed3_file
      and eyed3_file.tag
      #and eyed3_file.tag.artist
      #and eyed3_file.tag.title
      and eyed3_file.tag.album
    ):

      # artist = artist, title = title
      return cls(
        artist=eyed3_file.tag.album,
        title=path.split('/')[-1].split(',')[0],
      )
    else:
      return cls(artist=UNKNOWN, title=UNKNOWN)

  def as_dict(self):
    return {
      'artist': self.artist,
      'title': self.title,
    }

  def cache(self, key, cache):
    if not cache.get(key):
      cache.set(key, self.as_dict())


class Device:

  def __init__(self, name, path):
    # Check func not already registered
    try:
      eel.expose('get_artists_' + name)(self.get_artists)
      eel.expose('get_tracks_by_artist_' + name)(self.get_tracks_by_artist)
    except:
      pass
    self.name = name
    self.path = path

  def _get_audio_filenames(self):
    return [
      item for item in os.listdir(self.path)
      if item.endswith('.' + AUDIO_FORMAT)
    ]

  def load_all_data(self, verbose=False):
    if verbose:
      mprint(f'Loading all data from {self.name}...', 'normal')
    filenames = self._get_audio_filenames()
    self.tracks = []
    with Caches.Tracks as cache:
      for fname in filenames:
        if not (track := Track.fetch_from_cache(fname, cache=cache)):
          track = Track.fetch_from_file(os.path.join(self.path, fname))
          track.cache(fname, cache=cache)
        self.tracks.append(track)
    if verbose:
      mprint(f'Successfully loaded data from {self.name}!', 'good')

  def get_artists(self):
    self.load_all_data()
    print(self.name, 'LOADING')
    # Disclude UNKNOWNs for special list?
    return sorted({track.artist for track in self.tracks})

  def get_tracks_by_artist(self, artist):
    self.load_all_data()
    return sorted(track.title for track in self.tracks if track.artist == artist)


def _fetch_tracks(data):
  with Cache.Tracks as cache:
    for item in data:
      if item['artist'].strip() and item['title'].strip():
        track = Track(
          title=item['title'],
          artist=item['artist'],
          fetcher_id=item['fetcher_id'],
        )
        track.fetch()
        track.tag(cache=cache)
  mprint('Finished fetching tracks!', 'normal')

@eel.expose
def fetch_tracks(data):
  threading.Thread(target=_fetch_tracks, args=(data,)).start()


class DeviceManager:

  def __init__(self):
    self.devices = []
    self.current_usbs = set()
    self.selected_disk = None

  @property
  def usb_mount_path(self):
    if MAC_PLATFORM_PART in PLATFORM:
      return MAC_VOLUMES_DIR
    raise Exception(UNSUPPORTED_OS_MSG)

  @property
  def device_names(self):
    return [device.name for device in self.devices]

  def add(self, device: Device):
    self.devices.append(device)
    eel.updateDevices(self.device_names)

  def remove(self, device):
    self.devices.remove(device)
    eel.updateDevices(self.device_names)

  def find_usbs(self):
    available_usbs = set(os.listdir(self.usb_mount_path))
    return available_usbs - IGNORE_USBS

  def _get_device_by_name(self, name):
    try:
      return [
        device for device in self.devices if device.name == name
      ][0]
    except IndexError:
      ...

  def _poll_usbs(self):
    while True:
      usbs = self.find_usbs()
      removed = list(self.current_usbs - usbs)
      added = list(usbs - self.current_usbs)
      if removed:
        mprint(f'External disk removed {removed[0]}', 'bad')
        self.remove(self._get_device_by_name(removed[0]))
      elif added:
        mprint(f'External disk detected {added[0]}!', 'good')
        self.add(
          Device(
            name=added[0],
            path=os.path.join(self.usb_mount_path, added[0]),
          )
        )
      self.current_usbs = usbs
      eel.sleep(1)

  def poll_usbs(self):
    threading.Thread(target=self._poll_usbs).start()



def main():

  device_manager = DeviceManager()
  local_device = Device(name='local', path=DATA_DIR)

  eel.init('frontend')

  device_manager.add(local_device)
  eel.selectDevice(local_device.name);
  device_manager.poll_usbs()



  eel.start('main.html')




if __name__ == "__main__":
  main()
