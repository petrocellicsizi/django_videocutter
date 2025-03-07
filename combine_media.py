from moviepy import VideoFileClip, ImageClip, concatenate_videoclips
import os
from sys import argv


def create_combined_video(input_files, output_file="output_video.mp4", fps=24, duration_per_image=3):
    """
    Combine multiple photos and videos into a single video file.

    Parameters:
    - input_files: List of paths to input media files (photos or videos)
    - output_file: Name of the output video file
    - fps: Frames per second for the output video
    - duration_per_image: Duration in seconds for each photo
    """
    try:
        # List to store all video clips
        clips = []

        # Process each input file
        for file_path in input_files:
            if not os.path.exists(file_path):
                print(f"Warning: File not found - {file_path}")
                continue

            # Check if file is an image or video based on extension
            image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
            video_extensions = ['.mp4', '.avi', '.mov', '.mkv']

            ext = os.path.splitext(file_path.lower())[1]

            if ext in image_extensions:
                # Create a video clip from image with specified duration
                clip = ImageClip(file_path, duration=duration_per_image)
                clips.append(clip)
            elif ext in video_extensions:
                # Load video clip
                clip = VideoFileClip(file_path)
                clips.append(clip)
            else:
                print(f"Warning: Unsupported file format - {file_path}")
                continue

        if not clips:
            print("Error: No valid media files to process")
            return

        # Concatenate all clips
        final_clip = concatenate_videoclips(clips, method="compose")

        # Write the result to a file
        final_clip.write_videofile(
            output_file,
            fps=fps,
            codec="libx264",
            audio_codec="aac"
        )

        print(f"Video successfully created: {output_file}")

        # Close all clips to free memory
        for clip in clips:
            clip.close()
        final_clip.close()

    except Exception as e:
        print(f"Error occurred: {str(e)}")


def main():
    # Check if files were provided as command line arguments
    if len(argv) < 2:
        print("Usage: python script.py file1 file2 file3 ...")
        print("Supported formats: Images (.jpg, .jpeg, .png, .bmp) and Videos (.mp4, .avi, .mov, .mkv)")
        return

    # Get input files from command line arguments (excluding script name)
    input_files = argv[1:]

    # Create the combined video
    create_combined_video(
        input_files,
        output_file="combined_output.mp4",
        fps=24,  # Frames per second
        duration_per_image=3  # Duration for each photo in seconds
    )


if __name__ == "__main__":
    main()
    