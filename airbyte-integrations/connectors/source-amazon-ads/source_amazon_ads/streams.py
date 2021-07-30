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

from abc import ABC, abstractmethod
from json import dumps, loads
from typing import Any, Iterable, Mapping, MutableMapping, Optional

import requests
from airbyte_cdk.models import SyncMode
from airbyte_cdk.sources.streams.http import HttpStream

from .common import URL_BASE, PageToken, SourceContext
from .schemas import DisplayAdGroup, DisplayCampaign, DisplayCreatives, DisplayProductAds, DisplayTargeting, JSModel, Profile, Types


# Basic full refresh stream
class AmazonAdsStream(HttpStream, ABC):
    def __init__(self, config, *args, context: SourceContext = SourceContext(), **kwargs):
        self.ctx = context
        self._config = config
        super().__init__(*args, **kwargs)

    url_base = URL_BASE

    @property
    @abstractmethod
    def model(self) -> JSModel:
        """
        Pydantic model to represent json schema
        """

    def next_page_token(self, response: requests.Response) -> Optional[Mapping[str, Any]]:
        return None

    def request_headers(self, *args, **kvargs) -> MutableMapping[str, Any]:
        return {"Amazon-Advertising-API-ClientId": self._config.client_id}

    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        """
        :return an object representing single record in the response
        """
        yield from loads(response.text)

    def get_json_schema(self):
        return self.model.schema()


class Profiles(AmazonAdsStream):
    """
    This stream corresponds to Amazon Advertising API - Profiles
    https://advertising.amazon.com/API/docs/en-us/reference/2/profiles#/Profiles
    """

    primary_key = "profileId"
    model = Profile

    def path(self, **kvargs) -> str:
        return "v2/profiles"

    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        for record in super().parse_response(response, **kwargs):
            profile_id_obj = self.model.parse_obj(record)
            self.ctx.profiles.append(profile_id_obj)
            yield record

    def read_records(self, *args, **kvargs) -> Iterable[Mapping[str, Any]]:
        if self.ctx.profiles:
            yield from [profile.dict(exclude_unset=True) for profile in self.ctx.profiles]
        else:
            yield from super().read_records(*args, **kvargs)

    def fill_context(self):
        """
        Fill profiles info for other streams in case of "profiles" stream havent been specified on catalog config
        """
        _ = [record for record in self.read_records(SyncMode.full_refresh)]


class ContextStream(AmazonAdsStream):
    """
    Stream for getting resources based on context set by previous stream.
    """

    flattern_properties = []

    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        for record in super().parse_response(response, **kwargs):
            for prop in self.flattern_properties:
                if prop in record:
                    record[prop] = dumps(record[prop])
            yield record

    def read_records(self, *args, **kvargs) -> Iterable[Mapping[str, Any]]:
        for profile in self.ctx.profiles:
            if profile.accountInfo.type == Types.VENDOR:
                self.ctx.current_profile_id = profile.profileId
                yield from super().read_records(*args, **kvargs)

    def request_headers(self, *args, **kvargs) -> MutableMapping[str, Any]:
        headers = super().request_headers(*args, **kvargs)
        headers["Amazon-Advertising-API-Scope"] = str(self.ctx.current_profile_id)
        return headers


class PaginationStream(ContextStream):
    """
    Stream for getting resources with pagination support
    """

    PAGE_SIZE = 100

    def next_page_token(self, response: requests.Response) -> Optional[PageToken]:
        responses = loads(response.text)
        if len(responses) < PaginationStream.PAGE_SIZE:
            self.ctx.current_token = PageToken()
            return None
        else:
            next_token = PageToken(self.ctx.current_token.offset + PaginationStream.PAGE_SIZE)
            self.ctx.current_token = next_token
            return next_token

    def request_params(
        self,
        stream_state: Mapping[str, Any],
        stream_slice: Mapping[str, Any] = None,
        next_page_token: PageToken = None,
    ) -> MutableMapping[str, Any]:
        return {
            "startIndex": next_page_token.offset if next_page_token else 0,
            "count": PaginationStream.PAGE_SIZE,
        }


class SponsoredDisplayCampaigns(PaginationStream):
    """
    This stream corresponds to Amazon Advertising API - Sponsored Displays Campaigns
    https://advertising.amazon.com/API/docs/en-us/sponsored-display/3-0/openapi#/Campaigns
    """

    primary_key = "campaignId"
    model = DisplayCampaign

    def path(self, **kvargs) -> str:
        return "sd/campaigns"


class SponsoredDisplayAdGroups(PaginationStream):
    """
    This stream corresponds to Amazon Advertising API - Sponsored Displays Ad groups
    https://advertising.amazon.com/API/docs/en-us/sponsored-display/3-0/openapi#/Ad%20groups
    """

    primary_key = "adGroupId"
    model = DisplayAdGroup

    def path(self, **kvargs) -> str:
        return "sd/adGroups"


class SponsoredDisplayProductAds(PaginationStream):
    """
    This stream corresponds to Amazon Advertising API - Sponsored Displays Product Ads
    https://advertising.amazon.com/API/docs/en-us/sponsored-display/3-0/openapi#/Product%20ads
    """

    primary_key = "adId"
    model = DisplayProductAds

    def path(self, **kvargs) -> str:
        return "sd/productAds"


class SponsoredDisplayTargetings(PaginationStream):
    """
    This stream corresponds to Amazon Advertising API - Sponsored Displays Targetings
    https://advertising.amazon.com/API/docs/en-us/sponsored-display/3-0/openapi#/Targeting
    """

    primary_key = "targetId"
    model = DisplayTargeting
    flattern_properties = ["expression", "resolvedExpression"]

    def path(self, **kvargs) -> str:
        return "sd/targets"


class SponsoredDisplayCreatives(PaginationStream):
    """
    This stream corresponds to Amazon Advertising API - Sponsored Displays Creatives
    https://advertising.amazon.com/API/docs/en-us/sponsored-display/3-0/openapi#/Creatives
    """

    primary_key = "creativeId"
    model = DisplayCreatives

    flattern_properties = ["properties"]

    def path(self, **kvargs) -> str:
        return "sd/creatives"
