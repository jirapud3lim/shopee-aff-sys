"use strict";

const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));
const clean = (value) => (value ?? "").replace(/\s+/g, " ").trim();

function productLink(value) {
  try {
    const url = new URL(value, location.origin);
    if (url.origin !== "https://shopee.co.th") return null;
    const match = url.pathname.match(/^\/product\/(\d{1,20})\/(\d{1,20})\/?$/) ??
      url.pathname.match(/-i\.(\d{1,20})\.(\d{1,20})\/?$/);
    return match ? `https://shopee.co.th/product/${match[1]}/${match[2]}` : null;
  } catch { return null; }
}

function shopeePhoto(value) {
  try {
    const url = new URL(value);
    if (url.origin !== "https://down-th.img.susercontent.com") return null;
    const file = url.pathname.match(/^\/file\/([\w-]+)(?:@[^/]+)?$/)?.[1];
    // This common overlay is the store promotion badge rather than a product photo.
    if (!file || file === "th-11134258-7r98z-lza9f5c8o71l63") return null;
    return url.origin + "/file/" + file;
  } catch { return null; }
}

function orderLinks() {
  return [...new Set([...document.querySelectorAll("a[href]")]
    .map((anchor) => anchor.href)
    .filter((href) => /^https:\/\/shopee\.co\.th\/user\/purchase\/order\/\d+\/?(?:\?.*)?$/.test(href)))];
}

function productLinks() {
  return [...new Set([...document.querySelectorAll("a[href]")].map((a) => productLink(a.href)).filter(Boolean))];
}

async function completedOrders() {
  if (location.pathname.replace(/\/$/, "") !== "/user/purchase") return null;
  const tab = [...document.querySelectorAll("a, button, [role=tab]")].find((item) =>
    ["สำเร็จแล้ว", "completed"].includes(clean(item.textContent).toLowerCase()) && item.getClientRects().length);
  if (!tab) return null;
  const selected = () => tab.getAttribute("aria-selected") === "true" ||
    /^(?:page|true)$/.test(tab.getAttribute("aria-current") ?? "") ||
    /(?:--active|--selected|\bactive\b|\bselected\b)/.test(tab.className);
  // Shopee versions without an ARIA selection marker still have an explicit Completed control.
  // Wait for its result, and each order is checked again on the detail page.
  if (!selected()) {
    tab.click();
    await sleep(1050);
  }
  const orders = new Set(orderLinks());
  for (let page = 0; page < 4 && orders.size < 24; page++) {
    window.scrollTo(0, document.documentElement.scrollHeight);
    await sleep(700);
    orderLinks().forEach((href) => orders.add(href));
  }
  return [...orders].slice(0, 24);
}

function completedProducts() {
  if (!/^\/user\/purchase\/order\/\d+\/?$/.test(location.pathname)) return null;
  const state = clean(document.body.innerText);
  if (!/พัสดุถูกจัดส่งสำเร็จแล้ว|คำสั่งซื้อสำเร็จ|คำสั่งซื้อเสร็จสมบูรณ์|order completed|delivered successfully/i.test(state)) return null;
  if (/คำสั่งซื้อนี้ถูกยกเลิก|คำสั่งซื้อถูกยกเลิก|order has been cancelled/i.test(state)) return null;
  return productLinks().slice(0, 5);
}

function listing() {
  const product_url = productLink(location.href);
  if (!product_url) return null;
  const heading = [...document.querySelectorAll("h1")].find((item) => item.getClientRects().length);
  if (!heading) return null;
  const name = clean(heading.textContent).slice(0, 140);
  const family = /เครื่องใช้ในบ้าน|ห้องครัว|ห้องน้ำ|เครื่องครัว|ของใช้ในบ้าน|Kitchenware|Home & Living/i;
  const home = [...document.querySelectorAll("a[href]")].slice(0, 100)
    .some((anchor) => anchor.getClientRects().length && family.test(clean(anchor.textContent)));
  if (!name || !home) return { product_url, home: false };
  const photos = [...document.querySelectorAll("img")].filter((image) => {
    const { width, height, top } = image.getBoundingClientRect();
    return ((width >= 58 && height >= 58) || image.naturalWidth >= 600) &&
      top < 1300 && top > -700 && !/logo|avatar|banner|badge|icon/i.test(image.alt);
  }).sort((a, b) => Number(b.alt.includes(name)) - Number(a.alt.includes(name))
      || b.naturalWidth - a.naturalWidth)
    .map((image) => shopeePhoto(image.currentSrc || image.src)).filter(Boolean);
  return { product_url, name, home, photos: [...new Set(photos)].slice(0, 6) };
}

browser.runtime.onMessage.addListener((message, sender) => {
  if (sender.id !== browser.runtime.id) return;
  if (message.action === "completed") return completedOrders();
  if (message.action === "order" && new URL(message.expected).pathname === location.pathname) {
    return Promise.resolve(completedProducts());
  }
  if (message.action === "listing") return Promise.resolve(listing());
});
