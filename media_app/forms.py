# media_app/forms.py
from django import forms
from .models import MediaProject, MediaItem

class MediaProjectForm(forms.ModelForm):
    class Meta:
        model = MediaProject
        fields = ['title', 'description']

class MediaItemForm(forms.ModelForm):
    class Meta:
        model = MediaItem
        fields = ['file', 'media_type']

    file = forms.FileField(required=True)