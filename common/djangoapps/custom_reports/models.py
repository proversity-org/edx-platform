from django.db import models


class ReportsStatus(models.Model):
    class Meta(object):
        db_table = "reports_status"

    jobid = models.CharField(max_length=255, primary_key=True, db_index=True)

    STATUS_CHOICES = (
        (1, 'Running'),
        (2, 'Finished'),
    )

    status = models.CharField(max_length=15, choices=STATUS_CHOICES)
    created_on = models.DateTimeField(auto_now_add=True)
    result = models.TextField(null=True)
