import structlog

from . import params
from .util.aws_helpers import invalidate_cache
from .util.html_pages import (
    create_meeting_page,
    create_organization_page,
    create_topic_page,
)
from .util.log_config import setup_logging


def handler(event, context):
    setup_logging()
    aws_request_id = "*NO CONTEXT*" if context is None else context.aws_request_id
    params.log = structlog.get_logger()
    params.log = params.log.bind(aws_request_id=aws_request_id)
    params.log.info("STARTED", queue_event=event)

    ##STAGE Loop through meetings
    stage = "Loop through meetings"
    discovered_topics = dict()

    ## TODO: need to wrap to handle a resumption token
    response = params.meetings_table.scan(
        ProjectionExpression="recording_id, start_time, end_time, recording_path, meeting_topic, organization, files",
    )
    params.log.debug(stage, reason="Retrieved results", response=response)
    if (meetings := response.get("Items")) is None:
        params.log.error(stage, reason="NONE FOUND", get_item_response=response)
        return

    for meeting in meetings:
        params.log.debug(stage, reason="Handling meeting", meeting=meeting)
        organization = meeting["organization"]
        topic = meeting["meeting_topic"]
        if organization not in discovered_topics:
            discovered_topics[organization] = set()
        discovered_topics[organization].add(topic)
        create_meeting_page(meeting_document=meeting)
    params.log.info(stage, reason="Found topics", discovered_topics=discovered_topics)

    ##STAGE Loop through discovered topics
    stage = "Loop through discovered topics"
    for organization in discovered_topics:
        for topic in discovered_topics[organization]:
            create_topic_page(organization, topic)
        create_organization_page(organization)

    ##STAGE Create CloudFront invalidation
    stage = "Create CloudFront invalidation"
    response = invalidate_cache(aws_request_id)
    params.log.debug(stage, reason="Cache invalidated", response=response)
    return

    # for message in event["Records"]:
    #     log.debug(stage, reason="Received message", message=message)
    #     body = json.loads(message["body"])
    #     log = log.bind(recording_id=body["recording_id"])
    #     log.info(stage, reason="Processing message", message_body=body)

    #     create_meeting_page(body, log)
    #     create_topic_page(body["organization"], body["meeting_topic"], log)
    #     create_organization_page(body["organization"], log)

    #     message_to_delete = {
    #         "Id": message["messageId"],
    #         "ReceiptHandle": message["receiptHandle"],
    #     }
    #     response = webbuilder_notify.delete_messages(Entries=[message_to_delete])
    #     log.debug(stage, reason="Deleted message", response=response, message=message)

    # return
