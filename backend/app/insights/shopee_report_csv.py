"""Parse Shopee Thailand Affiliate Portal click and order CSV reports."""

import csv
import hashlib
import io
import json
import re
import unicodedata
from datetime import datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

BANGKOK = ZoneInfo("Asia/Bangkok")
MONEY_SCALE = 1_000_000
MAX_ROWS = 100_000
EMPTY = {"", "-", "--", "n/a", "null"}
HEADERS = {
    "click_id": ("Click ID", "รหัสคลิก", "รหัสการคลิก", "คลิก ID"),
    "click_date": ("Click Time", "Click Date", "Click Date/Time", "เวลาคลิก", "เวลาที่คลิก", "วันที่คลิก"),
    "order_id": ("Order ID", "รหัสการสั่งซื้อ", "รหัสคำสั่งซื้อ", "Order SN", "Order Number", "เลขที่คำสั่งซื้อ", "หมายเลขคำสั่งซื้อ"),
    "order_date": ("Order Time", "Order Date", "Order Creation Time", "Order Create Time", "Purchase Time", "เวลาที่สั่งซื้อ", "เวลาสั่งซื้อ", "วันที่สั่งซื้อ"),
    "line_id": ("Order Line ID", "Order Item ID", "Item Line ID", "รหัสรายการคำสั่งซื้อ"),
    "item_id": ("Item ID", "Product ID", "เลขที่สินค้า", "รหัสสินค้า", "เลขที่ผลิตภัณฑ์"),
    "model_id": ("Model ID", "Variation ID", "รหัสโมเดล", "เลขที่โมเดล"),
    "status": ("Order Status", "สถานะการสั่งซื้อ", "สถานะคำสั่งซื้อ"),
    "fraud": ("Fraud Status", "สถานะทุจริต", "สถานะการทุจริต"),
    "updated": ("Last Update Time", "Last Updated Time", "Update Time", "Updated At", "เวลาที่อัปเดต", "เวลาอัปเดตล่าสุด"),
    "channel": ("Channel", "ช่องทาง", "Affiliate Channel", "Platform"),
    "referrer": ("Referrer", "Referer", "Referral", "อ้างอิง", "แหล่งอ้างอิง"),
    "sub_id": ("Sub ID", "Sub IDs", "Sub ID(s)", "Affiliate Sub ID", "ซับไอดี"),
    "net_order": ("Net Commission", "Net Commission Amount", "Net Affiliate Commission", "Order Net Commission", "ค่าคอมมิชชั่นสุทธิ", "ค่าคอมมิชชันสุทธิ"),
    "order_amount": ("Order Total Commission", "Total Order Commission", "Order Commission", "ค่าคอมมิชชั่นคำสั่งซื้อ", "ค่าคอมมิชชั่นร้านค้า", "ค่าคอมมิชชันคำสั่งซื้อ", "ค่าคอมมิชชั่นการสั่งซื้อ"),
    "item_amount": ("Item Total Commission", "Total Item Commission", "Item Commission", "ค่าคอมมิชชั่นสินค้า", "ค่าคอมมิชชันสินค้า"),
    "estimated": ("Estimated Commission", "Estimated Affiliate Commission", "Affiliate Commission", "ค่าคอมมิชชั่นโดยประมาณ", "ค่าคอมมิชชันโดยประมาณ", "ค่าตอบแทนโดยประมาณ"),
    "confirmed": ("Confirmed Commission", "Validated Commission", "ค่าคอมมิชชั่นที่ยืนยันแล้ว", "ค่าคอมมิชชันที่ยืนยันแล้ว", "ค่าตอบแทนที่ยืนยันแล้ว"),
}
STATUS = {
    "unpaid": ("unpaid", "not paid", "to pay", "ยังไม่ชำระเงิน", "รอชำระเงิน"),
    "pending": ("pending", "processing", "รอดำเนินการ", "กำลังดำเนินการ"),
    "completed": ("completed", "complete", "success", "successful", "confirmed", "validated", "ดำเนินการสำเร็จ", "สำเร็จ", "ได้รับการยืนยัน"),
    "cancelled": ("cancelled", "canceled", "invalid", "rejected", "refunded", "ยกเลิก", "ยกเลิกแล้ว", "คืนเงิน", "ไม่ถูกต้อง"),
}


