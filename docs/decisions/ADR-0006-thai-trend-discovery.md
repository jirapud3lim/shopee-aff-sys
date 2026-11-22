# ADR-0006 — Thai trend discovery

**Status:** Accepted

**Date:** 2026-11-22

## Decision

Use Google's [Trending Now RSS export](https://support.google.com/trends/answer/3076011) for Thailand. Keep the public feed in a short-lived process cache, display its fetch time, and label the last available result when a refresh fails. Calculate matches per workspace against its saved Shopee product names using local Thai and Latin tokenization. Show the matching terms and let the operator open the product or check a phrase manually.

## Consequences

The Trending Now feed supplies a limited set of current queries and approximate search volumes. The feed has no category field. The matching uses title relevance and requires no external product or AI API. Manual keyword matching remains available during a feed outage.
