import json
import os
import uuid
from datetime import datetime, timezone
import kb_common as kb

kb.REGION = os.environ.get("AWS_REGION", "us-west-2")
BUCKET = os.environ["LESSONS_BUCKET"]


def handler(event, context):
    body = event if isinstance(event, dict) else json.loads(event.get("body", "{}"))
    lesson_id = str(uuid.uuid4())
    text = f"{body.get('topic','')} {body.get('problem','')} {body.get('resolution','')}"

    embedding = kb.embed(text)

    lesson = {
        "id": lesson_id,
        "topic": body.get("topic", ""),
        "problem": body.get("problem", ""),
        "resolution": body.get("resolution", ""),
        "tags": body.get("tags", []),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    kb.s3().put_object(
        Bucket=BUCKET,
        Key=f"lessons/{lesson_id}.json",
        Body=json.dumps(lesson),
        ContentType="application/json",
    )

    index = kb.load_index(BUCKET)
    index[lesson_id] = embedding
    kb.save_index(BUCKET, index)

    return {"statusCode": 200, "body": json.dumps({"id": lesson_id, "status": "stored"})}
