"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { channelLabels } from "./affiliate-links";
import AffiliateLinkSetup, { type AffiliateLink, type CatalogProduct } from "./affiliate-link-setup";
import type { StudioRequest } from "./meta-publishing";
import { ProductMetrics, type DiscoverySelection } from "./product-discovery";
import Storyboards, { type Board } from "./storyboards";

const stages = ["พรอมป์ Storyboard", "อนุมัติภาพนิ่ง", "สร้างวิดีโอ", "ตรวจพรีวิว", "เตรียมเผยแพร่"];
const presenter = "https://flow.google.com/project/81d65799-15e1-4834-b708-4e17857d09ff/character/0e74b82c-79cb-43da-badb-dc5e6d520d35";
const destinations: Record<string, { name: string; url: string; disclosure: string }> = {
  facebook: { name: "Facebook", url: "https://www.facebook.com/", disclosure: "ใช้เครื่องมือเปิดเผย AI ของ Meta และตรวจการเปิดเผยเชิงพาณิชย์ก่อนเผยแพร่" },
  instagram: { name: "Instagram", url: "https://www.instagram.com/", disclosure: "ใช้เครื่องมือเปิดเผย AI ของ Meta และตรวจการเปิดเผยเชิงพาณิชย์ก่อนเผยแพร่" },
  tiktok: { name: "TikTok Studio", url: "https://www.tiktok.com/tiktokstudio/upload", disclosure: "เปิด AI-generated content เมื่อใช้ภาพหรือเสียง AI ที่สมจริง และเลือก Branded content ในการเปิดเผยเชิงพาณิชย์สำหรับ Affiliate" },
  youtube: { name: "YouTube Studio", url: "https://studio.youtube.com/", disclosure: "ตรวจตัวเลือกเปิดเผยเนื้อหาที่ดัดแปลงหรือสร้างด้วย AI และการโปรโมตแบบชำระเงินในหน้าร่าง" },
};

type Props = {
  selection: DiscoverySelection;
  scope: string;
  token: string;
  products: CatalogProduct[];
  request: StudioRequest;
  onSave: (item: CatalogProduct) => void;
  onContinue: (item: CatalogProduct) => void;
  onClose: () => void;
  videoEditor: ReactNode;
  videoPicker: ReactNode;
  video: string;
  renderId: string;
  notice: ReactNode;
  initialAffiliate?: { item: CatalogProduct; link: AffiliateLink };
};

