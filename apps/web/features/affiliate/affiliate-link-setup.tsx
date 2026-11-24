"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { channelLabels } from "@/features/affiliate/affiliate-links";
import { safariCaptureEnabled } from "@/lib/safari-capture";

export type Selection = { kind: "offer" | "catalog"; id: string; name: string };
export type AffiliateJourney = { trend: string; offer: Selection | null };
export const emptyJourney: AffiliateJourney = { trend: "", offer: null };
export type CatalogProduct = { id: string; name: string; source_url: string; affiliate_url: string | null; image_rights_note: string | null };
export type AffiliateLink = { channel: string; affiliate_url: string; sub_id: string | null; shopee_verification?: string | null };
type SavedLink = { link: AffiliateLink; item: CatalogProduct; legacy?: boolean };
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

export default function AffiliateLinkSetup({ trend, offer, scope, token, products, request, onSave, onBusy, onContinue, inDialog, autoStart }: {
  trend: string;
  offer: Selection;
  scope: string;
  token: string;
  products: CatalogProduct[];
  request: <T>(path: string, token: string, init?: RequestInit) => Promise<T>;
  onSave: (product: CatalogProduct) => void;
  onBusy: (busy: boolean) => void;
  onContinue: (item: CatalogProduct, link: AffiliateLink) => void;
  inDialog?: boolean;
  autoStart?: boolean;
}) {
  const [sourceOverride, setSource] = useState<string | null>(null);
  const [channel, setChannel] = useState("facebook");
  const [link, setLink] = useState("");
  const [subIdOverride, setSubId] = useState<string | null>(null);
  const [newLink, setNewLink] = useState<AffiliateLink | null>(null);
  const [saved, setSaved] = useState<SavedLink | null>(null);
  const [checking, setChecking] = useState(true);
  const [verifiedUrl, setVerifiedUrl] = useState("");
  const [lookupError, setLookupError] = useState("");
  const [lookupRetry, setLookupRetry] = useState(0);
  const [working, setWorking] = useState(false);
  const [portalJob, setPortalJob] = useState<{
    id: string; tabId?: number; subId: string; source?: string; offerId?: string;
  } | null>(null);
  const [status, setStatus] = useState({ text: "", error: false });
  const [bridgeReady, setBridgeReady] = useState(false);
  const [generationMode, setGenerationMode] = useState<"api" | "partner" | false>();
  const portalTimeout = useRef<number | undefined>(undefined);
  const portalId = useRef("");
  const dispatchedPortal = useRef("");
  const autoStarted = useRef(false);
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
      const links = await request<AffiliateLink[]>(`${scope}/shopee-links/${item.id}`, token, { signal: controller.signal });
      if (controller.signal.aborted) return;
      const channelLink = links.find((entry) => entry.channel === channel && isAffiliateLink(entry.affiliate_url));
      if (channelLink) setSaved({ link: channelLink, item });
      else if (channel === "facebook" && isAffiliateLink(item.affiliate_url)) {
        setSaved({ link: { channel, affiliate_url: item.affiliate_url, sub_id: null }, item, legacy: true });
      }
    }
    lookup().catch(() => {
      if (!controller.signal.aborted) setLookupError("ตรวจลิงก์ที่บันทึกไว้ไม่สำเร็จ");
    }).finally(() => {
      if (!controller.signal.aborted) setChecking(false);
    });
    return () => controller.abort();
  }, [channel, existingProduct, lookupRetry, offer, path, request, scope, token]);

  useEffect(() => {
    const controller = new AbortController();
    request<{ generate_enabled: boolean; mode?: "partner" }>(
      scope + "/shopee-links", token, { signal: controller.signal },
    ).then((result) => {
      if (!controller.signal.aborted) setGenerationMode(result.generate_enabled ? result.mode ?? "api" : false);
    }).catch(() => { if (!controller.signal.aborted) setGenerationMode(false); });
    return () => controller.abort();
  }, [request, scope, token]);

  useEffect(() => {
    if (!safariCaptureEnabled) return;
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

  async function ensureProduct(origin: string) {
    const canonical = listingUrl(origin);
    const knownListing = listingUrl(existingProduct?.source_url);
    if (!canonical || (offer.kind === "offer" && listingItemId(canonical) !== offer.id) ||
        (knownListing && canonical !== knownListing) || (offer.kind === "catalog" && !knownListing)) {
      throw new Error("URL หน้าสินค้า Shopee ต้องตรงกับสินค้าที่เลือก");
    }
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
    return item;
  }

  async function persist(origin: string, url: string | null, tag: string) {
    setWorking(true);
    onBusy(true);
    try {
      const linkedListing = listingUrl(url ?? undefined);
      if (url !== null && (!isAffiliateLink(url) || (linkedListing && linkedListing !== listingUrl(origin)))) {
        throw new Error("ใช้ลิงก์ Affiliate ที่ Shopee สร้างให้สำหรับรายการสินค้านี้");
      }
      const item = await ensureProduct(origin);
      const result = await request<AffiliateLink>(`${scope}/shopee-links/${item.id}/${channel}`, token, {
        method: url === null ? "POST" : "PUT",
        body: JSON.stringify({ ...(url !== null && { affiliate_url: url }), sub_id: tag.trim() || null }),
      });
      setNewLink(result);
      setSaved({ link: result, item });
      onSave(item);
      setStatus({ text: "", error: false });
    } catch (error) {
      setStatus({ text: error instanceof Error ? error.message : "บันทึกลิงก์ไม่สำเร็จ", error: true });
    } finally {
      onBusy(false);
      setWorking(false);
    }
  }

  async function continueWithLink(selection: SavedLink) {
    setWorking(true);
    onBusy(true);
    try {
      const { item, link } = selection;
      const reviewed = selection.legacy ? link : await request<AffiliateLink>(
        `${scope}/shopee-links/${item.id}/${link.channel}/review`, token, {
          method: "POST", body: JSON.stringify({ affiliate_url: link.affiliate_url, sub_id: link.sub_id }),
        },
      );
      setSaved({ ...selection, link: reviewed });
      onContinue(item, reviewed);
    } catch (error) {
      setVerifiedUrl("");
      setStatus({ text: error instanceof Error ? error.message : "ตรวจลิงก์ไม่สำเร็จ", error: true });
    } finally {
      onBusy(false);
      setWorking(false);
    }
  }

  useEffect(() => {
    if (!portalJob) return;
    const activeJob = portalJob;
    function respond(event: Event) {
      if (!(event instanceof CustomEvent) || typeof event.detail !== "string") return;
      let data: SafariResult & { id?: string };
      try { data = JSON.parse(event.detail); } catch { return; }
      if (data.id !== portalId.current || data.id !== activeJob.id) return;
      if (data.error || (data.affiliate_url && data.source)) {
        portalId.current = "";
        window.clearTimeout(portalTimeout.current);
        setPortalJob(null);
        if (data.error) setStatus({ text: data.error, error: true });
        else if (data.affiliate_url && data.source) {
          const resolved = listingUrl(data.source);
          const expected = activeJob.source ? resolved === activeJob.source : listingItemId(data.source) === activeJob.offerId;
          if (!resolved || !expected || !isAffiliateLink(data.affiliate_url)) {
            setStatus({ text: "ลิงก์ที่ได้รับไม่ตรงกับสินค้าที่เลือก", error: true });
            return;
          }
          setSource(resolved);
          setLink(data.affiliate_url);
          void persist(resolved, data.affiliate_url, activeJob.subId);
        }
      } else if (data.tabId && !activeJob.tabId) {
        const resolved = listingUrl(data.source);
        if (resolved && (activeJob.source === resolved || listingItemId(resolved) === activeJob.offerId)) {
          setSource(resolved);
        }
        setPortalJob((job) => job && job.id === data.id ? { ...job, tabId: data.tabId } : job);
      }
    }
    window.addEventListener("studio:affiliate-response", respond);
    if (dispatchedPortal.current !== portalJob.id) {
      dispatchedPortal.current = portalJob.id;
      window.dispatchEvent(new CustomEvent("studio:affiliate-start", { detail: JSON.stringify(portalJob) }));
    }
    const interval = portalJob.tabId !== undefined ? window.setInterval(() => {
      const { id, tabId } = portalJob;
      window.dispatchEvent(new CustomEvent("studio:affiliate-status", { detail: JSON.stringify({ id, tabId }) }));
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
    setPortalJob({ id, subId, ...(listing ? { source: listing } : { offerId: offer.id }) });
    setStatus({ text: "", error: false });
    portalTimeout.current = window.setTimeout(() => {
      portalId.current = "";
      setPortalJob(null);
      setStatus({ text: "ยังไม่ได้รับลิงก์จาก Shopee ตรวจแท็บ Safari หรือนำลิงก์กลับมาบันทึกเอง", error: true });
    }, 120_000);
  }

  const pending = working || !!portalJob;
  const selectedLink = saved?.link.channel === channel ? saved : null;
  const reviewKey = selectedLink ? `${selectedLink.item.id}/${channel}/${selectedLink.link.affiliate_url}/${selectedLink.link.sub_id}` : "";
  const createdHere = !!selectedLink && newLink?.channel === channel &&
    newLink.affiliate_url === selectedLink.link.affiliate_url;

  useEffect(() => {
    if (generationMode !== false || !autoStart || autoStarted.current || checking || lookupError || !bridgeReady || pending ||
        selectedLink || (offer.kind !== "offer" && !listing)) return;
    autoStarted.current = true;
    startPortal();
  });

  return <section className={inDialog ? "affiliate-setup" : "panel affiliate-setup"}>
    {!inDialog && <div className="panel-head">
      <h2>ลิงก์ Affiliate ของสินค้าที่เลือก</h2>
      <a href="#discover">กลับไปเลือกสินค้า</a>
    </div>}
    {!inDialog && <div className="selected-offer">
      <strong>{offer.name}</strong>
      {trend && <p className="muted">เทรนด์ {trend}</p>}
    </div>}
    <label>ช่องทาง<select value={channel} disabled={pending || checking} onChange={(event) => {
      setChecking(true);
      setStatus({ text: "", error: false });
      setNewLink(null);
      setVerifiedUrl("");
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
        <p role="status"><strong>{createdHere ? "บันทึกลิงก์ใหม่แล้ว" : "พบลิงก์เดิมสำหรับช่องทางนี้"} · {channelLabels[channel]}</strong>
          {selectedLink.link.sub_id && ` · Sub ID ${selectedLink.link.sub_id}`}</p>
        <div>
          <strong>URL หน้าสินค้า Shopee</strong>
          <a className="affiliate-link-url" href={selectedLink.item.source_url} target="_blank" rel="noreferrer">{selectedLink.item.source_url}</a>
        </div>
        <div>
          <strong>ลิงก์ Affiliate จาก Shopee</strong>
          <a className="affiliate-link-url" href={selectedLink.link.affiliate_url} target="_blank" rel="noreferrer">{selectedLink.link.affiliate_url}</a>
        </div>
        {selectedLink.link.shopee_verification === "pending" &&
          <p className="muted">รอตรวจปลายทางใน Shopee เปิดลิงก์แล้วเทียบรายการสินค้า รุ่น และช่องทางก่อนยืนยัน</p>}
        <label className="checkbox"><input type="checkbox" checked={verifiedUrl === reviewKey}
          onChange={(event) => setVerifiedUrl(event.target.checked ? reviewKey : "")} />
          ตรวจแล้วว่าลิงก์เปิดรายการ Shopee เดียวกันและตรงกับช่องทางนี้
        </label>
        <div className="affiliate-setup-actions">
          <button type="button" className="primary" disabled={pending || verifiedUrl !== reviewKey}
            onClick={() => void continueWithLink(selectedLink)}>เตรียม Storyboard</button>
          <button type="button" className="secondary"
            onClick={() => void copy(selectedLink.link.affiliate_url, "คัดลอกลิงก์แล้ว")}>คัดลอกลิงก์</button>
        </div>
      </div> : <>
        <p className="workflow-empty"><strong>ยังไม่พบลิงก์สำหรับ {channelLabels[channel]}</strong> · สร้างลิงก์ใน Shopee แล้วบันทึกกลับมา</p>
        {listing && <div>
          <strong>URL หน้าสินค้า Shopee</strong>
          <a className="affiliate-link-url" href={listing} target="_blank" rel="noreferrer">{listing}</a>
        </div>}
        {safariCaptureEnabled && !generationMode && !bridgeReady && inDialog && <p className="muted">การเปิดฟอร์ม Shopee และรับลิงก์อัตโนมัติต้องใช้ Affiliate Studio Capture ใน Safari</p>}
        {safariCaptureEnabled && !generationMode && bridgeReady && (offer.kind === "offer" || listing) && <div className="affiliate-setup-actions">
          <button type="button" className="primary" disabled={pending} onClick={startPortal}>สร้างใน Shopee</button>
          {portalJob && <>
            <p role="status">{portalJob.tabId === undefined ? "กำลังเปิด Shopee และเตรียม URL สินค้า…" :
              "กรอกข้อมูลใน Shopee แล้ว กด “เอา ลิงก์” เพื่อให้ Studio รับและบันทึกลิงก์อัตโนมัติ"}</p>
            <button type="button" className="secondary" onClick={() => {
              portalId.current = "";
              window.clearTimeout(portalTimeout.current);
              setPortalJob(null);
            }}>ยกเลิกการรอ</button>
          </>}
        </div>}
        <details className="workflow-details" open={generationMode || !safariCaptureEnabled || (!inDialog && !bridgeReady) ? true : undefined}>
          <summary>{generationMode ? "สร้างลิงก์อัตโนมัติหรือบันทึกด้วยตนเอง" : "สร้างหรือบันทึกลิงก์ด้วยตนเอง"}</summary>
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
              {generationMode && <button type="button" className="primary" disabled={!listing || !/^[A-Za-z0-9]{1,100}$/.test(subId)}
                onClick={() => void persist(source, null, subId)}>
                {generationMode === "partner" ? "สร้างลิงก์พาร์ทเนอร์ Shopee" : "สร้างลิงก์อัตโนมัติผ่าน Shopee"}
              </button>}
              <div className="affiliate-setup-actions">
                <button type="button" className="secondary" disabled={!listing}
                  onClick={() => void copy(listing ?? "", "คัดลอก URL สินค้าแล้ว")}>คัดลอก URL สินค้า</button>
                <button type="button" className="secondary" onClick={() => void copy(subId, "คัดลอก Sub ID แล้ว")}>คัดลอก Sub ID</button>
              </div>
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
