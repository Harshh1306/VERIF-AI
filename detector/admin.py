from django.contrib import admin

from .models import DetectionRecord


@admin.register(DetectionRecord)
class DetectionRecordAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'file_type', 'result', 'confidence', 'created_at')
    list_filter = ('file_type', 'result', 'created_at')
    search_fields = ('title', 'user__username')

# Register your models here.
