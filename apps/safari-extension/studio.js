"use strict";

if (location.origin === "http://127.0.0.1:3014") {
  const notify = (detail) => window.dispatchEvent(new CustomEvent("studio:capture-response", {
    detail: JSON.stringify(detail),
  }));
  window.addEventListener("studio:capture-probe", () => notify({ ready: true }));
  let running = false;
  // The page keeps its Studio session token. Only the actual button click starts Safari collection.
  document.addEventListener("click", async (event) => {
    const hash = location.hash;
    const offers = hash === "#shopee-offers";
    if (!offers && hash !== "#purchase-previews") return;
    const selector = offers ? "#safari-offer-capture" : "#safari-purchase-capture";
    const button = event.target.closest?.(selector + "[data-request-id]");
    if (!event.isTrusted || !button || running) return;
    const id = button.dataset.requestId;
    if (!/^[0-9a-f-]{36}$/.test(id)) return;
    running = true;
    notify({ id, started: true });
    try {
      const result = await browser.runtime.sendMessage({ action: offers ? "collect-offers" : "collect", id });
      notify({ id, ...result });
    } catch {
      notify({ id, error: "ติดต่อส่วนขยาย Safari ไม่สำเร็จ" });
    } finally {
      running = false;
    }
  }, true);
}

if (location.origin === "http://127.0.0.1:3014") {
  window.addEventListener("studio:affiliate-probe", () => window.dispatchEvent(new Event("studio:affiliate-ready")));
  for (const action of ["affiliate-start", "affiliate-status"]) {
    window.addEventListener(`studio:${action}`, async (event) => {
      if (location.hash !== "#affiliate-links" || typeof event.detail !== "string") return;
      let data;
      try { data = JSON.parse(event.detail); } catch { return; }
      if (!/^[0-9a-f-]{36}$/.test(data?.id)) return;
      const response = await browser.runtime.sendMessage({ ...data, action })
        .catch(() => ({ error: "ติดต่อส่วนขยาย Safari ไม่สำเร็จ" }));
      window.dispatchEvent(new CustomEvent("studio:affiliate-response", {
        detail: JSON.stringify({ ...response, id: data.id }),
      }));
    });
  }
}
