from .. import params


def invalidate_cache(id):
    """Invalidate CloudFront cache

    :param id: identifier for this invalidation

    :returns: boto3.client.create_invalidation() response
    """
    cache_invalidations = list(dict.fromkeys(params.cache_invalidations))
    if len(cache_invalidations) < 10:
        cache_invalidations = ["/" + path for path in cache_invalidations]
    else:
        cache_invalidations = ["/*"]
    params.cache_invalidations = list()
    invalidation_batch = {
        "Paths": {
            "Quantity": len(cache_invalidations),
            "Items": cache_invalidations,
        },
        "CallerReference": id,
    }

    params.log.debug(
        reason="Sending invalidation batch", invalidation_batch=invalidation_batch
    )
    response = params.cloudfront.create_invalidation(
        DistributionId=params.CLOUDFRONT_ID,
        InvalidationBatch=invalidation_batch,
    )

    return response