# Keep Thai vowel and tone marks when removing separators.
def normalized_header(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    value = re.sub(r"\s*[\[(]\s*(?:฿|thb|บาท|thai baht)\s*[\])]\s*$", "", value)
    return "".join(c for c in value if unicodedata.category(c)[0] in "LMN")


def normalized_status(value: str) -> str:
    key = normalized_header(value)
    return next((status for status, aliases in STATUS.items()
                 if any(normalized_header(alias) == key for alias in aliases)), "unknown")


CHANNELS = {
    "facebook": ("facebook", "fb", "เฟซบุ๊ก", "เฟสบุ๊ค", "เฟสบุ๊ก", "com.facebook.katana"),
    "instagram": ("instagram", "ig", "อินสตาแกรม", "com.instagram.android"),
    "tiktok": ("tiktok", "ติ๊กต็อก"),
    "youtube": ("youtube", "ยูทูบ"),
    "line": ("line", "ไลน์"),
    "website": ("website", "web", "เว็บไซต์"),
    "shopee": ("shopee", "ช้อปปี้", "ชอปปี้"),
}
HOSTS = {
    "facebook.com": "facebook", "fb.com": "facebook", "fb.watch": "facebook",
    "instagram.com": "instagram", "tiktok.com": "tiktok", "youtube.com": "youtube",
    "youtu.be": "youtube", "line.me": "line", "shopee.co.th": "shopee",
}
CHANNEL_NAMES = {normalized_header(alias): key for key, names in CHANNELS.items() for alias in names}


def known_channel(value: str) -> str | None:
    known = CHANNEL_NAMES.get(normalized_header(value))
    if known:
        return known
    try:
        host = urlsplit(value if "://" in value else "//" + value).hostname or ""
    except ValueError:
        return None
    return next((channel for domain, channel in HOSTS.items()
                 if host == domain or host.endswith("." + domain)), None)


def report_channel(channel: str, referrer: str) -> str | None:
    known = known_channel(channel) or known_channel(referrer)
    if known:
        return known
    # Explicit channel labels can be custom. Keep only labels, never raw referrer URLs.
    if channel and len(channel) <= 80 and all(c.isalnum() or c in " _-" or
                                               unicodedata.category(c)[0] == "M" for c in channel):
        return channel.casefold()
    return None


def clean(value: str) -> str:
    value = value.strip()
    if value.startswith('="') and value.endswith('"'):
        value = value[2:-1]
    if value.startswith("'"):
        value = value[1:]
    return "" if value.casefold() in EMPTY else value


def report_time(value: str, field: str) -> datetime:
    if re.match(r"^[0-9]{4}[-/]", value):
        year = int(value[:4])
        if 2400 <= year <= 2700:
            value = str(year - 543) + value[4:]
        value = value.replace("/", "-", 2)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        # Shopee Thailand's date picker displays day-month-year.
        match = re.fullmatch(
            r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})(?:[ T](\d{1,2}):(\d{2})(?::(\d{2}))?)?",
            value,
        )
        if not match:
            raise ValueError(f"Invalid {field}") from None
        day, month, year, hour, minute, second = (int(part or 0) for part in match.groups())
        if 2400 <= year <= 2700:
            year -= 543
        try:
            parsed = datetime(year, month, day, hour, minute, second)
        except ValueError:
            raise ValueError(f"Invalid {field}") from None
    return parsed.astimezone(BANGKOK) if parsed.tzinfo else parsed.replace(tzinfo=BANGKOK)


def money(value: str) -> int | None:
    if not value:
        return None
    amount = value.replace("฿", "").replace(",", "").strip()
    try:
        scaled = Decimal(amount) * MONEY_SCALE
        if scaled.is_finite() and abs(scaled) <= 10**14 and scaled == scaled.to_integral_value():
            return int(scaled)
    except InvalidOperation:
        pass
    raise ValueError("Invalid commission amount or unsupported precision")


