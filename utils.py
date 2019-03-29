from plugins.bibliotik.models import BibliotikTorrent


def get_bibliotik_torrent_for_archiving():
    return BibliotikTorrent.objects.filter(
        category=BibliotikTorrent.CATEGORY_EBOOKS,
        torrent_info__torrent=None,
        is_deleted=False,
    ).order_by('id').first()
