"use strict";

const studioOrigin = "http://127.0.0.1:3014";
const purchaseURL = "https://shopee.co.th/user/purchase/";
const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));
let current = null;

function googleImages(query) {
  return "https://www.google.com/search?" + new URLSearchParams({ q: query, tbm: "isch", hl: "th" });
}

async function observe(tabId, action, waitMs = 4100, expected, model) {
  const until = Date.now() + waitMs;
  do {
    try {
      const tab = await browser.tabs.get(tabId);
      if (action === "images" && /^https:\/\/www\.google\.(?:com|co\.th)\/sorry\//.test(tab.url ?? "")) {
        return { blocked: true };
      }
      const result = await browser.tabs.sendMessage(tabId, { action, expected, model });
      if (result) return result;
    } catch {
      // A new page has not loaded its content script yet.
    }
    await sleep(320);
  } while (Date.now() < until);
  return null;
}

async function navigate(tabId, url, action, waitMs, model) {
  await browser.tabs.update(tabId, { url });
  await sleep(650);
  return observe(tabId, action, waitMs, url, model);
}

async function collect() {
  const tab = await browser.tabs.create({ url: purchaseURL, active: false });
  const seen = new Set();
  const deadline = Date.now() + 145000;
  let foundHome = false;
  try {
    const orders = await observe(tab.id, "completed", 9500);
    if (!orders?.length) return { error: "ไม่พบรายการซื้อสำเร็จ ตรวจการเข้าสู่ระบบ Shopee และสิทธิ์ Safari" };
    for (const order of orders) {
      if (Date.now() > deadline) break;
      const productUrls = await navigate(tab.id, order, "order");
      for (const productUrl of productUrls ?? []) {
        if (Date.now() > deadline || seen.has(productUrl)) continue;
        seen.add(productUrl);
        const product = await navigate(tab.id, productUrl, "listing");
        if (!product?.home || !product.photos?.length || product.product_url !== productUrl) continue;
        foundHome = true;
        const model = product.name.match(/\b[A-Z]{1,6}\d{2,8}[A-Z0-9]{0,8}\b/i)?.[0];
        if (!model) continue;
        const terms = product.name.replace(/Pre-order/gi, "").slice(0, 100);
        const first = await navigate(tab.id, googleImages(terms), "images", 6000, model);
        if (first?.blocked) return { error: "Google ขอให้ยืนยันใน Safari ก่อนค้นภาพ" };
        const results = new Set(first?.images ?? []);
        if (results.size < 2) {
          const query = terms + " site:light-and-bath.com OR site:potterscookshop.co.uk OR site:smeg.vn OR site:electronic4you.at";
          const second = await navigate(tab.id, googleImages(query), "images", 5600, model);
          if (second?.blocked) return { error: "Google ขอให้ยืนยันใน Safari ก่อนค้นภาพ" };
          second?.images?.forEach((url) => results.add(url));
        }
        if (results.size < 2) continue;
        return { purchase: {
          name: product.name, product_url: product.product_url, shopee_image: product.photos[0],
          search_images: [...results].slice(0, 2), purchase_confirmed: true,
          purchase_source: "shopee_completed", search_source: "google_images",
        }};
      }
    }
    return { error: foundHome ? "พบของใช้ในบ้าน แต่ยังเก็บภาพจากแหล่งที่รองรับได้ไม่ครบ" :
      "ยังไม่พบของใช้ในบ้านที่ตรวจสถานะซื้อสำเร็จได้ในรอบนี้" };
  } finally {
    await browser.tabs.remove(tab.id).catch(() => {});
  }
}

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
  if (!["collect", "collect-offers"].includes(message.action) || sender.id !== browser.runtime.id ||
      !sender.url?.startsWith(studioOrigin + "/") || !/^[0-9a-f-]{36}$/.test(message.id)) return;
  if (current) return Promise.resolve({ error: "Safari กำลังเก็บข้อมูลอีกรายการ" });
  const offers = message.action === "collect-offers";
  current = (offers ? collectOffers() : collect()).catch(() => ({
    error: offers ? "อ่านข้อเสนอสินค้าจาก Safari ไม่สำเร็จ" : "Safari เปิดหน้าประวัติซื้อหรือค้นภาพไม่สำเร็จ",
  }))
    .finally(() => { current = null; });
  return current;
});

const flowOrigin = "https://flow.google.com";
const flowTarget = /^\/project\/[a-f0-9-]{36}(?:\/collection\/[a-f0-9-]{36})?\/?$/;

async function startFlow(packageData) {
  let target;
  try {
    target = new URL(packageData?.url);
    if (target.origin !== flowOrigin || !flowTarget.test(target.pathname) ||
        target.search || target.hash || target.username || target.password) throw new Error();
  } catch {
    return { error: "ใช้ URL หน้าโปรเจกต์หรือคอลเลกชัน Flow" };
  }

  const tab = await browser.tabs.create({ url: target.href, active: true });
  const ready = await observe(tab.id, "flow-probe", 14000);
  if (!ready?.ready) return { error: "เปิด Flow แล้ว แต่ Safari ยังเข้าไม่ถึงส่วนขยาย ตรวจการเข้าสู่ระบบและสิทธิ์สำหรับ flow.google.com" };
  const result = await browser.tabs.sendMessage(tab.id, { action: "flow-run", packageData });
  if (!result?.started) return { error: result?.error ?? "เริ่มงานในโปรเจกต์ Flow ไม่สำเร็จ" };
  return { tabId: tab.id };
}

