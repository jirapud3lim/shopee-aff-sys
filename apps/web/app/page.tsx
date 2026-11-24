"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import AffiliateLinks, { channelLabels } from "@/features/affiliate/affiliate-links";
import AffiliateLinkSetup, { emptyJourney, readJourney, type AffiliateJourney, type AffiliateLink, type CatalogProduct } from "@/features/affiliate/affiliate-link-setup";
import AffiliateResults from "@/features/affiliate/affiliate-results";
import Campaigns from "@/features/publishing/campaigns";
import MetaPublishing from "@/features/publishing/meta-publishing";
import ProductDiscovery, { type DiscoverySelection } from "@/features/discovery/product-discovery";
import ProductWorkflow from "@/features/production/product-workflow";
import PurchasePreviews from "@/features/production/purchase-previews";
import ShopeeOffers from "@/features/discovery/shopee-offers";
import Storyboards, { type Board, type StoryboardSource } from "@/features/production/storyboards";
import TikTokPublishing from "@/features/publishing/tiktok-publishing";
import TrendExplorer from "@/features/discovery/trend-explorer";

type Workspace = { id: string; name: string; role: string };
type Product = CatalogProduct;
type ImportReport = {
  imported: number;
  duplicates: { row: number; source_url: string; reason: string }[];
  errors: { row: number; error: string }[];
};
type Render = { id: string; product_id: string; status: string };
type ReelDraft = { query: string; source: "trend" | "lookup"; scenes: string[] };
type Simulation = {
  id: string;
  render_id: string;
  video_status: string;
  comment_status: string;
  comment_verified: boolean;
  attempts: { phase: string; outcome: string }[];
};

const base = "/api/v1";
const sceneLabels = ["เปิดเรื่อง · 0–5 วิ", "แนะนำสินค้า · 5–10 วิ", "ชวนดูรายละเอียด · 10–15 วิ"];

function shortLine(value: string) {
  const clean = value.trim().replace(/\s+/g, " ");
  const segmenter = new Intl.Segmenter("th", { granularity: "grapheme" });
  if (clean.length <= 54) return clean;
  let trimmed = "";
  for (const { segment } of segmenter.segment(clean)) {
    if (trimmed.length + segment.length > 53) break;
    trimmed += segment;
  }
  return trimmed.trimEnd() + "…";
}
const steps = [
  { anchor: "products", title: "สินค้า", detail: "ข้อมูลสินค้า ลิงก์ และสิทธิ์ใช้ภาพ" },
  { anchor: "video", title: "วิดีโอ", detail: "เรนเดอร์และตรวจตัวอย่าง Reel" },
  { anchor: "simulation", title: "ทดสอบเผยแพร่", detail: "จำลองสถานะโพสต์และคอมเมนต์" },
  { anchor: "meta-publishing", title: "Facebook", detail: "โพสต์ Reel หรือเตรียมคลิปไปปักตะกร้า" },
  { anchor: "tiktok-publishing", title: "TikTok", detail: "เตรียมคลิปและแคปชันสำหรับ TikTok Studio" },
  { anchor: "campaigns", title: "แคมเปญ", detail: "จัดคิวและติดตามงานเผยแพร่" },
];

const marketTools = [
  { anchor: "trends", title: "สำรวจ Google Trends" },
  { anchor: "shopee-offers", title: "จัดอันดับและนำเข้าข้อเสนอ Shopee" },
  { anchor: "products", title: "คลังสินค้า / นำเข้า CSV" },
];
const productionTools = [
  { anchor: "storyboards", title: "Storyboard และแผนที่บันทึกไว้" },
  { anchor: "video", title: "ประกอบ Reel และตรวจวิดีโอ" },
  { anchor: "purchase-previews", title: "Reel จากสินค้าที่เคยซื้อ" },
  { anchor: "campaigns", title: "แคมเปญและคิวเผยแพร่" },
  { anchor: "simulation", title: "ทดสอบเผยแพร่" },
  { anchor: "tiktok-publishing", title: "เตรียมคลิปสำหรับ TikTok" },
];
const resultsTools = [
  { anchor: "affiliate-results", title: "รายงาน Shopee และ Sub ID" },
  { anchor: "meta-publishing", title: "Facebook · เผยแพร่และตรวจ Reel" },
];

function headers(token: string, json = false) {
  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(json ? { "Content-Type": "application/json" } : {}),
  };
}

