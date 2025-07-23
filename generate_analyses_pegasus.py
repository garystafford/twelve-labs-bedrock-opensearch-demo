import os
import json
import time
import random

from dotenv import load_dotenv
import boto3
from botocore.config import Config

from utilities import Utilities
from data import VideoAnalysis

load_dotenv()  # Loads variables from .env file

AWS_REGION = os.getenv("AWS_REGION_PEGASUS")
S3_VIDEO_STORAGE_BUCKET_PEGASUS = os.getenv("S3_VIDEO_STORAGE_BUCKET_PEGASUS")

MODEL_ID = "us.twelvelabs.pegasus-1-2-v1:0"
S3_SOURCE_PREFIX = "commercials"
LOCAL_DESTINATION_DIRECTORY = "bedrock_pegasus_analyses"


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
        s3_client, S3_VIDEO_STORAGE_BUCKET_PEGASUS, S3_SOURCE_PREFIX
    )

    # Wait for the job to complete and then read the output
    for video_file_name in video_file_names:
        local_file_path = (
            f"{LOCAL_DESTINATION_DIRECTORY}/{video_file_name.replace('.mp4', '.json')}"
        )
        if os.path.exists(local_file_path):
            print(f"Skipping {video_file_name}, already processed.")
            continue

        video_path = f"s3://{S3_VIDEO_STORAGE_BUCKET_PEGASUS}/{S3_SOURCE_PREFIX}/{video_file_name}"
        print(f"Generating analysis for video: {video_file_name}")

        # Define the prompts for title, summary, and keywords
        prompt_summary = "Generate a detailed summary of the video. Consider the visual, audio, textual, spatial, and temporal aspects in the video. Only provide the summary in the response; no pre-text, post-text, or quotation marks."
        prompt_title = "Generate a descriptive title for the video. Only provide the title in the response; no pre-text, post-text, or quotation marks."
        prompt_keywords = """Extract keywords from the video content as a list of strings, for example: ["keyword1", "keyword2", "keyword3", "keyword4"]. Only provide the list keywords in the response; no pre-text, post-text."""

        response_title = generate_video_analysis(
            bedrock_runtime_client, account_id, video_path, prompt_title
        )

        response_summary = generate_video_analysis(
            bedrock_runtime_client, account_id, video_path, prompt_summary
        )

        response_keywords = generate_video_analysis(
            bedrock_runtime_client, account_id, video_path, prompt_keywords
        )

        video_analysis = VideoAnalysis(
            videoName=video_file_name,
            s3URI=video_path,
            title=response_title["message"],
            summary=response_summary["message"],
            keywords=json.loads(response_keywords["message"]),
            dateCreated=time.strftime("%Y-%m-%dT%H:%M:%S %Z", time.gmtime()),
        )

        # Write the video analysis to a local file
        write_video_analysis_to_file(video_analysis, local_file_path)
        print(f"Video analysis written to: {local_file_path}")


def generate_video_analysis(
    client: boto3.client,
    account_id: str,
    video_path: str,
    prompt: str,
    max_retries: int = 5,
) -> dict:
    """Start the video analysis job.

    Args:
        client (boto3.client): The Boto3 client for the Bedrock service.
        account_id (str): The AWS account ID.
        video_path (str): The S3 path to the video file.
        prompt (str): The prompt to use for the video analysis.
        max_retries (int, optional): The maximum number of retry attempts. Defaults to 3.

    Raises:
        e: An error occurred while starting the video analysis job.

    Returns:
        dict: The response from the video analysis job.
    """

    # Reference: https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-pegasus.html
    request_body = {
        "inputPrompt": prompt,
        "mediaSource": {
            "s3Location": {
                "uri": video_path,
                "bucketOwner": account_id,
            }
        },
        "temperature": 0.2,
        # "maxOutputTokens": 2048,
        # "responseFormat": {
        #     "type": "json_schema",
        #     "json_schema": {
        #         "name": "video_analysis",
        #         "schema": {
        #             "type": "object",
        #             "properties": {
        #                 "summary": {"type": "string"},
        #                 "key_scenes": {"type": "array", "items": {"type": "string"}},
        #                 "duration": {"type": "string"},
        #             },
        #             "required": ["summary", "key_scenes"],
        #         },
        #     },
        # },
    }

    retries = 0
    while True:
        try:
            response = client.invoke_model(
                modelId=MODEL_ID,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json",
            )
            response_body = json.loads(response["body"].read())
            return response_body
        except Exception as e:
            if "ThrottlingException" in str(e) and retries < max_retries:
                retries += 1
                backoff_time = (2**retries) + random.uniform(
                    0, 1
                )  # Exponential backoff with jitter
                print(
                    f"Throttled. Retrying in {backoff_time:.2f} seconds (attempt {retries})..."
                )
                time.sleep(backoff_time)
            else:
                raise e  # Re-raise the exception if it's not a retryable error or max retries reached


# method that writes the video analysis response to a local file
def write_video_analysis_to_file(
    video_analysis: VideoAnalysis, local_file_path: str
) -> None:
    """Write the video analysis response to a local file.
    Args:
        video_analysis (VideoAnalysis): The video analysis object containing the response.
        local_file_path (str): The local file path where the response will be written.
    """
    with open(local_file_path, "w") as f:
        f.write(video_analysis.model_dump_json(indent=2))
    print(f"Response written to {local_file_path}")


if __name__ == "__main__":
    main()
    print("Video analysis completed successfully.")
