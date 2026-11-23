"use client";

import { useEffect, useState, type ReactNode } from "react";
import type { StudioRequest } from "./meta-publishing";

export const channelLabels: Record<string, string> = {
  facebook: "Facebook", instagram: "Instagram", tiktok: "TikTok",
  youtube: "YouTube", line: "LINE",
};

type Link = {
  product_id: string;
  product_name: string;
  channel: string | null;
  sub_id: string | null;
  affiliate_url: string;
};

type Props = {
  active: boolean;
  setup?: ReactNode;
  revision: number;
  busy: boolean;
  scope: string;
  token: string;
  request: StudioRequest;
  onProduct: (id: string) => void;
};

const channelName = (channel: string | null) => channel === null
  ? "ลิงก์สำรอง" : (channelLabels[channel] ?? channel);

export default function AffiliateLinks({ active, busy, scope, token, request, onProduct, setup, revision }: Props) {
  const [links, setLinks] = useState<Link[] | null>(null);
  const [channel, setChannel] = useState(":all");
  const [query, setQuery] = useState("");
  const [reload, setReload] = useState(0);
  const [error, setError] = useState("");
  const [feedback, setFeedback] = useState({ text: "", error: false });

  useEffect(() => {
    if (!active) return;
    const controller = new AbortController();
    setLinks(null);
    setError("");
    setFeedback({ text: "", error: false });
    request<Link[]>(scope + "/products/affiliate-links", token, { signal: controller.signal })
      .then((data) => { if (!controller.signal.aborted) setLinks(data); })
      .catch(() => {
        if (!controller.signal.aborted) setError("โหลดลิงก์ Affiliate ไม่สำเร็จ");
      });
    return () => controller.abort();
  }, [active, reload, revision, scope, token, request]);

  async function copy(link: Link) {
    try {
      await navigator.clipboard.writeText(link.affiliate_url);
      setFeedback({ text: `คัดลอกลิงก์ ${link.product_name} · ${channelName(link.channel)} แล้ว`, error: false });
    } catch {
      setFeedback({ text: "คัดลอกอัตโนมัติไม่สำเร็จ เลือกและคัดลอก URL จากรายการได้", error: true });
    }
  }

  const keyword = query.trim().toLocaleLowerCase("th");
  const channels = [...new Set((links ?? []).map((link) => link.channel))];
  const selected = channels.some((item) => (item ?? "") === channel) ? channel : ":all";
  const visible = (links ?? []).filter((link) =>
    (selected === ":all" || selected === (link.channel ?? "")) &&
    [link.product_name, link.sub_id, link.affiliate_url].some((value) => value?.toLocaleLowerCase("th").includes(keyword)));

  const library = <div className="panel">
      <div className="affiliate-link-filters">
        <label>ค้นหาสินค้า, Sub ID หรือ URL
          <input type="search" value={query} onChange={(event) => setQuery(event.target.value)} />
        </label>
        <label>ช่องทาง
          <select value={selected} onChange={(event) => setChannel(event.target.value)}>
            <option value=":all">ทุกช่องทาง</option>
            {channels.map((item) => <option key={item ?? ""} value={item ?? ""}>{channelName(item)}</option>)}
          </select>
        </label>
        <button type="button" className="secondary" disabled={!links && !error} onClick={() => setReload(reload + 1)}>โหลดใหม่</button>
      </div>
      {feedback.text && <p role={feedback.error ? "alert" : "status"} className={`notice ${feedback.error ? "error" : ""}`}>{feedback.text}</p>}
      {error && <p role="alert" className="notice error">{error}</p>}
      {!links && !error && <p role="status">กำลังโหลดลิงก์…</p>}
      {links && <p className="muted" aria-live="polite">แสดง {visible.length} จาก {links.length} ลิงก์</p>}
      {links && (visible.length ? <ul className="affiliate-link-list">
        {visible.map((link) => <li key={JSON.stringify([link.product_id, link.channel])}>
          <div>
            <button type="button" className="text-button" disabled={busy} onClick={() => onProduct(link.product_id)}>{link.product_name}</button>
            <p className="muted">{channelName(link.channel)}{link.sub_id && ` · Sub ID ${link.sub_id}`}</p>
            <p className="affiliate-link-url">{link.affiliate_url}</p>
          </div>
          <button type="button" className="secondary" onClick={() => void copy(link)}>คัดลอกลิงก์</button>
        </li>)}
      </ul> : <p className="muted">{links.length ? "ไม่พบลิงก์ที่ตรงกับตัวกรอง" : "ยังไม่มีลิงก์ Affiliate ในพื้นที่ทำงานนี้"}</p>)}
    </div>;

  return <section id="affiliate-links" className="affiliate-links">
    <header className="workspace-header"><h1 tabIndex={-1}>ลิงก์ Affiliate</h1></header>
    {setup ? <>
      {setup}
      <details className="panel workflow-details">
        <summary>ลิงก์ที่บันทึกไว้ทั้งหมด</summary>
        {library}
      </details>
    </> : <>
      <p>หากต้องการสร้างลิงก์ใหม่ ให้ <a href="#shopee-offers">เลือกข้อเสนอ Shopee</a> ก่อน</p>
      {library}
    </>}
  </section>;
}
