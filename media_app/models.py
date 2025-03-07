# media_app/models.py
from django.db import models
from django.contrib.auth.models import User
import os
import uuid


def get_file_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('uploads/', filename)


class MediaProject(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )

    PROJECT_TYPES = (
        ('life_story', 'Life Story'),
        ('event_coverage', 'Event Coverage'),
        ('memory_collection', 'Memory Collection'),
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    output_file = models.FileField(upload_to='outputs/', null=True, blank=True)
    type = models.CharField(max_length=20, choices=PROJECT_TYPES, default='life_story')

    def __str__(self):
        return self.title


class MediaItem(models.Model):
    MEDIA_TYPES = (
        ('image', 'Image'),
        ('video', 'Video'),
    )
    
    project = models.ForeignKey(MediaProject, related_name='media_items', on_delete=models.CASCADE)
    file = models.FileField(upload_to=get_file_path)
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPES)
    order = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.media_type} for {self.project.title}"

    def delete(self, *args, **kwargs):
        # Delete associated file
        if self.file and os.path.isfile(self.file.path):
            os.remove(self.file.path)
        super().delete(*args, **kwargs)