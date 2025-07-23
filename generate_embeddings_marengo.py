# Summary: This script generates video embeddings using the Amazon Bedrock Marengo model.
#          It retrieves video files from an S3 bucket, processes each video to generate embeddings,
#          and saves the results in a local directory.
# Author: Gary A. Stafford
# Date: 2025-07-23
# License: MIT License

import os
import time
import json

import boto3
from botocore.config import Config
from dotenv import load_dotenv

from utilities import Utilities
from data import VideoEmbeddings

load_dotenv()  # Loads variables from .env file


AWS_REGION = os.getenv("AWS_REGION_MARENGO")
S3_VIDEO_STORAGE_BUCKET_MARENGO = os.getenv("S3_VIDEO_STORAGE_BUCKET_MARENGO")
CLOUDFRONT_URL = os.getenv("CLOUDFRONT_URL")

MODEL_ID = "twelvelabs.marengo-embed-2-7-v1:0"
S3_SOURCE_PREFIX = "commercials"
S3_DESTINATION_PREFIX = "embeddings"
LOCAL_DESTINATION_DIRECTORY = "bedrock_marengo_embeddings"


def main() -> None:

    config = Config(
        retries={
            "max_attempts": 5,
            "mode": "standard",  # Or 'adaptive' for a more sophisticated approach
        }
    )

    bedrock_runtime_client = boto3.client(
        service_name="bedrock-runtime", region_name=AWS_REGION, config=config
    )

    s3_client = boto3.client("s3", region_name=AWS_REGION)

    sts = boto3.client("sts")
    account_id = sts.get_caller_identity()["Account"]

    # Get the list of MP4 files from the specified S3 bucket
    video_file_names = Utilities.get_list_of_video_names_from_s3(
        s3_client, S3_VIDEO_STORAGE_BUCKET_MARENGO, S3_SOURCE_PREFIX
    )

    # Wait for the job to complete and then read the output
    for video_file_name in video_file_names:
        local_file_path = (
            f"{LOCAL_DESTINATION_DIRECTORY}/{video_file_name.replace('.mp4', '.json')}"
        )
        if os.path.exists(local_file_path):
            print(f"Skipping {video_file_name}, already processed.")
            continue

        video_key = f"{S3_SOURCE_PREFIX}/{video_file_name}"
        video_s3_uri = f"s3://{S3_VIDEO_STORAGE_BUCKET_MARENGO}/{video_key}"
        print(f"Generating analysis for video: {video_file_name}")

        # Get metadata for the S3 object
        metadata = Utilities.get_s3_object_metadata(
            s3_client, S3_VIDEO_STORAGE_BUCKET_MARENGO, video_key
        )

        # Generate embeddings for the video
        response = generate_embeddings(bedrock_runtime_client, account_id, video_s3_uri)

        # Wait for the job to complete
        print(f"Job started with invocation ARN: {response['invocationArn']}")
        invocation_arn = response["invocationArn"]
        final_job_status = Utilities.poll_job_status(
            bedrock_runtime_client, invocation_arn
        )
        print(f"Final job status: {final_job_status}")

        # Download the output file from S3
        s3_prefix = invocation_arn.split("/")[-1]
        s3_key = f"{S3_DESTINATION_PREFIX}/{s3_prefix}/output.json"
        embeddings = download_embeddings_from_s3(s3_client, s3_key)
        video_embeddings = VideoEmbeddings(
            videoName=video_file_name,
            s3URI=video_s3_uri,
            keyframeURL=f"{CLOUDFRONT_URL}/{video_file_name.replace('.mp4', '.jpg')}",
            dateCreated=time.strftime("%Y-%m-%dT%H:%M:%S %Z", time.gmtime()),
            sizeBytes=metadata["ContentLength"],
            contentType=metadata["ContentType"],
            durationSec=round(embeddings["data"][-1]["endSec"], 2),
            embeddings=embeddings["data"],
        )

        # Write the video embedding to a local file
        write_video_analysis_to_file(video_embeddings, local_file_path)
        print(f"Video embeddings written to: {local_file_path}")


def generate_embeddings(client: boto3.client, account_id: str, video_path: str) -> dict:
    """Start the video analysis job.
    Args:
        client (boto3.client): The Boto3 client for the Bedrock service.
        account_id (str): The AWS account ID.
        video_path (str): The S3 path to the video file.
    Returns:
        dict: The response from the video analysis job.
    """
    response = client.start_async_invoke(
        modelId=MODEL_ID,
        modelInput={
            "inputType": "video",
            "mediaSource": {
                "s3Location": {
                    "uri": video_path,
                    "bucketOwner": account_id,
                }
            },
            "embeddingOption": ["visual-image", "visual-text", "audio"],
        },
        outputDataConfig={
            "s3OutputDataConfig": {
                "s3Uri": f"s3://{S3_VIDEO_STORAGE_BUCKET_MARENGO}/{S3_DESTINATION_PREFIX}/",
            }
        },
    )

    return response


def download_embeddings_from_s3(client: boto3.client, s3_key: str) -> VideoEmbeddings:
    """Download the output file from S3 and save it locally.
    Args:
        client (boto3.client): The Boto3 S3 client.
        s3_key (str): The S3 key of the output file.
    Returns:
        VideoEmbeddings: The video embedding object.
    """
    s3_object = client.get_object(
        Bucket=S3_VIDEO_STORAGE_BUCKET_MARENGO,
        Key=s3_key,
    )
    embeddings = json.loads(s3_object["Body"].read().decode("utf-8"))

    return embeddings


def write_video_analysis_to_file(
    video_embeddings: VideoEmbeddings, local_file_path: str
) -> None:
    """Write the video analysis response to a local file.
    Args:
        video_analysis (VideoEmbeddings): The video analysis object containing the response.
        local_file_path (str): The local file path where the response will be written.
    """
    with open(local_file_path, "w") as f:
        f.write(video_embeddings.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
    print("Video embeddings generation completed successfully.")
