"use strict";

const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));
const publishers = {
  "www.potterscookshop.co.uk": "/cdn/shop/files/",
  "cdn.hstatic.net": "/products/",
  "www.electronic4you.at": "/media/catalog/product/",
  "assets.4flow.cloud": "/WBF",
  "vc3i.rweb-images.com": "/www.light-and-bath.com/images/catalog_images/",
};

function publisherImage(value) {
  try {
    const url = new URL(value);
    const prefix = publishers[url.hostname];
    if (url.protocol !== "https:" || !prefix || !url.pathname.startsWith(prefix) ||
        url.username || url.password || (url.port && url.port !== "443")) return null;
    url.hash = "";
    return url.href;
  } catch { return null; }
}

function describesModel(element, model, url) {
  const label = [element.getAttribute("alt"), element.getAttribute("title"),
    element.getAttribute("aria-label"), element.parentElement?.innerText,
    element.parentElement?.parentElement?.innerText, url].join(" ").slice(0, 3500);
  return label.toLowerCase().includes(model.toLowerCase());
}

function imageLinks(context, model) {
  const links = [...context.querySelectorAll("a[href]")].map((anchor) => {
    try {
      const url = new URL(anchor.href);
      const original = url.searchParams.get("imgurl");
      return url.origin === location.origin && url.pathname === "/imgres" &&
        describesModel(anchor, model, url.searchParams.get("imgrefurl") ?? original) ? original : null;
    } catch { return null; }
  });
  const originals = [...context.querySelectorAll("img")].filter((image) => image.getClientRects().length > 0 &&
    describesModel(image, model, image.currentSrc || image.src))
    .flatMap((image) => [image.getAttribute("data-iurl"), image.currentSrc, image.src]);
  return [...new Set([...links, ...originals].map(publisherImage).filter(Boolean))];
}

async function collectImages(expected, model) {
  if (location.pathname !== "/search" || !model || new URL(expected).searchParams.get("q") !==
      new URL(location.href).searchParams.get("q")) return null;
  if (document.querySelector("form#captcha-form") || /\/sorry(\/|$)/.test(location.pathname)) {
    return { blocked: true };
  }
  const found = new Set(imageLinks(document, model));
  const thumbnails = [...document.querySelectorAll("#search img, #rso img, img")].filter((image) => {
    const rect = image.getBoundingClientRect();
    return rect.width >= 65 && rect.height >= 50 && image.alt && rect.top < 2500 &&
      image.closest("a, button, [role=button], [role=link], [data-ri]");
  }).slice(0, 16);
  for (const thumbnail of thumbnails) {
    if (found.size >= 4) break;
    const control = thumbnail.closest("[role=button], [role=link], button, a, [data-ri]");
    const link = thumbnail.closest("a[href]");
    // Google image previews can open in place. Refuse external links in this step.
    if (!control || (link && new URL(link.href).origin !== location.origin)) continue;
    thumbnail.click();
    await sleep(480);
    if (location.pathname !== "/search") break;
    imageLinks(document, model).forEach((url) => found.add(url));
  }
  return { images: [...found].slice(0, 5) };
}

browser.runtime.onMessage.addListener((message, sender) => {
  if (sender.id === browser.runtime.id && message.action === "images") {
    return collectImages(message.expected, message.model);
  }
});
