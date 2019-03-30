import time

from django.conf import settings
from huey.contrib.djhuey import db_periodic_task, lock_task

from Harvest.huey_scheduler import IntervalSeconds
from Harvest.utils import get_logger
from monitoring.decorators import update_component_status
from monitoring.models import ComponentStatus
from plugins.bibliotik.client import BibliotikClient
from plugins.bibliotik.exceptions import BibliotikTorrentNotFoundException
from plugins.bibliotik.html_parser import parse_search_results
from plugins.bibliotik_archiver.models import BibliotikArchiverState
from plugins.bibliotik_archiver.utils import get_bibliotik_torrent_for_archiving
from torrents.add_torrent import fetch_torrent, add_torrent_from_tracker
from torrents.models import Realm, DownloadLocation
from trackers.registry import TrackerRegistry

logger = get_logger(__name__)


@db_periodic_task(IntervalSeconds(settings.BIBLIOTIK_ARCHIVER_METADATA_INTERVAL))
@lock_task('bibliotik_archive_run')
@update_component_status(
    'bibliotik_archiver_metadata',
    error_message='Bibliotik archiver metadata crashed.',
)
def bibliotik_archive_run():
    start = time.time()

    state = BibliotikArchiverState.objects.get()
    if not state.is_metadata_enabled:
        return

    client = BibliotikClient()
    tracker = TrackerRegistry.get_plugin('bibliotik', 'bibliotik_archive_run')
    realm = Realm.objects.get(name=tracker.name)
    search_results = parse_search_results(client.search(''))
    max_tracker_id = search_results[0]['tracker_id']

    logger.info('Bibliotik max tracker id: {}.', max_tracker_id)

    num_scraped = 0
    # last_meta_tracker_id was the last one processed, so resume from the next.
    for tracker_id in range(state.last_meta_tracker_id + 1, max_tracker_id):
        try:
            fetch_torrent(realm, tracker, tracker_id)
            logger.info('Bibliotik torrent {} fetched.', tracker_id)
        except BibliotikTorrentNotFoundException:
            logger.info('Bibliotik torrent {} not found.', tracker_id)
        state.last_meta_tracker_id = tracker_id
        state.save(update_fields=('last_meta_tracker_id',))
        num_scraped += 1
        time.sleep(settings.BIBLIOTIK_ARCHIVER_METADATA_SLEEP)
        if time.time() - start >= 55:
            break

    time_taken = time.time() - start
    ComponentStatus.update_status(
        'bibliotik_archiver_metadata',
        ComponentStatus.STATUS_GREEN,
        'Completed Bibliotik archiver metadata run with {} torrents in {:.3f} s. Progress: {} / {}.'.format(
            num_scraped, time_taken, state.last_meta_tracker_id, max_tracker_id),
    )


@db_periodic_task(IntervalSeconds(settings.BIBLIOTIK_ARCHIVER_DOWNLOAD_INTERVAL))
@lock_task('bibliotik_archive_download_torrent')
@update_component_status(
    'bibliotik_archiver_download',
    error_message='Bibliotik archiver erdownload torrent crashed.',
)
def bibliotik_archive_download_torrent():
    start = time.time()

    state = BibliotikArchiverState.objects.get()
    if not state.is_download_enabled:
        return

    bibliotik_torrent, num_remaining = get_bibliotik_torrent_for_archiving()

    if not bibliotik_torrent:
        logger.info('Bibliotik torrent download - nothing to download.')
        return

    tracker = TrackerRegistry.get_plugin('bibliotik', 'bibliotik_archive_download_torrent')
    realm = Realm.objects.get(name=tracker.name)
    download_location = realm.get_preferred_download_location()

    if not download_location:
        logger.error('No download location for realm {}.', tracker.name)
        return

    tracker_id = bibliotik_torrent.torrent_info.tracker_id
    torrent_info = fetch_torrent(realm, tracker, tracker_id)
    if torrent_info.is_deleted:
        logger.info('Bibliotik torrent {} already deleted.', tracker_id)
        return

    logger.info('Downloading Bibliotik torrent {}.', tracker_id)
    add_torrent_from_tracker(
        tracker=tracker,
        tracker_id=tracker_id,
        download_path_pattern=download_location.pattern,
        force_fetch=False,
    )

    time_taken = time.time() - start
    ComponentStatus.update_status(
        'bibliotik_archiver_download',
        ComponentStatus.STATUS_GREEN,
        'Completed Bibliotik archiver download torrent run in {:.3f} s. Remaining: {}.'.format(
            time_taken, num_remaining - 1),
    )
