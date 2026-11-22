"use client";

import { FormEvent, useEffect, useState } from "react";

type Connection = {
  connected: boolean;
  publish_enabled: boolean;
  page_id: string | null;
  page_name: string | null;
  example_reel_id: string | null;
};
type Reel = {
  video_id: string;
  page_name: string;
  video_status: string | null;
  publish_status: string | null;
  url: string;
  comments: { id: string; author: string | null; message: string; url: string | null; hidden: boolean }[];
  comment_verified: boolean;
};
type Publication = {
  render_id: string;
  stage: string;
  video_id: string | null;
  include_comment: boolean;
  comment_id: string | null;
  error: string | null;
  reel: Reel | null;
  can_post_comment: boolean;
};

export type StudioRequest = <T>(path: string, token: string, init?: RequestInit) => Promise<T>;
type Props = {
  request: StudioRequest;
  scope: string;
  token: string;
  renderId: string;
  canPublishRender: boolean;
  productName: string;
  affiliateUrl?: string | null;
};

const wait = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));
const statusLabels: Record<string, string> = {
  published: "เผยแพร่แล้ว", processing: "กำลังประมวลผล", ready: "พร้อม", error: "ผิดพลาด",
  starting: "กำลังเปิดเซสชัน", uploading: "กำลังอัปโหลด", upload_failed: "อัปโหลดไม่สำเร็จ",
  finish_requested: "ส่งคำขอเผยแพร่แล้ว", comment_requested: "ส่งคำขอคอมเมนต์แล้ว",
  comment_sent: "Meta รับคอมเมนต์แล้ว",
};

function ReelResult({ reel }: { reel: Reel }) {
  return (
    <div className="result" aria-live="polite">
      <h3><a href={reel.url} target="_blank" rel="noreferrer">Reel {reel.video_id}</a></h3>
      <p>{reel.page_name} · {statusLabels[reel.publish_status ?? reel.video_status ?? ""] ?? "รอสถานะจาก Meta"}</p>
      {reel.comments.length > 0 ? reel.comments.map((comment) => (
        <div key={comment.id}>
          <p><strong>{comment.author}</strong>{comment.hidden && " · ถูกซ่อน"}</p>
          <p style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{comment.message}</p>
          {comment.url && <a href={comment.url} target="_blank" rel="noreferrer">ดูคอมเมนต์บน Facebook</a>}
        </div>
      )) : <p className="muted">ยังไม่มีคอมเมนต์จากเพจในผลอ่านกลับ</p>}
    </div>
  );
}

