"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { channelLabels } from "./affiliate-links";

export type Selection = { kind: "offer" | "catalog"; id: string; name: string };
export type AffiliateJourney = { trend: string; offer: Selection | null };
export const emptyJourney: AffiliateJourney = { trend: "", offer: null };
export type CatalogProduct = { id: string; name: string; source_url: string; affiliate_url: string | null; image_rights_note: string | null };
type Link = { channel: string; affiliate_url: string; sub_id: string | null };
type SavedLink = { link: Link; item: CatalogProduct };
type SafariResult = { source?: string; affiliate_url?: string; tabId?: number; error?: string };

const shopeeLinkTool = "https://affiliate.shopee.co.th/offer/custom_link";
const offerIdPattern = /^[1-9]\d{0,19}$/;
const productIdPattern = /^[0-9a-f-]{36}$/;

export function readJourney(workspace: string): AffiliateJourney {
  if (!workspace) return emptyJourney;
  try {
    const saved = JSON.parse(sessionStorage.getItem(`affiliate-journey:${workspace}`) ?? "null");
    if (typeof saved?.trend !== "string" || saved.trend.length > 300) return emptyJourney;
    const offer = saved.offer;
    const kind = offer?.kind ?? "offer";
    const valid = typeof offer?.id === "string" && typeof offer.name === "string" &&
      offer.name.length <= 300 && (kind === "offer" && offerIdPattern.test(offer.id)
        || kind === "catalog" && productIdPattern.test(offer.id));
    return { trend: saved.trend, offer: valid ? { kind, id: offer.id, name: offer.name } : null };
  } catch {
    return emptyJourney;
  }
}

function listingUrl(input?: string) {
  if (!input) return null;
  try {
    const url = new URL(input.trim());
    if (url.protocol !== "https:" || url.username || url.password || url.port ||
        !["shopee.co.th", "www.shopee.co.th"].includes(url.hostname)) return null;
    const ids = /^\/product\/(\d+)\/(\d+)\/?$/.exec(url.pathname) ??
      /-i\.(\d+)\.(\d+)\/?$/.exec(url.pathname);
    return ids ? `https://shopee.co.th/product/${ids[1]}/${ids[2]}` : null;
  } catch {
    return null;
  }
}

export function listingItemId(input?: string) {
  return listingUrl(input)?.split("/").at(-1);
}

function isAffiliateLink(input?: string | null): input is string {
  if (!input) return false;
  try {
    const url = new URL(input);
    return url.protocol === "https:" && !url.username && !url.password && !url.port &&
      /^(?:[a-z0-9-]+\.)*shopee\.co\.th$/.test(url.hostname) && url.pathname !== "/" &&
      (!listingUrl(input) || url.searchParams.has("utm_source") || url.searchParams.has("uls_trackid")) &&
      !url.hostname.startsWith("affiliate.");
  } catch {
    return false;
  }
}

function findProduct(items: CatalogProduct[], selection: Selection) {
  if (selection.kind === "catalog") return items.find((item) => item.id === selection.id);
  const matches = items.filter((item) => listingItemId(item.source_url) === selection.id);
  return matches.length === 1 ? matches[0] : undefined;
}

