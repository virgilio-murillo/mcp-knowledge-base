import json
import math
import boto3

REGION = None
_bedrock = None
_s3 = None


def s3():
    global _s3
    if not _s3:
        _s3 = boto3.client("s3", region_name=REGION)
    return _s3


def bedrock():
    global _bedrock
    if not _bedrock:
        _bedrock = boto3.client("bedrock-runtime", region_name=REGION)
    return _bedrock


def embed(text, model_id="amazon.titan-embed-text-v2:0", dims=1024):
    resp = bedrock().invoke_model(
        modelId=model_id,
        contentType="application/json",
        body=json.dumps({"inputText": text[:8000], "dimensions": dims}),
    )
    return json.loads(resp["body"].read())["embedding"]


def load_index(bucket):
    try:
        obj = s3().get_object(Bucket=bucket, Key="index/embeddings.json")
        return json.loads(obj["Body"].read())
    except s3().exceptions.NoSuchKey:
        return {}


def save_index(bucket, index):
    s3().put_object(
        Bucket=bucket, Key="index/embeddings.json",
        Body=json.dumps(index), ContentType="application/json",
    )


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _norm(a):
    return math.sqrt(sum(x * x for x in a))


def cosine_top_k(query_vec, index, k=5):
    if not index:
        return []
    qn = _norm(query_vec)
    scored = []
    for vid, vec in index.items():
        score = _dot(query_vec, vec) / (qn * _norm(vec) + 1e-10)
        scored.append((vid, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:k]
