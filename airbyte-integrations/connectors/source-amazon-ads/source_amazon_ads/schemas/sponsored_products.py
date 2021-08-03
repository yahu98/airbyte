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

from decimal import Decimal
from typing import Dict, List

from .common import JSEnum, JSModel, State, Targeting


class CampaignType(JSEnum):
    SPONSORED_PRODUCTS = "sponsoredProducts"


class TargetingType(JSEnum):
    MANUAL = "manual"
    AUTO = "auto"


class Strategy(JSEnum):
    LEGACYFORSALES = "legacyForSales"
    AUTOFORSALES = "autoForSales"
    MANUAL = "manual"


class Predicate(JSEnum):
    PLACEMENT_TOP = "placementTop"
    PLACEMENT_PRODUCT_PAGE = "placementProductPage"


class Adjustments(JSModel):
    predicate: Predicate
    percentage: Decimal


class Bidding(JSModel):
    strategy: Strategy
    adjustments: List[Adjustments]


class ProductCampaign(JSModel):
    portfolioId: Decimal
    campaignId: Decimal
    name: str
    tags: Dict[str, str]
    campaignType: CampaignType
    targetingType: TargetingType
    state: State
    dailyBudget: Decimal
    startDate: str
    endDate: str = None
    premiumBidAdjustment: bool
    bidding: Bidding


class ProductAdGroups(JSModel):
    adGroupId: Decimal
    name: str
    campaignId: Decimal
    defaultBid: Decimal
    state: State


class ProductAd(JSModel):
    adId: Decimal
    campaignId: Decimal
    adGroupId: Decimal
    sku: str
    asin: str
    state: State


class ProductTargeting(Targeting):
    campaignId: Decimal
