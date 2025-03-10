import os
import time
import numpy as np
from pathlib import Path
from PIL import Image
from moviepy.editor import VideoFileClip, ImageClip, concatenate_videoclips
from django.conf import settings


def process_media_project(project):
    """Process media items into a single video file"""
    try:
        # Ensure project ID is valid
        if project.id is None:
            raise ValueError("Project ID is None. Ensure the project is saved before processing.")

        project.status = 'processing'
        project.save()

        media_items = project.media_items.all().order_by('order')
        clips = []

        first_video_clip = None

        for item in media_items:
            # Ensure file name exists
            if item.file.name is None:
                raise ValueError(f"File name is None for media item {item.id}.")

            file_path = os.path.join(settings.MEDIA_ROOT, item.file.name)
            print(f"Processing file: {file_path}")

            if item.media_type == 'video':
                video_clip = VideoFileClip(file_path)
                if first_video_clip is None:
                    first_video_clip = video_clip  # Get first video resolution
                clips.append(video_clip)
            else:
                img = Image.open(file_path)

                # Resize image to match first video resolution
                if first_video_clip:
                    img = img.resize(first_video_clip.size)

                img_clip = ImageClip(np.array(img)).set_duration(3).set_fps(25)  # Add FPS and duration
                clips.append(img_clip)

        if clips:
            final_clip = concatenate_videoclips(clips)

            output_filename = f"project_{project.id}_{int(time.time())}.mp4"
            output_path = os.path.join(settings.MEDIA_ROOT, 'outputs', output_filename)
            Path(os.path.join(settings.MEDIA_ROOT, 'outputs')).mkdir(parents=True, exist_ok=True)

            final_clip.write_videofile(output_path, codec='libx264', fps=25)

            project.output_file = os.path.join('outputs', output_filename)
            project.status = 'completed'
            project.save()

            # Close clips properly
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