export default function MetaPublishing({
  request, scope, token, renderId, canPublishRender, productName, affiliateUrl,
}: Props) {
  const [config, setConfig] = useState<Connection | null>(null);
  const [existing, setExisting] = useState<Reel | null>(null);
  const [publication, setPublication] = useState<Publication | null>(null);
  const [loadedRender, setLoadedRender] = useState("");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const base = scope + "/publishing/meta";

  useEffect(() => {
    const controller = new AbortController();
    request<Connection>(base, token, { signal: controller.signal }).then(setConfig).catch((err) => {
      if (!controller.signal.aborted) setError(err.message);
    });
    return () => controller.abort();
  }, [base, token, request]);

  useEffect(() => {
    if (!config?.connected || !renderId) return;
    const controller = new AbortController();
    request<Publication | null>(base + "/publications/" + renderId, token, {
      signal: controller.signal,
    }).then((value) => {
      if (controller.signal.aborted) return;
      setPublication(value);
      setLoadedRender(renderId);
    }).catch((err) => {
      if (!controller.signal.aborted) setError(err.message);
    });
    return () => controller.abort();
  }, [base, config?.connected, renderId, request, token]);

  const job = publication?.render_id === renderId ? publication : null;

  async function run(action: string, task: () => Promise<void>) {
    setError("");
    setBusy(action);
    try {
      await task();
    } catch (err) {
      setError(err instanceof Error ? err.message : "ดำเนินการผ่าน Meta ไม่สำเร็จ");
    } finally {
      setBusy("");
    }
  }

  function readExisting(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const videoId = String(new FormData(event.currentTarget).get("video_id") ?? "").trim();
    void run("read", async () => {
      setExisting(null);
      setExisting(await request<Reel>(base + "/reels/" + videoId, token));
    });
  }

  async function poll(target: string, initial: Publication, continueComment: boolean) {
    let latest = initial;
    for (let attempt = 0; attempt < 8; attempt++) {
      if (latest.can_post_comment && continueComment) {
        latest = await request<Publication>(target + "/comment", token, { method: "POST" });
        setPublication(latest);
      }
      const settled = latest.reel?.publish_status === "published"
        && (!latest.include_comment || latest.reel.comment_verified);
      const failed = latest.error && latest.stage !== "finish_requested";
      if (settled || failed || latest.reel?.video_status === "error" || !latest.video_id) break;
      latest = await request<Publication>(target, token);
      setPublication(latest);
      if (attempt < 7) await wait(1800);
    }
  }

  function publish(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    if (!window.confirm(`เผยแพร่ Reel แบบสาธารณะบนเพจ ${config?.page_name || config?.page_id} หรือไม่`)) return;
    const target = base + "/publications/" + renderId;
    void run("publish", async () => {
      const created = await request<Publication>(base + "/publications", token, {
        method: "POST",
        body: JSON.stringify({
          render_id: renderId, caption: data.get("caption"),
          include_comment: data.has("comment"), ai_generated: data.has("ai_generated"),
        }),
      });
      setPublication(created);
      await poll(target, created, true);
    });
  }

  function checkPublication(continueComment = false) {
    const target = base + "/publications/" + renderId;
    void run("status", async () => {
      const latest = await request<Publication>(target, token);
      setPublication(latest);
      if (continueComment) await poll(target, latest, true);
    });
  }

  return (
    <section className="panel" id="meta-publishing">
      <div className="panel-head"><h2>เผยแพร่และตรวจสอบบน Facebook</h2><span>Meta Graph API</span></div>
      {error && <p className="notice error" role="alert">{error}</p>}
      {!config ? <p className="muted">กำลังตรวจการเชื่อมต่อ…</p> : !config.connected ? (
        <p className="muted">พื้นที่ทำงานนี้ยังไม่ได้เชื่อมกับเพจ Facebook</p>
      ) : (
        <div className="columns">
          <div className="column">
            <form onSubmit={readExisting}>
              <h3>อ่าน Reel ที่เผยแพร่แล้ว</h3>
              <label>รหัส Reel<input name="video_id" inputMode="numeric" pattern="[0-9]{1,30}" required defaultValue={config.example_reel_id ?? ""} /></label>
              <button className="primary" disabled={!!busy}>{busy === "read" ? "กำลังอ่าน…" : "อ่าน Reel และคอมเมนต์"}</button>
            </form>
            {existing && <ReelResult reel={existing} />}
          </div>
          <div className="column">
            <form onSubmit={publish}>
              <h3>โพสต์ Reel ใหม่</h3>
              <p className="muted">เพจ {config.page_name || config.page_id} · สาธารณะ</p>
              {!config.publish_enabled && <p className="muted">การเชื่อมต่อนี้เปิดให้อ่านสถานะ</p>}
              {!canPublishRender && <p className="muted">เลือกวิดีโอที่เรนเดอร์เสร็จจากส่วนวิดีโอ</p>}
              <label>แคปชัน<textarea key={renderId} name="caption" maxLength={500} rows={3} required defaultValue={productName} /></label>
              <label className="checkbox"><input key={renderId + (affiliateUrl ?? "")} name="comment" type="checkbox" disabled={!affiliateUrl} defaultChecked={!!affiliateUrl} /> โพสต์คอมเมนต์ลิงก์ Affiliate</label>
              <label className="checkbox"><input name="ai_generated" type="checkbox" /> วิดีโอใช้ AI สร้างหรือแก้ไข</label>
              <button className="primary" disabled={!!busy || !config.publish_enabled || !canPublishRender || loadedRender !== renderId || !!job}>{busy === "publish" ? "กำลังส่งให้ Facebook…" : "เผยแพร่จริงบน Facebook"}</button>
            </form>
            {job && <div className="result" aria-live="polite">
              <p>{statusLabels[job.stage] ?? job.stage}</p>
              {job.error && <p role="alert">{job.error}</p>}
              {job.reel && <ReelResult reel={job.reel} />}
              {job.reel?.comment_verified && <p>ยืนยันคอมเมนต์จาก Meta แล้ว</p>}
              <button type="button" disabled={!!busy} onClick={() => checkPublication()}>อ่านสถานะล่าสุด</button>
              {job.can_post_comment && config.publish_enabled && <button type="button" disabled={!!busy} onClick={() => checkPublication(true)}>โพสต์คอมเมนต์ Affiliate</button>}
            </div>}
          </div>
        </div>
      )}
    </section>
  );
}
