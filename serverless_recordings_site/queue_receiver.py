import json
import os

import boto3
import structlog

from . import params
from .util.aws_helpers import invalidate_cache
from .util.html_pages import (
    create_meeting_page,
    create_organization_page,
    create_topic_page,
)
from .util.log_config import setup_logging

response = params.s3.Object(params.WEBSITE_BUCKET, "login.html").upload_file(
    f"{os.environ['LAMBDA_TASK_ROOT']}/site_html/login.html",
    ExtraArgs={"ContentType": "text/html"},
)
print(f"Upload login file to S3 bucket: {response=}")

## This function will interact directly with the notification queue for events from the receive-recording Lambda
NOTIFY_WEBBUILDER_QUEUE_ARN = os.environ["NOTIFY_WEBBUILDER_QUEUE_ARN"]
queue_name = NOTIFY_WEBBUILDER_QUEUE_ARN.split(":")[-1]
account_id = NOTIFY_WEBBUILDER_QUEUE_ARN.split(":")[-2]
sqs_client = boto3.client("sqs")
queue_url_response = sqs_client.get_queue_url(
    QueueName=queue_name,
    QueueOwnerAWSAccountId=account_id,
)
sqs = boto3.resource("sqs")
webbuilder_notify = sqs.Queue(queue_url_response["QueueUrl"])


def _load_template(template):
    local_filename = f"/tmp/{template}"
    template = f"templates/{template}"
    if not os.path.exists(local_filename):
        params.s3.Bucket(params.WEBSITE_BUCKET).download_file(template, local_filename)
    return params.j2_env.get_template(template)


def handler(event, context):
    setup_logging()
    aws_request_id = "*NO CONTEXT*" if context is None else context.aws_request_id
    params.log = structlog.get_logger()
    params.log = params.log.bind(aws_request_id=aws_request_id)
    params.log.info("STARTED", queue_event=event)

    ##STAGE Process queue message
    stage = "Process queue message"
    for message in event["Records"]:
        params.log.debug(stage, reason="Received message", message=message)
        body = json.loads(message["body"])
        params.log = params.log.bind(recording_id=body["recording_id"])
        params.log.info(stage, reason="Processing message", message_body=body)

        create_meeting_page(body)
        create_topic_page(body["organization"], body["meeting_topic"])
        create_organization_page(body["organization"])

        message_to_delete = {
            "Id": message["messageId"],
            "ReceiptHandle": message["receiptHandle"],
        }
        response = webbuilder_notify.delete_messages(Entries=[message_to_delete])
        params.log.debug(
            stage, reason="Deleted message", response=response, message=message
        )

    ##STAGE Create CloudFront invalidation
    stage = "Create CloudFront invalidation"
    response = invalidate_cache(aws_request_id)
    params.log.debug(stage, reason="Cache invalidated", response=response)

    return