export default function ProductWorkflow({
  selection, scope, token, products, request, onSave, onContinue, onClose,
  videoEditor, videoPicker, video, renderId, notice, initialAffiliate,
}: Props) {
  const dialog = useRef<HTMLDialogElement>(null);
  const body = useRef<HTMLDivElement>(null);
  const [affiliateBusy, setAffiliateBusy] = useState(false);
  const [affiliate, setAffiliate] = useState(initialAffiliate);
  const [step, setStep] = useState(initialAffiliate ? 1 : 0);
  const [board, setBoard] = useState<Board>();
  const [file, setFile] = useState<File>();
  const [local, setLocal] = useState<{ file: File; url: string }>();
  const [fileError, setFileError] = useState("");
  const [verticalVideo, setVerticalVideo] = useState("");
  const [reviewed, setReviewed] = useState("");
  const [savedCaption, setSavedCaption] = useState("");
  const [aiDetails, setAiDetails] = useState("");
  const [simulating, setSimulating] = useState(false);
  const [simulation, setSimulation] = useState<{ key: string; message: string; error?: boolean }>();
  const [copyMessage, setCopyMessage] = useState("");
  const currentUrl = file ? (file === local?.file ? local.url : "") : video;
  const artifact = file?.name ?? (renderId ? `reel-${renderId}.mp4` : "");
  const approval = board?.review_version && board.approved_scenes.length
    ? `${board.id}/${board.review_version}/${board.approved_scenes.join(",")}` : "";
  const reviewKey = approval && currentUrl && currentUrl === verticalVideo ? `${approval}/${currentUrl}` : "";
  const reviewComplete = !!reviewKey && reviewed === reviewKey;
  const link = affiliate?.link;
  const destination = link && destinations[link.channel];
  const caption = [
    savedCaption.trim() || affiliate?.item.name,
    board?.variant && `รุ่น/ตัวเลือก · ${board.variant}`,
    aiDetails.trim() && `ใช้ AI สำหรับ${aiDetails.trim()}`,
    "หากซื้อผ่านลิงก์นี้ ผู้จัดทำอาจได้รับค่าคอมมิชชัน Affiliate",
    link?.affiliate_url,
  ].filter(Boolean).join("\n\n");

  const simulationKey = JSON.stringify([reviewKey, caption]);

  useEffect(() => {
    const element = dialog.current;
    const previousFocus = document.activeElement;
    const previousUrl = window.location.href;
    // Keep the market visible while using the existing Safari bridge's Affiliate route.
    window.history.replaceState(window.history.state, "", "#affiliate-links");
    element?.showModal();
    return () => {
      element?.close();
      if (window.location.hash === "#affiliate-links") {
        window.history.replaceState(window.history.state, "", previousUrl);
      }
      if (previousFocus instanceof HTMLElement && previousFocus.isConnected) previousFocus.focus();
    };
  }, []);
  useEffect(() => { body.current?.scrollTo(0, 0); }, [step]);
  useEffect(() => {
    if (!file) return;
    const url = URL.createObjectURL(file);
    setLocal({ file, url });
    return () => URL.revokeObjectURL(url);
  }, [file]);

  function accessible(stage: number) {
    if (stage === 1) return !!affiliate;
    if (stage === 2) return !!board;
    if (stage === 3 || stage === 4) return !!approval;
    return reviewComplete;
  }

  async function copy(value: string, label: string) {
    try {
      await navigator.clipboard.writeText(value);
      setCopyMessage(`คัดลอก${label}แล้ว`);
    } catch {
      setCopyMessage(`เลือกและคัดลอก${label}จากช่องที่แสดง`);
    }
  }

  async function simulatePublication() {
    if (!reviewComplete || file || link?.channel !== "facebook" || !renderId || simulating) return;
    setSimulating(true);
    try {
      const result = await request<{ video_status: string }>(scope + "/publishing/simulations", token, {
        method: "POST",
        body: JSON.stringify({ render_id: renderId, caption, include_comment: false }),
      });
      setSimulation({ key: simulationKey, message: result.video_status === "published"
        ? "จำลองการเผยแพร่สำเร็จ" : `ผลจำลอง · ${result.video_status}` });
    } catch (error) {
      setSimulation({ key: simulationKey, message: error instanceof Error ? error.message : "จำลองการเผยแพร่ไม่สำเร็จ", error: true });
    } finally {
      setSimulating(false);
    }
  }

  const { selection: selected, offer, trend } = selection;
  const title = step === 0 ? "ตรวจสอบลิงก์ Affiliate" : "เตรียม Storyboard และผลิตวิดีโอ";
  const visibleStep = step > 2 && !accessible(step) ? (approval ? 4 : board ? 2 : 1) : step;
  return <dialog className={`workflow-dialog ${step > 0 ? "workflow-wide" : ""}`} ref={dialog}
    aria-labelledby="workflow-heading" onCancel={(event) => { event.preventDefault(); if (!affiliateBusy) onClose(); }}>
    <header className="workflow-header">
      <div><p className="muted">{step === 0 ? "เลือกสินค้าและช่องทาง" : "ขั้นตอนผลิตคอนเทนต์"}</p>
        <h2 id="workflow-heading">{title}</h2></div>
      <button autoFocus type="button" className="workflow-close" disabled={affiliateBusy} onClick={onClose} aria-label="ปิดหน้าต่าง">×</button>
    </header>
    <div className="workflow-body" ref={body}>
      <div className="workflow-product">
        {offer?.image_url && <img src={offer.image_url} alt={selected.name} width={112} height={84}
          referrerPolicy="no-referrer" onError={(event) => { event.currentTarget.hidden = true; }} />}
        <div>
          <p className="muted">{trend ? "Google Trends" : "Shopee"}{link && ` · ${channelLabels[link.channel] ?? link.channel}`}</p>
          <h3>{affiliate?.item.name ?? selected.name}</h3>
          {board && <p>ตัวเลือกสินค้า · {board.variant}</p>}
          {affiliate && <a className="workflow-listing" href={affiliate.item.source_url} target="_blank" rel="noreferrer">ตรวจรายการสินค้าและตัวเลือกใน Shopee</a>}
          <ProductMetrics offer={offer} trend={trend} />
        </div>
      </div>

      <div hidden={step !== 0}>
        <AffiliateLinkSetup inDialog autoStart={!initialAffiliate && step === 0} trend={trend?.title ?? ""} offer={selected}
          scope={scope} token={token} products={products} request={request}
          onBusy={setAffiliateBusy} onSave={onSave} onContinue={(item, nextLink) => {
            if (affiliate?.item.id !== item.id || affiliate.link.channel !== nextLink.channel ||
                affiliate.link.affiliate_url !== nextLink.affiliate_url || affiliate.link.sub_id !== nextLink.sub_id) {
              setBoard(undefined);
              setFile(undefined);
              setReviewed("");
              setSavedCaption("");
              setAiDetails("");
            }
            onContinue(item);
            setAffiliate({ item, link: nextLink });
            setStep(1);
          }} />
        <button type="button" className="secondary workflow-back" disabled={affiliateBusy} onClick={onClose}>กลับไปเลือกสินค้าอื่น</button>
      </div>

      {affiliate && link && <div hidden={step === 0} className="workflow-production">
        <div className="workflow-link-bar">
          <strong>ลิงก์ Affiliate · {channelLabels[link.channel] ?? link.channel}</strong>
          <span>{link.affiliate_url}</span>{link.sub_id && <small>Sub ID · {link.sub_id}</small>}
        </div>
        <nav className="workflow-steps" aria-label="ขั้นตอนผลิตคอนเทนต์">
          {stages.map((stage, index) => <button key={stage} type="button" disabled={!accessible(index + 1)}
            aria-current={visibleStep === index + 1 ? "step" : undefined} onClick={() => setStep(index + 1)}>
            <small>ขั้นที่ {index + 1}</small>{stage}
          </button>)}
        </nav>
        {notice}
        <Storyboards key={`${affiliate.item.id}/${link.channel}/${link.affiliate_url}/${link.sub_id}`}
          scope={scope} token={token} request={request}
          source={{ kind: "catalog", id: affiliate.item.id, name: affiliate.item.name }}
          workflow={{ step: visibleStep, link, onBoard: setBoard }} onCloseDraft={() => setStep(0)} />

        <div hidden={visibleStep !== 3} className="workflow-stage">
          {approval && board && <>
            <section className="panel">
              <h3>สร้างเฉพาะฉากที่อนุมัติ</h3>
              <dl className="workflow-specs">
                <div><dt>สัดส่วนและโมเดล</dt><dd>9:16 · Veo 3.1 Lite</dd></div>
                <div><dt>ฉากที่อนุมัติ</dt><dd>{board.approved_scenes.map((shot) => String(shot).padStart(2, "0")).join(", ")}</dd></div>
                <div><dt>ความยาวตามแผน</dt><dd>{board.approved_scenes.reduce((sum, shot) => sum + board.scenes[shot - 1].seconds, 0)} วิ</dd></div>
                <div><dt>เสียง</dt><dd>Callirrhoe</dd></div>
              </dl>
              <p>ใน Flow ให้ตรวจงานเดิมและเครดิตก่อนส่ง เลือกพิธีกรที่บันทึกไว้และเสียง Callirrhoe แล้วตรวจ 9:16 และ Veo 3.1 Lite ก่อนส่งคำสั่งเฉพาะหมายเลขฉากด้านบน ดาวน์โหลดคลิปโดยคงหมายเลขฉากไว้</p>
              <a href={presenter} target="_blank" rel="noreferrer">เปิดพิธีกรคัดของเข้าบ้านใน Flow</a>
            </section>
            {videoEditor}
          </>}
        </div>

        <div hidden={visibleStep !== 4} className="workflow-stage">
          <section className="panel">
            <h3>ตรวจคลิปและเสียงก่อนส่งต่อ</h3>
            <div className="columns">
              <div className="preview">
                {currentUrl ? <video key={currentUrl} controls playsInline preload="metadata" src={currentUrl}
                  aria-label="ตัวอย่างวิดีโอก่อนเผยแพร่" onLoadedMetadata={(event) => {
                    const { videoWidth, videoHeight } = event.currentTarget;
                    setVerticalVideo(videoWidth * 16 === videoHeight * 9 ? currentUrl : "");
                    setFileError(videoWidth * 16 === videoHeight * 9 ? "" : "ใช้คลิปแนวตั้ง 9:16");
                  }} onError={() => { setVerticalVideo(""); setFileError("เปิดวิดีโอไม่ได้"); }} />
                  : <p className="muted">เลือก MP4 เพื่อเริ่มตรวจ</p>}
              </div>
              <div className="column">
                {videoPicker}
                <label>หรือใช้ไฟล์ MP4 ที่ตัดต่อเสร็จแล้ว
                  <input type="file" accept=".mp4,video/mp4" onChange={(event) => {
                    const next = event.currentTarget.files?.[0];
                    event.currentTarget.value = "";
                    if (!next) return;
                    if (!next.size || !next.name.toLowerCase().endsWith(".mp4")) {
                      setFileError("เลือกไฟล์ MP4 ที่มีข้อมูล");
                      return;
                    }
                    setFileError("");
                    setFile(next);
                  }} />
                </label>
                {file && <button type="button" className="text-button" onClick={() => {
                  setFile(undefined);
                  setFileError("");
                }}>นำไฟล์ {file.name} ออก</button>}
                {fileError && <p role="alert" className="notice error">{fileError}</p>}
                {currentUrl && <a href={currentUrl} download={artifact}>ดาวน์โหลด {artifact}</a>}
                <p>ดูและฟังจนจบ ตรวจสินค้า รุ่น ชื่อแบรนด์ ตัวเลข ซับ และตำแหน่งข้อความบนมือถือ</p>
                <label className="checkbox"><input type="checkbox" checked={reviewComplete} disabled={!reviewKey}
                  onChange={(event) => setReviewed(event.target.checked ? reviewKey : "")} /> ตรวจ MP4 เวอร์ชันนี้ครบแล้ว</label>
              </div>
            </div>
          </section>
        </div>

        <div hidden={visibleStep !== 5} className="workflow-stage">
          {reviewComplete && <section className="panel">
            <h3>เตรียมเผยแพร่ · {channelLabels[link.channel] ?? link.channel}</h3>
            <p>ไฟล์ที่ตรวจแล้ว · {artifact}</p>
            <label>แคปชัน<textarea rows={3} value={savedCaption} onChange={(event) => {
              setSavedCaption(event.target.value);
              setCopyMessage("");
            }} placeholder={affiliate.item.name} /></label>
            <label>ส่วนที่สร้างหรือปรับด้วย AI<input value={aiDetails} onChange={(event) => {
              setAiDetails(event.target.value);
              setCopyMessage("");
            }} placeholder="เช่น ภาพจาก Google Flow และเสียงบรรยาย" /></label>
            <label>แคปชันพร้อมลิงก์และข้อความเปิดเผยค่าคอมมิชชัน<textarea readOnly rows={5} value={caption} /></label>
            <div className="storyboard-actions">
              <button type="button" className="secondary" onClick={() => void copy(caption, "แคปชัน")}>คัดลอกแคปชัน</button>
              <a href={currentUrl} download={artifact}>ดาวน์โหลด MP4 ที่ตรวจแล้ว</a>
            </div>
            {copyMessage && <p role="status">{copyMessage}</p>}
            {!file && link.channel === "facebook" && renderId && <>
              <button type="button" className="secondary" disabled={simulating || caption.length > 500}
                onClick={() => void simulatePublication()}>{simulating ? "กำลังจำลอง…" : "จำลองการเผยแพร่"}</button>
              {caption.length > 500 && <p>ใช้แคปชันไม่เกิน 500 ตัวอักษรสำหรับการจำลอง</p>}
              {simulation?.key === simulationKey && <p role={simulation.error ? "alert" : "status"}>{simulation.message}</p>}
            </>}
            <p>ตรวจบัญชีปลายทาง ตัวเลือกสินค้า และลิงก์อีกครั้ง เก็บเป็นร่างจนกว่าจะยืนยันการเผยแพร่</p>
            {destination && <><p>{destination.disclosure}</p>
              <a href={destination.url} target="_blank" rel="noreferrer">ไปยัง {destination.name} เพื่อเตรียมโพสต์</a></>}
          </section>}
        </div>
      </div>}
    </div>
    {step > 0 && <footer className="workflow-footer">
      <button type="button" className="secondary" onClick={() => setStep(visibleStep - 1)}>
        {visibleStep === 1 ? "กลับไปดูลิงก์ Affiliate" : "ขั้นก่อนหน้า"}
      </button>
      {visibleStep < stages.length && <button type="button" className="primary"
        disabled={!accessible(visibleStep + 1)} onClick={() => setStep(visibleStep + 1)}>ถัดไป · {stages[visibleStep]}</button>}
      {visibleStep === stages.length && <button type="button" className="secondary" onClick={onClose}>กลับไปตลาดสินค้า</button>}
    </footer>}
  </dialog>;
}
