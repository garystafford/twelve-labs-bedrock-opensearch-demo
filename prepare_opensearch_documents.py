import json
import os
import time

from data import OpenSearchDocument, VideoAnalysis, VideoEmbeddings

LOCAL_EMBEDDINGS_DIRECTORY = "bedrock_marengo_embeddings"
LOCAL_ANALYSIS_DIRECTORY = "bedrock_pegasus_analyses"
LOCAL_OPENSEARCH_DIRECTORY = "documents"


def main():
    for analysis_file in os.listdir(LOCAL_ANALYSIS_DIRECTORY):
        if not analysis_file.endswith(".json"):
            print(f"Skipping {analysis_file}, not a JSON file.")
            continue

        print(f"Generating OpenSearch document for: {analysis_file}")

        # Construct file paths for embeddings and analysis
        embeddings_file_path = os.path.join(LOCAL_EMBEDDINGS_DIRECTORY, analysis_file)
        analysis_file_path = os.path.join(LOCAL_ANALYSIS_DIRECTORY, analysis_file)

        # Read the JSON files
        embeddings = VideoEmbeddings(**read_json_file(embeddings_file_path))
        analysis = VideoAnalysis(**read_json_file(analysis_file_path))

        # Prepare OpenSearch document
        opensearch_document: OpenSearchDocument = prepare_opensearch_documents(
            embeddings, analysis
        )

        # Write the OpenSearch document to a file
        write_opensearch_document(analysis_file, opensearch_document)


def write_opensearch_document(
    analysis_file: str, opensearch_document: OpenSearchDocument
) -> None:
    """Write the OpenSearch document to a file in the local directory.
    :param analysis_file: Name of the analysis file (used for naming the output).
    :param opensearch_document: OpenSearchDocument object to write.
    :return: None
    """
    os.makedirs(LOCAL_OPENSEARCH_DIRECTORY, exist_ok=True)
    output_file_path = os.path.join(LOCAL_OPENSEARCH_DIRECTORY, analysis_file)
    with open(output_file_path, "w") as output_file:
        json.dump(opensearch_document.model_dump(), output_file, indent=2)


def read_json_file(file_path: str) -> dict:
    """Read a JSON file and return the parsed data.
    :param file_path: Path to the JSON file.
    :return: Parsed JSON data as a dictionary.
    :raises FileNotFoundError: If the file does not exist.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, "r") as file:
        data = json.load(file)

    return data


def prepare_opensearch_documents(
    embeddings: VideoEmbeddings, analysis: VideoAnalysis
) -> OpenSearchDocument:
    """Prepare OpenSearch document from video embeddings and analysis data.
    :param embeddings: VideoEmbeddings object containing vector embeddings.
    :param analysis: VideoAnalysis object containing video analysis data.
    :return: OpenSearchDocument object ready for indexing.
    """
    document = OpenSearchDocument(
        videoName=analysis.videoName,
        s3URI=analysis.s3URI,
        keyframeURL=embeddings.keyframeURL,
        title=analysis.title,
        summary=analysis.summary,
        keywords=analysis.keywords,
        dateCreated=time.strftime("%Y-%m-%dT%H:%M:%S %Z", time.gmtime()),
        contentType=embeddings.contentType,
        sizeBytes=embeddings.sizeBytes,
        durationSec=embeddings.durationSec,
        embeddings=embeddings.embeddings,
    )

    return document


if __name__ == "__main__":
    main()
    print("OpenSearch documents prepared successfully.")
