import json
import os
import kb_common as kb

kb.REGION = os.environ.get("AWS_REGION", "us-west-2")
BUCKET = os.environ["LESSONS_BUCKET"]


def handler(event, context):
    body = event if isinstance(event, dict) else json.loads(event.get("body", "{}"))
    query = body.get("query", "")
    k = body.get("k", 5)

    query_vec = kb.embed(query)
    index = kb.load_index(BUCKET)
    results = kb.cosine_top_k(query_vec, index, k)

    lessons = []
    for lid, score in results:
        try:
            obj = kb.s3().get_object(Bucket=BUCKET, Key=f"lessons/{lid}.json")
            lesson = json.loads(obj["Body"].read())
            lesson["score"] = score
            lessons.append(lesson)
        except Exception:
            continue

    return {"statusCode": 200, "body": json.dumps({"results": lessons})}
