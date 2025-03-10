# Add to forms.py
from django import forms
from .models import MediaProject, MediaItem


class MediaProjectForm(forms.ModelForm):
    class Meta:
        model = MediaProject
        fields = ['title', 'description', 'type']


class MediaItemForm(forms.ModelForm):
    file = forms.FileField(
        help_text="Only image files (JPG, PNG, JPEG) and video files (MP4) are allowed."
    )

    class Meta:
        model = MediaItem
        fields = ['file', 'media_type']

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Get the file extension
            ext = file.name.split('.')[-1].lower()

            # Define allowed extensions
            image_types = ['jpg', 'jpeg', 'png']
            video_types = ['mp4']

            # Check if the file is an image or video
            if ext in image_types:
                self.instance.media_type = 'image'
            elif ext in video_types:
                self.instance.media_type = 'video'
            else:
                raise forms.ValidationError("Only image and video files are allowed.")

        return file
