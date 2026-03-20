import json
import os
import kb_common as kb

kb.REGION = os.environ.get("AWS_REGION", "us-west-2")
BUCKET = os.environ["LESSONS_BUCKET"]


def handler(event, context):
    lessons = []
    paginator = kb.s3().get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET, Prefix="lessons/"):
        for obj in page.get("Contents", []):
            data = kb.s3().get_object(Bucket=BUCKET, Key=obj["Key"])
            lessons.append(json.loads(data["Body"].read()))

    return {"statusCode": 200, "body": json.dumps({"lessons": lessons, "count": len(lessons)})}
