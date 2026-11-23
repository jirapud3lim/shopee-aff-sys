"use client";

import { useEffect, useState, type ReactNode } from "react";
import { listingItemId, type CatalogProduct, type Selection } from "./affiliate-link-setup";
import type { StudioRequest } from "./meta-publishing";
import { estimatedCommission, visiblePrice, type Offer } from "./shopee-offers";

type Trend = {
  title: string;
  traffic: string | null;
  matches: { product_id: string; name: string; opportunity: { total: number } }[];
  offer_matches: { offer_id: string; score: number }[];
};
type TrendFeed = { trends: Trend[]; stale: boolean };
type Card = { selection: Selection; offer?: Offer; trend?: Trend; score?: number };

const count = new Intl.NumberFormat("th-TH");
const baht = new Intl.NumberFormat("th-TH", { style: "currency", currency: "THB" });

function trendCards(feed: TrendFeed | undefined, products: CatalogProduct[], offers: Offer[]) {
  const catalog = new Map(products.map((item) => [item.id, item]));
  const byOfferId = new Map(offers.map((offer) => [offer.offer_id, offer]));
  const cards = new Map<string, Card>();
  function add(card: Card) {
    const key = card.offer?.offer_id ?? card.selection.id;
    if ((card.score ?? 0) > (cards.get(key)?.score ?? -1)) cards.set(key, card);
  }
  for (const trend of feed?.trends ?? []) {
    for (const match of trend.matches) {
      const id = listingItemId(catalog.get(match.product_id)?.source_url);
      add({
        selection: { kind: "catalog", id: match.product_id, name: match.name }, trend,
        offer: id ? byOfferId.get(id) : undefined, score: match.opportunity.total,
      });
    }
    for (const match of trend.offer_matches ?? []) {
      const offer = byOfferId.get(match.offer_id);
      if (!offer) continue;
      add({
        selection: { kind: "offer", id: offer.offer_id, name: offer.name }, offer, trend,
        score: match.score,
      });
    }
  }
  return [...cards.values()].sort((left, right) => (right.score ?? 0) - (left.score ?? 0));
}

function ProductCard({ card, onChoose }: { card: Card; onChoose: (item: Selection, trend: string) => void }) {
  const { selection, offer, trend } = card;
  return <article className="discovery-card">
    {offer?.image_url && <img src={offer.image_url} alt="" width={480} height={300}
      loading="lazy" referrerPolicy="no-referrer" onError={(event) => { event.currentTarget.hidden = true; }} />}
    <div className="discovery-card-content">
      {trend && <p className="discovery-trend">{trend.title}{trend.traffic && ` · ค้นหาประมาณ ${trend.traffic}`}</p>}
      <h3>{selection.name}</h3>
      {offer && <dl className="discovery-metrics">
        <div><dt>ราคา</dt><dd>{baht.format(visiblePrice(offer))}</dd></div>
        <div><dt>ยอดขาย Shopee</dt><dd>{count.format(offer.sold)}{offer.sold_is_minimum && "+"}</dd></div>
        <div><dt>อัตราค่าคอม</dt><dd>{count.format(offer.commission_bps / 100)}%</dd></div>
        <div><dt>คอม/ออเดอร์ (ประมาณ)</dt><dd>{baht.format(estimatedCommission(offer))}</dd></div>
      </dl>}
      <button type="button" className="primary"
        aria-label={`เลือกสินค้า ${selection.name}`}
        onClick={() => onChoose(selection, trend?.title ?? "")}>เลือกสินค้านี้</button>
    </div>
  </article>;
}

function Shelf({ cards, empty, onChoose }: { cards: Card[]; empty: ReactNode; onChoose: (item: Selection, trend: string) => void }) {
  const [limit, setLimit] = useState(4);
  if (!cards.length) return <div className="panel">{empty}</div>;
  return <>
    <div className="discovery-grid">{cards.slice(0, limit).map((card) =>
      <ProductCard key={card.selection.id} card={card} onChoose={onChoose} />)}</div>
    {cards.length > limit && <button className="secondary discovery-more" type="button"
      onClick={() => setLimit((current) => current + 8)}>ดูสินค้าเพิ่ม</button>}
  </>;
}

