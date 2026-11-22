"use strict";

const studioOrigin = "http://127.0.0.1:3014";
let current = null;

async function collectOffers() {
  const tabs = await browser.tabs.query({ url: "https://affiliate.shopee.co.th/offer/product_offer*" });
  const offerList = tabs.filter((tab) => new URL(tab.url).pathname === "/offer/product_offer");
  offerList.sort((left, right) => Number(right.active) - Number(left.active) ||
    (right.lastAccessed ?? 0) - (left.lastAccessed ?? 0));
  for (const tab of offerList) {
    const offers = await browser.tabs.sendMessage(tab.id, { action: "visible-offers" }).catch(() => null);
    if (offers?.length) return { offers };
  }
  return { error: "เปิดผลค้นหาในหน้า Affiliate ข้อเสนอผลิตภัณฑ์ใน Safari และอนุญาตให้ส่วนขยายอ่านหน้านี้" };
}

browser.runtime.onMessage.addListener((message, sender) => {
  if (message.action !== "collect-offers" || sender.id !== browser.runtime.id ||
      !sender.url?.startsWith(studioOrigin + "/") || !/^[0-9a-f-]{36}$/.test(message.id)) return;
  if (current) return Promise.resolve({ error: "Safari กำลังเก็บข้อมูลอีกรายการ" });
  current = collectOffers()
    .catch(() => ({ error: "อ่านข้อเสนอสินค้าจาก Safari ไม่สำเร็จ" }))
    .finally(() => { current = null; });
  return current;
});
