import os
import time
from pathlib import Path
from PIL import Image
from moviepy.editor import VideoFileClip, ImageClip, concatenate_videoclips, AudioFileClip
from django.conf import settings
import qrcode
from .google_drive_utils import upload_file_to_drive


def process_media_project(project):
    """Process media items into a single video file and upload to Google Drive"""
    clips = []  # Initialize clips list outside try block for proper cleanup

    try:
        # Ensure project ID is valid
        if project.id is None:
            raise ValueError("Project ID is None. Ensure the project is saved before processing.")

        project.status = 'processing'
        project.save()

        # Create necessary folders using pathlib for better path handling
        media_root = Path(settings.MEDIA_ROOT)
        resized_folder = media_root / 'resized_images'
        output_folder = media_root / 'outputs'
        qr_folder = media_root / 'qrcodes'

        # Create folders if they don't exist
        resized_folder.mkdir(parents=True, exist_ok=True)
        output_folder.mkdir(parents=True, exist_ok=True)
        qr_folder.mkdir(parents=True, exist_ok=True)

        media_items = project.media_items.all().order_by('order')

        if not media_items.exists():
            print(f"No media items found for project {project.id}")
            project.status = 'failed'
            project.save()
            return False

        # Define target size for consistency (HD by default)
        target_size = (1280, 720)

        # Find first video to determine target size (if any)
        first_video = next((item for item in media_items if item.media_type == 'video'), None)
        if first_video:
            try:
                video_path = media_root / first_video.file.name
                # Check if file exists before trying to open it
                if not video_path.exists():
                    print(f"Warning: Video file not found at {video_path}. Using default dimensions.")
                else:
                    with VideoFileClip(str(video_path)) as video:
                        target_size = video.size
            except Exception as e:
                print(f"Error determining size from first video: {str(e)}. Using default dimensions.")

        for item in media_items:
            # Ensure file name exists and file exists on disk
            if not item.file or not item.file.name:
                print(f"Warning: File is missing for media item {item.id}, skipping")
                continue

            # Use pathlib for better path handling
            file_path = media_root / item.file.name

            # Convert to string representation for libraries that don't support Path objects
            file_path_str = str(file_path)

            print(f"Processing file: {file_path_str}")

            # Check if file exists before processing
            if not file_path.exists():
                print(f"Error: File not found at {file_path_str}. Skipping this item.")
                continue

            try:
                if item.media_type == 'video':
                    # Load the video and take only the first 20 seconds
                    video = VideoFileClip(file_path_str)
                    # If video is shorter than 20 seconds, use the entire video
                    if video.duration > 20:
                        video_clip = video.subclip(0, 20)
                    else:
                        video_clip = video

                    clips.append(video_clip)
                else:  # Image processing
                    # Resize image to match target size
                    img = Image.open(file_path_str)
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

                    # Save resized image with unique filename
                    resized_filename = f"resized_{project.id}_{int(time.time())}_{file_path.name}"
                    resized_path = resized_folder / resized_filename
                    new_img.save(str(resized_path))

                    # Create image clip from resized image
                    img_clip = ImageClip(str(resized_path)).set_duration(2).set_fps(24)
                    clips.append(img_clip)
            except Exception as e:
                print(f"Error processing item {item.id}: {str(e)}. Skipping this item.")
                continue

        if clips:
            final_clip = concatenate_videoclips(clips, method="compose")

            # Calculate the total duration of the video (photos + videos)
            total_video_duration = sum([min(20, vid.duration) for vid in clips])

            # Select audio file based on project type
            audio_path = None
            if project.type == 'life_story':
                audio_path = Path(settings.BASE_DIR) / "media/needed_media/life.mp3"
            elif project.type == 'event_coverage':
                audio_path = Path(settings.BASE_DIR) / "media/needed_media/event.mp3"
            elif project.type == 'memory_collection':
                audio_path = Path(settings.BASE_DIR) / "media/needed_media/memory.mp3"
            else:
                # Default to life story audio if type is not recognized
                audio_path = Path(settings.BASE_DIR) / "media/needed_media/life.mp3"

            if audio_path.exists():
                audio = AudioFileClip(str(audio_path))

                # Trim the audio to match the total video duration
                audio = audio.subclip(0, total_video_duration)

                # Set the audio of the video to the loaded and trimmed audio
                final_clip = final_clip.set_audio(audio)
            else:
                print(f"Warning: Audio file '{audio_path}' not found. Proceeding without audio.")

            # Create a unique filename for the output
            output_filename = f"project_{project.id}_{int(time.time())}.mp4"
            # Full path for saving the file
            output_path = output_folder / output_filename
            output_path_str = str(output_path)

            # Save the video file locally first
            final_clip.write_videofile(output_path_str, codec='libx264', fps=24)

            # Upload to Google Drive
            drive_web_view_link = upload_file_to_drive(output_path_str, output_filename)

            if drive_web_view_link:
                # Store the Google Drive information in the project
                project.drive_web_view_link = drive_web_view_link

                # STILL store the relative path from MEDIA_ROOT for compatibility
                # This ensures Django's FileField knows how to create the URL
                relative_path = f'outputs/{output_filename}'
                project.output_file = relative_path

                # Generate QR code for the GOOGLE DRIVE video
                qr_filename = f"qr_project_{project.id}_{int(time.time())}.png"
                qr_path = qr_folder / qr_filename
                relative_qr_path = f'qrcodes/{qr_filename}'

                # Create QR code with the Google Drive URL to the video
                generate_qr_code_for_drive(project, relative_qr_path, str(qr_path), drive_web_view_link)

                project.status = 'completed'
                project.save()

                print(f"Project {project.id} completed. Output file on Drive: {drive_web_view_link}")
            else:
                print("Failed to upload to Google Drive, falling back to local storage")
                # Store local file path as fallback
                relative_path = f'outputs/{output_filename}'
                project.output_file = relative_path

                # Generate QR code for the local video
                qr_filename = f"qr_project_{project.id}_{int(time.time())}.png"
                qr_path = qr_folder / qr_filename
                relative_qr_path = f'qrcodes/{qr_filename}'

                # Create QR code with local URL placeholder
                generate_qr_code(project, relative_qr_path, str(qr_path))

                project.status = 'completed'
                project.save()

                print(f"Project {project.id} completed. Local output file: {relative_path}")

            return True
        else:
            project.status = 'failed'
            project.save()
            print(f"No valid clips were generated for project {project.id}")
            return False

    except Exception as e:
        print(f"Error processing project: {str(e)}")
        project.status = 'failed'
        project.save()
        return False
    finally:
        # Make sure to close all clips to free resources
        for clip in clips:
            try:
                clip.close()
            except Exception as e:
                print(f"Error closing clip: {str(e)}")


def generate_qr_code(project, relative_qr_path, qr_path):
    """Generate a QR code for the given output video file (local version)"""
    try:
        # We'll store the relative path first and update the actual URL in the view
        project.qr_code = relative_qr_path
        project.save()

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


def generate_qr_code_for_drive(project, relative_qr_path, qr_path, drive_web_view_link):
    """Generate a QR code for the Google Drive link"""
    try:
        # We'll store the relative path
        project.qr_code = relative_qr_path
        project.save()

        # Create QR code object
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )

        # Use the Google Drive web view link directly
        qr.add_data(drive_web_view_link)
        qr.make(fit=True)

        # Create and save the QR code image
        img = qr.make_image(fill="black", back_color="white")
        img.save(qr_path)

        return True
    except Exception as e:
        print(f"Error generating QR code for Drive link: {str(e)}")
        return False
