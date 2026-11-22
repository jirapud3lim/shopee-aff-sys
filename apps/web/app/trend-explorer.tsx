"use client";

import { FormEvent, useEffect, useState } from "react";
import type { StudioRequest } from "./meta-publishing";

type Match = { product_id: string; name: string; terms: string[]; phrase: boolean };
type Trend = {
  title: string; published_at: string | null; traffic: string | null; explore_url: string; matches: Match[];
};
type Feed = { source_url: string; stale: boolean; fetched_at: string; catalog_count: number; trends: Trend[] };
type Lookup = { query: string; explore_url: string; matches: Match[]; catalog_count: number };
type Props = {
  request: StudioRequest;
  scope: string;
  token: string;
  active: boolean;
  busy: boolean;
  onProduct: (id: string) => void;
};

const bangkok = new Intl.DateTimeFormat("th-TH", {
  dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Bangkok",
});

function Matches({ matches, busy, open }: { matches: Match[]; busy: boolean; open: (id: string) => void }) {
  if (!matches.length) return <p className="muted">ยังไม่พบสินค้าที่ตรงในคลัง</p>;
  return <ul className="trend-matches">
    {matches.map((item) => <li key={item.product_id}>
      <button type="button" className="text-button" disabled={busy} onClick={() => open(item.product_id)}>{item.name}</button>
      <p className="muted">{item.phrase ? "ตรงทั้งวลี" : "คำที่ตรง"} · {item.terms.join(" · ")}</p>
    </li>)}
  </ul>;
}

export default function TrendExplorer({ request, scope, token, active, busy, onProduct }: Props) {
  const [feed, setFeed] = useState<Feed | null>(null);
  const [hours, setHours] = useState("24");
  const [filter, setFilter] = useState("");
  const [matchedOnly, setMatchedOnly] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const [loading, setLoading] = useState(false);
  const [feedError, setFeedError] = useState("");
  const [lookup, setLookup] = useState<Lookup | null>(null);
  const [matching, setMatching] = useState(false);
  const [matchError, setMatchError] = useState("");
  const base = scope + "/trends";

  useEffect(() => {
    if (!active) return;
    const controller = new AbortController();
    setLoading(true);
    setFeedError("");
    request<Feed>(base + "?hours=" + hours, token, { signal: controller.signal })
      .then((data) => { if (!controller.signal.aborted) setFeed(data); })
      .catch(() => {
        if (!controller.signal.aborted) {
          setFeed(null);
          setFeedError("โหลดเทรนด์จาก Google ไม่ได้ในขณะนี้ คุณยังจับคู่คำค้นกับสินค้าในคลังได้");
        }
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [active, base, hours, refresh, request, token]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const query = String(new FormData(event.currentTarget).get("q")).trim();
    setMatching(true);
    setMatchError("");
    setLookup(null);
    try {
      setLookup(await request<Lookup>(base + "/matches?" + new URLSearchParams({ q: query }), token));
    } catch (error) {
      setMatchError(error instanceof Error ? error.message : "ค้นหาสินค้าไม่สำเร็จ");
    } finally {
      setMatching(false);
    }
  }

  const keyword = filter.trim().toLocaleLowerCase("th");
  const trends = (feed?.trends ?? []).filter((trend) =>
    (!matchedOnly || trend.matches.length > 0) && trend.title.toLocaleLowerCase("th").includes(keyword));

  return <div id="trends" className="trend-explorer">
    <header>
      <h1 tabIndex={-1}>เทรนด์ค้นหาในไทย</h1>
      <p className="muted">จับคู่คำค้น Google Trends กับชื่อสินค้า Shopee ในคลังของพื้นที่ทำงานนี้</p>
    </header>

    <section className="panel" aria-labelledby="trend-feed-title">
      <div className="panel-head">
        <h2 id="trend-feed-title">กำลังเป็นกระแส</h2>
        <a href={feed?.source_url ?? "https://trends.google.com/trending?geo=TH"} target="_blank" rel="noreferrer">Google Trends</a>
      </div>
      <div className="trend-filters">
        <label>ช่วงเวลา<select value={hours} onChange={(event) => setHours(event.target.value)}>
          <option value="24">24 ชั่วโมงล่าสุด</option>
          <option value="4">4 ชั่วโมงล่าสุด</option>
        </select></label>
        <label>กรองคำค้น<input type="search" value={filter} onChange={(event) => setFilter(event.target.value)} /></label>
        <label className="checkbox"><input type="checkbox" checked={matchedOnly}
          onChange={(event) => setMatchedOnly(event.target.checked)} /> เฉพาะที่พบสินค้า</label>
        <button type="button" className="secondary" disabled={loading} onClick={() => setRefresh((value) => value + 1)}>
          โหลดข้อมูล
        </button>
      </div>
      {feed && !loading && <p className="muted">
        {feed.stale ? "ใช้ข้อมูลที่โหลดไว้เมื่อ " : "ดึงข้อมูลเมื่อ "}{bangkok.format(Date.parse(feed.fetched_at))}
        {" · "}คลังสินค้า Shopee {feed.catalog_count} รายการ
      </p>}
      <p className="muted">จำนวนค้นหาเป็นค่าประมาณจาก Google สำหรับเทรนด์ในฟีด</p>
      {loading && <p role="status">กำลังโหลด Google Trends…</p>}
      {feedError && <p role="alert" className="notice error">{feedError}</p>}
      {feed && !loading && (trends.length ? <ul className="trend-list">
        {trends.map((trend) => <li key={trend.title} className="trend-row">
          <div>
            <h3>{trend.title}</h3>
            <p className="muted">{trend.traffic ? `ค้นหาประมาณ ${trend.traffic} · ` : ""}
              {trend.published_at ? bangkok.format(Date.parse(trend.published_at)) : "ไม่ระบุเวลา"}</p>
            <a href={trend.explore_url} target="_blank" rel="noreferrer">ดูความสนใจใน Google Trends</a>
          </div>
          <Matches matches={trend.matches} busy={busy} open={onProduct} />
        </li>)}
      </ul> : <p className="muted">ไม่มีเทรนด์ตรงกับตัวกรองในฟีด</p>)}
    </section>

    <section className="panel" aria-labelledby="trend-lookup-title">
      <h2 id="trend-lookup-title">จับคู่คำค้นเอง</h2>
      <form onSubmit={submit}>
        <label>คำค้นที่ต้องการตรวจ<input name="q" required minLength={2} maxLength={180} placeholder="ผ้าไมโครไฟเบอร์" /></label>
        <button className="primary" disabled={matching}>{matching ? "กำลังจับคู่…" : "ค้นหาสินค้าในคลัง"}</button>
      </form>
      {matchError && <p role="alert" className="notice error">{matchError}</p>}
      {lookup && <div className="result" aria-live="polite">
        <h3>{lookup.query}</h3>
        <p className="muted">พบ {lookup.matches.length} รายการ · คลังสินค้า Shopee {lookup.catalog_count} รายการ</p>
        <Matches matches={lookup.matches} busy={busy} open={onProduct} />
        <a href={lookup.explore_url} target="_blank" rel="noreferrer">ตรวจความสนใจของคำนี้ใน Google Trends</a>
      </div>}
    </section>
  </div>;
}
