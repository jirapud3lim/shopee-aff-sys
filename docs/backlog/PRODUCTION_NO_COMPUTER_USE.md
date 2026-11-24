# Open tickets สำหรับ production ที่ไม่มี Codex Computer Use

เปิดวันที่ 24 พฤศจิกายน 2026 ใน backlog ของ repository ดูผลตรวจรายขั้นใน [ตาราง Computer Use](../product/COMPUTER_USE_AUDIT.md)

**ลำดับงาน** PRD-01 กำหนดขอบเขต deployment จากนั้นทำเส้นทางนำเข้าและส่งต่องานด้วยผู้ใช้ใน PRD-02 ถึง PRD-10 ให้ครบก่อนเรียก production ว่ารองรับ pipeline ทั้งหมด งาน API ที่ยังรอสิทธิ์เดินคู่ขนานได้ เปิดใช้เฉพาะช่องทางที่ผ่านเกณฑ์ของ ticket นั้น

| Ticket | สถานะ | งาน |
|---|---|---|
| [PRD-01](#prd-01) | OPEN · P0 · ผ่านในเครื่อง รอ CI | ตรวจ production artifacts และ smoke test โดยไม่มี Computer Use |
| [PRD-02](#prd-02) | OPEN · P0 | ค้นหา นำเข้า และยืนยันสินค้ากับ variant |
| [PRD-03](#prd-03) | OPEN · P0 · ผ่าน mock รอทดสอบ Shopee จริง | สร้างและตรวจลิงก์ Affiliate แยกช่องทาง |
| [PRD-04](#prd-04) | OPEN · P0 | ส่งออกชุดภาพอ้างอิงและนำเข้า Storyboard รายช็อต |
| [PRD-05](#prd-05) | OPEN · P0 | ส่งต่องานสร้างวิดีโอ และพิสูจน์ Veo API |
| [PRD-06](#prd-06) | OPEN · P0 | เก็บและแก้เสียง Callirrhoe เป็นรายบรรทัด |
| [PRD-07](#prd-07) | OPEN · P0 | เรนเดอร์และตรวจ MP4 ก่อนอนุมัติ |
| [PRD-08](#prd-08) | OPEN · P0 | เผยแพร่และยืนยันผล Facebook |
| [PRD-09](#prd-09) | OPEN · P1 | ส่งต่อ TikTok และพิสูจน์ Inbox Upload API |
| [PRD-10](#prd-10) | OPEN · P1 | นำเข้ารายงาน Affiliate และเทียบยอด |

<a id="prd-01"></a>

## PRD-01 — ตรวจขอบเขต deployment

**งาน** ตรวจ Docker build context, runtime image, web bundle, API, worker และ scheduled jobs ให้ production ไม่มี Codex Computer Use, Codex credentials, browser session หรือ browser automation สำหรับพอร์ทัลภายนอก ตั้งค่า production UI ให้เลือกเส้นทาง manual หรือ API โดยไม่รอ Safari Capture ทดสอบบนเครื่องสะอาด ต่อยอดจาก staging Dockerfiles และ smoke test เดิม

**ปิดเมื่อ** CI ตรวจ production artifact และ configuration ได้ และทดสอบตั้งแต่เลือกสินค้าถึงเรนเดอร์ เตรียมโพสต์ และนำเข้า CSV ด้วย fixture, API test doubles และไฟล์ที่ผู้ใช้นำเข้า โดยไม่มี Codex หรือส่วนขยาย ตีพิมพ์ผลตรวจและระบุความสามารถที่ยังติดสิทธิ์แยกจากผล smoke test

**หลักฐานทดสอบในเครื่อง** เว็บ API และ worker แบบ Docker ผ่านการตรวจ artifacts และเครือข่ายและรัน smoke test ด้วย PostgreSQL สำเร็จ Chromium แยกจาก runtime ทดสอบการบันทึกลิงก์และอนุมัติ Storyboard โดยไม่มี browser bridge และไม่ส่งคำขอออกไปภายนอก เพิ่มขั้นตรวจใน GitHub Actions แล้ว รอผลบน runner หลัง push [วิธีรันทดสอบ](../ops/STAGING.md#verify-the-release-without-computer-use)

<a id="prd-02"></a>

## PRD-02 — ค้นหา นำเข้า และยืนยันสินค้า

**งาน** ใช้ Google Trends RSS และ scoring เดิม เปิดให้เพิ่มรายการข้อเสนอจาก URL และข้อมูลที่ผู้ใช้นำเข้าหรือกรอกเอง เก็บแหล่งข้อมูล เวลาที่เห็นราคา ยอดขาย และค่าคอม พร้อม Shop ID, Item ID, variant, ภาพต้นฉบับ และสิทธิ์ใช้ภาพ ศึกษา `productOfferV2` และ Product Feed เมื่อบัญชีไทยได้รับสิทธิ์ การยืนยันตัวเลือกใช้หลักฐานจากรายการและผู้ใช้เมื่อข้อมูล API มีแค่ระดับ Item ID

**ปิดเมื่อ** fixture ที่ใช้ snapshot เดียวกับ workflow เดิมให้คะแนนและลำดับเดียวกัน ระบบนำเข้า URL ซ้ำแล้วอ้างสินค้าเดิม รายการที่ ID หรือ variant ขัดกับภาพจะค้างให้ตรวจ และรายการยืนยันแล้วใช้ identity เดิมต่อถึงลิงก์และแผนงาน ทดสอบแยก workspace [Shopee Affiliate Open API ที่ตรวจไว้ในโครงการ](../api/SHOPEE_AFFILIATE_ENDPOINTS.md)

<a id="prd-03"></a>

## PRD-03 — สร้างและตรวจลิงก์ Affiliate

**งาน** ทำหน้าส่งต่อที่คัดลอก URL ต้นฉบับกับ Sub ID ให้ผู้ใช้เปิดเครื่องมือสร้างลิงก์ Shopee แล้ววางผลกลับในรายการที่เลือก ตรวจปลายทางด้วยการ resolve URL ฝั่ง server แบบจำกัดโดเมนและตรวจทุก redirect เมื่อรองรับ กรณีที่ต้องอาศัยแอปหรือ session ให้ผู้ใช้ยืนยันรายการจากปลายทางและบันทึกหลักฐาน ศึกษา `generateShortLink` หลังยืนยันสิทธิ์บัญชี เก็บผลตาม workspace, listing, channel และ Sub ID

**ปิดเมื่อ** ลิงก์ที่บันทึกพาไป Shop ID และ Item ID ที่เลือก หลักฐานการสร้างผูก Sub ID กับช่องทาง ลิงก์ผิดสินค้าหรือผิดช่องทางไม่ผ่าน และกรณียืนยันปลายทางไม่ได้แสดงสถานะรอตรวจ Shared variant picker ต้องมีรุ่นที่เลือกในคลิปหรือแคปชันตามกฎโครงการ วัดความเทียบเท่าจากปลายทางและการติดตามผล เพราะ URL สั้นอาจต่างกัน [Shopee Affiliate Open API ที่ตรวจไว้ในโครงการ](../api/SHOPEE_AFFILIATE_ENDPOINTS.md)

**สถานะ** Studio ใช้ลิงก์ที่บันทึกแล้วก่อน ปุ่มสร้างอัตโนมัติผ่าน Open API เปิดเฉพาะเจ้าของ workspace ที่ผูกกับบัญชีที่ได้รับสิทธิ์ เก็บลิงก์ตามรายการ ช่องทาง และ Sub ID ใช้ redirect แบบ HEAD บนโฮสต์ Shopee ที่กำหนดเพื่อตรวจรายการ และบันทึกผู้ตรวจเมื่อปลายทางต้องตรวจเอง ทดสอบด้วย mock แล้วทั้ง request signature การปฏิเสธปลายทางและ Sub ID ที่ผิด การแยก workspace และการส่งต่อไป Storyboard ยังรอ App ID, Secret และการยืนยันสิทธิ์ `generateShortLink` จากบัญชี Shopee Affiliate ประเทศไทยเพื่อทดสอบสด [วิธีเปิดใช้](../../README.md#shopee-product-discovery) · [Shopee Affiliate Open API](https://help.shopee.co.th/portal/4/article/198622)

**ทางเลือกโดยไม่ใช้ API** โหมดพาร์ทเนอร์ประกอบลิงก์ `an_redir` จากรายการ Shopee, Affiliate ID และ Sub ID โดยไม่เปิดพอร์ทัลอัตโนมัติ ทดสอบด้วย fixture ว่าปลายทางที่เปิดเผย publisher หรือ Sub ID ผิดถูกปฏิเสธ เกณฑ์เปิดใช้งานจริงคือยืนยันสิทธิ์บัญชีสำหรับรูปแบบนี้ เปิดลิงก์หนึ่งรายการให้ตรง Shop ID และ Item ID และเทียบ Sub ID ใน Click Report ของบัญชี หากบัญชีใช้รูปแบบพาร์ทเนอร์ไม่ได้ ให้ใช้ลิงก์จากพอร์ทัลหรือการส่งออก Batch ของ Shopee ทาง Batch ยังเป็นขั้นตอนผู้ใช้ [คู่มือพาร์ทเนอร์](https://help.shopee.co.th/portal/10/article/172214) · [คู่มือ Batch](https://help.shopee.co.th/portal/10/article/123906)

<a id="prd-04"></a>

## PRD-04 — ส่งออกภาพอ้างอิงและนำเข้า Storyboard รายช็อต

**งาน** ส่งออกพรอมป์และไฟล์ในสองขั้นเดิม ผู้ใช้นำภาพสินค้าตรงรุ่นไปสร้างภาพอ้างอิงแล้วนำกลับมาตรวจ จากนั้นส่งชุดภาพที่ผ่านพร้อมภาพพิธีกรที่อนุมัติเมื่อใช้พิธีกร เปิด Flow ด้วยลิงก์ปกติแล้วนำภาพนิ่งกลับเข้าตามเลขช็อต ทดสอบ Gemini Image API ด้วยภาพอ้างอิงที่มีสิทธิ์สำหรับงานภาพนิ่งหากทำผลได้เท่ากัน

**ปิดเมื่อ** Studio แสดงภาพนิ่งสมจริงจริงหนึ่งภาพ 9:16 ต่อช็อต พร้อมเลขช็อต เวลา บท และรุ่นสินค้า ผู้ตรวจเทียบสี ขนาด ฉลาก จำนวนสินค้า และพิธีกรได้ การอนุมัติผูกกับภาพเวอร์ชันที่แสดง การเปลี่ยนภาพต้องอนุมัติช็อตที่เปลี่ยนใหม่และคงช็อตอื่นไว้ [Google Flow Help](https://support.google.com/flow/answer/16935308) · [Gemini Image API](https://ai.google.dev/gemini-api/docs/image-generation)

<a id="prd-05"></a>

## PRD-05 — ส่งต่องานสร้างวิดีโอและพิสูจน์ Veo API

**งาน production รอบแรก** ให้ Studio ส่งออกเฉพาะช็อตที่อนุมัติพร้อมภาพเริ่มต้น คำสั่ง เลขช็อต และระยะเวลา ผู้ใช้เปิด Flow ตรวจงานเดิม เครดิต ตัวละครและเสียงตามที่ช็อตใช้ รวมถึง Veo 3.1 Lite และ 9:16 ก่อนสั่งสร้าง แล้วอัปโหลด MP4 กลับตามเลขช็อต จำกัดการแก้และส่งใหม่เฉพาะช็อตที่มีปัญหา

**งานพิสูจน์ API** ทดสอบ Google Cloud `veo-3.1-lite-generate-001` ด้วยโปรเจกต์และโควตาที่อนุมัติ เอกสารโมเดลระบุ Preview, 9:16 และงาน image-to-video แต่ไม่รองรับ asset-reference images หรือ audio input และคู่มือ image-to-video ที่ตรวจระบุเฉพาะโมเดล Standard กับ Fast ต้องยืนยันการเรียก Lite กับภาพเริ่มต้นจริงก่อนเลือก adapter Gemini Developer API ปิด endpoint Lite Preview เมื่อ 22 ตุลาคม 2026 ความเทียบเท่าของตัวละครที่บันทึกใน Flow และเสียงประจำตัวยังต้องพิสูจน์ หาก API ผ่าน ให้ใช้ job ID เดิมอ่านสถานะก่อน retry ผูก job กับช็อตและเวอร์ชัน และบังคับเพดานค่าใช้จ่ายก่อน submit

**ปิดเมื่อ** ผู้ใช้ทำช็อต product-only และช็อตที่มีพิธีกรผ่านเส้นทาง Flow และนำคลิปกลับเข้า Studio ได้โดยไม่ใช้ Computer Use คลิปเป็น 9:16 ผูกกับช็อตที่อนุมัติ ภาพและเสียงผ่านตรวจ และการ retry ช็อตหนึ่งคงคลิปอื่นไว้ เปิดใช้ API เฉพาะกลุ่มช็อตที่ผ่านการทดสอบเดียวกันและยืนยันตัวละครกับเสียงได้ หากค่าบังคับไม่พร้อม ให้ค้างช็อตไว้หรือส่งต่อให้ผู้ใช้ทำใน Flow

[Google Cloud Veo 3.1](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/veo/3-1-generate) · [คู่มือ image-to-video](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/video/generate-videos-from-an-image) · [Gemini API deprecations](https://ai.google.dev/gemini-api/docs/deprecations#veo-models)

<a id="prd-06"></a>

## PRD-06 — เก็บและแก้เสียง Callirrhoe รายบรรทัด

**งาน** ให้ Studio รับไฟล์เสียงที่บันทึกจากพิธีกรที่กำหนดใน Flow ผูกเสียงกับช็อต บรรทัด และเวอร์ชันบท ใช้เสียงเดิมเมื่อข้อความตรงกัน ทดสอบ Gemini TTS ที่มีชื่อเสียง Callirrhoe โดยเทียบโทนไทยและจังหวะกับเสียงที่อนุมัติใน Flow ชื่อเสียงเดียวกันยังไม่ยืนยันว่าใช้การตั้งค่าเสียงของตัวละครเดียวกัน ช็อตเห็นปากต้องตรวจ lip sync โดยผู้ตรวจ และค้างใน Flow เมื่อการใช้เสียงตามกฎโครงการยังยืนยันไม่ได้

**ปิดเมื่อ** ผู้ตรวจฟังชื่อแบรนด์ รุ่น ตัวเลข และจังหวะปากเทียบกับตัวอย่างแล้วผ่าน การแก้หนึ่งบรรทัดคงภาพที่อนุมัติและเสียงบรรทัดอื่นไว้ ตรวจ video stream hash เมื่อเปลี่ยนเฉพาะเสียงโดยไม่เข้ารหัสภาพใหม่ [Gemini TTS และรายการเสียง](https://ai.google.dev/gemini-api/docs/speech-generation#prebuilt-voices)

<a id="prd-07"></a>

## PRD-07 — เรนเดอร์และตรวจ MP4 ฉบับสุดท้าย

**งาน** ใช้ FFmpeg เดิมประกอบคลิป เพิ่มรายงาน `ffprobe` และ full decode ตรวจสัดส่วน ระยะเวลา codec และ audio stream ใช้การตรวจช่วงเงียบและตำแหน่งซับช่วยชี้จุดตรวจ เก็บเลขช็อต แหล่งไฟล์ และ hash ของผลเรนเดอร์ ให้ผู้ตรวจเปิด MP4 ดูและฟังจนจบ โดยตรวจตำแหน่งข้อความกับเครื่องเล่นมือถือของปลายทางก่อนอนุมัติ

**ปิดเมื่อ** fixture คลิปผิดสัดส่วน คลิปเสีย และคลิปที่เสียงขาดเข้าคิวตรวจหรือถูกบล็อกตามสาเหตุ คลิปผ่านได้เมื่อมีผลตรวจทางเทคนิคและบันทึกผู้ตรวจผูกกับ hash เมื่อเปลี่ยนไฟล์ต้องตรวจเวอร์ชันใหม่ [FFprobe](https://ffmpeg.org/ffprobe.html) · [FFmpeg filters](https://ffmpeg.org/ffmpeg-filters.html)

<a id="prd-08"></a>

## PRD-08 — เผยแพร่และยืนยันผล Facebook

**งาน** ใช้ Meta API เดิมกับ Page ที่ได้รับอนุญาตเมื่อเส้นทางนั้นรองรับตัวควบคุมการเปิดเผยที่จำเป็นครบ ถ้า API ใช้ป้ายที่ต้องการไม่ได้หรือผู้ใช้ต้องปักสินค้า ให้ Studio เตรียมไฟล์และแคปชัน แล้วให้ผู้ใช้เปิด Facebook เพื่อทำฉบับร่าง เปิดป้าย และเผยแพร่เองเมื่อได้รับอนุญาต เก็บ Reel ID/URL แล้วตรวจสถานะโพสต์ คอมเมนต์ Affiliate และแท็กสินค้าแยกกันตามที่ร้องขอ ใช้ read-back ของ Meta เมื่อรองรับ และให้ผู้ใช้ส่งหลักฐานการตรวจแท็กจากหน้าจอเมื่อ API อ่านไม่ได้

**ปิดเมื่อ** ทดสอบด้วย mock ว่าคำขอที่ขาดการอนุมัติหรือป้ายที่ต้องใช้ไม่ออกเป็นโพสต์ และสถานะคลุมเครือถูกตรวจกลับก่อนส่งซ้ำ เมื่อได้รับอนุญาตสำหรับ live test ให้ยืนยัน Page, Reel ID, คลิป, แคปชัน, ป้ายที่เกี่ยวข้อง และคอมเมนต์หรือลิงก์ตามเส้นทางนั้น แท็ก Shopee เปิดใช้เป็นความสามารถที่ยืนยันแล้วต่อเมื่อทดสอบแท็กและปลายทางสำเร็จ [Meta Page Video Reels API](https://developers.facebook.com/docs/graph-api/reference/page/video_reels) · [กฎการเปิดเผยของโครงการ](../../AGENTS.md#ai-content-and-disclosure)

<a id="prd-09"></a>

## PRD-09 — ส่งต่อ TikTok และพิสูจน์ Inbox Upload

**งาน** คงทางเลือกดาวน์โหลด MP4 และคัดลอกแคปชันให้ผู้ใช้เปิด TikTok Studio และอัปโหลดเอง เมื่อ Sandbox ตั้งค่า URL ที่จำเป็นและ target user อนุญาต `video.upload` แล้ว ให้ทดลอง Upload API แบบ `FILE_UPLOAD` และเก็บ `publish_id` เพื่อตรวจ `SEND_TO_USER_INBOX` ผู้ใช้ทำฉบับร่างต่อใน TikTok เปิดป้าย AI และการเปิดเผยเชิงพาณิชย์ตามที่ใช้ และเผยแพร่เมื่ออนุญาต

**ปิดเมื่อ** เส้นทาง manual เตรียมไฟล์และแคปชันจากเวอร์ชันที่ตรวจแล้วครบ และการทดสอบ API ยืนยันทั้งสถานะ Inbox และการแจ้งเตือนในบัญชีเป้าหมาย สถานะใน Studio แยก Inbox ออกจากเผยแพร่สำเร็จ การเปิดใช้ API ใน production ต้องผ่านการอนุมัติแอปและสิทธิ์บัญชี ส่วนการยืนยันโพสต์จริงและสิ่งที่แนบยังต้องใช้หลักฐานแยกตามปลายทาง [TikTok Sandbox](https://developers.tiktok.com/docs/en/add-a-sandbox) · [Upload API](https://developers.tiktok.com/docs/en/content-posting-api-reference-upload-video) · [Post Status](https://developers.tiktok.com/docs/en/content-posting-api-reference-get-video-status)

<a id="prd-10"></a>

## PRD-10 — นำเข้ารายงาน Affiliate และเทียบยอด

**งาน** ให้ผู้ใช้ส่งออก Click Report และ Order Report จาก Shopee แล้วนำเข้า Studio ด้วย parser เดิม เก็บเวลารายงานและผลนำเข้า ทดลอง `conversionReport` และ `validatedReport` หลังได้สิทธิ์เพื่อเติมข้อมูลคำสั่งซื้อและค่าคอม ใช้ Click Report CSV ต่อจนกว่าจะยืนยันแหล่งข้อมูลคลิกที่ให้ผลเทียบกันได้

**ปิดเมื่อ** CSV ชุดเดียวกันให้ยอดคลิก ออเดอร์ไม่ซ้ำ และค่าคอมตรงกับ baseline แยกตามช่องทางและ Sub ID ในเวลาไทย นำเข้าซ้ำแล้วไม่ซ้ำยอด การเปิด API ต้องเทียบกับ CSV ของบัญชีและช่วงเดียวกันโดยอธิบายผลต่างจากการปรับสถานะหรือช่วงเวลาได้ [Shopee Affiliate Open API ที่ตรวจไว้ในโครงการ](../api/SHOPEE_AFFILIATE_ENDPOINTS.md)

## เกณฑ์ยืนยันก่อนเปิด production

รัน pipeline จาก workspace ใหม่บน deployment ที่ไม่มี Codex หรือ browser extension ใช้ข้อมูลสินค้าที่ได้รับอนุญาตอย่างน้อยหนึ่งรายการที่มีตัวเลือกสินค้า เก็บหลักฐานรายการและ Sub ID, แผงที่อนุมัติ, คลิปและเสียงรายช็อต, ผลตรวจ MP4, ฉบับร่างหรือโพสต์ตามขอบเขตที่อนุญาต และยอดในรายงาน เปรียบเทียบผลกับ baseline ของ SKU และช่องทางเดียวกัน ใช้ fixture สำหรับการทดสอบอัตโนมัติ และเก็บหลักฐานจากแต่ละ provider ก่อนเปิดใช้ความสามารถ live ของ provider นั้น
