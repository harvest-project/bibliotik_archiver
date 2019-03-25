import logging
import time

from huey.contrib.djhuey import db_periodic_task, lock_task

from Harvest.huey_scheduler import Crontab
from plugins.bibliotik.client import BibliotikClient
from plugins.bibliotik.exceptions import BibliotikTorrentNotFoundException
from plugins.bibliotik.html_parser import parse_search_results
from plugins.bibliotik_archiver.models import BibliotikArchiverState
from torrents.add_torrent import fetch_torrent
from torrents.models import Realm
from trackers.registry import TrackerRegistry

logger = logging.getLogger(__name__)


@db_periodic_task(Crontab())
@lock_task('bibliotik_archive_run')
def bibliotik_archive_run():
    start = time.time()

    try:
        client = BibliotikClient()
    except BibliotikClient:
        logger.warning('Unable to obtain Bibliotik client.')
        return

    tracker = TrackerRegistry.get_plugin('bibliotik', 'bibliotik_archive_run')
    realm = Realm.objects.get(name=tracker.name)
    state = BibliotikArchiverState.objects.get()
    search_results = parse_search_results(client.search(''))
    max_tracker_id = search_results[0]['tracker_id']

    logger.info('Bibliotik max tracker id: {}.'.format(max_tracker_id))

    for tracker_id in range(state.last_meta_tracker_id, max_tracker_id):
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
