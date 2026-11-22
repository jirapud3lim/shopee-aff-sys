"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import AffiliateResults from "./affiliate-results";
import Campaigns from "./campaigns";
import MetaPublishing from "./meta-publishing";
import ShopeeOffers from "./shopee-offers";
import TrendExplorer from "./trend-explorer";

type Workspace = { id: string; name: string; role: string };
type Product = {
  id: string;
  name: string;
  source_url: string;
  affiliate_url: string | null;
  image_rights_note: string | null;
};
type ImportReport = {
  imported: number;
  duplicates: { row: number; source_url: string; reason: string }[];
  errors: { row: number; error: string }[];
};
type Render = { id: string; product_id: string; status: string };
type Simulation = {
  id: string;
  render_id: string;
  video_status: string;
  comment_status: string;
  comment_verified: boolean;
  attempts: { phase: string; outcome: string }[];
};

const base = "/api/v1";
const steps = [
  { anchor: "products", title: "สินค้า", detail: "ข้อมูลสินค้า ลิงก์ และสิทธิ์ใช้ภาพ" },
  { anchor: "video", title: "วิดีโอ", detail: "เรนเดอร์และตรวจตัวอย่าง Reel" },
  { anchor: "simulation", title: "ทดสอบเผยแพร่", detail: "จำลองสถานะโพสต์และคอมเมนต์" },
  { anchor: "meta-publishing", title: "Facebook", detail: "โพสต์และอ่านกลับผ่าน Meta API" },
  { anchor: "campaigns", title: "แคมเปญ", detail: "จัดคิวและติดตามงานเผยแพร่" },
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

const channelLabels: Record<string, string> = {
  facebook: "Facebook", instagram: "Instagram", tiktok: "TikTok",
  youtube: "YouTube", line: "LINE",
};

export default function Studio() {
  const [token, setToken] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceId, setWorkspaceId] = useState("");
  const [products, setProducts] = useState<Product[]>([]);
  const [productId, setProductId] = useState("");
  const [editingId, setEditingId] = useState("");
  const [renders, setRenders] = useState<Render[]>([]);
  const [renderId, setRenderId] = useState("");
  const [video, setVideo] = useState("");
  const [simulation, setSimulation] = useState<Simulation | null>(null);
  const [simulations, setSimulations] = useState<Simulation[]>([]);
  const [busy, setBusy] = useState("");
  const [notice, setNotice] = useState({ text: "", error: false });
  const [importReport, setImportReport] = useState<ImportReport | null>(null);
  const [linkResult, setLinkResult] = useState<{ path: string; links: ChannelLink[] } | null>(null);
  const [linkChannel, setLinkChannel] = useState("facebook");
  const [anchor, setAnchor] = useState("");
  const videoUrl = useRef("");
  const product = products.find((item) => item.id === productId);
  const editingProduct = products.find((item) => item.id === editingId);
  const render = renders.find((item) => item.id === renderId);
  const scope = `/workspaces/${workspaceId}`;
  const linkPath = productId ? `${scope}/products/${productId}/channel-links` : "";
  const channelLinks = linkResult?.path === linkPath ? linkResult.links : [];
  const activeLink = channelLinks.find((link) => link.channel === linkChannel);
  const facebookAffiliate = channelLinks.find((link) => link.channel === "facebook")?.affiliate_url;
  const showingResults = anchor === "affiliate-results";
  const showingOffers = anchor === "shopee-offers";
  const showingTrends = anchor === "trends";
  const showingWorkspace = !showingResults && !showingTrends && !showingOffers;

  useEffect(() => {
    const syncAnchor = () => setAnchor(window.location.hash.slice(1));
    syncAnchor();
    window.addEventListener("hashchange", syncAnchor);
    return () => window.removeEventListener("hashchange", syncAnchor);
  }, []);

  useEffect(() => {
    if (!workspaceId) return;
    const target = document.getElementById(anchor);
    target?.scrollIntoView();
    if (anchor === "affiliate-results" || anchor === "trends" || anchor === "shopee-offers") target?.querySelector("h1")?.focus({ preventScroll: true });
    if (anchor === "products") target?.querySelector("h2")?.focus({ preventScroll: true });
  }, [anchor, workspaceId]);

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
      setProductId(items[0]?.id ?? "");
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
    fetch(base + scope + `/renders/${renderId}/video`, {
      headers: headers(token),
      signal: controller.signal,
    }).then((response) => {
      if (!response.ok) throw new Error("เปิดตัวอย่างวิดีโอไม่ได้");
      return response.blob();
    }).then((blob) => {
      if (!active) return;
      videoUrl.current = URL.createObjectURL(blob);
      setVideo(videoUrl.current);
    }).catch((error) => {
      if (active) setNotice({ text: error.message, error: true });
    });
    return () => {
      active = false;
      controller.abort();
      if (videoUrl.current) URL.revokeObjectURL(videoUrl.current);
      videoUrl.current = "";
      setVideo("");
    };
  }, [render?.status, renderId, scope, token, workspaceId]);

  function selectWorkspace(id: string) {
    setProducts([]);
    setProductId("");
    setEditingId("");
    setRenders([]);
    setRenderId("");
    setSimulation(null);
    setSimulations([]);
    setImportReport(null);
    setNotice({ text: "", error: false });
    setWorkspaceId(id);
  }

  function selectProduct(id: string) {
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
    if (data.getAll("images").length !== 3) {
      setNotice({ text: "เลือกไฟล์ภาพ 3 ภาพ", error: true });
      return;
    }
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
            <form onSubmit={authenticate}>
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
    <div className="shell">
      <aside className="sidebar">
        <div className="wordmark"><span className="mark">A</span> Affiliate Studio</div>
        <div className="workspace">
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
        </div>
        {workspaceId && <nav aria-label="เมนู Studio">
          <a href="#shopee-offers" aria-current={showingOffers ? "location" : undefined}>สินค้าขายดีและค่าคอม</a>
          {steps.map((step) => <a href={`#${step.anchor}`} key={step.anchor}>{step.title}</a>)}
          <a href="#affiliate-results" aria-current={showingResults ? "location" : undefined}>ผลลัพธ์ Affiliate</a>
          <a href="#trends" aria-current={showingTrends ? "location" : undefined}>Google Trends</a>
        </nav>}
        <button type="button" className="text-button logout" onClick={logout} disabled={!!busy}>ออกจากระบบ</button>
      </aside>
      <main className="main">
        {(!workspaceId || showingWorkspace) && <header className="workspace-header"><h1>สตูดิโอ Reel</h1><span className="mode-tag">โหมดทดสอบ</span></header>}
        <div aria-live="polite">{status}</div>
        {!workspaceId && <section className="panel empty"><h2>เริ่มจากสร้างพื้นที่ทำงาน</h2><p>เพิ่มชื่อพื้นที่ทำงานเพื่อเริ่มจัดเก็บสินค้าและวิดีโอ</p></section>}
        {workspaceId && <>
          <div hidden={!showingResults}>
            <AffiliateResults key={workspaceId} active={showingResults} busy={!!busy} scope={scope}
              token={token} products={products} onProduct={openReportProduct} request={api} />
          </div>
          <div hidden={!showingOffers}>
            <ShopeeOffers key={workspaceId} active={showingOffers} scope={scope} token={token} request={api} />
          </div>
          <div hidden={!showingTrends}>
            <TrendExplorer key={workspaceId} active={showingTrends} scope={scope} token={token}
              busy={!!busy} onProduct={openReportProduct} request={api} />
          </div>
          <div className="studio-view" hidden={!showingWorkspace}>
          <section className="panel" id="products">
            <div className="panel-head"><h2 tabIndex={-1}>คลังสินค้า</h2><span>{products.length} รายการ</span></div>
            <div className="columns">
              <form key={editingId || "new"} onSubmit={saveProduct}>
                <h3>{editingId ? "แก้ไขสินค้า" : "เพิ่มสินค้า"}</h3>
                <label>ชื่อสินค้า<input name="name" required maxLength={300} defaultValue={editingProduct?.name} /></label>
                <label>ลิงก์สินค้า<input name="source_url" type="url" required maxLength={2083} defaultValue={editingProduct?.source_url} placeholder="https://" /></label>
                <label>ลิงก์ Affiliate สำรอง<input name="affiliate_url" type="url" maxLength={2083} defaultValue={editingProduct?.affiliate_url ?? ""} placeholder="https://" /></label>
                <label>สิทธิ์ใช้ภาพ<textarea name="image_rights_note" maxLength={2000} defaultValue={editingProduct?.image_rights_note ?? ""} rows={2} placeholder="เช่น ภาพถ่ายของร้านที่อนุญาตให้ใช้" /></label>
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
          {product && <section className="panel" aria-label="ลิงก์ Affiliate ตามช่องทาง">
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
          <section className="panel" id="video">
            <div className="panel-head"><h2>วิดีโอแนวตั้ง</h2><span>9:16 · 15 วินาที</span></div>
            <div className="columns">
              <div className="column">
                <form onSubmit={createVideo}>
                  <h3>เรนเดอร์จากภาพสินค้า</h3>
                  <p className="muted">{product ? product.name : "เลือกสินค้าในคลังสินค้าก่อน"}</p>
                  <label>ภาพสินค้า 3 ภาพ<input name="images" type="file" accept="image/jpeg,image/png,image/webp" multiple required /></label>
                  <button className="primary" disabled={!!busy || !product?.image_rights_note}>{busy === "render" ? "กำลังเรนเดอร์…" : "สร้างวิดีโอ"}</button>
                </form>
                <label>ตัวอย่างที่บันทึกไว้<select value={renderId} onChange={(event) => selectRender(event.target.value)} disabled={!!busy}>
                  <option value="">เลือกวิดีโอ</option>
                  {renders.filter((item) => item.product_id === productId).map((item) => <option key={item.id} value={item.id}>{item.status === "completed" ? "พร้อมดู" : "เรนเดอร์ไม่สำเร็จ"} · {item.id.slice(0, 8)}</option>)}
                </select></label>
              </div>
              <div className="preview">
                {video ? <video key={video} src={video} controls playsInline /> : <div className="preview-empty"><span aria-hidden="true">▶</span><p>ตัวอย่าง Reel</p></div>}
              </div>
            </div>
          </section>
          <section className="panel" id="simulation">
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
          <MetaPublishing key={workspaceId} request={api} scope={scope} token={token}
            renderId={renderId} canPublishRender={render?.status === "completed" && !!video}
            productName={product?.name ?? ""} affiliateUrl={facebookAffiliate ?? product?.affiliate_url} />
          <Campaigns key={workspaceId} scope={scope} token={token} active={anchor === "campaigns"}
            canManage={workspaces.find((workspace) => workspace.id === workspaceId)?.role === "owner"}
            renders={renders.filter((item) => item.status === "completed").map((item) => ({
              id: item.id, name: products.find((candidate) => candidate.id === item.product_id)?.name ?? item.id,
            }))} request={api} />
          </div>
        </>}
      </main>
    </div>
  );
}
