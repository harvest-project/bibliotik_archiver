from Harvest.settings import base

BIBLIOTIK_ARCHIVER_METADATA_SLEEP = base.env.float('DJANGO_BIBLIOTIK_ARCHIVER_METADATA_SLEEP', 1)
BIBLIOTIK_ARCHIVER_METADATA_INTERVAL = base.env.int('DJANGO_BIBLIOTIK_ARCHIVER_METADATA_INTERVAL', 60)
BIBLIOTIK_ARCHIVER_DOWNLOAD_INTERVAL = base.env.int('DJANGO_BIBLIOTIK_ARCHIVER_DOWNLOAD_INTERVAL', 60)
