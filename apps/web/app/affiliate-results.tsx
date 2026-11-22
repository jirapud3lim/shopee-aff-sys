"use client";

import { useState } from "react";
import {
  demoDays, demoLinks, demoProducts, growingProducts, lastDemoDate, numberOfDays,
  shiftDate, sumTotals, type DemoProduct, type Totals,
} from "./affiliate-demo";
import "./affiliate-results.css";

const firstDemoDate = demoDays[0].date;
const defaultStart = shiftDate(lastDemoDate, -6);
const number = new Intl.NumberFormat("th-TH");
const shortDate = new Intl.DateTimeFormat("th-TH", { day: "numeric", month: "short", timeZone: "Asia/Bangkok" });
const longDate = new Intl.DateTimeFormat("th-TH", { dateStyle: "medium", timeZone: "Asia/Bangkok" });
const metrics = [
  { key: "estimated", label: "ค่าคอมโดยประมาณ" },
  { key: "confirmed", label: "ค่าคอมยืนยันแล้ว" },
  { key: "orders", label: "ออเดอร์" },
  { key: "clicks", label: "คลิก" },
] as const;
const channels = [...new Set(demoLinks.map((link) => link.channel))];

function formatMetric(key: keyof Totals, value: number) {
  return (key === "estimated" || key === "confirmed" ? "฿" : "") + number.format(value);
}

function formatDate(date: string, formatter = shortDate) {
  return formatter.format(Date.parse(date));
}

type Props = {
  busy: boolean;
  savedProducts: Readonly<Partial<Record<DemoProduct["id"], string>>>;
  onProduct: (product: DemoProduct) => void;
};

