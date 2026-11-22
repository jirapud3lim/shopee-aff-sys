# Shopee Affiliate Open API (Thailand)

Source: [Shopee's official API catalog](https://affiliate.shopee.co.th/open_api/list). The operations below were reviewed in the Thai portal. The project currently configures `https://open-api.affiliate.shopee.co.th/graphql` as its GraphQL endpoint. Account authorization, request execution, and quotas still need live verification.

| Priority | Operation | Studio use |
| --- | --- | --- |
| First | [`productOfferV2`](https://affiliate.shopee.co.th/open_api/list?type=product_offer) | Search offers by keyword, shop ID, or item ID. Use product and offer URLs, price range, commission rate, sales count, and image URL to review candidates before import. |
| First | [`generateShortLink`](https://affiliate.shopee.co.th/open_api/list?type=short_link) | Generate an affiliate URL from `originUrl`. Optional `subIds` can identify a channel or Reel for reporting. |
| After publishing | [`conversionReport`](https://affiliate.shopee.co.th/open_api/list?type=conversion_report) | Retrieve orders in a purchase-time window, with status and commission fields. |
| After publishing | [`validatedReport`](https://affiliate.shopee.co.th/open_api/list?type=validation_report) | Reconcile validated commissions using `validationId`. |
| Bulk import | [Product Feed Offer List](https://affiliate.shopee.co.th/open_api/list?type=product_feed_offer) and [`getItemFeedData`](https://affiliate.shopee.co.th/open_api/list?type=product_feed_offer_detail) | Select a feed and retrieve its items. |
| Campaigns | [`shopeeOfferV2`](https://affiliate.shopee.co.th/open_api/list?type=shopee_offer) and [`shopOfferV2`](https://affiliate.shopee.co.th/open_api/list?type=brand_offer) | Find platform campaigns and shop-specific offers. |

Report cursors are single-use and expire after 30 seconds according to the portal. Keep manual entry and CSV import available. Record permission to reuse product imagery before rendering.
