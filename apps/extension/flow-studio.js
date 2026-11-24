"use strict";

if (location.origin === "http://127.0.0.1:3014") {
  const response = (detail) => window.dispatchEvent(
    new CustomEvent("studio:flow-response", { detail: JSON.stringify(detail) }),
  );
  const message = (action, fields) => browser.runtime.sendMessage({ action, ...fields });
  window.addEventListener("studio:flow-probe", () => response({ ready: true }));

  let reserved = null;
  document.addEventListener("click", (event) => {
    if (!event.isTrusted || location.hash !== "#storyboards") return;
    const button = event.target.closest?.("#safari-flow-storyboard[data-request-id]");
    if (!button || button.disabled || !/^[0-9a-f-]{36}$/.test(button.dataset.requestId)) return;
    const reservation = { id: button.dataset.requestId };
    reserved = reservation;
    window.setTimeout(() => {
      if (reserved === reservation) reserved = null;
    }, 20000);
  }, true);

  window.addEventListener("studio:flow-package", async (event) => {
    let data;
    try {
      data = JSON.parse(event.detail);
    } catch {
      return;
    }
    if (!reserved || data?.id !== reserved.id || location.hash !== "#storyboards") return;
    reserved = null;
    const { id } = data;
    try {
      const started = await message("studio-flow-start", { packageData: data });
      if (!started?.tabId) throw new Error(started?.error ?? "เปิดโปรเจกต์ Flow ไม่สำเร็จ");
      const deadline = Date.now() + 310000;
      while (Date.now() < deadline) {
        const update = await message("studio-flow-status", { id, tabId: started.tabId });
        if (update?.result || update?.error) {
          response({ id, ...update });
          return;
        }
        if (update?.status) response({ id, status: update.status });
        await new Promise((resolve) => window.setTimeout(resolve, 1500));
      }
      throw new Error("หมดเวลารอ Flow ตรวจแท็บ Flow ก่อนเริ่มใหม่");
    } catch (error) {
      response({ id, error: error.message || "ติดต่อ Safari ไม่สำเร็จ" });
    }
  });
}
