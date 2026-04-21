from django.conf import settings
from django.db import models


class DetectionRecord(models.Model):
    FILE_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
    ]

    RESULT_CHOICES = [
        ('real', 'Real'),
        ('fake', 'Fake'),
        ('uncertain', 'Uncertain'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='detections',
    )
    title = models.CharField(max_length=120)
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES)
    uploaded_file = models.FileField(upload_to='uploads/%Y/%m/%d/')
    result = models.CharField(max_length=10, choices=RESULT_CHOICES)
    confidence = models.FloatField()
    summary = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} ({self.file_type})'
