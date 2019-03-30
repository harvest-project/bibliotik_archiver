from django.db import models


class BibliotikArchiverState(models.Model):
    is_metadata_enabled = models.BooleanField()
    is_download_enabled = models.BooleanField(default=False)
    last_meta_tracker_id = models.BigIntegerField()
