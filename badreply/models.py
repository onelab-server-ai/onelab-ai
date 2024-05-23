from django.db import models

from oneLabProject.models import Period


# Create your models here.
class BadReply(Period):
    comment = models.TextField(null=False, blank=False)
    target = models.IntegerField()


    class Meta:
        db_table = 'tbl_bad_reply'
        ordering = ['-created_date']