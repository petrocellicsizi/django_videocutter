import os
import time
import numpy as np
from pathlib import Path
from PIL import Image
from moviepy import VideoFileClip, ImageClip, concatenate_videoclips
from django.conf import settings


def process_media_project(project):
    """Process media items into a single video file"""
    try:
        # Update project status
        project.status = 'processing'
        project.save()

        media_items = project.media_items.all().order_by('order')
        clips = []

        for item in media_items:
            file_path = os.path.join(settings.MEDIA_ROOT, item.file.name)

            if item.media_type == 'video':
                # Process video
                video_clip = VideoFileClip(file_path)
                clips.append(video_clip)
            else:
                # Process image (convert to video clip)
                img = Image.open(file_path)
                img_clip = ImageClip(np.array(img))
                clips.append(img_clip)

        # Concatenate all clips
        if clips:
            final_clip = concatenate_videoclips(clips)

            # Define output filename
            output_filename = f"project_{project.id}_{int(time.time())}.mp4"
            output_path = os.path.join(settings.MEDIA_ROOT, 'outputs', output_filename)

            # Ensure output directory exists
            Path(os.path.join(settings.MEDIA_ROOT, 'outputs')).mkdir(parents=True, exist_ok=True)

            # Export final video
            final_clip.write_videofile(output_path, codec='libx264')

            # Update project with output file
            relative_path = os.path.join('outputs', output_filename)
            project.output_file = relative_path
            project.status = 'completed'
            project.save()

            # Close clips to release resources
            for clip in clips:
                clip.close()
            final_clip.close()

            return True
        else:
            project.status = 'failed'
            project.save()
            return False

    except Exception as e:
        print(f"Error processing project: {str(e)}")
        project.status = 'failed'
        project.save()
        return False