browser.runtime.onMessage.addListener((message, sender) => {
  if (!["studio-flow-start", "studio-flow-status"].includes(message.action) ||
      sender.id !== browser.runtime.id || !sender.url?.startsWith(studioOrigin + "/")) return;
  if (message.action === "studio-flow-start") {
    return startFlow(message.packageData).catch(() => ({ error: "ส่งงานไป Flow ใน Safari ไม่สำเร็จ" }));
  }
  if (!Number.isInteger(message.tabId) || !/^[0-9a-f-]{36}$/.test(message.id)) return;
  return browser.tabs.get(message.tabId).then((tab) => {
    if (!tab.url?.startsWith(flowOrigin + "/project/")) return { error: "แท็บออกจากหน้าโปรเจกต์ Flow" };
    return browser.tabs.sendMessage(message.tabId, { action: "flow-status", id: message.id });
  }).catch(() => ({ error: "ติดต่อแท็บงาน Flow ไม่สำเร็จ กรุณาตรวจผลใน Flow ก่อนเริ่มงานใหม่" }));
});

const affiliateOrigin = "https://affiliate.shopee.co.th";
const affiliateJobs = new Map();
const affiliateListing = /^https:\/\/shopee\.co\.th\/product\/\d+\/\d+$/;

async function openAffiliate(message, sender) {
  const { id, offerId, subId } = message;
  const listing = message.source;
  if (!/^[a-zA-Z0-9]{1,100}$/.test(subId) ||
      !(offerId ? /^[1-9]\d{0,19}$/.test(offerId) : affiliateListing.test(listing ?? ""))) {
    return { error: "ข้อมูลสินค้าหรือ Sub ID ไม่ถูกต้อง" };
  }
  const toolUrl = affiliateOrigin + "/offer/custom_link";
  const tab = await browser.tabs.create({
    url: offerId ? affiliateOrigin + "/offer/product_offer/" + offerId : toolUrl,
    active: true,
  });
  let source = listing;
  if (offerId) {
    const observed = await observe(tab.id, "affiliate-source", 9500, undefined, offerId);
    source = observed?.source;
    if (!affiliateListing.test(source ?? "") || source.split("/").at(-1) !== offerId) {
      return { error: "ยังอ่าน URL สินค้าจากข้อเสนอไม่ได้ ตรวจการเข้าสู่ระบบและสิทธิ์ Safari หรือกรอก URL เอง" };
    }
    await browser.tabs.update(tab.id, { url: toolUrl });
  }
  const deadline = Date.now() + 9000;
  do {
    const result = await browser.tabs.sendMessage(tab.id, { action: "affiliate-fill", id, source, subId }).catch(() => null);
    if (result?.ready) {
      affiliateJobs.set(tab.id, { id, source, senderId: sender.tab?.id });
      setTimeout(() => affiliateJobs.delete(tab.id), 125_000);
      return { tabId: tab.id };
    }
    await sleep(300);
  } while (Date.now() < deadline);
  return { error: "Safari ยังเตรียมฟอร์ม Shopee ไม่สำเร็จ ตรวจการเข้าสู่ระบบและสิทธิ์ส่วนขยาย" };
}

async function readAffiliate(message, sender) {
  const job = affiliateJobs.get(message.tabId);
  if (!job || job.id !== message.id || job.senderId !== sender.tab?.id) {
    return { error: "เซสชันสร้างลิงก์หมดอายุ กรุณาเริ่มจาก Studio อีกครั้ง" };
  }
  const tab = await browser.tabs.get(message.tabId);
  if (new URL(tab.url).origin !== affiliateOrigin || new URL(tab.url).pathname !== "/offer/custom_link") {
    return { error: "แท็บ Safari ออกจากเครื่องมือสร้างลิงก์ Shopee" };
  }
  const result = await browser.tabs.sendMessage(tab.id, { action: "affiliate-result", id: job.id });
  if (result?.affiliate_url) {
    if (!/^https:\/\/s\.shopee\.co\.th\/[a-zA-Z0-9]+\/?$/.test(result.affiliate_url)) {
      return { error: "Shopee ไม่ได้ส่งลิงก์สั้นในรูปแบบที่รองรับ" };
    }
    return { source: job.source, affiliate_url: result.affiliate_url };
  }
  return result ?? { pending: true };
}

browser.runtime.onMessage.addListener((message, sender) => {
  if (!["affiliate-start", "affiliate-status"].includes(message.action) ||
      sender.id !== browser.runtime.id || !sender.url?.startsWith(studioOrigin + "/") ||
      !/^[0-9a-f-]{36}$/.test(message.id)) return;
  const action = message.action === "affiliate-start" ? openAffiliate : readAffiliate;
  return action(message, sender).catch(() => ({ error: "ติดต่อหน้าสร้างลิงก์ Shopee ใน Safari ไม่สำเร็จ" }));
});
