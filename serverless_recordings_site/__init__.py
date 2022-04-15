import os

import boto3
import jinja2


class Params:
    pass


params = Params()

params.MEETINGS_TABLE_ARN = os.environ["MEETINGS_TABLE_ARN"]
params.table_name = params.MEETINGS_TABLE_ARN.split(":")[-1].split("/")[-1]
params.dynamodb = boto3.resource("dynamodb")
params.meetings_table = params.dynamodb.Table(params.table_name)

params.WEBSITE_BUCKET = os.environ["WEBSITE_BUCKET"]
params.s3 = boto3.resource("s3")
params.j2_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(
        searchpath=f"{os.environ['LAMBDA_TASK_ROOT']}/page_templates"
    )
)

params.CLOUDFRONT_ID = os.environ["CLOUDFRONT_ID"]
params.cloudfront = boto3.client("cloudfront")
params.cache_invalidations = list()
