from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from .. import params
from .string_constructors import project_time, recording_path


def create_meeting_page(meeting_document):
    """Create HTML page in S3 for a meeting occurrence

    :param meeting_document: Dictionary of meeting details

    :returns: None
    """
    ##STAGE Create meeting page
    stage = "Create meeting page"
    # params.log.info(stage, "Function Start", meeting=meeting_document)

    fname = f"{meeting_document['recording_path']}/index.html"
    meeting_document["start_time"] = project_time(
        meeting_document["start_time"], pretty=True
    )
    meeting_document["end_time"] = project_time(
        meeting_document["end_time"], pretty=True
    )
    params.log.info(
        stage, reason="Render input", render_input=meeting_document, fname=fname
    )

    meeting_page = params.j2_env.get_template("meeting.j2.html").render(
        **meeting_document
    )
    try:
        response = params.s3.Bucket(params.WEBSITE_BUCKET).put_object(
            Key=fname,
            Body=meeting_page,
            ContentType="text/html",
        )
    except ClientError as e:
        params.log.error(stage, reason=str(e), exception=e, fname=fname)
        raise RuntimeError from e
    params.log.debug(stage, reason="Put page to S3", response=response)
    params.cache_invalidations.append(fname)
    return


def create_topic_page(org, topic):
    """Create HTML page in S3 for all meeting in a topic

    :param org: organization hosting the meeting
    :parameter topic: meeting topic

    :returns: None
    """
    ##STAGE Create topic page
    stage = "Create topic page"
    log = params.log.bind(topic=topic)

    response = params.meetings_table.scan(
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
    for meeting in reversed(sorted(meetings, key=lambda i: i["start_time"])):
        entry = {
            "start_time": project_time(
                meeting["start_time"], do_round=True, pretty=True
            ),
            "recording_path": f"/{meeting['recording_path']}/",
        }
        render_input["meetings"].append(entry)
    fname = f"{recording_path(organization=org, meeting_topic=topic)}/index.html"
    log.info(stage, reason="Render input", render_input=render_input, fname=fname)

    topic_page = params.j2_env.get_template("topic.j2.html").render(**render_input)
    try:
        response = params.s3.Bucket(params.WEBSITE_BUCKET).put_object(
            Key=fname,
            Body=topic_page,
            ContentType="text/html",
        )
    except ClientError as e:
        log.error(stage, reason=str(e), exception=e, filename=fname)
        raise RuntimeError from e
    log.debug(stage, reason="Put page to S3", response=response)
    params.cache_invalidations.append(fname)
    return


def create_organization_page(org):
    """Create HTML page in S3 for all topics in an organization

    :param org: organization

    :returns: None
    """
    ##STAGE Create organization page
    stage = "Create organization page"
    log = params.log.bind(organization=org)

    response = params.meetings_table.scan(
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

    topic_page = params.j2_env.get_template("organization.j2.html").render(
        **render_input
    )
    try:
        response = params.s3.Bucket(params.WEBSITE_BUCKET).put_object(
            Key=fname,
            Body=topic_page,
            ContentType="text/html",
        )
    except ClientError as e:
        log.error(stage, reason=str(e), exception=e, filename=fname)
        raise RuntimeError from e
    log.debug(stage, reason="Put page to S3", response=response)
    params.cache_invalidations.append(fname)
    return
