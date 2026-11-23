# Affiliate Studio workflow

## จากเลือกสินค้าถึงตรวจโพสต์

```mermaid
flowchart TD
    discover["Google Trends, คัดสินค้า Shopee หรือเลือกจากคลัง"]
    product["ยืนยัน Shop ID, Item ID, ตัวเลือกสินค้า และสิทธิ์ใช้สื่อ"]
    affiliate["บันทึกลิงก์ Affiliate แยกตามช่องทาง"]
    plan["เขียนบท แคปชัน และวางลำดับช็อต"]
    footage{"ใช้ Google Flow หรือไม่?"}
    reference["ตรวจภาพอ้างอิงจากตัวเลือกสินค้าจริง"]
    storyboard["สร้างสตอรีบอร์ดภาพนิ่งสมจริง 9:16"]
    storyboardGate{"ผู้ใช้อนุมัติสตอรีบอร์ดหรือยัง?"}
    generate["สร้างเฉพาะช็อตที่อนุมัติด้วย Veo 3.1 Lite"]
    edit["ประกอบคลิปแนวตั้งและส่งออก MP4"]
    videoGate{"ตรวจภาพ เสียง ซับ และสินค้าผ่านหรือยัง?"}
    repair["แก้เฉพาะช็อต เสียง หรือข้อความที่มีปัญหา"]
    platform["เลือกปลายทาง เตรียมไฟล์ แคปชัน และลิงก์"]
    approval{"อนุมัติเผยแพร่และตรวจป้ายเปิดเผยแล้วหรือยัง?"}
    hold["ค้างไว้สำหรับตรวจหรือทำต่อในฉบับร่าง"]
    facebook["Facebook Reels ผ่าน Meta API หรือโพสต์ใน Facebook"]
    tiktok["TikTok Studio อัปโหลดผ่านหน้าเว็บ"]
    tiktokApi["TikTok Content Posting API รอทดสอบส่งเข้า Inbox"]
    verify["ตรวจโพสต์จริงและลิงก์หรือคอมเมนต์ Affiliate แยกกัน"]

    discover --> product --> affiliate --> plan --> footage
    footage -->|"ใช้ Flow"| reference --> storyboard --> storyboardGate
    storyboardGate -->|"แก้แผงที่เกี่ยวข้อง"| storyboard
    storyboardGate -->|"อนุมัติ"| generate --> edit
    footage -->|"ใช้ไฟล์ที่มีอยู่"| edit
    edit --> videoGate
    videoGate -->|"ต้องแก้"| repair --> edit
    repair -.->|"เมื่อแก้ช็อต Flow"| storyboard
    videoGate -->|"ผ่าน"| platform --> approval
    approval -->|"ยังไม่ครบ"| hold
    approval -->|"Facebook"| facebook --> verify
    approval -->|"TikTok"| tiktok --> verify
    platform -.->|"เมื่อสิทธิ์พร้อม"| tiktokApi
```

- **Google Flow** ใช้ตัวละครพิธีกรคัดของเข้าบ้านและเสียง Callirrhoe ตามกฎโครงการ หากแก้หรือเพิ่มช็อต ให้แสดงแผงสตอรีบอร์ดที่เกี่ยวข้องและขออนุมัติอีกครั้งก่อนสร้างวิดีโอ เก็บภาพอ้างอิง คลิป เสียง และเวอร์ชันที่อนุมัติตามเลขช็อต [กฎการผลิตและเผยแพร่](../../AGENTS.md)
- **Facebook** เคยยืนยันการเผยแพร่ Reel และอ่านคอมเมนต์ Affiliate กลับผ่าน Meta API แล้ว ส่วนการปักสินค้าผ่านหน้า Facebook ใช้ขั้นตอนแยกและยังรอยืนยันผล [วิธีเชื่อม Facebook](../../README.md#connect-a-local-facebook-page)
- **TikTok** เคยอัปโหลด MP4 ทดสอบผ่าน TikTok Studio จนเห็นสถานะ Uploaded และตัวอย่างวิดีโอ การส่งฉบับร่างผ่าน API ยังรอการตั้งค่า Sandbox และการอนุญาต `video.upload` [สถานะการทดสอบ](../agent/SESSION_HANDOFF.md)

## รายงาน Affiliate และการเลือกสินค้ารอบถัดไป

```mermaid
flowchart LR
    report["Shopee Click Report และ Order Report"]
    importCsv["นำเข้า CSV ในพื้นที่ทำงาน"]
    match["จับคู่ลิงก์ด้วยช่องทางและ Sub ID"]
    results["ดูคลิก คำสั่งซื้อ และค่าคอมมิชชัน"]
    rank["ใช้ยอดคลิกและคำสั่งซื้อประกอบการจัดอันดับสินค้า"]

    report --> importCsv --> match --> results --> rank
```

ดูวิธีนำเข้าและวิธีนับคลิกกับคำสั่งซื้อจาก [คู่มือรายงาน Affiliate](../../README.md#import-shopee-affiliate-reports)
