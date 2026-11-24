"use client";

import { FormEvent, useEffect, useState } from "react";
import type { StudioRequest } from "@/features/publishing/meta-publishing";
import { safariCaptureEnabled } from "@/lib/safari-capture";

type Asset = { source: "shopee" | "google"; file: string; url: string };
type Preview = {
  id: string; generated_at: string; seconds: number; assets: Asset[];
  opening?: { source: "google_flow"; seconds: number; starts_at?: number };
};
type Purchase = {
  id: string; name: string; product_url: string; preview: Preview | null;
  purchase_source?: "shopee_completed";
};
type Props = { active: boolean; scope: string; token: string; request: StudioRequest };
type CaptureReply = { ready?: boolean; id?: string; started?: boolean; error?: string; purchase?: object };

export default function PurchasePreviews({ active, scope, token, request }: Props) {
  const [items, setItems] = useState<Purchase[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [pending, setPending] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [video, setVideo] = useState("");
  const [safariReady, setSafariReady] = useState(false);
  const [captureId, setCaptureId] = useState("");
  const selected = items.find((item) => item.id === selectedId);
  const preview = selected?.preview;
  const base = scope + "/purchase-previews";

  useEffect(() => {
    if (!safariCaptureEnabled) return;
    if (!active || window.location.origin !== "http://127.0.0.1:3014") {
      setSafariReady(false);
      setCaptureId("");
      setPending((value) => value === "safari" || value === "capture-render" ? "" : value);
      return;
    }
    let timeout: ReturnType<typeof setTimeout> | undefined;
    let alive = true;
    const controller = new AbortController();
    if (!captureId) setCaptureId(crypto.randomUUID());

    const reply = async (event: Event) => {
      if (!(event instanceof CustomEvent) || typeof event.detail !== "string") return;
      let message: CaptureReply;
      try { message = JSON.parse(event.detail); } catch { return; }
      if (message.ready === true) setSafariReady(true);
      if (!captureId || message.id !== captureId) return;
      if (message.started) {
        setError("");
        setPending("safari");
        clearTimeout(timeout);
        timeout = setTimeout(() => {
          setError("Safari ใช้เวลานานเกินไป ตรวจแท็บ Shopee และสิทธิ์ส่วนขยายแล้วลองอีกครั้ง");
          setPending("");
          setCaptureId(crypto.randomUUID());
        }, 180_000);
        return;
      }
      clearTimeout(timeout);
      try {
        if (message.error || !message.purchase) throw new Error(message.error || "ยังไม่มีสินค้าที่พร้อมเรนเดอร์");
        setPending("capture-render");
        const item = await request<Purchase>(base + "/collect-and-render", token, {
          method: "POST", body: JSON.stringify(message.purchase), signal: controller.signal,
        });
        if (!alive) return;
        setItems((records) => [item, ...records.filter((record) => record.id !== item.id)]);
        setSelectedId(item.id);
      } catch (failure) {
        if (alive) setError(failure instanceof Error ? failure.message : "สร้างตัวอย่างไม่สำเร็จ");
      } finally {
        if (alive) {
          setPending("");
          setCaptureId(crypto.randomUUID());
        }
      }
    };
    window.addEventListener("studio:capture-response", reply);
    const probe = () => window.dispatchEvent(new Event("studio:capture-probe"));
    probe();
    const retry = setInterval(probe, 2000);
    return () => {
      alive = false;
      clearTimeout(timeout);
      clearInterval(retry);
      controller.abort();
      window.removeEventListener("studio:capture-response", reply);
    };
  }, [active, base, captureId, request, token]);

  useEffect(() => {
    if (!active) return;
    const controller = new AbortController();
    setLoading(true);
    setError("");
    request<Purchase[]>(base, token, { signal: controller.signal }).then((records) => {
      if (controller.signal.aborted) return;
      setItems(records);
      setSelectedId((value) => records.some((item) => item.id === value) ? value : (records[0]?.id ?? ""));
    }).catch(() => {
      if (!controller.signal.aborted) setError("โหลดรายการซื้อสำเร็จไม่ได้");
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, [active, base, request, token]);

  useEffect(() => {
    setVideo("");
    if (!active || !selectedId || !preview) return;
    const controller = new AbortController();
    let objectUrl = "";
    fetch("/api/v1" + base + "/" + selectedId + "/video/" + preview.id, {
      headers: { Authorization: "Bearer " + token }, signal: controller.signal,
    }).then((response) => {
      if (!response.ok) throw new Error("เปิดตัวอย่างไม่ได้");
      return response.blob();
    }).then((blob) => {
      if (!controller.signal.aborted) {
        objectUrl = URL.createObjectURL(blob);
        setVideo(objectUrl);
      }
    }).catch(() => {
      if (!controller.signal.aborted) setError("เปิดตัวอย่างไม่ได้");
    });
    return () => {
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [active, base, preview, selectedId, token]);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    setPending("save");
    setError("");
    try {
      const item = await request<Purchase>(base, token, {
        method: "POST",
        body: JSON.stringify({
          name: data.get("name"), product_url: data.get("product_url"), shopee_image: data.get("shopee_image"),
          search_images: data.getAll("search_images"), purchase_confirmed: data.has("purchase_confirmed"),
        }),
      });
      setItems((records) => [item, ...records.filter((record) => record.id !== item.id)]);
      setSelectedId(item.id);
      form.reset();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "บันทึกรายการไม่ได้");
    } finally { setPending(""); }
  }

  async function render() {
    if (!selected) return;
    setPending("render");
    setError("");
    try {
      const result = await request<Preview>(base + "/" + selected.id + "/render", token, { method: "POST" });
      setItems((records) => records.map((item) => item.id === selected.id ? { ...item, preview: result } : item));
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "สร้างตัวอย่างไม่สำเร็จ");
    } finally { setPending(""); }
  }

  async function importFlow(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    const form = event.currentTarget;
    const data = new FormData(form);
    setPending("flow");
    setError("");
    try {
      const result = await request<Preview>(base + "/" + selected.id + "/flow-preview", token, {
        method: "POST", body: data,
      });
      setItems((records) => records.map((item) => item.id === selected.id ? { ...item, preview: result } : item));
      form.reset();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "นำเข้าช็อตจาก Flow ไม่สำเร็จ");
    } finally { setPending(""); }
  }

  return <section id="purchase-previews" className="purchase-previews">
    <header className="workspace-header"><h1 tabIndex={-1}>Reel จากสินค้าที่เคยซื้อ</h1></header>
    <div className="panel">
      <div className="columns">
        <div className="column">
          {safariCaptureEnabled && <>
            <button id="safari-purchase-capture" data-request-id={captureId} type="button" className="primary"
              disabled={!safariReady || !captureId || loading || !!pending}>
              {pending === "safari" ? "Safari กำลังตรวจประวัติซื้อและค้นภาพ…" :
                pending === "capture-render" ? "Studio กำลังเก็บภาพและเรนเดอร์…" : "ดึงจาก Safari และสร้างตัวอย่าง"}
            </button>
            {!safariReady && <p className="muted">เปิดหน้า Studio ใน Safari และเปิดใช้ส่วนขยาย Affiliate Studio Purchase Capture</p>}
          </>}
          <label>สินค้าที่ซื้อสำเร็จ<select disabled={loading || !!pending} value={selectedId}
            onChange={(event) => setSelectedId(event.target.value)}>
            <option value="">เลือกสินค้า</option>
            {items.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select></label>
          {selected && <>
            {selected.purchase_source === "shopee_completed" && <p className="muted">มาจากประวัติซื้อสำเร็จใน Shopee</p>}
            <a href={selected.product_url} target="_blank" rel="noreferrer">ดูหน้าสินค้าบน Shopee</a>
            <a href={`https://www.google.com/search?tbm=isch&q=${encodeURIComponent(selected.name)}`}
              target="_blank" rel="noreferrer">ค้นภาพสินค้าใน Google</a>
            <button type="button" className="primary" disabled={!!pending}
              onClick={() => void render()}>{pending === "render" ? "กำลังเก็บภาพและเรนเดอร์…" : "เก็บภาพและสร้างตัวอย่าง"}</button>
          </>}
          {preview && <>
            <form key={selectedId} onSubmit={importFlow} className="import">
              <label>นำเข้าช็อตเปิดจาก Google Flow (MP4)
                <input type="file" name="clip" accept="video/mp4,.mp4" required disabled={!!pending} />
              </label>
              <label>ข้อความบนช็อตแรก (ถ้ามี)
                <input name="opening_text" maxLength={70} disabled={!!pending} />
              </label>
              <label className="checkbox"><input name="product_first" type="checkbox" value="true" disabled={!!pending} />
                เปิดด้วยภาพสินค้าจริง แล้วแทรกช็อตจาก Flow
              </label>
              <button className="secondary" disabled={!!pending}>
                {pending === "flow" ? "กำลังต่อช็อตเปิดกับภาพสินค้า…" : "ต่อช็อตเปิดและสร้าง Reel 15 วินาที"}
              </button>
            </form>
            <h2>ภาพที่ใช้</h2>
            {preview.opening && <p className="muted">{preview.opening.starts_at === undefined
              ? `ช็อตเปิดจาก Google Flow · ${preview.opening.seconds} วินาที`
              : `ภาพสินค้าจริงขึ้นก่อน · แทรก Google Flow ที่วินาที ${preview.opening.starts_at}–${preview.opening.starts_at + preview.opening.seconds}`}</p>}
            <ul className="purchase-assets">{preview.assets.map((asset) =>
              <li key={asset.file}>{asset.source === "shopee" ? "Shopee" : "ค้นภาพจาก Google"} · <code>{asset.file}</code></li>
            )}</ul>
            <p className="muted">ใช้ตรวจตัวอย่าง สิทธิ์เผยแพร่ภาพยังรอยืนยัน</p>
          </>}
          {error && <p className="notice error" role="alert">{error}</p>}
          <details>
            <summary>เพิ่มสินค้าที่ตรวจแล้ว</summary>
            <form onSubmit={save}>
              <label>ชื่อสินค้า<input name="name" required maxLength={140} /></label>
              <label>หน้าสินค้า Shopee<input name="product_url" type="url" required /></label>
              <label>URL ภาพจาก Shopee<input name="shopee_image" type="url" required /></label>
              <label>URL ภาพที่ค้นเพิ่ม · มุมใช้งาน<input name="search_images" type="url" required /></label>
              <label>URL ภาพที่ค้นเพิ่ม · รายละเอียด<input name="search_images" type="url" required /></label>
              <label className="checkbox"><input name="purchase_confirmed" type="checkbox" required /> ตรวจแล้วว่าซื้อสำเร็จ</label>
              <button className="secondary" disabled={loading || !!pending}>เพิ่มในรายการ</button>
            </form>
          </details>
        </div>
        <div className="preview">
          {video ? <video key={video} src={video} controls playsInline />
            : <div className="preview-empty"><p>{preview ? "กำลังเปิดตัวอย่าง…" : "ตัวอย่าง Reel"}</p></div>}
        </div>
      </div>
    </div>
  </section>;
}
