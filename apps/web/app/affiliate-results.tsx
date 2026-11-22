"use client";

import { FormEvent, useEffect, useState } from "react";
import "./affiliate-results.css";

const metrics = [
  { key: "estimated", label: "ค่าคอมโดยประมาณ" },
  { key: "confirmed", label: "ค่าคอมยืนยันตามออเดอร์" },
  { key: "orders", label: "ออเดอร์" },
  { key: "clicks", label: "คลิก" },
] as const;
type Metric = (typeof metrics)[number]["key"];
type Totals = Record<Metric, number>;
type Kind = "clicks" | "orders";
type Bounds = { first: string; last: string };
type Group = { channel: string; sub_id: string | null; product_id: string | null };
type Day = Totals & Group & { date: string };
type Report = { sources: Partial<Record<Kind, Bounds>>; days: Day[] };
type ImportResult = { kind: Kind; rows: number; saved: number; skipped: number };
type Props = {
  active: boolean;
  busy: boolean;
  scope: string;
  token: string;
  products: { id: string; name: string }[];
  onProduct: (id: string) => void;
  request: <T>(path: string, token: string, init?: RequestInit) => Promise<T>;
};

const labels: Record<string, string> = {
  facebook: "Facebook", instagram: "Instagram", tiktok: "TikTok",
  youtube: "YouTube", line: "LINE", website: "เว็บไซต์", shopee: "Shopee", unknown: "ไม่ทราบช่องทาง",
};
const kinds: { key: Kind; label: string }[] = [
  { key: "clicks", label: "รายงานคลิก" }, { key: "orders", label: "รายงานคำสั่งซื้อ" },
];
const counts = new Intl.NumberFormat("th-TH");
const baht = new Intl.NumberFormat("th-TH", { style: "currency", currency: "THB" });
const shortDate = new Intl.DateTimeFormat("th-TH", {
  day: "numeric", month: "short", timeZone: "Asia/Bangkok",
});
const longDate = new Intl.DateTimeFormat("th-TH", { dateStyle: "medium", timeZone: "Asia/Bangkok" });
const dayMs = 86_400_000;
const moneyScale = 1_000_000;
const zero = (): Totals => ({ clicks: 0, orders: 0, estimated: 0, confirmed: 0 });
const sourceFor = (key: Metric): Kind => key === "clicks" ? "clicks" : "orders";
const channelName = (channel: string) => labels[channel] ?? channel;

function shiftDate(date: string, delta: number) {
  return new Date(Date.parse(date) + delta * dayMs).toISOString().slice(0, 10);
}

function formatDate(date: string, formatter = shortDate) {
  return formatter.format(Date.parse(date));
}

function formatMetric(key: Metric, value: number | null) {
  if (value === null) return "—";
  return key === "estimated" || key === "confirmed" ? baht.format(value / moneyScale) : counts.format(value);
}

function add(target: Totals, value: Totals) {
  for (const { key } of metrics) target[key] += value[key];
}

function covered(bounds: Bounds | undefined, start: string, end: string) {
  return !!bounds && start <= bounds.last && end >= bounds.first;
}

