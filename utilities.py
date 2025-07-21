from typing import List
import time

import boto3


class Utilities:
    @staticmethod
    def get_list_of_video_names_from_s3(
        client: boto3.client, bucket: str, prefix: str
    ) -> List[str]:
        """Get a list of video file names from an S3 bucket with the specified prefix.
        Args:
            client (boto3.client): The Boto3 S3 client.
            bucket (str): The name of the S3 bucket.
            prefix (str): The prefix to filter the objects.
        Returns:
            List[str]: A list of video file names (with .mp4 extension) in the specified S3 bucket.
        """
        response = client.list_objects_v2(Bucket=bucket, Prefix=prefix)

        video_files = []
        if "Contents" in response:
            for obj in response["Contents"]:
                if obj["Key"].endswith(".mp4"):
                    filename = obj["Key"].split("/")[-1]
                    video_files.append(filename)
        return video_files

    @staticmethod
    def get_s3_object_metadata(client: boto3.client, bucket: str, key: str) -> dict:
        """Get metadata for an S3 object.
        Args:
            client (boto3.client): The Boto3 S3 client.
            bucket (str): The name of the S3 bucket.
            key (str): The key of the S3 object.
        Returns:
            dict: The metadata of the S3 object.
        """
        response = client.head_object(Bucket=bucket, Key=key)
        return response

    @staticmethod
    def poll_job_status(client: boto3.client, invocation_arn: str) -> str:
        """Poll the job status until it is completed or failed.
        Args:
            client (boto3.client): The Boto3 client for the Bedrock service.
            invocation_arn (str): The ARN of the job invocation.
        Returns:
            str: The final job status.
        """
        while True:
            response = client.get_async_invoke(invocationArn=invocation_arn)
            status = response["status"]

            print(f"Invocation status: {status}")

            if status == "Completed":
                print("Job completed!")
                break
            elif status == "Failed":
                print(f"Job failed: {response.get('failureMessage')}")
                break
            else:
                # Still in progress, so wait and retry
                time.sleep(10)  # Adjust polling interval as necessary
        return response["status"]