export default function ProductDiscovery({ request, scope, token, products, onChoose }: {
  request: StudioRequest;
  scope: string;
  token: string;
  products: CatalogProduct[];
  onChoose: (item: Selection, trend: string) => void;
}) {
  const [feed, setFeed] = useState<TrendFeed>();
  const [offers, setOffers] = useState<Offer[]>([]);
  const [trendsStatus, setTrendsStatus] = useState<"loading" | "ready" | "error">("loading");
  const [offersStatus, setOffersStatus] = useState<"loading" | "ready" | "error">("loading");
  const [revision, setRevision] = useState(0);
  const [sort, setSort] = useState<"estimate" | "rate" | "sold">("estimate");

  useEffect(() => {
    const controller = new AbortController();
    const init = { signal: controller.signal };
    setOffersStatus("loading");
    setTrendsStatus("loading");
    request<TrendFeed>(scope + "/trends?hours=24&include_offers=true", token, init).then((data) => {
      if (controller.signal.aborted) return;
      setFeed(data);
      setTrendsStatus("ready");
    }).catch(() => { if (!controller.signal.aborted) setTrendsStatus("error"); });
    request<Offer[]>(scope + "/shopee-offers", token, init).then((data) => {
      if (controller.signal.aborted) return;
      setOffers(data);
      setOffersStatus("ready");
    }).catch(() => { if (!controller.signal.aborted) setOffersStatus("error"); });
    return () => controller.abort();
  }, [request, revision, scope, token]);

  const metric = (offer: Offer) => sort === "estimate" ? estimatedCommission(offer)
    : sort === "rate" ? offer.commission_bps : offer.sold;
  const ranked = [...offers].sort((left, right) => metric(right) - metric(left) || right.sold - left.sold ||
    left.offer_id.localeCompare(right.offer_id));
  const retry = <button type="button" className="secondary" onClick={() => setRevision((value) => value + 1)}>ลองโหลดอีกครั้ง</button>;

  return <div className="discovery" id="discover">
    <header className="discovery-header">
      <h1 tabIndex={-1}>เลือกสินค้า</h1>
      <p className="muted">เลือกจากสินค้าตามกระแสหรือข้อเสนอค่าคอมสูง แล้ว Studio จะค้นลิงก์ Affiliate ให้</p>
      <button type="button" className="secondary discovery-jump" onClick={() => {
        const heading = document.getElementById("discovery-commission");
        heading?.focus({ preventScroll: true });
        heading?.scrollIntoView({ block: "start" });
      }}>ไปที่สินค้าค่าคอมสูง ↓</button>
    </header>
    <section className="discovery-shelf" aria-labelledby="discovery-trends">
      <div className="discovery-section-head">
        <div>
          <h2 id="discovery-trends">สินค้าตามกระแส Google Trends</h2>
          <p className="muted">จับคู่สินค้ากับคำค้นมาแรงในไทยช่วง 24 ชั่วโมง{feed?.stale && " · ข้อมูลล่าสุดที่บันทึกไว้"}</p>
        </div>
        <a href="#trends">ดูเทรนด์ทั้งหมด</a>
      </div>
      <Shelf cards={trendCards(feed, products, offers)} onChoose={onChoose} empty={
        trendsStatus === "loading" ? <p role="status">กำลังโหลดเทรนด์…</p> :
        trendsStatus === "error" ? <><p role="alert">โหลด Google Trends ไม่สำเร็จ</p>{retry}</> :
        <p>ยังไม่พบสินค้าที่ตรงกับเทรนด์ <a href="#trends">เลือกคำค้นเพื่อคัดสินค้า</a></p>
      } />
    </section>
    <section className="discovery-shelf" aria-labelledby="discovery-commission">
      <div className="discovery-section-head">
        <div>
          <h2 id="discovery-commission" tabIndex={-1}>สินค้าค่าคอมสูงใน Shopee</h2>
          <p className="muted">จากข้อเสนอที่บันทึกไว้ · ค่าคอมประมาณจากราคา × อัตราที่ Shopee แสดง</p>
        </div>
        <label>เรียงตาม<select value={sort} onChange={(event) => setSort(event.target.value as typeof sort)}>
          <option value="estimate">ค่าคอมบาทต่อออเดอร์</option>
          <option value="rate">อัตราค่าคอม (%)</option>
          <option value="sold">ยอดขาย</option>
        </select></label>
      </div>
      <Shelf cards={ranked.map((offer) => ({
        selection: { kind: "offer", id: offer.offer_id, name: offer.name }, offer,
      }))} onChoose={onChoose} empty={
        offersStatus === "loading" ? <p role="status">กำลังโหลดข้อเสนอ…</p> :
        offersStatus === "error" ? <><p role="alert">โหลดข้อเสนอ Shopee ไม่สำเร็จ</p>{retry}</> :
        <p>ยังไม่มีข้อเสนอในพื้นที่ทำงาน <a href="#shopee-offers">นำเข้าข้อเสนอ Shopee</a></p>
      } />
    </section>
  </div>;
}
