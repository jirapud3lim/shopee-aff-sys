"use strict";

if (location.origin === "http://127.0.0.1:3014") {
  const notify = (detail) => window.dispatchEvent(new CustomEvent("studio:capture-response", {
    detail: JSON.stringify(detail),
  }));
  let running = false;
  // The page keeps its Studio session token. Only the actual button click starts Safari collection.
  document.addEventListener("click", async (event) => {
    const button = event.target.closest?.("#safari-offer-capture[data-request-id]");
    if (!event.isTrusted || !button || running || location.hash !== "#shopee-offers") return;
    const id = button.dataset.requestId;
    if (!/^[0-9a-f-]{36}$/.test(id)) return;
    running = true;
    notify({ id, started: true });
    try {
      const result = await browser.runtime.sendMessage({ action: "collect-offers", id });
      notify({ id, ...result });
    } catch {
      notify({ id, error: "ติดต่อส่วนขยาย Safari ไม่สำเร็จ" });
    } finally {
      running = false;
    }
  }, true);
}
