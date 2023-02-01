import eel
from dataclasses import dataclass
import shutil
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
    self._data = {}

  def __enter__(self):
    self._touch()
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
  def __init__(self, artist: str, title: str, path: str, fetcher_id: str = ''):
    self.title = title
    self.artist = artist
    self.fetcher_id = fetcher_id
    self.path = path

    if not self.is_lost:
      self.format_properties()

  def __eq__(self, other_track: 'Track') -> bool:
    return (
      self.title == other_track.title
      and self.artist == other_track.artist
    )

  def __hash__(self) -> int:
      return hash((self.artist, self.title))

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
    return os.path.join(self.path, self.file_name)

  def format_properties(self):
    self.format_artist()
    self.format_title()

  def format_artist(self):
    self.artist = self.artist.lower().title()

  def format_title(self):
    self.title = self.title.lower().capitalize()

  def download_progress_hook(self, info):
    return eel.updateFetcherTrackProgress(
      self.fetcher_id, info.get('_percent_str', "100%")
    )

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
  def fetch_from_cache(cls, path: str, key: str, cache: Cache) -> 'Track':
    if item := cache.get(key):
      return cls(artist=item['artist'], title=item['title'], path=path)

  @classmethod
  def fetch_from_file(cls, path: str, fname: str) -> 'Track':
    eyed3_file = eyed3.load(os.path.join(path, fname))
    if (
      eyed3_file
      and eyed3_file.tag
      and eyed3_file.tag.artist
      and eyed3_file.tag.title
    ):
      return cls(
        artist=eyed3_file.tag.artist,
        title=eyed3_file.tag.title,
        path=path,
      )
    else:
      return cls(artist=UNKNOWN, title=UNKNOWN, path=path)

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
    self.name = name
    self.path = path
    self.tracks = []

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
        print(fname)
        if not (track := Track.fetch_from_cache(self.path, fname, cache=cache)):
          track = Track.fetch_from_file(path=self.path, fname=fname)
          track.cache(fname, cache=cache)
        self.tracks.append(track)
    if verbose:
      mprint(f'Successfully loaded data from {self.name}!', 'good')

  def get_artists(self):
    self.load_all_data()
    # Disclude UNKNOWNs for special list?
    return sorted({track.artist for track in self.tracks})

  def get_tracks_by_artist(self, artist):
    self.load_all_data()
    return sorted(track.title for track in self.tracks if track.artist == artist)

  def compare_data(other_device: 'Device') -> set[Track]:
    return set(self.tracks) - set(other_device.tracks)

  def save_data(self, tracks: list[Track]) -> None:
    for track in tracks:
      from_path = track.full_path
      to_path = os.path.join(self.path, track.file_name)
      print(from_path, '>>>', to_path)
      shutil.copyfile(from_path, to_path)


def _fetch_tracks(data):
  with Caches.Tracks as cache:
    for item in data:
      if item['artist'].strip() and item['title'].strip():
        track = Track(
          title=item['title'],
          artist=item['artist'],
          fetcher_id=item['fetcher_id'],
          path=DATA_DIR,
        )
        track.fetch()
        track.tag(cache=cache)
  eel.loadArtists('local')
  mprint('Finished fetching tracks!', 'normal')

@eel.expose
def fetch_tracks(data):
  threading.Thread(target=_fetch_tracks, args=(data,)).start()


class DeviceManager:

  def __init__(self):
    self._devices = {}
    self._current_usbs = set()
    self.selected_disk = None

  def activate(self):
    self.load_local()
    self.poll_usbs()

  @property
  def usb_mount_path(self):
    if MAC_PLATFORM_PART in PLATFORM:
      return MAC_VOLUMES_DIR
    raise Exception(UNSUPPORTED_OS_MSG)

  @property
  def device_names(self) -> list:
    return list(self._devices.keys())

  def load_local(self) -> None:
    self.add(local_device := Device(name='local', path=DATA_DIR))

  def add(self, device: Device) -> None:
    self._devices[device.name] = device
    eel.updateDevices(self.device_names)

  def remove(self, device: Device) -> None:
    self._devices.pop(device.name)
    eel.updateDevices(self.device_names)

  def get(self, name: str) -> Device:
    return self._devices[name]

  def find_usbs(self) -> set[str]:
    available_usbs = set(os.listdir(self.usb_mount_path))
    return available_usbs - IGNORE_USBS

  def _poll_usbs(self):
    while True:
      usbs = self.find_usbs()

      # TODO: consider multiple devices arrving/leaving in the same
      # poll iteration
      removed = list(self._current_usbs - usbs)
      added = list(usbs - self._current_usbs)
      if removed:
        mprint(f'External disk removed {removed[0]}', 'bad')
        self.remove(self._devices[removed[0]])
      elif added:
        mprint(f'External disk detected {added[0]}!', 'good')
        self.add(
          Device(
            name=added[0],
            path=os.path.join(self.usb_mount_path, added[0]),
          )
        )
      self._current_usbs = usbs
      eel.sleep(1)

  def poll_usbs(self):
    threading.Thread(target=self._poll_usbs).start()

  def sync_all(self):
    if (device_count := len(self._devices)) < 2:
      return

    all_tracks = []
    for device in self._devices.values():
      all_tracks += device.tracks
    all_tracks = set(all_tracks)

    for device in self._devices.values():
      if missing_tracks := all_tracks - set(device.tracks):
        mprint(f'Adding {len(missing_tracks)} track(s) to {device.name}')
        device.save_data(missing_tracks)
        eel.loadArtists(device.name)
    mprint(f'Finished syncing {device_count} devices!', mood='good')


class MainContext:

  def __init__(self):
    eel.expose(self.get_device_names)
    eel.expose(self.load_artists)
    eel.expose(self.load_tracks)
    eel.expose(self.sync_all)
    self.device_manager = DeviceManager()

  def __call__(self):
    eel.init('frontend')
    self.device_manager.activate()
    eel.start('main.html')

  def get_device_names(self):
    return self.device_manager.device_names

  def load_artists(self, source):
    return self.device_manager.get(source).get_artists()

  def load_tracks(self, source, artist):
    return self.device_manager.get(source).get_tracks_by_artist(artist)

  def sync_all(self):
    self.device_manager.sync_all()


def main():
  main_context = MainContext()
  return main_context()

if __name__ == "__main__":
  main()
