import os
import urllib

import boto3

MEETINGS_TABLE_ARN = os.environ["MEETINGS_TABLE_ARN"]
table_name = MEETINGS_TABLE_ARN.split(":")[-1].split("/")[-1]
dynamodb = boto3.resource("dynamodb")
meetings_table = dynamodb.Table(table_name)


def parseCookies(headers):
    parsedCookie = {}
    if headers.get("cookie"):
        for cookie in headers["cookie"][0]["value"].split(";"):
            if cookie:
                parts = cookie.split("=")
                parsedCookie[parts[0].strip()] = parts[1].strip()
    return parsedCookie


def handler(event, context):
    request = event["Records"][0]["cf"]["request"]
    response = event["Records"][0]["cf"]["response"]
    print(f"{response=}")

    headers = request["headers"]

    # if request["uri"] != "/folio/erm-sub-sig/2022-02-09T07:55/index.html":
    #     return request

    # """
    # Check for session-id in request cookie in viewer-request event,
    # if session-id is absent, redirect the user to sign in page with original
    # request sent as redirect_url in query params.
    # """

    # # Check for session-id in cookie, if present, then proceed with request
    # parsedCookies = parseCookies(headers)

    # if parsedCookies and parsedCookies["session-id"]:
    #     return request

    # URI encode the original request to be sent as redirect_url in query params
    redirectUrl = "https://%s%s?%s" % (
        headers["host"][0]["value"],
        request["uri"],
        request["querystring"],
    )
    encodedRedirectUrl = urllib.parse.quote_plus(redirectUrl.encode("utf-8"))

    response = {
        "status": "302",
        "statusDescription": "Found",
        "headers": {
            "location": [
                {
                    "key": "Location",
                    "value": f"https://{headers['host'][0]['value']}/login.html?redirect_url=%s"
                    % encodedRedirectUrl,
                }
            ]
        },
    }
    return response
