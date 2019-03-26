import logging
import time

from huey.contrib.djhuey import db_periodic_task, lock_task

from Harvest.huey_scheduler import Crontab
from plugins.bibliotik.client import BibliotikClient
from plugins.bibliotik.exceptions import BibliotikTorrentNotFoundException
from plugins.bibliotik.html_parser import parse_search_results
from plugins.bibliotik.models import BibliotikTorrent
from plugins.bibliotik_archiver.models import BibliotikArchiverState
from torrents.add_torrent import fetch_torrent, add_torrent_from_tracker
from torrents.models import Realm, DownloadLocation
from trackers.registry import TrackerRegistry

logger = logging.getLogger(__name__)


@db_periodic_task(Crontab())
@lock_task('bibliotik_archive_run')
def bibliotik_archive_run():
    start = time.time()

    state = BibliotikArchiverState.objects.get()
    if not state.is_enabled:
        return

    try:
        client = BibliotikClient()
    except BibliotikClient:
        logger.warning('Unable to obtain Bibliotik client.')
        return

    tracker = TrackerRegistry.get_plugin('bibliotik', 'bibliotik_archive_run')
    realm = Realm.objects.get(name=tracker.name)
    search_results = parse_search_results(client.search(''))
    max_tracker_id = search_results[0]['tracker_id']

    logger.info('Bibliotik max tracker id: {}.'.format(max_tracker_id))

    # last_meta_tracker_id was the last one processed, so resume from the next.
    for tracker_id in range(state.last_meta_tracker_id + 1, max_tracker_id):
        try:
            fetch_torrent(realm, tracker, tracker_id)
            logger.info('Bibliotik torrent {} fetched.'.format(tracker_id))
        except BibliotikTorrentNotFoundException:
            logger.info('Bibliotik torrent {} not found.'.format(tracker_id))
        state.last_meta_tracker_id = tracker_id
        state.save(update_fields=('last_meta_tracker_id',))
        time.sleep(1)
        if time.time() - start >= 55:
            break


@db_periodic_task(Crontab())
@lock_task('bibliotik_archive_download_torrent')
def bibliotik_archive_download_torrent():
    state = BibliotikArchiverState.objects.get()
    if not state.is_download_enabled:
        return

    bibliotik_torrent = BibliotikTorrent.objects.filter(
        category=BibliotikTorrent.CATEGORY_EBOOKS,
        torrent_info__torrent=None,
        is_deleted=False,
    ).order_by('id').first()

    if not bibliotik_torrent:
        logger.info('Bibliotik torrent download - nothing to download.')
        return

    tracker = TrackerRegistry.get_plugin('bibliotik', 'bibliotik_archive_download_torrent')
    realm = Realm.objects.get(name=tracker.name)
    download_location = DownloadLocation.objects.filter(realm=realm).order_by('?').first()

    if not download_location:
        logger.error('No download location for realm {}.'.format(tracker.name))
        return

    tracker_id = bibliotik_torrent.torrent_info.tracker_id
    torrent_info = fetch_torrent(realm, tracker, tracker_id)
    if torrent_info.is_deleted:
        logger.info('Bibliotik torrent {} already deleted.'.format(tracker_id))
        return

    logger.info('Downloading Bibliotik torrent {}.'.format(tracker_id))
    add_torrent_from_tracker(tracker, tracker_id, download_location.pattern, force_fetch=False)
