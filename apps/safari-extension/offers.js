"use strict";

function displayedSales(text) {
  const match = text.match(/^ขายได้\s*([\d,.]+)\s*(พัน|หมื่น|แสน|ล้าน|k|m)?\s*(\+)?\s*ชิ้น$/i);
  if (!match) return null;
  const units = { พัน: 1000, หมื่น: 10000, แสน: 100000, ล้าน: 1000000, k: 1000, m: 1000000 };
  return {
    sold: Math.floor(Number(match[1].replaceAll(",", "")) * (units[match[2]?.toLowerCase()] ?? 1)),
    sold_is_minimum: Boolean(match[3]),
  };
}

function visibleOffers() {
  const cards = document.querySelectorAll('main a[href*="/offer/product_offer/"]');
  const offers = new Map();
  for (const card of cards) {
    if (!card.getClientRects().length) continue;
    const offerId = new URL(card.href).pathname.match(/^\/offer\/product_offer\/([1-9]\d{0,19})$/)?.[1];
    if (!offerId) continue;
    const lines = card.innerText.split("\n").map((line) => line.trim()).filter(Boolean);
    const priceIndex = lines.findIndex((line) => line.startsWith("฿"));
    if (priceIndex < 1) continue;
    const price = (lines[priceIndex] === "฿" ? lines[priceIndex + 1] : lines[priceIndex])
      ?.match(/^฿?\s*([\d,]+(?:\.\d{1,2})?)$/);
    const sale = lines.map(displayedSales).find(Boolean);
    const rate = lines.map((line) => line.match(/^อัตราค่าคอมมิชชัน\s*([\d]+(?:\.\d{1,2})?)\s*%$/)).find(Boolean);
    if (!price || !sale || !rate) continue;
    offers.set(offerId, {
      offer_id: offerId,
      name: [...lines[priceIndex - 1]].slice(0, 300).join(""),
      price_satang: Math.round(Number(price[1].replaceAll(",", "")) * 100),
      commission_bps: Math.round(Number(rate[1]) * 100),
      ...sale,
    });
    if (offers.size === 100) break;
  }
  return [...offers.values()];
}

browser.runtime.onMessage.addListener((message, sender) => {
  if (message.action !== "visible-offers" || sender.id !== browser.runtime.id) return;
  return Promise.resolve(visibleOffers());
});
