import qrcode
from sys import argv
import os


def create_video_qr(video_path, output_file="video_qr.png"):
    """
    Create a QR code from a video file path.

    Parameters:
    - video_path: Path to the video file
    - output_file: Name of the output QR code image file
    """
    try:
        # Check if video file exists
        if not os.path.exists(video_path):
            print(f"Error: Video file not found - {video_path}")
            return

        # Check if it's a video file based on extension
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv']
        ext = os.path.splitext(video_path.lower())[1]

        if ext not in video_extensions:
            print(f"Warning: File might not be a video - {video_path}")

        # Create QR code instance
        qr = qrcode.QRCode(
            version=1,  # Controls the size of the QR Code (1-40)
            error_correction=qrcode.constants.ERROR_CORRECT_L,  # About 7% error correction
            box_size=10,  # Size of each box in pixels
            border=4,  # Border thickness in boxes
        )

        # Add the video path to the QR code
        qr.add_data(video_path)
        qr.make(fit=True)

        # Create an image from the QR Code instance
        qr_image = qr.make_image(fill_color="black", back_color="white")

        # Save the QR code image
        qr_image.save(output_file)

        print(f"QR code successfully created: {output_file}")
        print(f"QR code contains: {video_path}")

    except Exception as e:
        print(f"Error occurred: {str(e)}")


def main():
    # Check if video path was provided as command line argument
    if len(argv) != 2:
        print("Usage: python script.py /path/to/video.mp4")
        print("Supported formats: .mp4, .avi, .mov, .mkv")
        return

    # Get video path from command line argument
    video_path = argv[1]

    # Create output filename based on video filename
    video_filename = os.path.splitext(os.path.basename(video_path))[0]
    output_file = f"{video_filename}_qr.png"

    # Create the QR code
    create_video_qr(video_path, output_file)


if __name__ == "__main__":
    main()