def stable_key(*parts: str) -> str:
    return hashlib.sha256(json.dumps(parts, ensure_ascii=False).encode("utf-8")).hexdigest()


def read_report(content: bytes, kind: str) -> tuple[dict[str, dict], int]:
    if content.startswith((b"\xff\xfe", b"\xfe\xff")):
        text = content.decode("utf-16")
    else:
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = content.decode("cp874")
    if not text.strip() or "\x00" in text:
        raise ValueError("Upload a Shopee CSV file")
    first = text.splitlines()[0]
    delimiter = "\t" if first.count("\t") > first.count(",") else ","
    reader = csv.DictReader(io.StringIO(text, newline=""), delimiter=delimiter, strict=True)
    header_map = {normalized_header(name): name for name in reader.fieldnames or [] if name.strip()}
    if len(header_map) != len([name for name in reader.fieldnames or [] if name.strip()]):
        raise ValueError("The CSV has duplicate column headers")
    fields = {
        key: [header_map[normalized_header(alias)] for alias in aliases if normalized_header(alias) in header_map]
        for key, aliases in HEADERS.items()
    }
    id_field, date_field = ("click_id", "click_date") if kind == "clicks" else ("order_id", "order_date")
    if not fields[id_field] or not fields[date_field]:
        label = "Click ID and Click Time" if kind == "clicks" else "Order ID and Order Time"
        raise ValueError(f"The selected report must contain {label} (Thai headers are supported)")
    sub_columns = [header_map.get(f"subid{index}") for index in range(1, 6)]
    records = {}
    duplicate_count = 0
    for row in reader:
        if reader.line_num > MAX_ROWS + 1:
            raise ValueError(f"CSV exceeds {MAX_ROWS:,} rows")
        if all(not value for value in row.values()):
            continue
        try:
            if None in row or any(value is None for value in row.values()):
                raise ValueError("Column count does not match the header")

            def get(key: str) -> str:
                return next((value for col in fields[key] if (value := clean(row[col]))), "")

            identifier = get(id_field)
            if not identifier or not get(date_field):
                raise ValueError("Missing record ID or date")
            when = report_time(get(date_field), date_field)
            sub_id = get("sub_id")
            if not sub_id:
                sub_id = "-".join(clean(row[column]) if column else "" for column in sub_columns)
            sub_id = sub_id.strip("- ").strip()
            if len(sub_id) > 600:
                raise ValueError("Sub ID is too long")
            channel = report_channel(get("channel"), get("referrer"))
            record = {"day": when.date(), "sub_id": sub_id or None, "source_channel": channel}
            if kind == "clicks":
                key = stable_key(identifier)
            else:
                line_id = get("line_id")
                key = stable_key(identifier, line_id) if line_id else stable_key(
                    identifier, get("item_id"), get("model_id"),
                )
                status = normalized_status(get("status"))
                if normalized_header(get("fraud")) in {"fraud", "fraudulent", "ทุจริต"}:
                    status = "cancelled"
                updated = get("updated")
                net_order = money(get("net_order"))
                order_amount = net_order if net_order is not None else money(get("order_amount"))
                item_amount = money(get("item_amount"))
                estimated = money(get("estimated"))
                record.update(
                    order_key=stable_key(identifier),
                    allocation="order" if order_amount is not None else "line",
                    estimated=order_amount if order_amount is not None else (
                        estimated if estimated is not None else item_amount
                    ),
                    confirmed=money(get("confirmed")),
                    status=status,
                    updated=report_time(updated, "update time").isoformat() if updated else None,
                )
            if key in records:
                duplicate_count += 1
                prior = records[key]
                if kind == "orders" and prior["updated"] and record["updated"]:
                    if prior["updated"] > record["updated"]:
                        continue
                    if prior["updated"] < record["updated"]:
                        records[key] = record
                        continue
                if prior != record:
                    raise ValueError("Conflicting rows for the same record ID")
            records[key] = record
        except ValueError as exc:
            raise ValueError(f"Row {reader.line_num}: {exc}") from None
    return records, duplicate_count
