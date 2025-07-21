import os
from ffmpeg import FFmpeg

LOCAL_KEYFRAMES_DIRECTORY = "keyframes"
LOCAL_VIDEOS_DIRECTORY = "videos"


def main():
    if not os.path.exists(LOCAL_KEYFRAMES_DIRECTORY):
        os.makedirs(LOCAL_KEYFRAMES_DIRECTORY)

    for file in os.listdir(LOCAL_VIDEOS_DIRECTORY):
        if file.endswith(".mp4"):
            print(file)
            input_path = os.path.join(LOCAL_VIDEOS_DIRECTORY, file)
            output_path = os.path.join(
                LOCAL_KEYFRAMES_DIRECTORY, f"{os.path.splitext(file)[0]}.jpg"
            )
            timestamp = "00:00:02"  # HH:MM:SS format
            print(f"Extracting first keyframe from {input_path} to {output_path}")
            extract_first_keyframe(input_path, output_path, timestamp)


def extract_first_keyframe(input_path, output_path, timestamp):
    """
    Extracts the first keyframe from a video file and saves it as a JPEG image.

    :param input_path: Path to the input video file.
    :param output_path: Path where the extracted keyframe will be saved.
    """
    ffmpeg = FFmpeg().input(input_path, ss=timestamp).output(output_path, vframes=1)
    ffmpeg.execute()


if __name__ == "__main__":
    main()
