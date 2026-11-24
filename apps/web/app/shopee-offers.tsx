"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { safariCaptureEnabled } from "./safari-capture";

const portal = "https://affiliate.shopee.co.th/offer/product_offer";
const numbers = new Intl.NumberFormat("th-TH");
const currency = new Intl.NumberFormat("th-TH", { style: "currency", currency: "THB" });
const dates = new Intl.DateTimeFormat("th-TH", {
  timeZone: "Asia/Bangkok", dateStyle: "medium", timeStyle: "short",
});

type OfferInput = {
  offer_id: string;
  name: string;
  sold: number;
  sold_is_minimum: boolean;
  price_satang: number;
  commission_bps: number;
  image_url?: string | null;
};
export type Offer = OfferInput & { observed_at: string };
type Props = {
  active: boolean;
  scope: string;
  token: string;
  onStoryboard: (id: string, name: string) => void;
  trend: string;
  onChooseOffer: (id: string, name: string) => void;
  request: <T>(path: string, token: string, init?: RequestInit) => Promise<T>;
};

const sortOptions = {
  balanced: "ยอดขายและอัตราค่าคอม",
  sold: "ยอดขายสูงสุด",
  rate: "อัตราค่าคอมสูงสุด",
  estimate: "ค่าคอมประมาณต่อชิ้นสูงสุด",
} as const;
type Sort = keyof typeof sortOptions;

export function visiblePrice(offer: Offer) {
  return offer.price_satang / 100;
}

export function estimatedCommission(offer: Offer) {
  return visiblePrice(offer) * offer.commission_bps / 10_000;
}

function sortValue(offer: Offer, sort: Sort) {
  switch (sort) {
    case "sold": return offer.sold;
    case "rate": return offer.commission_bps;
    case "estimate": return estimatedCommission(offer);
    case "balanced": return Math.log10(1 + offer.sold) * offer.commission_bps;
  }
}

function readOfferId(input: string) {
  const url = new URL(input);
  const match = /^\/offer\/product_offer\/([1-9]\d{0,19})\/?$/.exec(url.pathname);
  if (url.origin !== "https://affiliate.shopee.co.th" || url.username || url.password || !match) {
    throw new Error("ใช้ลิงก์หน้ารายละเอียดข้อเสนอผลิตภัณฑ์จาก Shopee Affiliate");
  }
  return match[1];
}

