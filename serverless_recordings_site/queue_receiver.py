import json
import os

import boto3
import jinja2
import structlog
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from .util.log_config import setup_logging
from .util.recording_path import project_time, recording_path

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

MEETINGS_TABLE_ARN = os.environ["MEETINGS_TABLE_ARN"]
table_name = MEETINGS_TABLE_ARN.split(":")[-1].split("/")[-1]
dynamodb = boto3.resource("dynamodb")
meetings_table = dynamodb.Table(table_name)

WEBSITE_BUCKET = os.environ["WEBSITE_BUCKET"]
s3 = boto3.resource("s3")
j2_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(
        searchpath=f"{os.environ['LAMBDA_TASK_ROOT']}/page_templates"
    )
)

response = s3.Object(WEBSITE_BUCKET, "login.html").upload_file(
    f"{os.environ['LAMBDA_TASK_ROOT']}/site_html/login.html",
    ExtraArgs={"ContentType": "text/html"},
)
print(f"Upload login file to S3 bucket: {response=}")


def _load_template(template):
    local_filename = f"/tmp/{template}"
    template = f"templates/{template}"
    if not os.path.exists(local_filename):
        s3.Bucket(WEBSITE_BUCKET).download_file(template, local_filename)
    return j2_env.get_template(template)


def create_organization_page(org, log):
    ##STAGE Create organization page
    stage = "Create organization page"
    log = log.bind(organization=org)

    response = meetings_table.scan(
        IndexName="organization-index",
        Select="ALL_PROJECTED_ATTRIBUTES",
        FilterExpression=Key("organization").eq(org),
    )
    log.debug(stage, reason="Retrieved results", response=response)
    if (topics := response.get("Items")) is None:
        log.error(stage, reason="NONE FOUND", org=org, get_item_response=response)
        return

    topics = list({v["meeting_topic"]: v for v in topics})
    topics.sort()

    render_input = {
        "organization": org,
        "topics": [],
    }
    for topic in topics:
        entry = {
            "meeting_topic": topic,
            "meeting_topic_path": f"/{recording_path(organization=org, meeting_topic=topic)}/",
        }
        render_input["topics"].append(entry)
    fname = f"{recording_path(organization=org)}/index.html"
    log.info(stage, reason="Render input", render_input=render_input, fname=fname)

    topic_page = j2_env.get_template("organization.j2.html").render(**render_input)
    try:
        response = s3.Bucket(WEBSITE_BUCKET).put_object(
            Key=fname,
            Body=topic_page,
            ContentType="text/html",
        )
    except ClientError as e:
        log.error(stage, reason=str(e), exception=e, filename=fname)
        raise RuntimeError from e
    log.debug(stage, reason="Put page to S3", response=response)
    return


def create_topic_page(org, topic, log):
    ##STAGE Create topic page
    stage = "Create topic page"
    log = log.bind(topic=topic)

    response = meetings_table.scan(
        IndexName="meeting-index",
        Select="ALL_PROJECTED_ATTRIBUTES",
        FilterExpression=Key("meeting_topic").eq(topic),
    )
    log.debug(stage, reason="Retrieved results", response=response)
    if (meetings := response.get("Items")) is None:
        log.error(stage, reason="NONE FOUND", topic=topic, get_item_response=response)
        return

    render_input = {
        "organization": org,
        "meeting_topic": topic,
        "meetings": [],
    }
    for meeting in meetings:
        entry = {
            "start_time": project_time(
                meeting["start_time"], do_round=True, pretty=True
            ),
            "recording_path": f"/{meeting['recording_path']}/",
        }
        render_input["meetings"].append(entry)
    fname = f"{recording_path(organization=org, meeting_topic=topic)}/index.html"
    log.info(stage, reason="Render input", render_input=render_input, fname=fname)

    topic_page = j2_env.get_template("topic.j2.html").render(**render_input)
    try:
        response = s3.Bucket(WEBSITE_BUCKET).put_object(
            Key=fname,
            Body=topic_page,
            ContentType="text/html",
        )
    except ClientError as e:
        log.error(stage, reason=str(e), exception=e, filename=fname)
        raise RuntimeError from e
    log.debug(stage, reason="Put page to S3", response=response)
    return


def create_meeting_page(meeting_document, log):
    ##STAGE Create meeting page
    stage = "Create meeting page"

    fname = f"{meeting_document['recording_path']}/index.html"
    meeting_document["start_time"] = project_time(
        meeting_document["start_time"], pretty=True
    )
    meeting_document["end_time"] = project_time(
        meeting_document["end_time"], pretty=True
    )
    log.info(stage, reason="Render input", render_input=meeting_document, fname=fname)

    meeting_page = j2_env.get_template("meeting.j2.html").render(**meeting_document)
    try:
        response = s3.Bucket(WEBSITE_BUCKET).put_object(
            Key=fname,
            Body=meeting_page,
            ContentType="text/html",
        )
    except ClientError as e:
        log.error(stage, reason=str(e), exception=e, fname=fname)
        raise RuntimeError from e
    log.debug(stage, reason="Put page to S3", response=response)
    return


def handler(event, context):
    setup_logging()
    log = structlog.get_logger()
    aws_request_id = "*NO CONTEXT*" if context is None else context.aws_request_id
    log = structlog.get_logger()
    log = log.bind(aws_request_id=aws_request_id)

    log.info("STARTED", queue_event=event)

    ##STAGE Receive queue message
    stage = "Receive queue message"
    while True:
        messages_to_delete = []
        for message in webbuilder_notify.receive_messages(
            AttributeNames=["SentTimestamp"],
            MaxNumberOfMessages=1,
            MessageAttributeNames=["All"],
            VisibilityTimeout=20,
            WaitTimeSeconds=0,
        ):
            log.debug(stage, reason="Received message", message=message)
            body = json.loads(message.body)
            log = log.bind(recording_id=body["recording_id"])
            log.info(stage, reason="Processing message", message_body=body)

            create_meeting_page(body, log)
            create_topic_page(body["organization"], body["meeting_topic"], log)
            create_organization_page(body["organization"], log)

            messages_to_delete.append(
                {
                    "Id": message.message_id,
                    "ReceiptHandle": message.receipt_handle,
                }
            )

        # Break out of While-True loop if no messages to delete (meaning
        # no messages were received)
        if len(messages_to_delete) == 0:
            break
        # Delete messages from the SQS queue
        else:
            response = webbuilder_notify.delete_messages(Entries=messages_to_delete)
            log.debug(stage, reason="Deleted queue messages", response=response)

    return
