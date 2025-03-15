import os
import time
from pathlib import Path
from PIL import Image
from moviepy.editor import VideoFileClip, ImageClip, concatenate_videoclips, AudioFileClip
from django.conf import settings
import qrcode


def process_media_project(project):
    """Process media items into a single video file"""
    try:
        # Ensure project ID is valid
        if project.id is None:
            raise ValueError("Project ID is None. Ensure the project is saved before processing.")

        project.status = 'processing'
        project.save()

        # Create a folder for resized images
        resized_folder = os.path.join(settings.MEDIA_ROOT, 'resized_images')
        Path(resized_folder).mkdir(parents=True, exist_ok=True)

        # Create output folder if it doesn't exist
        output_folder = os.path.join(settings.MEDIA_ROOT, 'outputs')
        Path(output_folder).mkdir(parents=True, exist_ok=True)

        # Create QR codes folder if it doesn't exist
        qr_folder = os.path.join(settings.MEDIA_ROOT, 'qrcodes')
        Path(qr_folder).mkdir(parents=True, exist_ok=True)

        media_items = project.media_items.all().order_by('order')
        clips = []

        # Define target size for consistency (HD by default)
        target_size = (1280, 720)

        # Find first video to determine target size (if any)
        first_video = next((item for item in media_items if item.media_type == 'video'), None)
        if first_video:
            video_path = os.path.join(settings.MEDIA_ROOT, first_video.file.name)
            with VideoFileClip(video_path) as video:
                target_size = video.size

        for item in media_items:
            # Ensure file name exists
            if item.file.name is None:
                raise ValueError(f"File name is None for media item {item.id}.")

            file_path = os.path.join(settings.MEDIA_ROOT, item.file.name)
            print(f"Processing file: {file_path}")

            if item.media_type == 'video':
                # Load the video and take only the first 20 seconds
                video = VideoFileClip(file_path)
                # If video is shorter than 20 seconds, use the entire video
                if video.duration > 20:
                    video_clip = video.subclip(0, 20)
                else:
                    video_clip = video

                clips.append(video_clip)
            else:  # Image processing
                # Resize image to match target size
                img = Image.open(file_path)
                width, height = img.size
                target_width, target_height = target_size
                img_aspect = width / height
                target_aspect = target_width / target_height

                if img_aspect > target_aspect:  # Image is wider than target
                    new_width = target_width
                    new_height = int(target_width / img_aspect)
                else:  # Image is taller than target
                    new_height = target_height
                    new_width = int(target_height * img_aspect)

                # Resize image to fit within target dimensions
                img_resized = img.resize((new_width, new_height), Image.LANCZOS)

                # Create new image with padding
                new_img = Image.new('RGB', target_size, (0, 0, 0))

                # Paste resized image centered in the padded image
                paste_x = (target_width - new_width) // 2
                paste_y = (target_height - new_height) // 2
                new_img.paste(img_resized, (paste_x, paste_y))

                # Save resized image
                resized_filename = f"resized_{project.id}_{os.path.basename(file_path)}"
                resized_path = os.path.join(resized_folder, resized_filename)
                img_resized.save(resized_path)

                # Create image clip from resized image
                img_clip = ImageClip(resized_path).set_duration(2).set_fps(24)
                clips.append(img_clip)

        if clips:
            final_clip = concatenate_videoclips(clips, method="compose")

            # Calculate the total duration of the video (photos + videos)
            total_video_duration = sum([min(20, vid.duration) for vid in clips])

            # Select audio file based on project type
            audio_path = None
            if project.type == 'life_story':
                audio_path = "media/needed_media/life.mp3"
            elif project.type == 'event_coverage':
                audio_path = "media/needed_media/event.mp3"
            elif project.type == 'memory_collection':
                audio_path = "media/needed_media/memory.mp3"
            else:
                # Default to life story audio if type is not recognized
                audio_path = "media/needed_media/life.mp3"

            if os.path.exists(audio_path):
                audio = AudioFileClip(audio_path)

                # Trim the audio to match the total video duration
                audio = audio.subclip(0, total_video_duration)

                # Set the audio of the video to the loaded and trimmed audio
                final_clip = final_clip.set_audio(audio)
            else:
                print(f"Warning: Audio file '{audio_path}' not found. Proceeding without audio.")

            # Create a unique filename for the output
            output_filename = f"project_{project.id}_{int(time.time())}.mp4"
            # Full path for saving the file
            output_path = os.path.join(output_folder, output_filename)

            # Save the video file
            final_clip.write_videofile(output_path, codec='libx264', fps=24)

            # IMPORTANT: Store just the relative path from MEDIA_ROOT
            # This ensures Django's FileField knows how to create the URL
            relative_path = os.path.join('outputs', output_filename)
            project.output_file = relative_path

            # Generate QR code for the video
            qr_filename = f"qr_project_{project.id}_{int(time.time())}.png"
            qr_path = os.path.join(qr_folder, qr_filename)
            relative_qr_path = os.path.join('qrcodes', qr_filename)

            # Create QR code with the URL to the video
            # We're using request.build_absolute_uri in the view, not here
            # This is just a placeholder that will be replaced in the model
            generate_qr_code(project, relative_qr_path, qr_path)

            project.status = 'completed'
            project.save()

            print(f"Project {project.id} completed. Output file: {relative_path}")

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


def generate_qr_code(project, relative_qr_path, qr_path):
    """Generate a QR code for the given output video file"""
    try:
        # We'll store the relative path first and update the actual URL in the view
        project.qr_code = relative_qr_path

        # Create QR code object
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )

        # At this point, we don't have the full URL, so we'll use a placeholder
        # The actual URL will be constructed in the view
        qr.add_data("PLACEHOLDER_URL")
        qr.make(fit=True)

        # Create and save the QR code image
        img = qr.make_image(fill="black", back_color="white")
        img.save(qr_path)

        return True
    except Exception as e:
        print(f"Error generating QR code: {str(e)}")
        return False
