"use client";

import { FormEvent, useEffect, useState } from "react";
import type { StudioRequest } from "@/features/publishing/meta-publishing";

type RenderOption = { id: string; name: string };
type Job = {
  id: string;
  render_id: string;
  caption: string;
  scheduled_at: string;
  state: string;
  video_id: string | null;
  reel_url: string | null;
  comment_url: string | null;
  include_comment: boolean;
  error: string | null;
};
type Campaign = { id: string; name: string; mode: "simulation" | "live"; state: string; items: Job[] };
type Queue = { campaigns: Campaign[]; live_enabled: boolean; page_name: string };
type Draft = { render_id: string; caption: string; scheduled_at: string; include_comment: boolean; ai_generated: boolean };
type Action = "activate" | "pause" | "resume" | "cancel";
type Props = {
  scope: string;
  token: string;
  active: boolean;
  canManage: boolean;
  renders: RenderOption[];
  request: StudioRequest;
};

const date = new Intl.DateTimeFormat("th-TH", { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Bangkok" });
const labels: Record<string, string> = {
  draft: "ฉบับร่าง", active: "เปิดคิว", paused: "พักคิว", cancelled: "ยกเลิก",
  queued: "รอเวลา", dispatching: "กำลังส่ง", verifying: "กำลังตรวจผล",
  completed: "เสร็จแล้ว", needs_attention: "ต้องตรวจสอบ",
};
const actions: Record<string, Action[]> = {
  draft: ["activate", "cancel"], active: ["pause", "cancel"], paused: ["resume", "cancel"],
};
const actionLabels: Record<Action, string> = {
  activate: "ยืนยันเปิดคิว", pause: "พักคิว", resume: "เปิดคิวต่อ", cancel: "ยกเลิกงานที่รอส่ง",
};
const finishedStates = new Set(["completed", "cancelled", "needs_attention"]);

function nextSlot(offset = 5) {
  return new Date(Date.now() + (7 * 60 + offset) * 60_000).toISOString().slice(0, 16);
}

export default function Campaigns({ scope, token, active, canManage, renders, request }: Props) {
  const [queue, setQueue] = useState<Queue | null>(null);
  const [draft, setDraft] = useState<Draft[]>([]);
  const [renderId, setRenderId] = useState("");
  const [name, setName] = useState("");
  const [mode, setMode] = useState<"simulation" | "live">("simulation");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [pending, setPending] = useState<{ campaign: Campaign; action: Action } | null>(null);
  const base = scope + "/campaigns";

  useEffect(() => {
    if (!active || busy) return;
    const controller = new AbortController();
    const load = () => request<Queue>(base, token, { signal: controller.signal })
      .then((value) => { if (!controller.signal.aborted) setQueue(value); })
      .catch((err: Error) => { if (!controller.signal.aborted) setError(err.message); });
    void load();
    const timer = window.setInterval(load, 5000);
    return () => { controller.abort(); window.clearInterval(timer); };
  }, [active, base, busy, request, token]);

  const choices = renders.filter((render) => !draft.some((item) => item.render_id === render.id));
  const availableRender = choices.find((render) => render.id === renderId) ?? choices[0];

  function addItem() {
    if (!availableRender) return;
    setDraft((items) => [...items, {
      render_id: availableRender.id, caption: availableRender.name,
      scheduled_at: nextSlot(5 + items.length * 10), include_comment: true, ai_generated: false,
    }]);
    setRenderId("");
  }

  function updateItem(id: string, patch: Partial<Draft>) {
    setDraft((items) => items.map((item) => item.render_id === id ? { ...item, ...patch } : item));
  }

  async function run(task: () => Promise<void>) {
    setError("");
    setBusy(true);
    try {
      await task();
    } catch (err) {
      setError(err instanceof Error ? err.message : "ดำเนินการไม่สำเร็จ");
    } finally {
      setBusy(false);
    }
  }

  function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void run(async () => {
      const saved = await request<Campaign>(base, token, {
        method: "POST",
        body: JSON.stringify({ name, mode, items: draft.map((item) => ({
          ...item, scheduled_at: item.scheduled_at + ":00+07:00",
        })) }),
      });
      setQueue((value) => value && ({ ...value, campaigns: [saved, ...value.campaigns] }));
      setName("");
      setDraft([]);
    });
  }

  function apply(campaign: Campaign, action: Action) {
    setPending(null);
    void run(async () => {
      const updated = await request<Campaign>(`${base}/${campaign.id}/actions`, token, {
        method: "POST", body: JSON.stringify({ action }),
      });
      setQueue((value) => value && ({
        ...value, campaigns: value.campaigns.map((row) => row.id === updated.id ? updated : row),
      }));
    });
  }

  function reconcile(campaign: Campaign, job: Job) {
    void run(async () => {
      const updated = await request<Campaign>(`${base}/${campaign.id}/items/${job.id}/reconcile`, token, { method: "POST" });
      setQueue((value) => value && ({
        ...value, campaigns: value.campaigns.map((row) => row.id === updated.id ? updated : row),
      }));
    });
  }

  return (
    <section className="panel" id="campaigns">
      <div className="panel-head"><h2>แคมเปญและคิวเผยแพร่</h2><span>เวลาไทย</span></div>
      {error && <p role="alert" className="notice error">{error}</p>}
      {canManage && <form onSubmit={save}>
        <h3>สร้างแคมเปญ</h3>
        <div className="columns">
          <label>ชื่อแคมเปญ<input value={name} onChange={(event) => setName(event.target.value)} required maxLength={120} /></label>
          <label>โหมด<select value={mode} onChange={(event) => setMode(event.target.value === "live" ? "live" : "simulation")}>
            <option value="simulation">จำลองการโพสต์</option>
            {queue?.live_enabled && <option value="live">Facebook · {queue.page_name || "เพจที่เชื่อมไว้"}</option>}
          </select></label>
        </div>
        <label>วิดีโอที่เรนเดอร์เสร็จ<select value={availableRender?.id ?? ""} onChange={(event) => setRenderId(event.target.value)}>
          {!choices.length && <option value="">ยังไม่มีวิดีโอให้เพิ่ม</option>}
          {choices.map((render) => <option key={render.id} value={render.id}>{render.name} · {render.id.slice(0, 8)}</option>)}
        </select></label>
        <button type="button" className="secondary" disabled={busy || !availableRender || draft.length >= 500} onClick={addItem}>เพิ่มวิดีโอเข้าคิว</button>
        {draft.map((item) => <fieldset key={item.render_id} className="campaign-item">
          <legend>{renders.find((render) => render.id === item.render_id)?.name ?? item.render_id}</legend>
          <label>กำหนดวันและเวลา<input type="datetime-local" required value={item.scheduled_at}
            onChange={(event) => updateItem(item.render_id, { scheduled_at: event.target.value })} /></label>
          <label>แคปชัน<textarea rows={2} required maxLength={500} value={item.caption}
            onChange={(event) => updateItem(item.render_id, { caption: event.target.value })} /></label>
          <label className="checkbox"><input type="checkbox" checked={item.include_comment}
            onChange={(event) => updateItem(item.render_id, { include_comment: event.target.checked })} /> คอมเมนต์ลิงก์ Affiliate ของช่องทาง Facebook</label>
          <label className="checkbox"><input type="checkbox" checked={item.ai_generated}
            onChange={(event) => updateItem(item.render_id, { ai_generated: event.target.checked })} /> วิดีโอใช้ AI สร้างหรือแก้ไข</label>
          <button type="button" className="text-button" onClick={() => setDraft((items) => items.filter((row) => row.render_id !== item.render_id))}>นำออกจากร่าง</button>
        </fieldset>)}
        <button className="primary" disabled={busy || draft.length === 0 || !queue}>บันทึกฉบับร่าง ({draft.length} งาน)</button>
      </form>}
      <h3>สถานะคิว</h3>
      {!queue && !error && <p className="muted">กำลังโหลดคิว…</p>}
      {queue?.campaigns.length === 0 && <p className="muted">ยังไม่มีแคมเปญ</p>}
      {queue?.campaigns.map((campaign) => {
        const finished = campaign.items.every((item) => finishedStates.has(item.state));
        const completed = campaign.items.filter((item) => item.state === "completed").length;
        return <details key={campaign.id} className="campaign-item">
          <summary>{campaign.name} · {campaign.mode === "live" ? "โพสต์จริง" : "จำลอง"} · {completed === campaign.items.length ? labels.completed : labels[campaign.state]} · เสร็จ {completed}/{campaign.items.length}</summary>
          {canManage && !finished && <div className="campaign-actions">
            {(actions[campaign.state] ?? []).map((action) => <button type="button" className="secondary" key={action}
              disabled={busy || (campaign.mode === "live" && !queue.live_enabled && (action === "activate" || action === "resume"))}
              onClick={() => {
                if (campaign.mode === "live" && (action === "activate" || action === "resume")) setPending({ campaign, action });
                else apply(campaign, action);
              }}>{actionLabels[action]}</button>)}
          </div>}
          {pending?.campaign.id === campaign.id && <div className="notice">
            <p>งานในคิว {campaign.items.length} รายการจะเผยแพร่สาธารณะตามกำหนดบนเพจ {queue.page_name || "ที่เชื่อมไว้"}</p>
            <div className="campaign-actions">
              <button type="button" className="primary" disabled={busy} onClick={() => apply(campaign, pending.action)}>ยืนยันเผยแพร่ตามคิว</button>
              <button type="button" className="secondary" onClick={() => setPending(null)}>กลับไปตรวจร่าง</button>
            </div>
          </div>}
          <ul className="campaign-jobs">{campaign.items.map((item) => <li key={item.id}>
            <strong>{date.format(Date.parse(item.scheduled_at))} · {labels[item.state] || item.state}</strong>
            <p>{item.caption}</p>
            {item.error && <p className="muted">{item.error}</p>}
            {item.reel_url && <a href={item.reel_url} target="_blank" rel="noreferrer">ดู Reel</a>}
            {item.comment_url && <a href={item.comment_url} target="_blank" rel="noreferrer">ดูคอมเมนต์ Affiliate</a>}
            {canManage && item.state === "needs_attention" && item.video_id && <button type="button"
              className="secondary" disabled={busy} onClick={() => reconcile(campaign, item)}>ตรวจผลจาก Meta</button>}
          </li>)}</ul>
        </details>;
      })}
    </section>
  );
}
