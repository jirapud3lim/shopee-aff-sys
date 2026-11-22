export const demoProducts = [
  { id: "fan", name: "พัดลมพกพาปรับแรงลม", category: "แก็ดเจ็ต", price: 259, marketRank: 1 },
  { id: "tumbler", name: "แก้วเก็บความเย็น 750 มล.", category: "ของใช้ในบ้าน", price: 389, marketRank: 2 },
  { id: "organizer", name: "กล่องจัดระเบียบลิ้นชัก", category: "จัดเก็บของ", price: 149, marketRank: 3 },
] as const;

export type DemoProduct = (typeof demoProducts)[number];

export const demoLinks = [
  { product: demoProducts[0], channel: "TikTok", subId: "FANTT", seed: 17, commission: 24 },
  { product: demoProducts[1], channel: "Facebook", subId: "CUPFB", seed: 23, commission: 38 },
  { product: demoProducts[2], channel: "Instagram", subId: "BOXIG", seed: 31, commission: 15 },
  { product: demoProducts[0], channel: "Facebook", subId: "FANFB", seed: 11, commission: 24 },
] as const;

export type Totals = { clicks: number; orders: number; estimated: number; confirmed: number };

export const emptyTotals: Totals = { clicks: 0, orders: 0, estimated: 0, confirmed: 0 };

export function sumTotals(rows: readonly Totals[]): Totals {
  return rows.reduce((sum, row) => ({
    clicks: sum.clicks + row.clicks,
    orders: sum.orders + row.orders,
    estimated: sum.estimated + row.estimated,
    confirmed: sum.confirmed + row.confirmed,
  }), emptyTotals);
}

const dayMs = 86_400_000;
export const lastDemoDate = "2026-11-21";

export function shiftDate(date: string, days: number) {
  return new Date(Date.parse(date) + days * dayMs).toISOString().slice(0, 10);
}

export function numberOfDays(from: string, to: string) {
  return (Date.parse(to) - Date.parse(from)) / dayMs + 1;
}

export const demoDays = Array.from({ length: 60 }, (_, index) => {
  const date = shiftDate(lastDemoDate, index - 59);
  const links = demoLinks.map((link, linkIndex) => {
    if (index === 47) return { ...link, ...emptyTotals };
    const growth = index >= 53 ? [1, 3, 0, 0][linkIndex] : 0;
    const orders = (index * link.seed + Math.floor(index / 4)) % 4 + growth;
    const clicks = 9 + orders * (5 + linkIndex) + (index * link.seed) % 31;
    const estimated = orders * link.commission;
    const confirmed = Math.max(0, orders - (index >= 53 ? 2 : index % 3)) * link.commission;
    return { ...link, orders, clicks, estimated, confirmed };
  });
  return { date, links };
});

export const growingProducts = demoProducts.map((product) => {
  const ordersForLink = (subId: string, days: typeof demoDays) => days.reduce((total, day) => (
    total + (day.links.find((link) => link.subId === subId)?.orders ?? 0)
  ), 0);
  const channels = demoLinks.filter((link) => link.product.id === product.id).map((link) => ({
    name: link.channel,
    current: ordersForLink(link.subId, demoDays.slice(-7)),
    previous: ordersForLink(link.subId, demoDays.slice(-14, -7)),
  }));
  const current = channels.reduce((total, channel) => total + channel.current, 0);
  const previous = channels.reduce((total, channel) => total + channel.previous, 0);
  return { product, current, previous, channels };
}).filter(({ current, previous }) => current > previous).sort((a, b) => (
  (b.current - b.previous) - (a.current - a.previous)
));