export default function AffiliateLinkSetup({ autoStart, onAutoStartHandled, trend, offer, scope, token, products, request, onSave, onBusy, onContinue }: {
  autoStart: boolean;
  onAutoStartHandled: () => void;
  trend: string;
  offer: Selection;
  scope: string;
  token: string;
  products: CatalogProduct[];
  request: <T>(path: string, token: string, init?: RequestInit) => Promise<T>;
  onSave: (product: CatalogProduct) => void;
  onBusy: (busy: boolean) => void;
  onContinue: (item: CatalogProduct) => void;
}) {
  const [sourceOverride, setSource] = useState<string | null>(null);
  const [channel, setChannel] = useState("facebook");
  const [link, setLink] = useState("");
  const [subIdOverride, setSubId] = useState<string | null>(null);
  const [saved, setSaved] = useState<SavedLink | null>(null);
  const [checking, setChecking] = useState(true);
  const [lookupError, setLookupError] = useState("");
  const [lookupRetry, setLookupRetry] = useState(0);
  const [working, setWorking] = useState(false);
  const [portalJob, setPortalJob] = useState<{ id: string; tabId?: number; subId: string } | null>(null);
  const [status, setStatus] = useState({ text: "", error: false });
  const [bridgeReady, setBridgeReady] = useState(false);
  const portalTimeout = useRef<number | undefined>(undefined);
  const portalId = useRef("");
  const existingProduct = findProduct(products, offer);
  const path = scope + "/products";
  const source = sourceOverride ?? existingProduct?.source_url ?? "";
  const subId = subIdOverride ?? `${channel}${listingItemId(source) ?? offer.id.replaceAll("-", "")}`;
  const listing = listingUrl(source);

  useEffect(() => {
    const controller = new AbortController();
    setChecking(true);
    setLookupError("");
    setSaved(null);
    async function lookup() {
      const item = existingProduct ?? findProduct(
        await request<CatalogProduct[]>(path, token, { signal: controller.signal }), offer,
      );
      if (!item || controller.signal.aborted) return;
      const links = await request<Link[]>(`${path}/${item.id}/channel-links`, token, { signal: controller.signal });
      if (controller.signal.aborted) return;
      const channelLink = links.find((entry) => entry.channel === channel && isAffiliateLink(entry.affiliate_url));
      if (channelLink) setSaved({ link: channelLink, item });
      else if (channel === "facebook" && isAffiliateLink(item.affiliate_url)) {
        setSaved({ link: { channel, affiliate_url: item.affiliate_url, sub_id: null }, item });
      }
    }
    lookup().catch(() => {
      if (!controller.signal.aborted) setLookupError("ตรวจลิงก์ที่บันทึกไว้ไม่สำเร็จ");
    }).finally(() => {
      if (!controller.signal.aborted) setChecking(false);
    });
    return () => controller.abort();
  }, [channel, existingProduct, lookupRetry, offer, path, request, token]);

  useEffect(() => {
    const ready = () => setBridgeReady(true);
    window.addEventListener("studio:affiliate-ready", ready);
    window.dispatchEvent(new Event("studio:affiliate-probe"));
    return () => window.removeEventListener("studio:affiliate-ready", ready);
  }, []);

  async function copy(value: string, message: string) {
    try {
      await navigator.clipboard.writeText(value);
      setStatus({ text: message, error: false });
    } catch {
      setStatus({ text: "คัดลอกอัตโนมัติไม่สำเร็จ เลือกและคัดลอกจากช่อง URL ได้", error: true });
    }
  }

  async function saveLink(origin: string, url: string, tag: string) {
    const canonical = listingUrl(origin);
    if (!canonical || (offer.kind === "offer" && listingItemId(canonical) !== offer.id) ||
        (offer.kind === "catalog" && canonical !== listingUrl(existingProduct?.source_url))) {
      throw new Error("URL หน้าสินค้า Shopee ต้องตรงกับสินค้าที่เลือก");
    }
    if (!isAffiliateLink(url)) throw new Error("ใช้ลิงก์ Affiliate ที่ Shopee สร้างให้");
    const oneProduct = (items: CatalogProduct[]) => items.find((item) => listingUrl(item.source_url) === canonical);
    let item = existingProduct && listingUrl(existingProduct.source_url) === canonical ? existingProduct
      : oneProduct(await request<CatalogProduct[]>(path, token));
    if (!item) {
      try {
        item = await request<CatalogProduct>(path, token, {
          method: "POST", body: JSON.stringify({ name: offer.name, source_url: canonical }),
        });
      } catch (error) {
        item = oneProduct(await request<CatalogProduct[]>(path, token));
        if (!item) throw error;
      }
    }
    const result = await request<Link>(`${path}/${item.id}/channel-links/${channel}`, token, {
      method: "PUT", body: JSON.stringify({ affiliate_url: url, sub_id: tag.trim() || null }),
    });
    setSaved({ link: result, item });
    onSave(item);
  }

  async function persist(origin: string, url: string, tag: string) {
    setWorking(true);
    onBusy(true);
    try {
      await saveLink(origin, url, tag);
      setStatus({ text: "", error: false });
    } catch (error) {
      setStatus({ text: error instanceof Error ? error.message : "บันทึกลิงก์ไม่สำเร็จ", error: true });
    } finally {
      onBusy(false);
      setWorking(false);
    }
  }

  useEffect(() => {
    if (!portalJob) return;
    function respond(event: Event) {
      if (!(event instanceof CustomEvent) || typeof event.detail !== "string") return;
      let data: SafariResult & { id?: string };
      try { data = JSON.parse(event.detail); } catch { return; }
      if (data.id !== portalId.current || data.id !== portalJob?.id) return;
      if (data.error || (data.affiliate_url && data.source)) {
        portalId.current = "";
        window.clearTimeout(portalTimeout.current);
        setPortalJob(null);
        if (data.error) setStatus({ text: data.error, error: true });
        else if (data.affiliate_url && data.source && portalJob) {
          setSource(data.source);
          setLink(data.affiliate_url);
          void persist(data.source, data.affiliate_url, portalJob.subId);
        }
      } else if (data.tabId && !portalJob?.tabId) {
        setPortalJob({ ...portalJob!, tabId: data.tabId });
      }
    }
    window.addEventListener("studio:affiliate-response", respond);
    const interval = portalJob.tabId !== undefined ? window.setInterval(() => {
      window.dispatchEvent(new CustomEvent("studio:affiliate-status", { detail: JSON.stringify(portalJob) }));
    }, 1000) : undefined;
    return () => {
      window.removeEventListener("studio:affiliate-response", respond);
      window.clearInterval(interval);
    };
  });

  useEffect(() => () => window.clearTimeout(portalTimeout.current), []);

  function startPortal() {
    if (portalId.current || working) return;
    const id = crypto.randomUUID();
    portalId.current = id;
    setPortalJob({ id, subId });
    setStatus({ text: "", error: false });
    portalTimeout.current = window.setTimeout(() => {
      portalId.current = "";
      setPortalJob(null);
      setStatus({ text: "ยังไม่ได้รับลิงก์จาก Shopee ตรวจแท็บ Safari หรือนำลิงก์กลับมาบันทึกเอง", error: true });
    }, 120_000);
    window.dispatchEvent(new CustomEvent("studio:affiliate-start", {
      detail: JSON.stringify({ id, subId, ...(offer.kind === "offer" ? { offerId: offer.id } : { source: listing }) }),
    }));
  }

  const pending = working || !!portalJob;
  const selectedLink = saved?.link.channel === channel ? saved : null;
  useEffect(() => {
    if (!autoStart || checking) return;
    onAutoStartHandled();
    if (!selectedLink && !lookupError && bridgeReady && (offer.kind === "offer" || listing)) {
      startPortal();
    }
  });

  return <section className="panel affiliate-setup" aria-labelledby="affiliate-setup-title">
    <div className="panel-head">
      <h2 id="affiliate-setup-title">ลิงก์ Affiliate ของสินค้าที่เลือก</h2>
      <a href="#discover">กลับไปเลือกสินค้า</a>
    </div>
    <div className="selected-offer">
      <strong>{offer.name}</strong>
      {trend && <p className="muted">เทรนด์ {trend}</p>}
    </div>
    <label>ช่องทาง<select value={channel} disabled={pending} onChange={(event) => {
      setStatus({ text: "", error: false });
      setLink("");
      setSubId(null);
      setChannel(event.target.value);
    }}>
      {Object.entries(channelLabels).map(([key, name]) => <option key={key} value={key}>{name}</option>)}
    </select></label>
    {checking ? <p role="status">กำลังหาลิงก์ Affiliate…</p> :
      lookupError ? <div className="affiliate-setup-actions">
        <p role="alert">{lookupError}</p>
        <button type="button" className="secondary" onClick={() => setLookupRetry((value) => value + 1)}>ลองอีกครั้ง</button>
      </div> : selectedLink ? <div className="affiliate-link-ready">
        <p role="status"><strong>ลิงก์ {channelLabels[channel]} พร้อมใช้</strong>
          {selectedLink.link.sub_id && ` · Sub ID ${selectedLink.link.sub_id}`}</p>
        <p className="affiliate-link-url">{selectedLink.link.affiliate_url}</p>
        <div className="affiliate-setup-actions">
          <button type="button" className="primary" onClick={() => onContinue(selectedLink.item)}>เตรียม Storyboard</button>
          <button type="button" className="secondary"
            onClick={() => void copy(selectedLink.link.affiliate_url, "คัดลอกลิงก์แล้ว")}>คัดลอกลิงก์</button>
        </div>
      </div> : <>
        <p>ยังไม่มีลิงก์ {channelLabels[channel]} สำหรับสินค้านี้</p>
        {bridgeReady && (offer.kind === "offer" || listing) && <div className="affiliate-setup-actions">
          <button type="button" className="primary" disabled={pending} onClick={startPortal}>สร้างใน Shopee</button>
          {portalJob && <>
            <p role="status">รอรับลิงก์จาก Safari กด “เอา ลิงก์” ใน Shopee เพื่อให้ Studio รับและบันทึกลิงก์กลับมา</p>
            <button type="button" className="secondary" onClick={() => {
              portalId.current = "";
              window.clearTimeout(portalTimeout.current);
              setPortalJob(null);
            }}>ยกเลิกการรอ</button>
          </>}
        </div>}
        <details className="workflow-details" open={!bridgeReady || undefined}>
          <summary>สร้างหรือบันทึกลิงก์ด้วยตนเอง</summary>
          <form onSubmit={(event: FormEvent<HTMLFormElement>) => {
            event.preventDefault();
            if (!pending) void persist(source, link.trim(), subId);
          }}>
            <fieldset disabled={pending}>
              {offer.kind === "offer" && <a href={`https://affiliate.shopee.co.th/offer/product_offer/${offer.id}`}
                target="_blank" rel="noreferrer">เปิดข้อเสนอเพื่อดู URL สินค้า</a>}
              <label>URL หน้าสินค้า Shopee<input type="url" required maxLength={2083} value={source}
                onChange={(event) => setSource(event.target.value)} /></label>
              <label>Sub ID<input required pattern="[A-Za-z0-9]+" maxLength={100} value={subId}
                onChange={(event) => setSubId(event.target.value)} /></label>
              <a href={shopeeLinkTool} target="_blank" rel="noreferrer">เปิดเครื่องมือสร้างลิงก์ Shopee</a>
              <label>ลิงก์ Affiliate จาก Shopee<input type="url" required maxLength={2083} value={link}
                onChange={(event) => setLink(event.target.value)} placeholder="https://s.shopee.co.th/…" /></label>
              <button type="submit" className="secondary">บันทึกลิงก์และ Sub ID</button>
            </fieldset>
          </form>
        </details>
      </>}
    {status.text && <p className={`notice${status.error ? " error" : ""}`} role={status.error ? "alert" : "status"}>{status.text}</p>}
  </section>;
}
