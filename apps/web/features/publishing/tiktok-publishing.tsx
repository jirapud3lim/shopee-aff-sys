"use client";

import { useEffect, useState } from "react";

const affiliateDisclosure = "หากซื้อผ่านลิงก์หรือสินค้าที่แนบไว้ ผู้จัดทำอาจได้รับค่าคอมมิชชัน";

type Props = {
  renderId: string;
  videoUrl: string;
  productName: string;
};

export default function TikTokPublishing({ renderId, videoUrl, productName }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [localPreview, setLocalPreview] = useState<{ file: File; url: string } | null>(null);
  const [caption, setCaption] = useState(productName);
  const [aiElements, setAiElements] = useState("");
  const [affiliate, setAffiliate] = useState(false);
  const [fileError, setFileError] = useState("");
  const [copyStatus, setCopyStatus] = useState("");
  const [showCopyText, setShowCopyText] = useState(false);
  const clipUrl = file ? (localPreview?.file === file ? localPreview.url : "") : videoUrl;
  const aiDisclosure = aiElements.trim() ? `ใช้ AI สำหรับ${aiElements.trim()}` : "";
  const finalCaption = [caption.trim(), aiDisclosure, affiliate ? affiliateDisclosure : ""]
    .filter(Boolean).join("\n\n");

  useEffect(() => {
    if (!file) return;
    const url = URL.createObjectURL(file);
    setLocalPreview({ file, url });
    return () => URL.revokeObjectURL(url);
  }, [file]);

  function selectFile(next: File | null) {
    setFile(next);
    setLocalPreview(null);
    setCaption(next ? "" : productName);
    setAiElements("");
    setAffiliate(false);
    setCopyStatus("");
    setShowCopyText(false);
    setFileError("");
  }

  async function copyCaption() {
    try {
      await navigator.clipboard.writeText(finalCaption);
      setCopyStatus("คัดลอกแคปชันแล้ว");
    } catch {
      setShowCopyText(true);
      setCopyStatus("เลือกและคัดลอกแคปชันจากช่องด้านล่าง");
    }
  }

  return (
    <section className="panel" id="tiktok-publishing">
      <div className="panel-head"><h2 tabIndex={-1}>เตรียมคลิปสำหรับ TikTok</h2></div>
      <div className="columns">
        <div className="column">
          {!file && (videoUrl ? <p className="muted">คลิป Studio · {productName} · {renderId.slice(0, 8)}</p>
            : <p className="muted"><a href="#video">เลือก Reel ที่เรนเดอร์แล้ว</a> หรือเลือกไฟล์ MP4 ด้านล่าง</p>)}
          <label>ใช้ไฟล์ MP4 ที่ตัดต่อเสร็จแล้ว
            <input type="file" accept=".mp4,video/mp4" onChange={(event) => {
              const selected = event.currentTarget.files?.[0];
              event.currentTarget.value = "";
              if (!selected) return;
              if (!selected.name.toLowerCase().endsWith(".mp4") || !selected.size) {
                setFileError("เลือกไฟล์ MP4 ที่มีข้อมูล");
                return;
              }
              selectFile(selected);
            }} />
          </label>
          {fileError && <p className="notice error" role="alert">{fileError}</p>}
          {file && <>
            <p>{file.name}</p>
            <button type="button" className="text-button" onClick={() => selectFile(null)}>นำไฟล์ MP4 ออก</button>
          </>}
          {clipUrl && <div className="preview">
            <video key={clipUrl} src={clipUrl} controls playsInline preload="metadata" aria-label="ตัวอย่างคลิปสำหรับ TikTok" />
          </div>}
          {clipUrl && !file && <a href={clipUrl} download={`reel-${renderId}.mp4`}>ดาวน์โหลด MP4 จาก Studio</a>}
        </div>
        <div className="column">
          <label>แคปชัน TikTok<textarea rows={3} value={caption} onChange={(event) => {
            setCaption(event.target.value);
            setCopyStatus("");
          }} /></label>
          <label>ส่วนที่สร้างหรือปรับด้วย AI (ถ้ามี)
            <input value={aiElements} placeholder="เช่น ภาพจาก Google Flow และเสียงบรรยาย"
              onChange={(event) => {
                setAiElements(event.target.value);
                setCopyStatus("");
              }} />
          </label>
          <label className="checkbox"><input type="checkbox" checked={affiliate} onChange={(event) => {
            setAffiliate(event.target.checked);
            setCopyStatus("");
          }} /> เพิ่มข้อความแจ้งค่าคอมมิชชัน Affiliate</label>
          <button type="button" className="secondary" disabled={!finalCaption} onClick={() => void copyCaption()}>คัดลอกแคปชัน TikTok</button>
          {copyStatus && <p className="muted" role="status">{copyStatus}</p>}
          {showCopyText && <label>แคปชันพร้อมคัดลอก<textarea rows={4} value={finalCaption} readOnly /></label>}
          {clipUrl && <a href="https://www.tiktok.com/tiktokstudio/upload" target="_blank" rel="noreferrer">เปิดหน้าอัปโหลด TikTok Studio</a>}
          <p className="muted">ตรวจคลิปและเสียงให้จบ แล้วอัปโหลด MP4 และวางแคปชันในบัญชี TikTok ที่ต้องการ ตรวจตัวเลือกและชื่อรุ่นสินค้าก่อนโพสต์</p>
          <p className="muted">เปิด AI-generated content สำหรับภาพหรือเสียง AI ที่เหมือนจริง เปิดการเปิดเผยเนื้อหาเชิงพาณิชย์เมื่อโปรโมตสินค้า และเลือก Branded content สำหรับ Affiliate ของแบรนด์อื่น หากหน้าเว็บขาดตัวเลือกที่ต้องใช้ ให้ทำต่อในแอป TikTok ก่อนเผยแพร่</p>
        </div>
      </div>
    </section>
  );
}
