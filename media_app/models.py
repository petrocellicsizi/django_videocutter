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
    qr_code = models.FileField(upload_to='qrcodes/', null=True, blank=True)
    type = models.CharField(max_length=20, choices=PROJECT_TYPES, default='life_story')
    drive_file_id = models.CharField(max_length=100, null=True, blank=True)
    drive_web_view_link = models.URLField(max_length=500, null=True, blank=True)

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

    # Add this to your MediaItem model in models.py
    def delete(self, *args, **kwargs):
        # Store file path for later deletion attempt
        file_path = self.file.path if self.file else None

        # First remove the file field reference from the model
        # This keeps the database clean even if file deletion fails
        if self.file:
            self.file = None
            self.save(update_fields=['file'])

        # Delete the model instance
        super().delete(*args, **kwargs)

        # Now try to delete the actual file
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except (PermissionError, OSError) as e:
                # Log the error but don't raise an exception
                print(f"Warning: Could not delete file {file_path}: {e}")
                # Optionally, you could add this file to a cleanup queue for later deletion

    def clean(self):
        if self.file:
            ext = self.file.name.split('.')[-1].lower()
            image_types = ['jpg', 'jpeg', 'png']
            video_types = ['mp4']

            if self.media_type == 'image' and ext not in image_types:
                from django.core.exceptions import ValidationError
                raise ValidationError(
                    f"Selected file type '{ext}' is not allowed for images. Please use jpg, jpeg, or png.")
            elif self.media_type == 'video' and ext not in video_types:
                from django.core.exceptions import ValidationError
                raise ValidationError(f"Selected file type '{ext}' is not allowed for videos. Please use mp4.")
            elif ext not in image_types and ext not in video_types:
                from django.core.exceptions import ValidationError
                raise ValidationError("Only image(jpg,jpeg,png) and video files(mp4) are allowed.")

            # Add video duration check
            if self.media_type == 'video' and ext in video_types:
                try:
                    # Import here to avoid circular imports
                    from moviepy.editor import VideoFileClip
                    import tempfile
                    import os

                    # Create a temporary file to check the duration
                    with tempfile.NamedTemporaryFile(delete=False) as temp:
                        for chunk in self.file.chunks():
                            temp.write(chunk)

                    try:
                        with VideoFileClip(temp.name) as video:
                            if video.duration > 120:
                                from django.core.exceptions import ValidationError
                                raise ValidationError(
                                    "Videos must be 120 seconds (2 minutes) or shorter. Please trim your video before uploading.")
                    except Exception as e:
                        from django.core.exceptions import ValidationError
                        raise ValidationError(f"Error validating video: {str(e)}")
                    finally:
                        # Clean up temp file
                        if os.path.exists(temp.name):
                            os.remove(temp.name)

                except ImportError:
                    # If moviepy is not available, skip this validation
                    pass
