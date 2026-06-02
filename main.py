import subprocess
import os
import argparse
import logging
import shutil

from datetime import datetime, UTC
from time import sleep
from pathlib import Path

# Configure logging to output to stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


VIDEO_EXTENTIONS = {".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv"}
SLEEP_TIME_SECONDS = 5 # in seconds

def encode_video(input_path: str, output_dir: str) -> None:
    """
    Encodes a video file using FFmpeg with NVIDIA NVENC hardware acceleration.

    Args:
        input_path (str): Path to the input video file.
        output_dir (str): Directory where the encoded file will be saved.
    """
    # Get the filename without extension and add timestamp
    input_name = os.path.splitext(os.path.basename(input_path))[0]
    now = datetime.now(tz=UTC)
    timestamp = int(now.timestamp())
    output_filename = f"{input_name}_{timestamp}.mkv"
    output_path = os.path.join(output_dir, output_filename)

    logger.info(f"Encoding {input_path} to {output_path}...")

    # FFmpeg command using NVIDIA NVENC
    ffmpeg_command = [
        "ffmpeg",
        "-hwaccel", "cuda",
        "-hwaccel_output_format", "cuda",
        "-i", input_path,
        "-c:v", "hevc_nvenc",
        "-preset", "p6",
        "-profile:v", "main10",
        "-rc", "constqp",
        "-cq", "22",
        "-b:v", "0",
        "-map", "0:v",
        "-map", "0:a",
        "-map", "0:s?",
        "-c:a", "aac",
        "-b:a", "192k",
        "-c:s", "copy",
        output_path
    ]

    # Execute the command
    try:
        result = subprocess.run(
            ffmpeg_command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        logger.info(f"Encoding completed successfully: {output_path}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Encoding failed with exit code {e.returncode}")
        logger.error(f"Error output: {e.stderr}")
        raise  # Re-raise to handle the error in the caller

def is_video_file(filepath: Path) -> bool:
    """Check if the file is a video file based on its extension."""
    return filepath.suffix.lower() in VIDEO_EXTENTIONS

def monitor_and_transcode(input_dir: Path, transcoding_dir: Path, transcoded_dir: Path) -> None:
    """
    Monitors the input directory for video files, moves them to transcoding_dir,
    transcodes them one by one, and moves the result to transcoded_dir.

    Args:
        input_dir (Path): Directory to monitor for new video files.
        transcoding_dir (Path): Directory where files are moved before transcoding.
        transcoded_dir (Path): Directory where transcoded files are saved.
    """
    # Create directories if they don't exist
    os.makedirs(str(transcoding_dir), exist_ok=True)
    os.makedirs(str(transcoded_dir), exist_ok=True)

    logger.info(f"Monitoring directory: {input_dir}")

    some_files_previously_detected = True

    while True:
        # Check for files in the input directory
        files = (f for f in input_dir.iterdir() if f.is_file())

        first_file = next(input_dir.iterdir(), None)
        some_files_detected = first_file is not None

        if not some_files_detected and some_files_previously_detected:
            logger.info("No content found, waiting...")

        some_files_previously_detected = some_files_detected
        # Process each file in the input directory
        for file_path in files:

            filename = file_path.name

            if not is_video_file(file_path):
                logger.warning(f"Skipping non-video file: {filename}")
                continue

            # Move the file to the transcoding directory
            transcoding_path = transcoding_dir.joinpath(filename)
            shutil.move(file_path, transcoding_path)
            logger.info(f"Moved {filename} to {transcoding_dir} for transcoding.")

            # Transcode the file
            try:
                encode_video(
                    input_path=transcoding_path, 
                    output_dir=transcoded_dir,
                )
                # Remove the original file after successful transcoding
                transcoding_path.unlink(missing_ok=True)
                logger.info(f"Removed original file: {transcoding_path}")
            except Exception as e:
                logger.error(f"Failed to transcode {filename}: {e}")
                # Move the file back to input_dir if transcoding fails
                shutil.move(transcoding_path, file_path)
                logger.error(f"Moved {filename} back to {input_dir}.")

        # Wait a bit before checking again
        sleep(SLEEP_TIME_SECONDS)

if __name__ == "__main__":
    # Configure argument parser
    parser = argparse.ArgumentParser(
        description="Monitor a directory for video files, transcode them using FFmpeg with NVIDIA NVENC, and save the result in a transcoded directory."
    )
    parser.add_argument(
        "-i", "--input-dir",
        type=str,
        required=True,
        help="Directory to monitor for new video files."
    )
    parser.add_argument(
        "-t", "--transcoding-dir",
        type=str,
        default="transcoding",
        help="Directory where files are moved before transcoding. Default: 'transcoding'."
    )
    parser.add_argument(
        "-o", "--transcoded-dir",
        type=str,
        default="transcoded",
        help="Directory where transcoded files are saved. Default: 'transcoded'."
    )

    # Parse arguments
    args = parser.parse_args()

    # Call the monitoring function
    monitor_and_transcode(
        input_dir=Path(args.input_dir), 
        transcoding_dir=Path(args.transcoding_dir), 
        transcoded_dir=Path(args.transcoded_dir),
    )