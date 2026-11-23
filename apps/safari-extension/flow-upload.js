"use strict";

// Runs in Flow's page world so its own short-lived file input can receive the approved File.
window.addEventListener("affiliate-studio-flow-select-file", (event) => {
  let asset;
  try {
    asset = JSON.parse(event.detail);
  } catch {
    return;
  }
  if (!/^studio-[0-9a-f]{8}-(?:product|presenter)\.(?:jpg|png|webp)$/.test(asset?.name) ||
      typeof asset.data !== "string" || asset.data.length > 16_777_248) return;
  const match = /^data:(image\/(?:jpeg|png|webp));base64,([A-Za-z0-9+/=]+)$/.exec(asset.data);
  const upload = [...document.querySelectorAll("flow-add-menu-side-nav button")].find((button) =>
    button.getClientRects().length && /(?:อัปโหลดสื่อ|Upload media)/i.test(button.textContent));
  if (!match || !upload) return;

  const [, type, contents] = match;
  const binary = atob(contents);
  const bytes = Uint8Array.from(binary, (value) => value.charCodeAt(0));
  const input = HTMLInputElement.prototype;
  const originalClick = input.click;
  const originalPicker = input.showPicker;
  let selected = false;
  function supplyFile(original, ...args) {
    if (this.type !== "file" || selected) return original?.apply(this, args);
    const transfer = new DataTransfer();
    transfer.items.add(new File([bytes], asset.name, { type }));
    this.files = transfer.files;
    selected = true;
    queueMicrotask(() => {
      this.dispatchEvent(new Event("change", { bubbles: true }));
    });
  }
  // Flow creates a detached input as part of the Upload media click.
  try {
    input.click = function (...args) { return supplyFile.call(this, originalClick, ...args); };
    if (originalPicker) {
      input.showPicker = function (...args) { return supplyFile.call(this, originalPicker, ...args); };
    }
    upload.click();
  } finally {
    input.click = originalClick;
    if (originalPicker) input.showPicker = originalPicker;
  }
  window.dispatchEvent(new CustomEvent("affiliate-studio-flow-file-selected", {
    detail: JSON.stringify({ name: asset.name, selected }),
  }));
});
