"use strict";

const portal = "https://affiliate.shopee.co.th";
const offerPath = /^\/offer\/product_offer\/([1-9]\d{0,19})\/?$/;
const listingPattern = /^https:\/\/shopee\.co\.th\/product\/\d+\/\d+$/;
const shortPattern = /^https:\/\/s\.shopee\.co\.th\/[a-zA-Z0-9]+\/?$/;
let job;

function affiliateSource(offerId) {
  if (location.pathname.match(offerPath)?.[1] !== offerId) return null;
  for (const link of document.querySelectorAll('a[href]')) {
    if (link.innerText.trim() !== "ดูสินค้า" || !link.getClientRects().length) continue;
    try {
      const url = new URL(link.href);
      if (url.protocol !== "https:" || !["shopee.co.th", "www.shopee.co.th"].includes(url.host) ||
          url.username || url.password) continue;
      const parts = url.pathname.match(/^\/product\/(\d+)\/(\d+)\/?$/) ??
        url.pathname.match(/-i\.(\d+)\.(\d+)\/?$/);
      if (parts?.[2] === offerId) return { source: `https://shopee.co.th/product/${parts[1]}/${parts[2]}` };
    } catch {
      // No verified listing on this link.
    }
  }
  return null;
}

function formFields() {
  const visible = (element) => !element.disabled && element.getClientRects().length;
  const source = [...document.querySelectorAll("textarea")].find((input) => visible(input) &&
    input.placeholder.includes("5") && input.placeholder.includes("ลิงก์"));
  const sub = [...document.querySelectorAll('input[placeholder]')].find((input) => visible(input) &&
    input.placeholder.includes("SportShoes"));
  const submit = [...document.querySelectorAll("button")].find((button) => visible(button) &&
    /^(เอา\s*ลิงก์|รับ\s*ลิงก์)$/.test(button.innerText.trim()));
  return source && sub && submit ? { source, sub, submit } : null;
}

function writeInput(input, value) {
  const native = input instanceof HTMLTextAreaElement ? HTMLTextAreaElement : HTMLInputElement;
  Object.getOwnPropertyDescriptor(native.prototype, "value").set.call(input, value);
  input.dispatchEvent(new Event("input", { bubbles: true }));
  input.dispatchEvent(new Event("change", { bubbles: true }));
}

function startAffiliate(message) {
  if (location.pathname !== "/offer/custom_link" || !listingPattern.test(message.source) ||
      !/^[a-zA-Z0-9]{1,100}$/.test(message.subId)) return null;
  if (job) return job.id === message.id ? { ready: true } : null;
  const fields = formFields();
  if (!fields) return null;
  writeInput(fields.source, message.source);
  writeInput(fields.sub, message.subId);
  job = { id: message.id, approved: false, error: "" };
  document.addEventListener("click", (event) => {
    if (!event.isTrusted || !event.target.closest("button")?.isSameNode(fields.submit)) return;
    if (fields.source.value.trim() !== message.source || fields.sub.value !== message.subId) {
      job.error = "ข้อมูลสินค้าและ Sub ID ใน Shopee ถูกเปลี่ยน กรุณาเริ่มใหม่จาก Studio";
      return;
    }
    job.approved = true;
  }, true);
  fields.submit.scrollIntoView({ block: "end" });
  return { ready: true };
}

function affiliateResult(id) {
  if (!job || job.id !== id) return { error: "เปิดหน้าเครื่องมือ Shopee ใหม่จาก Studio แล้วลองอีกครั้ง" };
  if (job.error) return { error: job.error };
  if (!job.approved) return { pending: true };
  const copy = [...document.querySelectorAll("button")].find((button) => !button.disabled &&
    button.getClientRects().length && button.innerText.trim() === "คัดลอกลิงก์");
  for (let parent = copy?.parentElement; parent && parent !== document.body; parent = parent.parentElement) {
    if (!parent.innerText.includes("กรุณาคัดลอกลิงก์สั้น")) continue;
    const links = [...parent.querySelectorAll("textarea,input,a[href]")]
      .filter((field) => field.getClientRects().length)
      .map((field) => (field.value || field.href || "").trim())
      .filter((value) => shortPattern.test(value));
    if (links.length === 1) return { affiliate_url: links[0] };
    break;
  }
  return { pending: true };
}

browser.runtime.onMessage.addListener((message, sender) => {
  if (sender.id !== browser.runtime.id || location.origin !== portal) return;
  if (message.action === "affiliate-source") return Promise.resolve(affiliateSource(message.model));
  if (message.action === "affiliate-fill") return Promise.resolve(startAffiliate(message));
  if (message.action === "affiliate-result") return Promise.resolve(affiliateResult(message.id));
});