export default function AffiliateResults({ active, busy, scope, token, products, onProduct, request }: Props) {
  const [period, setPeriod] = useState<"7" | "30" | "custom">("7");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [channel, setChannel] = useState("");
  const [subId, setSubId] = useState("");
  const [metric, setMetric] = useState<Metric>("estimated");
  const [sort, setSort] = useState<Metric>("estimated");
  const [compare, setCompare] = useState(true);
  const [report, setReport] = useState<Report | null>(null);
  const [refresh, setRefresh] = useState(0);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState<Kind | null>(null);
  const [uploadResult, setUploadResult] = useState<ImportResult | null>(null);
  const [uploadError, setUploadError] = useState("");
  const [readError, setReadError] = useState("");

  const sources = report?.sources ?? {};
  const bounds = Object.values(sources);
  const last = bounds.map((range) => range.last).sort().at(-1) ?? "";
  const start = period === "custom" ? from : last && shiftDate(last, 1 - Number(period));
  const end = period === "custom" ? to : last;
  const valid = start && end && start <= end;
  const span = valid ? Math.round((Date.parse(end) - Date.parse(start)) / dayMs) + 1 : 0;
  const priorStart = span ? shiftDate(start, -span) : "";
  const query = period === "custom" && valid ? `?start=${priorStart}&end=${end}` : "";

  useEffect(() => {
    if (!active) return;
    const controller = new AbortController();
    setReadError("");
    setLoading(true);
    request<Report>(scope + "/affiliate-reports" + query, token, { signal: controller.signal })
      .then((data) => { if (!controller.signal.aborted) setReport(data); })
      .catch((error: Error) => { if (!controller.signal.aborted) setReadError(error.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [active, query, refresh, request, scope, token]);

  function upload(event: FormEvent<HTMLFormElement>, kind: Kind) {
    event.preventDefault();
    const form = event.currentTarget;
    setUploading(kind);
    setUploadResult(null);
    setUploadError("");
    request<ImportResult>(scope + "/affiliate-reports/import/" + kind, token, {
      method: "POST", body: new FormData(form),
    }).then((result) => {
      setUploadResult(result);
      setRefresh((value) => value + 1);
      form.reset();
    }).catch((error: Error) => setUploadError(error.message))
      .finally(() => setUploading(null));
  }

  const daily = (report?.days ?? []).map((row) => ({
    ...row, estimated: Math.round(row.estimated * moneyScale),
    confirmed: Math.round(row.confirmed * moneyScale),
  }));
  const visible = valid ? daily.filter((row) => row.date >= start && row.date <= end) : [];
  const channels = [...new Set(visible.map((row) => row.channel))].sort();
  const activeChannel = channels.includes(channel) ? channel : "";
  const subIds = [...new Set(visible.filter((row) => !activeChannel || row.channel === activeChannel)
    .map((row) => row.sub_id ?? ""))].sort();
  const activeSubId = subId === "-" ? subIds.includes("") : !!subId && subIds.includes(subId);
  const included = (row: Day) => (!activeChannel || row.channel === activeChannel)
    && (!activeSubId || (row.sub_id ?? "-") === subId);
  const previous = valid && compare ? daily.filter((row) =>
    row.date >= priorStart && row.date < start && included(row)) : [];
  const current = visible.filter(included);
  const hasSource = (key: Metric) => !!valid && covered(sources[sourceFor(key)], start, end);
  const totals = zero();
  const grouped = new Map<string, Totals & Group>();
  for (const row of current) {
    add(totals, row);
    const key = JSON.stringify([row.channel, row.sub_id]);
    const group = grouped.get(key) ?? {
      ...zero(), channel: row.channel, sub_id: row.sub_id, product_id: row.product_id,
    };
    add(group, row);
    if (group.product_id !== row.product_id) group.product_id = null;
    grouped.set(key, group);
  }
  const groups = [...grouped.values()].sort((a, b) => b[sort] - a[sort]);
  const canCompare = !!valid && covered(sources[sourceFor(metric)], priorStart, shiftDate(start, -1));
  const bucketCount = hasSource(metric) ? Math.min(span, 12) : 0;
  const points = Array.from({ length: bucketCount }, (_, index) => {
    const offset = Math.floor(index * span / bucketCount);
    const date = shiftDate(start, offset);
    const lastDate = shiftDate(start, Math.floor((index + 1) * span / bucketCount) - 1);
    const sum = (rows: Day[], from: string, to: string) =>
      covered(sources[sourceFor(metric)], from, to)
        ? rows.reduce((total, row) => total + (row.date >= from && row.date <= to ? row[metric] : 0), 0)
        : null;
    return {
      date,
      label: date === lastDate ? formatDate(date) : `${formatDate(date)} – ${formatDate(lastDate)}`,
      value: sum(current, date, lastDate),
      prior: sum(previous, shiftDate(date, -span), shiftDate(lastDate, -span)),
    };
  });
  const largest = Math.max(1, ...points.map((point) => Math.max(point.value ?? 0, point.prior ?? 0)));
  const metricName = metrics.find(({ key }) => key === metric)?.label;

  return (
    <div className="affiliate-results" id="affiliate-results">
      <header className="affiliate-header">
        <div><h1 tabIndex={-1}>ผลลัพธ์ Affiliate</h1><p className="muted">ข้อมูลจากรายงาน Shopee ที่นำเข้าในพื้นที่ทำงานนี้</p></div>
      </header>

      <section className="panel" aria-labelledby="affiliate-import-title">
        <div className="affiliate-section-head"><h2 id="affiliate-import-title">นำเข้ารายงาน Shopee</h2></div>
        <div className="columns">
          {kinds.map(({ key, label }) => <form key={key} onSubmit={(event) => upload(event, key)}>
            <label>{label}<input type="file" name="file" accept=".csv,text/csv" required disabled={!!uploading} /></label>
            <p className="muted">{sources[key] ? `วันที่พบในไฟล์ ${formatDate(sources[key].first, longDate)} – ${formatDate(sources[key].last, longDate)}` : "ยังไม่มีรายการที่นำเข้า"}</p>
            <button className="secondary" disabled={!!uploading}>{uploading === key ? "กำลังนำเข้า…" : `นำเข้า${label}`}</button>
          </form>)}
        </div>
        {uploadError && <p role="alert" className="notice error">{uploadError}</p>}
        {uploadResult && <p role="status" className="notice">อ่าน {uploadResult.rows} แถว · บันทึกหรืออัปเดต {uploadResult.saved} · ข้าม {uploadResult.skipped} แถว</p>}
      </section>

      {readError && <p role="alert" className="notice error">{readError}</p>}
      {loading && <p role="status" className="muted">กำลังอ่านรายงาน…</p>}
      {!last && !loading && !readError && <p className="muted">นำเข้า CSV รายงานคลิกหรือคำสั่งซื้อเพื่อดูผล</p>}

      {last && <>
        <section className="affiliate-overview" aria-labelledby="affiliate-overview-title">
          <div className="affiliate-section-head">
            <h2 id="affiliate-overview-title">ภาพรวม</h2>
            <div className="affiliate-filters">
              <div className="affiliate-toggle" role="group" aria-label="ช่วงวันที่">
                {([["7", "7 วัน"], ["30", "30 วัน"], ["custom", "กำหนดเอง"]] as const).map(([value, label]) =>
                  <button key={value} type="button" aria-pressed={period === value} onClick={() => {
                    if (value === "custom" && !from && !to) { setFrom(start); setTo(end); }
                    setPeriod(value);
                  }}>{label}</button>)}
              </div>
              <select aria-label="ช่องทางของรายงาน" value={activeChannel} onChange={(event) => {
                setChannel(event.target.value); setSubId("");
              }}>
                <option value="">ทุกช่องทาง</option>
                {channels.map((value) => <option key={value} value={value}>{channelName(value)}</option>)}
              </select>
              <select aria-label="Sub ID ของรายงาน" value={activeSubId ? subId : ""} onChange={(event) => setSubId(event.target.value)}>
                <option value="">ทุก Sub ID</option>
                {subIds.map((value) => <option key={value} value={value || "-"}>{value || "ไม่มี Sub ID"}</option>)}
              </select>
            </div>
          </div>
          {period === "custom" && <div className="affiliate-dates">
            <label>ตั้งแต่<input type="date" value={from} onChange={(event) => setFrom(event.target.value)} /></label>
            <label>ถึง<input type="date" value={to} onChange={(event) => setTo(event.target.value)} /></label>
          </div>}
          <p className="affiliate-range muted" aria-live="polite">
            {valid ? `${formatDate(start, longDate)} – ${formatDate(end, longDate)}` : "เลือกวันเริ่มต้นและวันสิ้นสุดให้ถูกต้อง"}
          </p>
          <div className="affiliate-metrics" role="group" aria-label="ตัวชี้วัดในกราฟ">
            {metrics.map(({ key, label }) => <button key={key} type="button" className="affiliate-metric"
              aria-pressed={key === metric} onClick={() => setMetric(key)}>
              <span>{label}</span><strong>{formatMetric(key, hasSource(key) ? totals[key] : null)}</strong>
            </button>)}
          </div>
        </section>

        <section className="panel" aria-labelledby="affiliate-chart-title">
          <div className="affiliate-section-head">
            <h2 id="affiliate-chart-title">แนวโน้ม{metricName}</h2>
            {canCompare && <label className="checkbox"><input type="checkbox" checked={compare}
              onChange={(event) => setCompare(event.target.checked)} /> เทียบช่วงก่อนหน้า</label>}
          </div>
          {points.length ? <>
            <div className="affiliate-chart-legend" aria-hidden="true"><span>ช่วงที่เลือก</span>{compare && canCompare && <span>ช่วงก่อนหน้า</span>}</div>
            <div className="affiliate-chart" aria-hidden="true">
              {points.map(({ date, label, value, prior }, index) => <div className="affiliate-chart-point" key={date}>
                <div className="affiliate-bars" title={`${label} · ${formatMetric(metric, value)}`}>
                  {compare && canCompare && <div className="affiliate-prior-bar" style={{ height: `${Math.max(0, prior ?? 0) / largest * 100}%` }} />}
                  <div className="affiliate-current-bar" style={{ height: `${Math.max(0, value ?? 0) / largest * 100}%` }} />
                </div>
                <span>{index === 0 || index === points.length - 1 ? formatDate(date) : " "}</span>
              </div>)}
            </div>
            <details className="affiliate-chart-data">
              <summary>ดูตัวเลขในกราฟ</summary>
              <table><thead><tr><th scope="col">วันที่</th><th scope="col">ช่วงที่เลือก</th>{compare && canCompare && <th scope="col">ช่วงก่อนหน้า</th>}</tr></thead>
                <tbody>{points.map(({ date, label, value, prior }) => <tr key={date}><th scope="row">{label}</th>
                  <td>{formatMetric(metric, value)}</td>{compare && canCompare && <td>{formatMetric(metric, prior)}</td>}</tr>)}</tbody>
              </table>
            </details>
          </> : <p className="muted">ไม่มีข้อมูลสำหรับตัวชี้วัดนี้ในช่วงที่เลือก</p>}
        </section>

        <section className="panel" aria-labelledby="affiliate-links-title">
          <div className="affiliate-section-head">
            <h2 id="affiliate-links-title">ผลงานตามช่องทางและ Sub ID</h2>
            <label className="affiliate-sort">เรียงตาม<select value={sort} onChange={(event) => setSort(event.target.value as Metric)}>
              {metrics.map(({ key, label }) => <option key={key} value={key}>{label}</option>)}
            </select></label>
          </div>
          {groups.length ? <ul className="affiliate-link-list">{groups.map((group) => {
            const product = products.find((item) => item.id === group.product_id);
            return <li key={JSON.stringify([group.channel, group.sub_id])} className="affiliate-link">
              <div>
                <strong>{channelName(group.channel)}</strong>
                <p className="muted">Sub ID · {group.sub_id || "ไม่มี Sub ID"}</p>
                {product && <button type="button" className="text-button" disabled={busy} onClick={() => onProduct(product.id)}>{product.name}</button>}
              </div>
              <dl className="affiliate-link-metrics">{metrics.map(({ key, label }) =>
                <div key={key}><dt>{label}</dt><dd>{formatMetric(key, hasSource(key) ? group[key] : null)}</dd></div>)}</dl>
            </li>;
          })}</ul> : <p className="muted">ไม่มีรายการตรงกับตัวกรอง</p>}
          <p className="muted affiliate-source-note">ยอดออเดอร์นับตามรหัสคำสั่งซื้อ ค่าคอมที่ยืนยันตามออเดอร์อิงรายงานคำสั่งซื้อ</p>
        </section>
      </>}
    </div>
  );
}
