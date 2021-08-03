#
# MIT License
#
# Copyright (c) 2020 Airbyte
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#

from json import dumps, loads
from urllib.parse import parse_qs, urlparse

import pytest
import responses
from airbyte_cdk.models import SyncMode
from jsonschema import validate
from source_amazon_ads import SourceAmazonAds


def setup_responses(
    profiles_response=None,
    campaigns_response=None,
    adgroups_response=None,
    targeting_response=None,
    product_ads_response=None,
):
    responses.add(
        responses.POST,
        "https://api.amazon.com/auth/o2/token",
        json={"access_token": "alala", "expires_in": 10},
    )
    if profiles_response:
        responses.add(
            responses.GET,
            "https://advertising-api.amazon.com/v2/profiles",
            body=profiles_response,
        )
    if campaigns_response:
        responses.add(
            responses.GET,
            "https://advertising-api.amazon.com/sd/campaigns",
            body=campaigns_response,
        )
    if adgroups_response:
        responses.add(
            responses.GET,
            "https://advertising-api.amazon.com/sd/adGroups",
            body=adgroups_response,
        )
    if targeting_response:
        responses.add(
            responses.GET,
            "https://advertising-api.amazon.com/sd/targets",
            body=targeting_response,
        )
    if product_ads_response:
        responses.add(
            responses.GET,
            "https://advertising-api.amazon.com/sd/productAds",
            body=product_ads_response,
        )


@responses.activate
def test_streams_profile(test_config, profiles_response):
    setup_responses(profiles_response=profiles_response)

    source = SourceAmazonAds()
    streams = source.streams(test_config)
    assert len(streams) == 17
    profile_stream = streams[0]
    assert profile_stream.name == "profiles"
    assert streams[1].name == "sponsored_display_campaigns"
    assert streams[6].name == "sponsored_product_campaigns"
    assert streams[7].name == "sponsored_product_ad_groups"
    assert streams[8].name == "sponsored_product_keywords"
    assert streams[9].name == "sponsored_product_negative_keywords"
    assert streams[10].name == "sponsored_product_ads"
    assert streams[11].name == "sponsored_product_targetings"
    assert streams[12].name == "sponsored_products_report_stream"
    assert streams[13].name == "sponsored_brands_campaigns"
    assert streams[14].name == "sponsored_brands_ad_groups"
    assert streams[15].name == "sponsored_brands_keywords"
    assert streams[16].name == "sponsored_brands_report_stream"
    schema = profile_stream.get_json_schema()
    records = profile_stream.read_records(SyncMode.full_refresh)
    records = [r for r in records]
    assert len(responses.calls) == 2
    assert len(profile_stream._ctx.profiles) == 4
    assert len(records) == 4
    expected_records = loads(profiles_response)
    for record, expected_record in zip(records, expected_records):
        validate(schema=schema, instance=record)
        assert record == expected_record


@responses.activate
def test_streams_campaigns_4_vendors(test_config, profiles_response, campaigns_response):
    profiles_response = loads(profiles_response)
    for profile in profiles_response:
        profile["accountInfo"]["type"] = "vendor"
    profiles_response = dumps(profiles_response)
    setup_responses(profiles_response=profiles_response, campaigns_response=campaigns_response)

    source = SourceAmazonAds()
    streams = source.streams(test_config)
    profile_stream = streams[0]
    campaigns_stream = streams[1]
    records = profile_stream.read_records(SyncMode.full_refresh)
    profile_records = [r for r in records]
    records = campaigns_stream.read_records(SyncMode.full_refresh)
    campaigns_records = [r for r in records]
    assert len(campaigns_records) == len(profile_records) * len(loads(campaigns_response))


@pytest.mark.parametrize(
    ("page_size"),
    [1, 2, 5, 1000000],
)
@responses.activate
def test_streams_campaigns_pagination(mocker, test_config, profiles_response, campaigns_response, page_size):
    mocker.patch("source_amazon_ads.streams.common.PaginationStream.PAGE_SIZE", page_size)
    profiles_response = loads(profiles_response)
    for profile in profiles_response:
        profile["accountInfo"]["type"] = "vendor"
    profiles_response = dumps(profiles_response)
    setup_responses(profiles_response=profiles_response)

    source = SourceAmazonAds()
    streams = source.streams(test_config)
    campaigns_stream = streams[1]
    profile_stream = streams[0]
    campaigns = loads(campaigns_response)

    def campaigns_paginated_response_cb(request):
        query = urlparse(request.url).query
        query = parse_qs(query)
        start_index, count = (int(query[f][0]) for f in ["startIndex", "count"])
        response_body = campaigns[start_index : start_index + count]
        return (200, {}, dumps(response_body))

    responses.add_callback(
        responses.GET,
        "https://advertising-api.amazon.com/sd/campaigns",
        content_type="application/json",
        callback=campaigns_paginated_response_cb,
    )
    profile_records = profile_stream.read_records(SyncMode.full_refresh)
    profile_records = [r for r in profile_records]

    campaigns_records = campaigns_stream.read_records(SyncMode.full_refresh)
    campaigns_records = [r for r in campaigns_records]
    assert len(campaigns_records) == len(profile_records) * len(loads(campaigns_response))


@pytest.mark.parametrize(
    ("stream_name", "endpoint"),
    [
        ("sponsored_display_ad_groups", "sd/adGroups"),
        ("sponsored_display_product_ads", "sd/productAds"),
        ("sponsored_display_targetings", "sd/targets"),
    ],
)
@responses.activate
def test_streams_adgroup(
    test_config, stream_name, endpoint, profiles_response, adgroups_response, targeting_response, product_ads_response
):
    setup_responses(
        profiles_response=profiles_response,
        adgroups_response=adgroups_response,
        targeting_response=targeting_response,
        product_ads_response=product_ads_response,
    )

    source = SourceAmazonAds()
    streams = source.streams(test_config)
    profile_stream = streams[0]
    test_stream = [stream for stream in streams if stream.name == stream_name][0]
    _ = [r for r in profile_stream.read_records(SyncMode.full_refresh)]

    records = test_stream.read_records(SyncMode.full_refresh)
    records = [r for r in records]
    assert len(records) == 4
    schema = test_stream.get_json_schema()
    for r in records:
        validate(schema=schema, instance=r)
    assert any([endpoint in call.request.url for call in responses.calls])