async function api<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const response = await fetch(base + path, {
    ...init,
    headers: { ...headers(token, typeof init?.body === "string"), ...init?.headers },
  });
  if (!response.ok) {
    const error = await response.json().catch(() => null);
    const detail = error?.detail;
    if (typeof detail === "string") throw new Error(detail);
    if (typeof detail?.message === "string") throw new Error(detail.message);
    if (Array.isArray(detail)) {
      throw new Error(detail.map((item) => `${item.loc?.at(-1) ?? ""} ${item.msg ?? ""}`.trim()).join(" · "));
    }
    throw new Error(`ดำเนินการไม่สำเร็จ (HTTP ${response.status})`);
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

type ChannelLink = { channel: string; affiliate_url: string; sub_id: string | null };

export default function Studio() {
  const [token, setToken] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");
  const authForm = useRef<HTMLFormElement>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceId, setWorkspaceId] = useState("");
  const [products, setProducts] = useState<Product[]>([]);
  const [productId, setProductId] = useState("");
  const [editingId, setEditingId] = useState("");
  const [renders, setRenders] = useState<Render[]>([]);
  const [renderId, setRenderId] = useState("");
  const [preview, setPreview] = useState<{ path: string; url: string } | null>(null);
  const [mediaFiles, setMediaFiles] = useState<File[]>([]);
  const [reelPlan, setReelPlan] = useState("");
  const [draft, setDraft] = useState<ReelDraft | null>(null);
  const [simulation, setSimulation] = useState<Simulation | null>(null);
  const [simulations, setSimulations] = useState<Simulation[]>([]);
  const [busy, setBusy] = useState("");
  const [notice, setNotice] = useState({ text: "", error: false });
  const [importReport, setImportReport] = useState<ImportReport | null>(null);
  const [linkResult, setLinkResult] = useState<{ path: string; links: ChannelLink[] } | null>(null);
  const [linkChannel, setLinkChannel] = useState("facebook");
  const [anchor, setAnchor] = useState("");
  const [affiliateJourney, setAffiliateJourney] = useState<AffiliateJourney>(emptyJourney);
  const [productFlow, setProductFlow] = useState<{
    product: DiscoverySelection; initialAffiliate?: { item: CatalogProduct; link: AffiliateLink };
  }>();
  const [linkRevision, setLinkRevision] = useState(0);
  const [boardDraft, setBoardDraft] = useState<(StoryboardSource & { workspace: string }) | null>(null);
  const product = products.find((item) => item.id === productId);
  const editingProduct = products.find((item) => item.id === editingId);
  const render = renders.find((item) => item.id === renderId);
  const scope = `/workspaces/${workspaceId}`;
  const videoPath = `${scope}/renders/${renderId}/video`;
  const video = preview?.path === videoPath && render?.product_id === productId ? preview.url : "";
  const linkPath = productId ? `${scope}/products/${productId}/channel-links` : "";
  const channelLinks = linkResult?.path === linkPath ? linkResult.links : [];
  const activeLink = channelLinks.find((link) => link.channel === linkChannel);
  const facebookAffiliate = channelLinks.find((link) => link.channel === "facebook")?.affiliate_url;
  const showingResults = anchor === "affiliate-results";
  const showingDiscovery = anchor === "" || anchor === "discover";
  const showingLinks = anchor === "affiliate-links";
  const showingOffers = anchor === "shopee-offers";
  const showingStoryboards = anchor === "storyboards";
  const showingTrends = anchor === "trends";
  const showingPurchases = anchor === "purchase-previews";
  const [recentStoryboard, setRecentStoryboard] = useState<Board>();
  const marketActive = showingDiscovery || marketTools.some((item) => item.anchor === anchor);
  const productionActive = productionTools.some((item) => item.anchor === anchor);
  const resultsActive = resultsTools.some((item) => item.anchor === anchor);
  const showingWorkspace = ["products", "video", "simulation", "meta-publishing", "tiktok-publishing", "campaigns"].includes(anchor);
  const contextualTools = marketActive ? marketTools : productionActive ? productionTools : resultsActive ? resultsTools : [];

  useEffect(() => {
    const match = /^#review-login=([a-f0-9]{64})$/.exec(window.location.hash);
    if (!match) return;
    window.history.replaceState(window.history.state, "", window.location.pathname + window.location.search);
    void fetch("/api/review-prefill", {
      method: "POST",
      headers: { "x-studio-review-nonce": match[1] },
      cache: "no-store",
    }).then(async (response) => {
      if (!response.ok) return;
      const credentials: { email: string; password: string } = await response.json();
      const form = authForm.current;
      if (form?.dataset.mode !== "login") return;
      const email = form.elements.namedItem("email");
      const password = form.elements.namedItem("password");
      if (email instanceof HTMLInputElement && password instanceof HTMLInputElement) {
        // The one-time review launch selects the QA account even if Safari filled another login.
        email.value = credentials.email;
        password.value = credentials.password;
      }
    }).catch(() => {
      // Leave the form available for manual sign-in.
    });
  }, []);

  useEffect(() => {
    const syncAnchor = () => setAnchor(window.location.hash.slice(1));
    syncAnchor();
    window.addEventListener("hashchange", syncAnchor);
    return () => window.removeEventListener("hashchange", syncAnchor);
  }, []);

  useEffect(() => {
    if (!workspaceId) return;
    const target = document.getElementById(anchor || "discover");
    if (anchor === "discover" || !anchor) window.scrollTo(0, 0);
    else target?.scrollIntoView();
    if (!showingWorkspace) target?.querySelector("h1")?.focus({ preventScroll: true });
    if (["products", "video", "tiktok-publishing"].includes(anchor)) target?.querySelector("h2")?.focus({ preventScroll: true });
  }, [anchor, showingWorkspace, workspaceId]);

  useEffect(() => {
    if (!workspaceId || !token || !showingDiscovery || productFlow) return;
    const controller = new AbortController();
    setRecentStoryboard(undefined);
    api<Board[]>(scope + "/storyboards", token, { signal: controller.signal }).then((boards) => {
      if (!controller.signal.aborted) setRecentStoryboard(boards[0]);
    }).catch(() => {});
    return () => controller.abort();
  }, [productFlow, scope, showingDiscovery, token, workspaceId]);

  useEffect(() => {
    if (!linkPath || !token) return;
    const controller = new AbortController();
    api<ChannelLink[]>(linkPath, token, { signal: controller.signal }).then((links) => {
      if (!controller.signal.aborted) setLinkResult({ path: linkPath, links });
    }).catch((error) => {
      if (!controller.signal.aborted) setNotice({ text: error.message, error: true });
    });
    return () => controller.abort();
  }, [linkPath, token]);

  function saveChannelLink(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    void run("channel-link", async () => {
      const saved = await api<ChannelLink>(`${linkPath}/${linkChannel}`, token, {
        method: "PUT",
        body: JSON.stringify({
          affiliate_url: data.get("channel_url"),
          sub_id: String(data.get("sub_id") ?? "").trim() || null,
        }),
      });
      setLinkResult((previous) => ({
        path: linkPath,
        links: [...(previous?.path === linkPath ? previous.links : []).filter((link) => link.channel !== saved.channel), saved],
      }));
      setNotice({ text: "บันทึกลิงก์ตามช่องทางแล้ว", error: false });
    });
  }

  useEffect(() => {
    if (!workspaceId || !token) return;
    const controller = new AbortController();
    let active = true;
    const init = { signal: controller.signal };
    Promise.all([
      api<Product[]>(scope + "/products", token, init),
      api<Render[]>(scope + "/renders", token, init),
      api<Simulation[]>(scope + "/publishing/simulations", token, init),
    ]).then(([items, media, saved]) => {
      if (!active) return;
      setProducts(items);
      setProductId((selected) => items.some((item) => item.id === selected) ? selected : (items[0]?.id ?? ""));
      setRenders(media);
      setSimulations(saved);
    }).catch((error) => {
      if (active) setNotice({ text: error.message, error: true });
    });
    return () => { active = false; controller.abort(); };
  }, [scope, token, workspaceId]);

  useEffect(() => {
    if (!workspaceId || !token || !renderId || render?.status !== "completed") return;
    const controller = new AbortController();
    let active = true;
    let objectUrl = "";
    fetch(base + videoPath, {
      headers: headers(token),
      signal: controller.signal,
    }).then((response) => {
      if (!response.ok) throw new Error("เปิดตัวอย่างวิดีโอไม่ได้");
      return response.blob();
    }).then((blob) => {
      if (!active) return;
      objectUrl = URL.createObjectURL(blob);
      setPreview({ path: videoPath, url: objectUrl });
    }).catch((error) => {
      if (active) setNotice({ text: error.message, error: true });
    });
    return () => {
      active = false;
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      setPreview(null);
    };
  }, [render?.status, renderId, token, videoPath, workspaceId]);

  function selectWorkspace(id: string) {
    setMediaFiles([]);
    setReelPlan("");
    setProducts([]);
    setProductId("");
    setEditingId("");
    setRenders([]);
    setRenderId("");
    setDraft(null);
    setSimulation(null);
    setSimulations([]);
    setImportReport(null);
    setNotice({ text: "", error: false });
    setAffiliateJourney(readJourney(id));
    setProductFlow(undefined);
    setWorkspaceId(id);
  }

  function goToAffiliateStep(next: AffiliateJourney, step: string) {
    setAffiliateJourney(next);
    try {
      sessionStorage.setItem(`affiliate-journey:${workspaceId}`, JSON.stringify(next));
    } catch {
      // The current tab can continue without browser storage.
    }
    window.location.hash = step;
  }

  function chooseProduct(selection: DiscoverySelection, trend = selection.trend?.title ?? "") {
    const next = { trend, offer: selection.selection };
    setAffiliateJourney(next);
    try {
      sessionStorage.setItem(`affiliate-journey:${workspaceId}`, JSON.stringify(next));
    } catch {
      // The current tab can continue without browser storage.
    }
    setNotice({ text: "", error: false });
    setProductFlow({ product: selection });
  }

  function saveWorkflowProduct(item: CatalogProduct) {
    setProducts((current) => current.some((product) => product.id === item.id) ? current : [item, ...current]);
    setLinkRevision((revision) => revision + 1);
  }

  function selectProduct(id: string) {
    if (id !== productId) {
      setDraft(null);
      setMediaFiles([]);
      setReelPlan("");
    }
    setProductId(id);
    setEditingId("");
    setRenderId("");
    setSimulation(null);
  }

  function selectRender(id: string) {
    setRenderId(id);
    setSimulation(simulations.find((item) => item.render_id === id) ?? null);
  }

  function openReportProduct(id: string) {
    selectProduct(id);
    window.location.hash = "products";
  }

  function openStoryboard(kind: StoryboardSource["kind"], id: string, name: string) {
    setBoardDraft({ kind, id, name, workspace: workspaceId });
    window.location.hash = "storyboards";
  }

  function prepareReel(id: string, query: string, source: ReelDraft["source"]) {
    const selected = products.find((item) => item.id === id);
    if (!selected) {
      setNotice({ text: "ไม่พบสินค้าในคลังของพื้นที่ทำงานนี้", error: true });
      return;
    }
    selectProduct(id);
    setDraft({
      query, source, scenes: [
        "กำลังมองหาอยู่ไหม?\n" + shortLine(query),
        shortLine(selected.name),
        "ดูรายละเอียดสินค้าก่อนตัดสินใจ",
      ],
    });
    setNotice({ text: "", error: false });
    window.location.hash = "video";
  }

  async function run(label: string, action: () => Promise<void>) {
    if (busy) return;
    setBusy(label);
    setNotice({ text: "", error: false });
    try {
      await action();
    } catch (error) {
      setNotice({ text: error instanceof Error ? error.message : "เกิดข้อผิดพลาด", error: true });
    } finally {
      setBusy("");
    }
  }

  function authenticate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    void run(mode, async () => {
      const { token: access } = await api<{ token: string }>(`/auth/${mode}`, "", {
        method: "POST",
        body: JSON.stringify({ email: data.get("email"), password: data.get("password") }),
      });
      const owned = await api<Workspace[]>("/workspaces", access);
      setWorkspaces(owned);
      selectWorkspace(owned[0]?.id ?? "");
      setToken(access);
    });
  }

  function createWorkspace(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    void run("workspace", async () => {
      await api("/workspaces", token, { method: "POST", body: JSON.stringify({ name: data.get("name") }) });
      const available = await api<Workspace[]>("/workspaces", token);
      const created = available.find((item) => !workspaces.some((known) => known.id === item.id));
      setWorkspaces(available);
      selectWorkspace(created?.id ?? available[0]?.id ?? "");
      form.reset();
    });
  }

  function saveProduct(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    void run("product", async () => {
      const path = scope + "/products" + (editingId ? `/${editingId}` : "");
      const created = await api<Product>(path, token, {
        method: editingId ? "PATCH" : "POST",
        body: JSON.stringify({
          name: data.get("name"),
          source_url: data.get("source_url"),
          affiliate_url: data.get("affiliate_url") || null,
          image_rights_note: data.get("image_rights_note") || null,
        }),
      });
      setProducts((items) => editingId
        ? items.map((item) => item.id === created.id ? created : item)
        : [created, ...items]);
      if (editingId) setEditingId("");
      else selectProduct(created.id);
      form.reset();
      setNotice({ text: editingId ? "บันทึกข้อมูลสินค้าแล้ว" : "เพิ่มสินค้าแล้ว", error: false });
    });
  }

  function importProducts(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    void run("import", async () => {
      const result = await api<ImportReport>(scope + "/products/import", token, { method: "POST", body: data });
      const items = await api<Product[]>(scope + "/products", token);
      setProducts(items);
      if (!productId && items.length) selectProduct(items[0].id);
      setImportReport(result);
      form.reset();
      setNotice({ text: "ตรวจไฟล์ CSV แล้ว", error: false });
    });
  }

  function createVideo(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const hasFootage = mediaFiles.some((file) => file.type.startsWith("video/") || /\.(mp4|mov)$/i.test(file.name));
    const plan = reelPlan.trim();
    if (!mediaFiles.length || (!plan && !hasFootage && mediaFiles.length < 4)) {
      setNotice({ text: "เลือกคลิปสินค้าหรือภาพสินค้าอย่างน้อย 4 ภาพ", error: true });
      return;
    }
    if (plan) {
      try { JSON.parse(plan); } catch {
        setNotice({ text: "ตรวจรูปแบบ JSON ของแผนก่อนสร้างวิดีโอ", error: true });
        return;
      }
      data.set("reel_plan", plan);
      data.delete("scene_texts");
    }
    mediaFiles.forEach((file) => data.append("media", file));
    data.set("product_id", productId);
    void run("render", async () => {
      const result = await api<Render>(scope + "/renders", token, { method: "POST", body: data });
      setRenders((items) => [result, ...items]);
      selectRender(result.id);
      setNotice({ text: result.status === "completed" ? "วิดีโอพร้อมดูตัวอย่าง" : "เรนเดอร์ไม่สำเร็จ", error: result.status !== "completed" });
    });
  }

  function simulate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    void run("simulate", async () => {
      const result = await api<Simulation>(scope + "/publishing/simulations", token, {
        method: "POST",
        body: JSON.stringify({ render_id: renderId, caption: data.get("caption"), include_comment: data.has("comment") }),
      });
      setSimulation(result);
      setSimulations((items) => [result, ...items.filter((item) => item.id !== result.id)]);
    });
  }

  function logout() {
    void run("logout", async () => {
      await api("/auth/logout", token, { method: "POST" });
      selectWorkspace("");
      setWorkspaces([]);
      setToken("");
    });
  }

  const status = notice.text && (
    <p role={notice.error ? "alert" : "status"} className={`notice ${notice.error ? "error" : ""}`}>{notice.text}</p>
  );

  const videoEditor = (
    <form key={productId} onSubmit={createVideo}>
      <h3>สร้าง Reel จากฟุตเทจและภาพสินค้า</h3>
      <p className="muted">{product ? product.name : "เลือกสินค้าในคลังสินค้าก่อน"}</p>
      {draft && !reelPlan.trim() && <fieldset disabled={!!busy} className="reel-script">
        <legend>สคริปต์ Reel</legend>
        <p className="muted">{draft.source === "trend" ? "เทรนด์" : "คำค้น"} · {draft.query}</p>
        <p className="muted">แก้ข้อความที่จะขึ้นบนจอได้ ฉากละไม่เกิน 3 บรรทัด</p>
        {draft.scenes.map((text, index) => <label key={sceneLabels[index]}>{sceneLabels[index]}
          <textarea name="scene_texts" required maxLength={120} rows={2} value={text}
            onChange={(event) => {
              const value = event.target.value;
              setDraft({ ...draft, scenes: draft.scenes.map((scene, i) => i === index ? value : scene) });
            }} />
        </label>)}
        <button className="text-button" type="button" onClick={() => setDraft(null)}>นำสคริปต์ออก</button>
      </fieldset>}
      {product && !product.image_rights_note && <p className="muted">บันทึกสิทธิ์ใช้ฟุตเทจและภาพในคลังสินค้าก่อนเรนเดอร์</p>}
      <label>เพิ่มคลิปหรือภาพสินค้า
        <input type="file" accept=".mp4,.mov,image/jpeg,image/png,image/webp" multiple disabled={!!busy}
          onChange={(event) => {
            const next = [...mediaFiles, ...Array.from(event.currentTarget.files ?? [])];
            event.currentTarget.value = "";
            if (next.length > 12 || next.reduce((size, file) => size + file.size, 0) > 64 * 1024 * 1024) {
              setNotice({ text: "เพิ่มได้ไม่เกิน 12 ไฟล์ รวมไม่เกิน 64 MiB", error: true });
              return;
            }
            setMediaFiles(next);
            setNotice({ text: "", error: false });
          }} />
      </label>
      <p className="muted">ใช้คลิป MP4/MOV ร่วมกับภาพได้ แนะนำให้เปิดด้วยคลิปที่เห็นสินค้าชัด
        ถ้าใช้ภาพอย่างเดียวให้เลือก 4–12 ภาพ ถ้าใช้คลิปอย่างเดียวให้มีฟุตเทจรวมอย่างน้อย 15 วินาที
        ตัวอย่างไม่มีเสียงจากคลิปต้นฉบับ</p>
      {mediaFiles.length > 0 && <ol className="reel-media" aria-label="ลำดับไฟล์ใน Reel">
        {mediaFiles.map((file, index) => <li key={index}>
          <span><strong>A{index + 1}</strong> · {file.name}</span>
          {[-1, 1].map((direction) => <button key={direction} type="button" className="text-button"
            disabled={!!busy || index + direction < 0 || index + direction >= mediaFiles.length}
            aria-label={`${direction < 0 ? "เลื่อนขึ้น" : "เลื่อนลง"} ${file.name}`}
            onClick={() => {
              const target = index + direction;
              setMediaFiles((files) => {
                const next = [...files];
                [next[index], next[target]] = [next[target], next[index]];
                return next;
              });
            }}>{direction < 0 ? "ขึ้น" : "ลง"}</button>)}
          <button type="button" className="text-button" disabled={!!busy}
            aria-label={`นำ ${file.name} ออก`}
            onClick={() => setMediaFiles((files) => files.filter((_, position) => position !== index))}>นำออก</button>
        </li>)}
      </ol>}
      <details open={reelPlan ? true : undefined}>
        <summary>ตัดตามแผน Master Prompt v2</summary>
        <label>ไฟล์แผน JSON
          <input type="file" accept=".json,application/json" disabled={!!busy} onChange={async (event) => {
            const file = event.currentTarget.files?.[0];
            event.currentTarget.value = "";
            if (!file) return;
            if (file.size > 32_768) {
              setNotice({ text: "ไฟล์แผน JSON ต้องไม่เกิน 32 KiB", error: true });
              return;
            }
            const input = event.currentTarget;
            try {
              const contents = await file.text();
              if (input.isConnected) setReelPlan(contents);
            } catch {
              setNotice({ text: "เปิดไฟล์แผน JSON ไม่ได้", error: true });
            }
          }} />
        </label>
        <label>แผน Master Prompt v2 (JSON)
          <textarea rows={7} value={reelPlan} maxLength={32768} disabled={!!busy}
            onChange={(event) => setReelPlan(event.target.value)} />
        </label>
        <p className="muted">ใช้ A1–A12 ตามลำดับไฟล์ด้านบน แผนต้องเริ่มที่ 0 และจบที่ 15 วินาที
          รองรับภาพนิ่งและช่วงเวลาของคลิป ระบุซับใน subtitle_th เว้นแผนว่างเพื่อแบ่งเวลาอัตโนมัติ</p>
      </details>
      <button className="primary" disabled={!!busy || !product?.image_rights_note}>{busy === "render" ? "กำลังเรนเดอร์…" : "สร้างวิดีโอ"}</button>
    </form>
  );
  const videoPicker = (
    <label>ตัวอย่างที่บันทึกไว้<select value={renderId} onChange={(event) => selectRender(event.target.value)} disabled={!!busy}>
      <option value="">เลือกวิดีโอ</option>
      {renders.filter((item) => item.product_id === productId).map((item) => <option key={item.id} value={item.id}>{item.status === "completed" ? "พร้อมดู" : "เรนเดอร์ไม่สำเร็จ"} · {item.id.slice(0, 8)}</option>)}
    </select></label>
  );

  if (!token) {
    return (
      <main className="entry">
        <section className="entry-intro">
          <p className="wordmark"><span className="mark">A</span> Affiliate Studio</p>
          <h1>จากสินค้า<br />ถึงวิดีโอพร้อมโพสต์</h1>
          <p>จัดเก็บลิงก์สินค้า เรนเดอร์คลิปแนวตั้ง และดูผลทดสอบการเผยแพร่ในพื้นที่ทำงานเดียว</p>
          <div className="entry-steps">
            {steps.map((step) => <div key={step.anchor}><strong>{step.title}</strong><span>{step.detail}</span></div>)}
          </div>
        </section>
        <section className="entry-form">
          <div className="form-card">
            <h2>{mode === "login" ? "เข้าสู่ระบบ" : "สร้างบัญชี"}</h2>
            <p className="muted">ใช้บัญชีสำหรับพื้นที่ทำงานของคุณ</p>
            <form ref={authForm} data-mode={mode} method="post" onSubmit={authenticate}>
              <label>อีเมล<input type="email" name="email" required autoComplete="email" /></label>
              <label>รหัสผ่าน<input type="password" name="password" required minLength={mode === "register" ? 12 : 1} autoComplete={mode === "register" ? "new-password" : "current-password"} /></label>
              <button className="primary" disabled={!!busy}>{busy ? "กำลังดำเนินการ…" : mode === "login" ? "เข้าสู่ระบบ" : "สร้างบัญชี"}</button>
            </form>
            {status}
            <button type="button" className="text-button" onClick={() => { setMode(mode === "login" ? "register" : "login"); setNotice({ text: "", error: false }); }}>
              {mode === "login" ? "สร้างบัญชีใหม่" : "กลับไปเข้าสู่ระบบ"}
            </button>
          </div>
        </section>
      </main>
    );
  }

  return (
    <div className="shell variant-a">
      <header className="sidebar">
        <a className="wordmark studio-brand" href="#discover"><span className="mark">A</span> Shopee Affiliate Studio</a>
        <details className="workspace" open={!workspaceId || undefined}>
          <summary>{workspaces.find((item) => item.id === workspaceId)?.name ?? "พื้นที่ทำงาน"}</summary>
          <label>พื้นที่ทำงาน<select value={workspaceId} disabled={!!busy} onChange={(event) => selectWorkspace(event.target.value)}>
            {!workspaces.length && <option value="">ยังไม่มีพื้นที่ทำงาน</option>}
            {workspaces.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select></label>
          <details open={!workspaceId}>
            <summary>เพิ่มพื้นที่ทำงาน</summary>
            <form onSubmit={createWorkspace}>
              <label>ชื่อพื้นที่ทำงาน<input name="name" required maxLength={100} /></label>
              <button className="secondary" disabled={!!busy}>สร้างพื้นที่ทำงาน</button>
            </form>
          </details>
        </details>
        {workspaceId && <nav aria-label="เมนู Studio">
          <a href="#discover" aria-current={marketActive ? "location" : undefined}>ตลาดสินค้า</a>
          <a href="#affiliate-links" aria-current={showingLinks ? "location" : undefined}>ลิงก์ Affiliate</a>
          <a href="#storyboards" aria-current={productionActive ? "location" : undefined}>งานผลิต</a>
          <a href="#affiliate-results" aria-current={resultsActive ? "location" : undefined}>ผลลัพธ์</a>
        </nav>}
        <button type="button" className="text-button logout" onClick={logout} disabled={!!busy}>ออกจากระบบ</button>
      </header>
      <main className="main">
        {!workspaceId && <header className="workspace-header"><h1>สตูดิโอ Reel</h1><span className="mode-tag">โหมดทดสอบ</span></header>}
        <div aria-live="polite">{status}</div>
        {!workspaceId && <section className="panel empty"><h2>เริ่มจากสร้างพื้นที่ทำงาน</h2><p>เพิ่มชื่อพื้นที่ทำงานเพื่อเริ่มจัดเก็บสินค้าและวิดีโอ</p></section>}
        {workspaceId && <>
          {!!contextualTools.length && <details className="studio-toolbox">
            <summary>{marketActive ? "เครื่องมือสินค้า" : productionActive ? "เครื่องมือสำหรับงานผลิต" : "เครื่องมือรายงานและตรวจโพสต์"}</summary>
            <ul>{contextualTools.map(({ anchor: destination, title }) => <li key={destination}>
              <a href={`#${destination}`} aria-current={anchor === destination ? "page" : undefined}>{title}</a>
            </li>)}</ul>
          </details>}
          {showingDiscovery && <ProductDiscovery key={`discover/${workspaceId}`} scope={scope} token={token}
            products={products} request={api} onChoose={chooseProduct} linkRevision={linkRevision}
            recentWork={recentStoryboard ? { name: recentStoryboard.product_name, reviewed: !!recentStoryboard.approved_scenes.length } : undefined} />}
          <div hidden={!showingPurchases}>
            <PurchasePreviews key={workspaceId} active={showingPurchases} scope={scope} token={token} request={api} />
          </div>
          <div hidden={!showingLinks}>
            <AffiliateLinks key={workspaceId} active={showingLinks} busy={!!busy} scope={scope} revision={linkRevision}
              token={token} onProduct={openReportProduct} request={api}
              setup={showingLinks && affiliateJourney.offer && <AffiliateLinkSetup
                key={`${workspaceId}/${affiliateJourney.offer.id}`}
                trend={affiliateJourney.trend} offer={affiliateJourney.offer}
                scope={scope} token={token} request={api} products={products}
                onBusy={(saving) => setBusy(saving ? "affiliate-journey" : "")}
                onSave={saveWorkflowProduct}
                onContinue={(item, link) => {
                  selectProduct(item.id);
                  setProductFlow({
                    product: { selection: { kind: "catalog", id: item.id, name: item.name } },
                    initialAffiliate: { item, link },
                  });
                }} />} />
          </div>
          <div hidden={!showingResults}>
            <AffiliateResults key={workspaceId} active={showingResults} busy={!!busy} scope={scope}
              token={token} products={products} onProduct={openReportProduct} request={api} />
          </div>
          <div hidden={!showingOffers}>
            <ShopeeOffers key={workspaceId} active={showingOffers} scope={scope} token={token} request={api}
              trend={affiliateJourney.trend} onStoryboard={(id, name) => openStoryboard("offer", id, name)}
              onChooseOffer={(id, name) => chooseProduct({ selection: { kind: "offer", id, name } }, affiliateJourney.trend)} />
          </div>
          {showingStoryboards && <Storyboards key={workspaceId} scope={scope} token={token} request={api}
            source={boardDraft?.workspace === workspaceId ? boardDraft : null} onCloseDraft={() => setBoardDraft(null)} />}
          <div hidden={!showingTrends}>
            <TrendExplorer key={workspaceId} active={showingTrends} scope={scope} token={token}
              busy={!!busy} onProduct={openReportProduct} onPrepare={prepareReel}
              onChooseTrend={(trend) => goToAffiliateStep({ trend, offer: null }, "shopee-offers")}
              onStoryboard={(id, name) => openStoryboard("catalog", id, name)} request={api} />
          </div>
          <div className="studio-view" hidden={!showingWorkspace}>
          <section className="panel" id="products" hidden={anchor !== "products"}>
            <div className="panel-head"><h2 tabIndex={-1}>คลังสินค้า</h2><span>{products.length} รายการ</span></div>
            <div className="columns">
              <form key={editingId || "new"} onSubmit={saveProduct}>
                <h3>{editingId ? "แก้ไขสินค้า" : "เพิ่มสินค้า"}</h3>
                <label>ชื่อสินค้า<input name="name" required maxLength={300} defaultValue={editingProduct?.name} /></label>
                <label>ลิงก์สินค้า<input name="source_url" type="url" required maxLength={2083} defaultValue={editingProduct?.source_url} placeholder="https://" /></label>
                <label>ลิงก์ Affiliate สำรอง<input name="affiliate_url" type="url" maxLength={2083} defaultValue={editingProduct?.affiliate_url ?? ""} placeholder="https://" /></label>
                <label>สิทธิ์ใช้ภาพและวิดีโอ<textarea name="image_rights_note" maxLength={2000} defaultValue={editingProduct?.image_rights_note ?? ""} rows={2} placeholder="เช่น ภาพถ่ายของร้านที่อนุญาตให้ใช้" /></label>
                <button className="primary" disabled={!!busy}>{busy === "product" ? "กำลังบันทึก…" : editingId ? "บันทึกการแก้ไข" : "เพิ่มสินค้า"}</button>
                {editingId && <button type="button" className="text-button" onClick={() => setEditingId("")} disabled={!!busy}>ยกเลิกการแก้ไข</button>}
              </form>
              <div className="column">
                <label>สินค้าที่จะใช้<select value={productId} onChange={(event) => selectProduct(event.target.value)} disabled={!!busy}>
                  <option value="">เลือกสินค้า</option>
                  {products.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                </select></label>
                {product && <>
                  <p className="product-info">{product.image_rights_note ? `สิทธิ์ใช้ภาพ · ${product.image_rights_note}` : "ยังไม่มีข้อมูลสิทธิ์ใช้ภาพ"}</p>
                  <button type="button" className="text-button" onClick={() => setEditingId(product.id)} disabled={!!busy}>แก้ไขสินค้าที่เลือก</button>
                </>}
                <form onSubmit={importProducts} className="import">
                  <h3>นำเข้าจาก CSV</h3>
                  <label>ไฟล์ CSV<input name="file" type="file" accept=".csv,text/csv" required /></label>
                  <p className="muted csv-columns">name, source_url, affiliate_url, image_rights_note<br />คอลัมน์เสริม: affiliate_channel, affiliate_sub_id</p>
                  <button className="secondary" disabled={!!busy}>นำเข้า CSV</button>
                </form>
                {importReport && <details open>
                  <summary>นำเข้า {importReport.imported} · ซ้ำ {importReport.duplicates.length} · ข้อผิดพลาด {importReport.errors.length}</summary>
                  <ul>
                    {importReport.duplicates.map((item) => <li key={item.row}>แถว {item.row} · ลิงก์ซ้ำ</li>)}
                    {importReport.errors.map((item) => <li key={item.row}>แถว {item.row} · {item.error}</li>)}
                  </ul>
                </details>}
              </div>
            </div>
          </section>
          {product && <section className="panel" hidden={anchor !== "products"} aria-label="ลิงก์ Affiliate ตามช่องทาง">
            <div className="panel-head"><h2>ลิงก์ Affiliate ตามช่องทาง</h2></div>
            <div className="columns">
              <div className="column">
                <label>ช่องทาง<select value={linkChannel} onChange={(event) => setLinkChannel(event.target.value)} disabled={!!busy}>
                  {Object.entries(channelLabels).map(([key, label]) => <option value={key} key={key}>{label}</option>)}
                </select></label>
                {linkResult?.path === linkPath && <form key={`${linkPath}/${linkChannel}/${activeLink?.affiliate_url ?? ""}/${activeLink?.sub_id ?? ""}`} onSubmit={saveChannelLink}>
                  <label>ลิงก์ที่สร้างจาก Shopee<input type="url" name="channel_url" required maxLength={2083} defaultValue={activeLink?.affiliate_url} /></label>
                  <label>Sub ID<input name="sub_id" pattern="[A-Za-z0-9]+" maxLength={100} defaultValue={activeLink?.sub_id ?? ""} /></label>
                  <button className="primary" disabled={!!busy}>บันทึกลิงก์ช่องทาง</button>
                </form>}
              </div>
              <div className="column">
                {channelLinks.length ? channelLinks.map((link) => <div key={link.channel}>
                  <strong>{channelLabels[link.channel] ?? link.channel}</strong>
                  {link.sub_id && <p>Sub ID · {link.sub_id}</p>}
                  <button className="text-button" type="button" onClick={() => void run("copy-link", async () => {
                    await navigator.clipboard.writeText(link.affiliate_url);
                    setNotice({ text: "คัดลอกลิงก์แล้ว", error: false });
                  })}>คัดลอกลิงก์ {channelLabels[link.channel] ?? link.channel}</button>
                </div>) : <p className="muted">ยังไม่มีลิงก์แยกตามช่องทาง</p>}
              </div>
            </div>
          </section>}
          <section className="panel" id="video" hidden={anchor !== "video"}>
            <div className="panel-head"><h2 tabIndex={-1}>วิดีโอแนวตั้ง</h2><span>9:16 · 15 วินาที</span></div>
            <div className="columns">
              <div className="column">
                <label>สินค้าสำหรับวิดีโอ<select value={productId} disabled={!!busy}
                  onChange={(event) => selectProduct(event.target.value)}>
                  <option value="">เลือกสินค้า</option>
                  {products.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                </select></label>
                {!productFlow && <>{videoEditor}{videoPicker}</>}
              </div>
              <div className="preview">
                {video ? <video key={video} src={video} controls playsInline /> : <div className="preview-empty"><span aria-hidden="true">▶</span><p>ตัวอย่าง Reel</p></div>}
              </div>
            </div>
          </section>
          <section className="panel" id="simulation" hidden={anchor !== "simulation"}>
            <div className="panel-head"><h2>ทดสอบเผยแพร่</h2><span>Meta จำลอง</span></div>
            <div className="columns">
              <form onSubmit={simulate}>
                <label>แคปชัน<textarea key={renderId} name="caption" required maxLength={500} rows={4} defaultValue={product?.name ?? ""} /></label>
                <label className="checkbox"><input name="comment" type="checkbox" disabled={!facebookAffiliate && !product?.affiliate_url} /> จำลองคอมเมนต์ลิงก์ Affiliate</label>
                <button disabled={!!busy || render?.status !== "completed" || !video} className="primary">{busy === "simulate" ? "กำลังทดสอบ…" : "จำลองการเผยแพร่"}</button>
              </form>
              <div className="result">
                <h3>ผลจำลอง</h3>
                {simulation ? <>
                  <dl><div><dt>วิดีโอ</dt><dd>{simulation.video_status}</dd></div><div><dt>คอมเมนต์</dt><dd>{simulation.comment_status}</dd></div><div><dt>อ่านคอมเมนต์กลับ</dt><dd>{simulation.comment_verified ? "ยืนยันแล้ว" : "—"}</dd></div></dl>
                  <details><summary>ประวัติการส่งและตรวจสถานะ</summary><ul>{simulation.attempts.map((item, index) => <li key={index}>{item.phase} · {item.outcome}</li>)}</ul></details>
                </> : <p className="muted">จะเห็นผลที่นี่หลังจำลองการเผยแพร่</p>}
              </div>
            </div>
          </section>
          {["simulation", "meta-publishing", "tiktok-publishing"].includes(anchor) && <div className="panel studio-publish-source">
            {videoPicker}
            <a href="#video">เลือกสินค้าและจัดการวิดีโอ</a>
          </div>}
          <div hidden={anchor !== "meta-publishing"}><MetaPublishing key={`meta/${workspaceId}`} request={api} scope={scope} token={token}
            renderId={renderId} videoUrl={video} productName={product?.name ?? ""}
            productUrl={product?.source_url} facebookAffiliateUrl={facebookAffiliate}
            affiliateUrl={facebookAffiliate ?? product?.affiliate_url} /></div>
          <div hidden={anchor !== "tiktok-publishing"}><TikTokPublishing key={`${workspaceId}/${productId}/${renderId}`}
            renderId={renderId} videoUrl={video} productName={product?.name ?? ""} /></div>
          <div hidden={anchor !== "campaigns"}><Campaigns key={workspaceId} scope={scope} token={token} active={anchor === "campaigns"}
            canManage={workspaces.find((workspace) => workspace.id === workspaceId)?.role === "owner"}
            renders={renders.filter((item) => item.status === "completed").map((item) => ({
              id: item.id, name: products.find((candidate) => candidate.id === item.product_id)?.name ?? item.id,
            }))} request={api} /></div>
          </div>
        </>}
      </main>
      {productFlow && <ProductWorkflow selection={productFlow.product} initialAffiliate={productFlow.initialAffiliate}
        scope={scope} token={token} products={products} request={api} onSave={saveWorkflowProduct}
        onContinue={(item) => { if (item.id !== productId) selectProduct(item.id); }}
        onClose={() => setProductFlow(undefined)} videoEditor={videoEditor} videoPicker={videoPicker}
        video={video} renderId={renderId} notice={status} />}
    </div>
  );
}
