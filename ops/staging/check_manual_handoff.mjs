import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import { createRequire } from "node:module";

// Playwright is installed on the test runner, outside the deployment images.
const require = createRequire(import.meta.url);
const { chromium } = require("playwright");
const origin = process.env.STAGING_WEB_ORIGIN ?? "http://127.0.0.1:3110";
const browser = await chromium.launch();

try {
  const context = await browser.newContext({ serviceWorkers: "block" });
  const remoteRequests = [];
  await context.route("**/*", (route) => {
    const url = new URL(route.request().url());
    if (url.origin === origin) return route.continue();
    remoteRequests.push(url.origin);
    return route.abort();
  });
  await context.addInitScript(() => {
    window.studioBridgeEvents = [];
    for (const name of ["affiliate-probe", "affiliate-start", "flow-probe", "flow-package", "capture-probe"]) {
      window.addEventListener("studio:" + name, () => window.studioBridgeEvents.push(name));
    }
  });
  const page = await context.newPage();
  const credential = { email: `smoke-${randomUUID()}@example.com`, password: randomUUID() };
  const register = await page.request.post(origin + "/api/v1/auth/register", { data: credential });
  assert.equal(register.status(), 201);
  const { token } = await register.json();
  const headers = { authorization: `Bearer ${token}` };
  const workspaces = await page.request.get(origin + "/api/v1/workspaces", { headers });
  assert.equal(workspaces.status(), 200);
  const [workspace] = await workspaces.json();
  const scope = origin + "/api/v1/workspaces/" + workspace.id;
  const productName = "Manual handoff fixture";
  const source = "https://shopee.co.th/product/123/456";
  const mockPartner = process.env.STUDIO_SHOPEE_MOCK === "partner";
  const mockShopee = mockPartner || process.env.STUDIO_SHOPEE_MOCK === "1";
  const link = mockPartner
    ? "https://s.shopee.co.th/an_redir?" + new URLSearchParams({
      origin_link: source, affiliate_id: "123", sub_id: "facebook456----",
    })
    : "https://s.shopee.co.th/manual-fixture";
  let generated = 0;
  if (mockShopee) {
    await context.route(scope + "/shopee-links", (route) => route.fulfill({
      json: { generate_enabled: true, ...(mockPartner && { mode: "partner" }) },
    }));
    await context.route(new RegExp(scope + "/shopee-links/[^/]+/facebook$"), async (route) => {
      assert.equal(route.request().method(), "POST");
      const body = route.request().postDataJSON();
      assert.deepEqual(body, { sub_id: "facebook456" });
      const result = await route.fetch({
        method: "PUT", postData: { ...body, affiliate_url: link },
      });
      assert.equal(result.status(), 200);
      generated++;
      await route.fulfill({ response: result });
    });
  }
  const offers = await page.request.post(scope + "/shopee-offers", { headers, data: { offers: [{
    offer_id: "456", name: productName, sold: 120, sold_is_minimum: false,
    price_satang: 10000, commission_bps: 600,
  }] } });
  assert.equal(offers.status(), 200);

  await page.goto(origin);
  await page.getByLabel("อีเมล").fill(credential.email);
  await page.getByLabel("รหัสผ่าน").fill(credential.password);
  await page.getByRole("button", { name: "เข้าสู่ระบบ", exact: true }).click();
  await page.getByRole("button", { name: "เลือกสินค้า " + productName }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByRole("button", { name: "บันทึกลิงก์และ Sub ID" }).waitFor();
  assert.equal(await dialog.getByRole("button", { name: "สร้างใน Shopee", exact: true }).count(), 0);
  await dialog.getByLabel("URL หน้าสินค้า Shopee").fill(source);
  if (mockShopee) {
    const label = mockPartner ? "สร้างลิงก์พาร์ทเนอร์ Shopee" : "สร้างลิงก์อัตโนมัติผ่าน Shopee";
    await dialog.getByRole("button", { name: label }).click();
  } else {
    assert.equal(await dialog.getByRole("button", { name: "สร้างลิงก์อัตโนมัติผ่าน Shopee" }).count(), 0);
    await dialog.getByLabel("ลิงก์ Affiliate จาก Shopee").fill(link);
    await dialog.getByRole("button", { name: "บันทึกลิงก์และ Sub ID" }).click();
  }
  await dialog.getByText(/บันทึกลิงก์ใหม่แล้ว · Facebook/).waitFor();
  assert.equal(generated, Number(mockShopee));
  await dialog.getByRole("checkbox", { name: /ตรวจแล้วว่าลิงก์/ }).check();
  await dialog.getByRole("button", { name: "เตรียม Storyboard", exact: true }).click();
  await dialog.locator("[name=creative_prompt]").fill("Smoke fixture only");
  await dialog.locator("[name=variant]").fill("White fixture");
  await dialog.locator("[name=verified]").fill("Synthetic fixture");
  const image = { name: "fixture.png", mimeType: "image/png", buffer: Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAkAAAAQCAIAAABLKsIUAAAAGklEQVR4nGP8//8/Aw7AhEuCYVQOF6B3mAEAUtEDHVdVkSQAAAAASUVORK5CYII=", "base64",
  ) };
  await dialog.locator("[name=product]").setInputFiles(image);
  await dialog.locator("[name=presenter]").setInputFiles(image);
  await dialog.getByRole("button", { name: "บันทึกแผนและรูปอ้างอิง" }).click();
  await dialog.getByRole("button", { name: /ถัดไป.*อนุมัติภาพนิ่ง/ }).click();
  await dialog.getByRole("button", { name: "คัดลอกพรอมป์และเปิด Flow" }).waitFor();
  assert.equal(await dialog.locator("#safari-flow-storyboard").count(), 0);
  await dialog.locator("[name=image]").setInputFiles(image);
  await dialog.getByRole("button", { name: "นำเข้าภาพเพื่อรอตรวจ" }).click();
  const firstShot = dialog.getByRole("checkbox", { name: /ฉาก 01/ });
  await firstShot.check();
  await dialog.getByRole("button", { name: "บันทึกฉากที่อนุมัติ" }).click();
  await dialog.getByText("อนุมัติแล้ว 1 / 4 ฉาก", { exact: true }).waitFor();
  assert.deepEqual(await page.evaluate(() => window.studioBridgeEvents), []);
  assert.deepEqual(remoteRequests, []);
  const mode = mockPartner ? "mocked partner" : mockShopee ? "mocked automatic" : "manual";
  console.log(`Clean browser: ${mode} Affiliate link and storyboard approval passed with zero bridge events or external requests.`);
} finally {
  await browser.close();
}