export default function AffiliateResults({ busy, savedProducts, onProduct }: Props) {
  const [period, setPeriod] = useState<"7" | "30" | "custom">("7");
  const [from, setFrom] = useState(defaultStart);
  const [to, setTo] = useState(lastDemoDate);
  const [channel, setChannel] = useState("");
  const [metric, setMetric] = useState<keyof Totals>("estimated");
  const [sort, setSort] = useState<keyof Totals>("estimated");
  const [compare, setCompare] = useState(true);
  const [trend, setTrend] = useState<"market" | "studio">("market");
  const [selectedLink, setSelectedLink] = useState("");
  const start = period === "custom" ? from : shiftDate(lastDemoDate, 1 - Number(period));
  const end = period === "custom" ? to : lastDemoDate;
  const validRange = !!start && !!end && start <= end;
  const visible = validRange ? demoDays.filter(({ date }) => date >= start && date <= end) : [];
  const hasCoverage = visible.length > 0;
  const canCompare = hasCoverage && visible.length === numberOfDays(start, end)
    && shiftDate(start, -visible.length) >= firstDemoDate;
  const totalsForDay = (day: (typeof demoDays)[number]) => sumTotals(day.links.filter((link) => !channel || link.channel === channel));
  const totals = sumTotals(visible.map(totalsForDay));
  const previous = canCompare ? demoDays.filter(({ date }) => date >= shiftDate(start, -visible.length) && date < start) : [];
  const bucketSize = visible.length > 14 ? Math.ceil(visible.length / 10) : 1;
  const points = [];
  for (let index = 0; index < visible.length; index += bucketSize) {
    const bucket = visible.slice(index, index + bucketSize);
    const date = bucket[0].date;
    const last = bucket[bucket.length - 1].date;
    points.push({
      date,
      label: date === last ? formatDate(date) : `${formatDate(date)} – ${formatDate(last)}`,
      value: sumTotals(bucket.map(totalsForDay))[metric],
      prior: sumTotals(previous.slice(index, index + bucketSize).map(totalsForDay))[metric],
    });
  }
  const largestPoint = Math.max(1, ...points.map(({ value, prior }) => Math.max(value, compare && canCompare ? prior : 0)));
  const allVisibleLinks = visible.flatMap((day) => day.links);
  const links = demoLinks.filter((link) => !channel || link.channel === channel).map((link) => ({
    ...link,
    ...sumTotals(allVisibleLinks.filter((row) => row.subId === link.subId)),
  })).sort((a, b) => b[sort] - a[sort]);
  const metricName = metrics.find(({ key }) => key === metric)?.label;
  const trends = trend === "market"
    ? demoProducts.map((product) => ({ product, channels: [], reason: `อันดับ ${product.marketRank} ในรายการมาแรงตัวอย่าง` }))
    : growingProducts.map(({ product, channels, current, previous: prior }) => ({
      product, channels, reason: `${current} ออเดอร์ เทียบกับ ${prior} ออเดอร์ใน 7 วันก่อนหน้า`,
    }));

  return (
    <div className="affiliate-results" id="affiliate-results">
      <header className="affiliate-header">
        <div>
          <h1 tabIndex={-1}>ผลลัพธ์ Affiliate</h1>
          <p className="muted">ข้อมูลครอบคลุม {formatDate(firstDemoDate)} – {formatDate(lastDemoDate, longDate)}</p>
        </div>
        <span className="affiliate-demo-label">ข้อมูลตัวอย่าง</span>
      </header>

      <section className="affiliate-overview" aria-labelledby="affiliate-overview-title">
        <div className="affiliate-section-head">
          <h2 id="affiliate-overview-title">ภาพรวม</h2>
          <div className="affiliate-filters">
            <div className="affiliate-toggle" role="group" aria-label="ช่วงวันที่">
              {([ ["7", "7 วัน"], ["30", "30 วัน"], ["custom", "กำหนดเอง"] ] as const).map(([value, label]) => (
                <button key={value} type="button" aria-pressed={period === value} onClick={() => setPeriod(value)}>{label}</button>
              ))}
            </div>
            <select aria-label="ช่องทางของรายงาน" value={channel} onChange={(event) => setChannel(event.target.value)}>
              <option value="">ทุกช่องทาง</option>
              {channels.map((value) => <option key={value}>{value}</option>)}
            </select>
          </div>
        </div>
        {period === "custom" && <div className="affiliate-dates">
          <label>ตั้งแต่<input type="date" value={from} onChange={(event) => setFrom(event.target.value)} /></label>
          <label>ถึง<input type="date" value={to} onChange={(event) => setTo(event.target.value)} /></label>
        </div>}
        <p className="affiliate-range muted" aria-live="polite">
          {validRange ? `${formatDate(start, longDate)} – ${formatDate(end, longDate)}` : "เลือกวันเริ่มต้นและวันสิ้นสุดให้ถูกต้อง"}
        </p>
        {hasCoverage && visible.length < numberOfDays(start, end) && <p className="muted">แสดงเฉพาะวันที่มีข้อมูลตัวอย่าง</p>}
        <div className="affiliate-metrics" role="group" aria-label="ตัวชี้วัดในกราฟ">
          {metrics.map(({ key, label }) => (
            <button key={key} type="button" className="affiliate-metric" aria-pressed={key === metric} onClick={() => setMetric(key)}>
              <span>{label}</span><strong>{hasCoverage ? formatMetric(key, totals[key]) : "—"}</strong>
            </button>
          ))}
        </div>
      </section>

      <section className="panel affiliate-trending" aria-labelledby="affiliate-trending-title">
        <div className="affiliate-section-head">
          <div>
            <h2 id="affiliate-trending-title">สินค้ากำลังมาแรง</h2>
            <p className="muted">{formatDate(defaultStart)} – {formatDate(lastDemoDate)} · ข้อมูลตัวอย่าง</p>
          </div>
          <div className="affiliate-toggle" role="group" aria-label="แหล่งข้อมูลสินค้ามาแรง">
            <button type="button" aria-pressed={trend === "market"} onClick={() => setTrend("market")}>มาแรงบน Shopee</button>
            <button type="button" aria-pressed={trend === "studio"} onClick={() => setTrend("studio")}>กำลังโตใน Studio</button>
          </div>
        </div>
        <ul className="affiliate-trend-grid">
          {trends.map(({ product, channels, reason }) => (
            <li key={product.id} className="affiliate-trend-card">
              <div className={`affiliate-product-photo affiliate-photo-${product.id}`} aria-hidden="true" />
              <div className="affiliate-trend-info">
                <span className="affiliate-category">{product.category}</span>
                <h3>{product.name}</h3>
                <p className="affiliate-price">{formatMetric("estimated", product.price)}</p>
                <p className="affiliate-trend-reason">{reason}</p>
                {channels.length > 0 && <details>
                  <summary>ดูออเดอร์ตามช่องทาง</summary>
                  <ul className="affiliate-trend-channels">{channels.map(({ name, current, previous }) => (
                    <li key={name}>{name} · {current} ออเดอร์ (ก่อนหน้า {previous})</li>
                  ))}</ul>
                </details>}
                <button type="button" className="text-button" onClick={() => onProduct(product)} disabled={busy}>
                  {savedProducts[product.id] ? "เปิดใน Studio" : "เพิ่มเข้า Studio"}
                </button>
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section className="panel" aria-labelledby="affiliate-chart-title">
        <div className="affiliate-section-head">
          <h2 id="affiliate-chart-title">แนวโน้ม{metricName}</h2>
          {canCompare && <label className="checkbox"><input type="checkbox" checked={compare} onChange={(event) => setCompare(event.target.checked)} /> เทียบช่วงก่อนหน้า</label>}
        </div>
        {hasCoverage ? <>
          <div className="affiliate-chart-legend" aria-hidden="true"><span>ช่วงที่เลือก</span>{compare && canCompare && <span>ช่วงก่อนหน้า</span>}</div>
          <div className="affiliate-chart" aria-hidden="true">
            {points.map(({ date, label, value, prior }, index) => (
              <div className="affiliate-chart-point" key={date}>
                <div className="affiliate-bars" title={`${label} · ${formatMetric(metric, value)}${compare && canCompare ? ` · ช่วงก่อนหน้า ${formatMetric(metric, prior)}` : ""}`}>
                  {compare && canCompare && <div className="affiliate-prior-bar" style={{ height: `${prior / largestPoint * 100}%` }} />}
                  <div className="affiliate-current-bar" style={{ height: `${value / largestPoint * 100}%` }} />
                </div>
                <span>{index === 0 || index === points.length - 1 || (points.length >= 5 && index === Math.floor(points.length / 2)) ? formatDate(date) : " "}</span>
              </div>
            ))}
          </div>
          {totals.orders === 0 && <p className="muted">ไม่มีออเดอร์ในช่วงนี้</p>}
          <details className="affiliate-chart-data">
            <summary>ดูตัวเลขในกราฟ</summary>
            <table><thead><tr><th scope="col">วันที่</th><th scope="col">ช่วงที่เลือก</th>{compare && canCompare && <th scope="col">ช่วงก่อนหน้า</th>}</tr></thead>
              <tbody>{points.map(({ date, label, value, prior }) => (
                <tr key={date}><th scope="row">{label}</th><td>{formatMetric(metric, value)}</td>{compare && canCompare && <td>{formatMetric(metric, prior)}</td>}</tr>
              ))}</tbody>
            </table>
          </details>
        </> : <p className="muted">{validRange ? "ไม่มีข้อมูลตัวอย่างในช่วงที่เลือก" : "เลือกช่วงวันที่เพื่อดูแนวโน้ม"}</p>}
      </section>

      <section className="panel" aria-labelledby="affiliate-links-title">
        <div className="affiliate-section-head">
          <h2 id="affiliate-links-title">ผลงานรายลิงก์</h2>
          {hasCoverage && <label className="affiliate-sort">เรียงตาม<select value={sort} onChange={(event) => setSort(event.target.value as keyof Totals)}>
            {metrics.map(({ key, label }) => <option key={key} value={key}>{label}</option>)}
          </select></label>}
        </div>
        {hasCoverage ? <>
          <ul className="affiliate-link-list">
            {links.map((link) => (
              <li key={link.subId} className="affiliate-link">
                <div>
                  <button type="button" className="text-button" aria-expanded={selectedLink === link.subId} onClick={() => setSelectedLink(selectedLink === link.subId ? "" : link.subId)}>{link.product.name}</button>
                  <p className="muted">{link.channel} · Sub ID {link.subId}</p>
                </div>
                <dl className="affiliate-link-metrics">
                  {metrics.map(({ key, label }) => <div key={key}><dt>{label}</dt><dd>{formatMetric(key, link[key])}</dd></div>)}
                </dl>
                {selectedLink === link.subId && <div className="affiliate-link-detail">
                  <button type="button" className="secondary" onClick={() => onProduct(link.product)} disabled={busy}>
                    {savedProducts[link.product.id] ? "เปิดใน Studio" : "เพิ่มเข้า Studio"}
                  </button>
                </div>}
              </li>
            ))}
          </ul>
        </> : <p className="muted">เลือกช่วงที่มีข้อมูลตัวอย่างเพื่อดูผลงานรายลิงก์</p>}
        <p className="affiliate-source-note muted">สถานะรายงานจริง · ยังไม่มีข้อมูลจาก Shopee</p>
      </section>
    </div>
  );
}
