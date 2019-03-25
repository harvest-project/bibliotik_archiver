from django.db import models


class BibliotikArchiverState(models.Model):
    is_enabled = models.BooleanField()
    last_meta_tracker_id = models.BigIntegerField()
