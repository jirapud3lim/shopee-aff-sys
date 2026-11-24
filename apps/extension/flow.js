"use strict";

(() => {
  const labels = {
    agent: ["Agent จาก Flow", "Flow Agent"],
    close: ["ปิด", "Close"],
    settings: ["ทริกเกอร์การตั้งค่า", "Settings trigger"],
    editor: ["คุณต้องการสร้างอะไร", "What do you want to create?"],
    image: ["รูปภาพ", "Image"],
    ingredient: ["องค์ประกอบ", "Ingredient"],
    generate: ["เริ่มสร้าง", "Generate", "Create"],
    preview: ["มุมมองรูปภาพแบบอ่านอย่างเดียว", "Read-only image view"],
  };
  const mimeTypes = new Set(["image/jpeg", "image/png", "image/webp"]);
  const maxImageBytes = 12 * 1024 * 1024;
  const pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  let job = null;

  function visible(element) {
    return element.getClientRects().length > 0 && !element.closest("[hidden],[inert]");
  }

  function label(element) {
    const explicit = element.getAttribute("aria-label") ?? element.getAttribute("alt");
    if (explicit) return explicit.trim();
    const copy = element.cloneNode(true);
    copy.querySelectorAll('[aria-hidden="true"],[role="img"],img,i,svg,mat-icon,flow-icon')
      .forEach((icon) => icon.remove());
    return copy.textContent.trim().replace(/\s+/g, " ");
  }

  function all(selector, names = [], scope = document) {
    return [...scope.querySelectorAll(selector)].filter((element) => visible(element) &&
      (!names.length || names.includes(label(element))));
  }

  function one(selector, names) {
    const candidates = all(selector, names);
    return candidates.length === 1 ? candidates[0] : null;
  }

  async function waitFor(check, message, timeout = 12000) {
    const deadline = Date.now() + timeout;
    do {
      const result = check();
      if (result) return result;
      await pause(300);
    } while (Date.now() < deadline);
    throw new Error(message);
  }

  function requireClick(selector, names, message) {
    const element = one(selector, names);
    if (!element || element.disabled) throw new Error(message);
    element.click();
    return element;
  }

  async function setImageMode() {
    const agent = one("button[aria-pressed]", labels.agent);
    if (!agent) {
      const sideClose = one("button[aria-label]", labels.close);
      if (sideClose && one("button[aria-label]", ["การตั้งค่า Agent", "Agent settings"])) {
        sideClose.click();
      }
    }
    const toggle = await waitFor(() => one("button[aria-pressed]", labels.agent), "ไม่พบปุ่มสลับ Flow Agent");
    if (toggle.getAttribute("aria-pressed") === "true") toggle.click();
    const settings = await waitFor(() => one("button[aria-label]", labels.settings), "ไม่พบการตั้งค่า Image ใน Flow");
    settings.click();
    for (const name of [labels.image, ["9:16"], ["x1"]]) {
      const radio = await waitFor(() => one('[role="radio"]', name), "ตรวจการตั้งค่าภาพใน Flow ไม่สำเร็จ");
      if (radio.getAttribute("aria-checked") !== "true") radio.click();
      await waitFor(() => one('[role="radio"]', name)?.getAttribute("aria-checked") === "true",
        "Flow ไม่ยืนยันโหมด Image, 9:16 และ x1");
    }
    settings.click();
  }

  function assertImageMode() {
    const settings = one("button[aria-label]", labels.settings);
    const model = settings?.textContent ?? "";
    if (!/Nano Banana|Imagen/i.test(model) || !model.includes("crop_9_16") ||
        !/\bx1\b/.test(model) || /วิดีโอ|video/i.test(model) ||
        one("button[aria-pressed]", labels.agent)?.getAttribute("aria-pressed") !== "false") {
      throw new Error("หยุดก่อนส่งคำสั่ง เพราะยืนยันโหมด Image 9:16 หนึ่งภาพใน Flow ไม่ได้");
    }
  }

  async function attach(composer, asset, index, id) {
    const type = /^data:(image\/(?:jpeg|png|webp));base64,/.exec(asset.data)?.[1];
    if (!type) throw new Error("ไฟล์อ้างอิงใน Studio ไม่ใช่ภาพที่รองรับ");
    const extension = { "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp" }[type];
    const name = `studio-${id.slice(0, 8)}-${index === 0 ? "product" : "presenter"}.${extension}`;
    requireClick("button[aria-label]", ["เพิ่มองค์ประกอบลงในช่องพรอมต์", "Add ingredients to prompt"],
      "ไม่พบตัวเลือกเพิ่มรูปอ้างอิงใน Flow");
    await waitFor(() => all("flow-add-menu-side-nav button").some((button) =>
      /อัปโหลดสื่อ|Upload media/i.test(button.textContent)), "ไม่พบปุ่มอัปโหลดรูปใน Flow");
    let response;
    function onSelected(event) {
      const result = JSON.parse(event.detail);
      if (result.name === name) response = result;
    }
    window.addEventListener("affiliate-studio-flow-file-selected", onSelected);
    try {
      window.dispatchEvent(new CustomEvent("affiliate-studio-flow-select-file", {
        detail: JSON.stringify({ name, data: asset.data }),
      }));
      await waitFor(() => response, "Safari ไม่ตอบรับการส่งไฟล์ผ่านตัวเลือก Upload media", 4000);
    } finally {
      window.removeEventListener("affiliate-studio-flow-file-selected", onSelected);
    }
    if (!response.selected) throw new Error("Flow ไม่ได้เปิดตัวเลือกรับไฟล์ภาพ");

    const option = await waitFor(() => all('[role="option"]').find((item) => {
      const title = label(item);
      return title.includes(name) && !/กำลังอัปโหลด|Uploading/i.test(title) &&
        !item.querySelector('[role="progressbar"]');
    }), "Flow ยังอัปโหลดรูปไม่สำเร็จ ตรวจข้อความในแท็บ Flow", 25000);
    option.click();
    requireClick("button", ["เพิ่มไปยังพรอมต์", "Add to prompt"], "Flow ยังไม่พร้อมเพิ่มรูปที่อัปโหลดไปในพรอมป์");
    await waitFor(() => {
      const ingredients = all("button[aria-label]", labels.ingredient, composer);
      return ingredients.length === index + 1 && ingredients.every((button) => {
        const thumbnail = button.querySelector("img");
        return thumbnail?.complete && thumbnail.naturalWidth > 0;
      });
    }, "Flow ยังไม่ได้แนบรูปอ้างอิงครบ", 20000);
  }

  function gallery() {
    return all('flow-grid-tile-container[role="group"]').flatMap((card) => {
      const image = [...card.querySelectorAll("img")].find((img) =>
        /การ์ดแสดงรูปภาพ|image card/i.test(img.alt) && img.complete && img.naturalWidth &&
        img.currentSrc.startsWith(location.origin + "/"));
      return image ? [{ card, src: image.currentSrc, name: card.getAttribute("aria-label") ?? "" }] : [];
    });
  }

  async function fullImage() {
    const image = await waitFor(() => {
      const current = one("img", labels.preview);
      return current?.complete && current.naturalWidth >= 512 && current.naturalHeight > current.naturalWidth
        ? current : null;
    }, "เปิดภาพผลลัพธ์ขนาดเต็มจาก Flow ไม่สำเร็จ");
    const source = new URL(image.currentSrc, location.origin);
    if (source.origin !== location.origin) throw new Error("Flow ไม่แสดงภาพผลลัพธ์บนโดเมนที่รองรับ");
    const response = await fetch(source, { credentials: "same-origin", signal: AbortSignal.timeout(15000) });
    if (!response.ok) throw new Error("ดาวน์โหลดภาพผลลัพธ์จาก Flow ไม่สำเร็จ");
    const blob = await response.blob();
    if (!mimeTypes.has(blob.type) || !blob.size || blob.size > maxImageBytes) {
      throw new Error("Flow ส่งไฟล์ที่ไม่ใช่ภาพนิ่งที่ Studio รองรับ");
    }
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(new Error("อ่านไฟล์ภาพจาก Flow ไม่สำเร็จ"));
      reader.readAsDataURL(blob);
    });
  }

  async function generate(packageData) {
    await setImageMode();
    const editor = await waitFor(() => one('[contenteditable="true"][role="textbox"]', labels.editor),
      "ไม่พบช่องพรอมป์ในโปรเจกต์ Flow");
    const composer = editor.closest("flow-base-prompt-box");
    if (!composer) throw new Error("ยืนยันแผงสร้างรูปภาพของ Flow ไม่ได้");
    if (editor.innerText.trim() || all("button[aria-label]", labels.ingredient, composer).length) {
      throw new Error("พบพรอมป์หรือรูปเดิมใน Flow เปิดโปรเจกต์ที่มีช่องพรอมป์ว่างก่อน");
    }
    for (const [index, reference] of packageData.refs.entries()) {
      job.status = `กำลังแนบรูปอ้างอิง ${index + 1}/2`;
      await attach(composer, reference, index, packageData.id);
    }

    const knownImages = gallery();
    const knownSources = new Set(knownImages.map(({ src }) => src));
    const unloadedNames = new Set(all('flow-grid-tile-container[role="group"]')
      .filter((card) => !knownImages.some((image) => image.card === card))
      .map((card) => card.getAttribute("aria-label")));
    editor.focus();
    document.execCommand("insertText", false, packageData.prompt);
    const marker = `Studio job ${packageData.id.slice(0, 8)}`;
    await waitFor(() => {
      const current = one('[contenteditable="true"][role="textbox"]', labels.editor);
      return (current?.textContent ?? "").includes(marker);
    }, "พรอมป์ไม่ปรากฏในช่องสร้างภาพของ Flow");
    job.status = "แนบรูปและพรอมป์แล้ว กำลังรอปุ่มสร้างรูปใน Flow";
    const submit = await waitFor(() => {
      const button = one("button[aria-label]", labels.generate);
      return button && !button.disabled && button.getAttribute("aria-disabled") !== "true" ? button : null;
    }, "Flow ยังไม่พร้อมรับคำขอสร้างภาพ");
    assertImageMode();
    job.status = "กำลังตรวจว่า Flow รับคำขอสร้างภาพนิ่ง";
    const clickedAt = Date.now();
    submit.click();

    const result = await waitFor(() => {
      if (all('flow-grid-tile-container[role="group"]').some((card) => label(card).includes(marker))) {
        job.status = "Flow รับคำขอสร้างภาพนิ่งแล้ว";
      } else if (Date.now() - clickedAt >= 5000) {
        job.status = "ถ้า Flow ยังไม่เริ่มสร้าง ให้กดเริ่มสร้างในแท็บ Flow หนึ่งครั้ง Studio จะรอรับภาพกลับมา";
      }
      const candidates = gallery().filter(({ src, name }) =>
        !knownSources.has(src) && !unloadedNames.has(name) && name && !name.toLowerCase().startsWith("studio-"));
      if (candidates.length > 1) throw new Error("พบภาพใหม่หลายรายการใน Flow จึงยังไม่เลือกภาพให้อัตโนมัติ");
      return candidates[0];
    }, "รอภาพจาก Flow เกินเวลา ตรวจผลในแท็บ Flow ก่อนเริ่มใหม่", 240000);
    job.status = "กำลังนำภาพนิ่งกลับ Studio";
    result.card.click();
    await waitFor(() => /\/edit\/[0-9a-f-]{36}$/.test(location.pathname),
      "เปิดการ์ดภาพใหม่ใน Flow ไม่สำเร็จ");
    await waitFor(() => document.body.innerText.includes(marker),
      "ยืนยันว่าภาพใหม่เป็นผลลัพธ์ของงานนี้ไม่ได้");
    const data = await fullImage();
    job.result = { data, url: location.origin + location.pathname };
  }

  browser.runtime.onMessage.addListener((message, sender) => {
    if (sender.id !== browser.runtime.id) return;
    if (message.action === "flow-probe") return Promise.resolve({ ready: true });
    if (message.action === "flow-status" && message.id === job?.id) {
      return Promise.resolve({ status: job.status, result: job.result, error: job.error });
    }
    if (message.action !== "flow-run" || job || !/^\/project\/[a-f0-9-]{36}(?:\/collection\/[a-f0-9-]{36})?\/?$/.test(location.pathname)) return;
    const data = message.packageData;
    if (!data || !/^[0-9a-f-]{36}$/.test(data.id) ||
        typeof data.prompt !== "string" || data.prompt.length > 15000 ||
        !data.prompt.startsWith("Create a still-image storyboard only.") ||
        data.refs?.length !== 2 || !data.refs.every((item) =>
          typeof item?.data === "string" && /^data:image\/(jpeg|png|webp);base64,/.test(item.data) &&
          item.data.length <= maxImageBytes * 4 / 3 + 32)) {
      return Promise.resolve({ error: "ชุดข้อมูลภาพนิ่งจาก Studio ไม่ครบหรือไม่ถูกต้อง" });
    }
    job = { id: data.id, status: "กำลังตรวจการตั้งค่า Image ใน Flow" };
    void generate(data).catch((error) => { job.error = error.message; });
    return Promise.resolve({ started: true });
  });
})();