export default function ShopeeOffers({ active, scope, token, request, onStoryboard, trend, onChooseOffer }: Props) {
  const path = scope + "/shopee-offers";
  const [offers, setOffers] = useState<Offer[]>([]);
  const [minimumSales, setMinimumSales] = useState("100");
  const [minimumRate, setMinimumRate] = useState("5");
  const [sort, setSort] = useState<Sort>("balanced");
  const [searchOverride, setSearchOverride] = useState<{ trend: string; value: string } | null>(null);
  const search = searchOverride?.trend === trend ? searchOverride.value : trend;
  const setSearch = (value: string) => setSearchOverride({ trend, value });
  const [requestId, setRequestId] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState<{ message: string; error?: boolean } | null>(null);
  const captureTimeout = useRef<number | undefined>(undefined);

  useEffect(() => {
    if (!active) return;
    const controller = new AbortController();
    request<Offer[]>(path, token, { signal: controller.signal })
      .then((result) => { if (!controller.signal.aborted) setOffers(result); })
      .catch((error) => { if (!controller.signal.aborted) setNotice({ message: error.message, error: true }); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [active, path, request, token]);

  useEffect(() => {
    if (safariCaptureEnabled && window.isSecureContext) setRequestId(crypto.randomUUID());
    return () => window.clearTimeout(captureTimeout.current);
  }, []);

  async function save(input: OfferInput[]) {
    setBusy(true);
    setNotice(null);
    try {
      const result = await request<{ saved: number }>(path, token, {
        method: "POST", body: JSON.stringify({ offers: input }),
      });
      setOffers(await request<Offer[]>(path, token));
      setNotice({ message: `บันทึกข้อมูล Shopee แล้ว ${result.saved} รายการ` });
      return true;
    } catch (error) {
      setNotice({ message: (error as Error).message, error: true });
      return false;
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!requestId) return;
    function onCapture(event: Event) {
      if (!(event instanceof CustomEvent) || typeof event.detail !== "string") return;
      let data;
      try { data = JSON.parse(event.detail); } catch { return; }
      if (data?.id !== requestId || data.started) return;
      window.clearTimeout(captureTimeout.current);
      setRequestId(crypto.randomUUID());
      if (Array.isArray(data.offers) && data.offers.length) {
        void save(data.offers);
      } else {
        setBusy(false);
        setNotice({ message: data.error || "ไม่พบข้อเสนอที่มียอดขายและอัตราค่าคอมครบ", error: true });
      }
    }
    window.addEventListener("studio:capture-response", onCapture);
    return () => window.removeEventListener("studio:capture-response", onCapture);
  });

  function startCapture() {
    window.clearTimeout(captureTimeout.current);
    setBusy(true);
    setNotice(null);
    captureTimeout.current = window.setTimeout(() => {
      setRequestId(crypto.randomUUID());
      setBusy(false);
      setNotice({ message: "Safari ไม่ตอบกลับ ตรวจส่วนขยาย Affiliate Studio Capture และสิทธิ์อ่านหน้า Shopee", error: true });
    }, 8000);
  }

  async function saveManually(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    let id: string;
    try { id = readOfferId(String(data.get("offer_url"))); }
    catch { setNotice({ message: "ใช้ลิงก์หน้ารายละเอียดข้อเสนอผลิตภัณฑ์จาก Shopee Affiliate", error: true }); return; }
    if (await save([{
      offer_id: id,
      name: String(data.get("name")),
      sold: Number(data.get("sold")),
      sold_is_minimum: data.has("sold_is_minimum"),
      price_satang: Math.round(Number(data.get("price")) * 100),
      commission_bps: Math.round(Number(data.get("rate")) * 100),
    }])) form.reset();
  }

  const keyword = search.trim().toLocaleLowerCase("th");
  const matches = offers.filter((offer) => offer.sold >= Number(minimumSales) &&
    offer.commission_bps >= Math.round(Number(minimumRate) * 100) &&
    offer.name.toLocaleLowerCase("th").includes(keyword));
  matches.sort((left, right) => sortValue(right, sort) - sortValue(left, sort) ||
    right.sold - left.sold || right.commission_bps - left.commission_bps ||
    left.offer_id.localeCompare(right.offer_id));

  return <div id="shopee-offers" className="trend-explorer">
    <header><h1 tabIndex={-1}>คัดสินค้า Shopee</h1>
      {trend && <p className="muted">เทรนด์ที่เลือก <strong>{trend}</strong> · ปรับคำค้นสินค้าให้ตรงกับของที่ต้องการได้</p>}
    </header>
    <section className="panel">
      <div className="panel-head"><h2>จัดอันดับสินค้า</h2><a href="#trends">กลับไปที่เทรนด์</a></div>
      <div className="trend-filters">
        <label>คำค้นสินค้า<input type="search" value={search} onChange={(event) => setSearch(event.target.value)} /></label>
        <label>ยอดขายขั้นต่ำ (ชิ้น)<input type="number" min="0" value={minimumSales}
          onChange={(event) => setMinimumSales(event.target.value)} /></label>
        <label>ค่าคอมขั้นต่ำ (%)<input type="number" min="0" max="100" step="0.01" value={minimumRate}
          onChange={(event) => setMinimumRate(event.target.value)} /></label>
        <label>เรียงตาม<select value={sort} onChange={(event) => setSort(event.target.value as Sort)}>
          {Object.entries(sortOptions).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select></label>
      </div>
      <p className="muted">แสดง {numbers.format(matches.length)} จาก {numbers.format(offers.length)} รายการ ·
        ยอดขายตามที่ Shopee แสดงโดยไม่ระบุช่วงเวลา · ค่าคอมต่อชิ้นเป็นค่าประมาณจากราคา × อัตราที่แสดง
        ยอดจ่ายจริงขึ้นอยู่กับเงื่อนไขของ Shopee</p>
      {sort === "balanced" && <p className="muted">อันดับแบบผสมใช้ log₁₀(1 + ยอดขาย) × อัตราค่าคอม
        เพื่อให้ยอดขายและค่าคอมมีผลต่ออันดับทั้งคู่</p>}
      {loading ? <p role="status">กำลังโหลดข้อเสนอ…</p> : matches.length ? <ol className="offer-list">
        {matches.map((offer) => <li key={offer.offer_id}>
          <div><h3>{offer.name}</h3>
            <p className="muted">เห็นข้อมูลเมื่อ {dates.format(Date.parse(offer.observed_at))}</p>
            <div className="affiliate-setup-actions">
              <button type="button" className="primary" onClick={() => onChooseOffer(offer.offer_id, offer.name)}
                aria-label={`เลือกสินค้า ${offer.name}`}>เลือกเพื่อสร้างลิงก์</button>
              <a href={portal + "/" + offer.offer_id} target="_blank" rel="noreferrer">ดูข้อเสนอ</a>
            </div>
            <details><summary>งานคอนเทนต์</summary>
              <button type="button" className="text-button" onClick={() => onStoryboard(offer.offer_id, offer.name)}>เตรียม Storyboard</button>
            </details>
          </div>
          <dl className="offer-metrics">
            <div><dt>ขายได้</dt><dd>{numbers.format(offer.sold)}{offer.sold_is_minimum ? "+" : ""} ชิ้น</dd></div>
            <div><dt>ราคา</dt><dd>{currency.format(visiblePrice(offer))}</dd></div>
            <div><dt>ค่าคอม</dt><dd>{numbers.format(offer.commission_bps / 100)}%</dd></div>
            <div><dt>ค่าคอมโดยประมาณ</dt><dd>{currency.format(estimatedCommission(offer))}/ชิ้น</dd></div>
          </dl>
        </li>)}
      </ol> : <div>
        <p>{offers.length ? "ไม่มีข้อเสนอที่ตรงกับตัวกรอง" : "ยังไม่มีข้อเสนอในพื้นที่ทำงาน เปิดส่วน “นำเข้าข้อเสนอจาก Shopee” ด้านล่างเพื่อเริ่ม"}</p>
        {keyword && !!offers.length && <button type="button" className="text-button" onClick={() => setSearch("")}>
          ล้างคำค้นสินค้า
        </button>}
      </div>}
    </section>
    <details className="panel workflow-details">
      <summary>นำเข้าข้อเสนอจาก Shopee</summary>
      <div className="panel-head">
        <h2>ข้อเสนอจาก Shopee Affiliate</h2>
        <a href={portal} target="_blank" rel="noreferrer">เปิดข้อเสนอผลิตภัณฑ์</a>
      </div>
      {safariCaptureEnabled && <>
        <p className="muted">ค้นสินค้าใน Shopee Affiliate แล้วนำผลที่แสดงใน Safari เข้ามาจัดอันดับ</p>
        <button id="safari-offer-capture" data-request-id={requestId} type="button" className="secondary"
          disabled={busy || !requestId} onClick={startCapture}>ดึงข้อเสนอจาก Safari</button>
      </>}
      <details open={safariCaptureEnabled ? undefined : true}>
        <summary>เพิ่มข้อเสนอจาก Shopee ทีละรายการ</summary>
        <form className="offer-entry" onSubmit={saveManually}>
          <label>ลิงก์หน้าข้อเสนอ<input name="offer_url" type="url" required maxLength={2083} /></label>
          <label>ชื่อสินค้า<input name="name" required maxLength={300} /></label>
          <div className="trend-filters">
            <label>ยอดขาย (ชิ้น)<input name="sold" type="number" min="0" max="2147483647" required /></label>
            <label>ราคา (บาท)<input name="price" type="number" min="0.01" max="99999999.99" step="0.01" required /></label>
            <label>ค่าคอม (%)<input name="rate" type="number" min="0" max="100" step="0.01" required /></label>
          </div>
          <label className="offer-check"><input name="sold_is_minimum" type="checkbox" /> Shopee แสดงเครื่องหมาย + หลังยอดขาย</label>
          <button className="secondary" disabled={busy}>บันทึกข้อเสนอ</button>
        </form>
      </details>
      {busy && <p role="status">กำลังบันทึกหรืออ่านข้อเสนอ…</p>}
      {notice && <p role={notice.error ? "alert" : "status"}>{notice.message}</p>}
    </details>
  </div>;
}
