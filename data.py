from pydantic import BaseModel
from typing import List


# Data models for TwelveLabs Marengo model for vector embeddings structure
class VideoEmbeddingSegment(BaseModel):
    embedding: List[float]
    embeddingOption: str
    startSec: float
    endSec: float


class VideoEmbeddings(BaseModel):
    videoName: str
    s3URI: str
    keyframeURL: str
    dateCreated: str
    sizeBytes: int
    durationSec: float = 0.0
    contentType: str
    embeddings: List[VideoEmbeddingSegment]


# Data model for TwelveLabs Pegasus model for video analysis structure
class VideoAnalysis(BaseModel):
    videoName: str
    s3URI: str
    title: str
    summary: str
    keywords: list[str] = []
    dateCreated: str


# Data model for OpenSearch document structure
class OpenSearchDocument(BaseModel):
    videoName: str
    s3URI: str
    keyframeURL: str
    title: str
    summary: str
    keywords: List[str]
    dateCreated: str
    contentType: str
    sizeBytes: int
    durationSec: float = 0.0
    embeddings: List[VideoEmbeddingSegment]
