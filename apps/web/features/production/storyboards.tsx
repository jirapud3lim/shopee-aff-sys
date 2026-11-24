"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import type { AffiliateLink } from "@/features/affiliate/affiliate-link-setup";
import { safariCaptureEnabled } from "@/lib/safari-capture";

export type StoryboardSource = { kind: "offer" | "catalog"; id: string; name: string };
type Scene = { seconds: number; action: string; dialogue: string };
type Asset = "product" | "presenter" | "board";
export type Board = {
  id: string;
  product_name: string;
  source: StoryboardSource["kind"];
  source_id: string;
  affiliate: AffiliateLink | null;
  review_version: string | null;
  approved_scenes: number[];
  variant: string;
  verified_details: string;
  creative_prompt?: string;
  scenes: Scene[];
  files: Partial<Record<Asset, string>>;
};
type Props = {
  scope: string;
  token: string;
  source: StoryboardSource | null;
  onCloseDraft: () => void;
  workflow?: { step: number; link: AffiliateLink; onBoard: (board: Board | undefined) => void };
  request: <T>(path: string, token: string, init?: RequestInit) => Promise<T>;
};

const types = "image/jpeg,image/png,image/webp";
const flowHome = "https://flow.google.com/";
const flowProject = /^\/project\/[a-f0-9-]{36}(?:\/collection\/[a-f0-9-]{36})?\/?$/;
const flowImage = /^https:\/\/flow\.google\.com\/project\/[a-f0-9-]{36}\/edit\/[a-f0-9-]{36}$/;
type FlowResponse = {
  ready?: boolean;
  id?: string;
  status?: string;
  error?: string;
  result?: { data: string; url: string };
};

function imageData(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === "string") resolve(reader.result);
      else reject(new Error("เตรียมไฟล์ภาพอ้างอิงไม่สำเร็จ"));
    };
    reader.onerror = () => reject(new Error("เตรียมไฟล์ภาพอ้างอิงไม่สำเร็จ"));
    reader.readAsDataURL(blob);
  });
}
const starterScenes: Scene[] = [
  { seconds: 4, action: "เปิดด้วยพิธีกรที่เห็นหน้าชัดและมีสินค้าจริงอยู่ในเฟรม", dialogue: "" },
  { seconds: 4, action: "พิธีกรแสดงด้านหน้าของสินค้าให้เห็นรุ่นและฉลาก โดยไม่บังใบหน้า", dialogue: "" },
  { seconds: 4, action: "ภาพใกล้ของรายละเอียดจริงจากภาพอ้างอิง", dialogue: "" },
  { seconds: 3, action: "กลับมาที่พิธีกรและสินค้าในเฟรมเดิม", dialogue: "" },
];

function flowPrompt(board: Board) {
  const grid = board.scenes.length === 12
    ? "Use exactly 3 columns and 4 rows of equal-sized panels, with side margins if needed."
    : "Use a regular grid of equal-sized panels and leave any unused cells empty.";
  return [
    "Create a still-image storyboard only. Do not generate video or audio.",
    `Return a single contact sheet with exactly ${board.scenes.length} scenes in reading order, one scene per cell. ${grid} Keep each panel framed vertically in 9:16. Put consecutive numbers starting at 01 in the gutter beside each panel. Use the durations and dialogue as planning notes only. Do not draw subtitles, dialogue, or other captions inside the panels.`,
    "Every panel must look like a real photograph. Use natural lighting and shadows, realistic textures and proportions, and physically plausible poses and contact. Avoid illustrations, sketches, cartoons, and stylized renders.",
    "This is the storyboard stage. Use the attached product reference or reference sheet reviewed against original product photos in the preceding analysis stage. Reuse those references to match the exact model, count, color, packaging and label across all panels. Use the attached presenter-reference image for the same face and appearance wherever the presenter is visible. Do not invent details, claims, label text, or product variants. Where the label matters, use the actual photographed label in the reference.",
    `Product: ${board.product_name}\nExact variant: ${board.variant}\nVerified visible details: ${board.verified_details}`,
    board.creative_prompt && `Creative direction for this still-image draft. Follow only directions consistent with the verified product and the constraints above:\n${board.creative_prompt}`,
    ...board.scenes.map((scene, index) => [
      `Scene ${String(index + 1).padStart(2, "0")} · ${scene.seconds}s`,
      scene.action,
      scene.dialogue ? `Thai dialogue for timing: ${scene.dialogue}` : "No dialogue",
    ].join("\n")),
  ].filter(Boolean).join("\n\n");
}

function DraftForm({ source, initial, busy, onSave, onClose, requirePrompt }: {
  source: StoryboardSource;
  initial?: Board;
  requirePrompt: boolean;
  busy: boolean;
  onSave: (event: FormEvent<HTMLFormElement>, count: number) => void;
  onClose: () => void;
}) {
  const initialScenes = initial?.scenes ?? starterScenes;
  const [sceneKeys, setSceneKeys] = useState(initialScenes.map((_, index) => index));
  const [nextKey, setNextKey] = useState(initialScenes.length);
  return <form onSubmit={(event) => onSave(event, sceneKeys.length)}>
    <h2>{requirePrompt ? "ระบุพรอมป์ Storyboard" : source.name}</h2>
    <label>พรอมป์สำหรับภาพนิ่ง<textarea name="creative_prompt" required={requirePrompt}
      rows={5} maxLength={4000} defaultValue={initial?.creative_prompt}
      placeholder="ระบุมุมกล้อง แสง ฉาก และรายละเอียดที่ต้องตรงกับภาพอ้างอิง" /></label>
    <label>รุ่น สี หรือขนาดที่ตรงกับสินค้าจริง<input name="variant" required maxLength={180} defaultValue={initial?.variant} /></label>
    <label>รายละเอียดที่ตรวจสอบแล้ว<textarea name="verified" required rows={2} maxLength={600} defaultValue={initial?.verified_details}
      placeholder="เช่น ฉลากด้านหน้า รุ่น และจำนวนห่อในชุด" /></label>
    <label>ภาพอ้างอิงสินค้าที่ตรวจเทียบกับรูปจริงแล้ว<input name="product" required={!initial} type="file" accept={types} /></label>
    <label>รูปอ้างอิงหน้าพิธีกร<input name="presenter" required={!initial} type="file" accept={types} /></label>
    {initial && <p className="muted">เว้นช่องรูปเพื่อใช้ภาพอ้างอิงเดิม หากเปลี่ยนตัวเลือกสินค้า ให้แนบภาพสินค้าที่ตรวจแล้วใหม่</p>}
    {sceneKeys.map((key, index) => <fieldset key={key} className="storyboard-scene">
      <legend>ฉาก {String(index + 1).padStart(2, "0")}</legend>
      <label>ระยะเวลา (วินาที)<input name={`seconds-${index}`} type="number" required min={1} max={15}
        defaultValue={initialScenes[key]?.seconds ?? 3} /></label>
      <label>ภาพและการกระทำ<textarea name={`action-${index}`} required maxLength={500} rows={2}
        defaultValue={initialScenes[key]?.action ?? ""} /></label>
      <label>บทพูดไทย<textarea name={`dialogue-${index}`} maxLength={300} rows={2} defaultValue={initialScenes[key]?.dialogue} /></label>
      <button type="button" className="secondary" disabled={busy || sceneKeys.length === 1}
        onClick={() => setSceneKeys(sceneKeys.filter((item) => item !== key))}>ลบฉาก {index + 1}</button>
    </fieldset>)}
    <div className="storyboard-actions">
      <button type="button" className="secondary" disabled={busy || sceneKeys.length === 12} onClick={() => {
        setSceneKeys([...sceneKeys, nextKey]);
        setNextKey(nextKey + 1);
      }}>เพิ่มฉาก</button>
      <button className="primary" disabled={busy}>บันทึกแผนและรูปอ้างอิง</button>
      <button type="button" className="text-button" disabled={busy} onClick={onClose}>ปิดร่าง</button>
    </div>
  </form>;
}

export default function Storyboards({ scope, token, source, request, onCloseDraft, workflow }: Props) {
  const path = scope + "/storyboards";
  const [boards, setBoards] = useState<Board[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [preview, setPreview] = useState<{ id: string; version: string; url: string }>();
  const [showDraft, setShowDraft] = useState<boolean>();
  const [revisionOf, setRevisionOf] = useState<Board>();
  const [review, setReview] = useState<{ version: string; id: string; scenes: number[] }>();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [flowUrl, setFlowUrl] = useState("");
  const [flowReady, setFlowReady] = useState(false);
  const [flowRequest, setFlowRequest] = useState("");
  const [resultLink, setResultLink] = useState<{ id: string; url: string } | null>(null);
  const activeFlow = useRef<{ id: string; boardId: string } | null>(null);
  const matchingBoards = workflow ? boards.filter((item) => item.source === source?.kind &&
    item.source_id === source?.id && item.affiliate?.channel === workflow.link.channel &&
    item.affiliate.affiliate_url === workflow.link.affiliate_url && item.affiliate.sub_id === workflow.link.sub_id) : boards;
  const board = matchingBoards.find((item) => item.id === selectedId) ?? matchingBoards[0];
  const boardId = board?.id;
  const boardVersion = board?.review_version;
  const reviewImage = preview?.id === boardId && preview?.version === boardVersion ? preview : undefined;
  const reviewScenes = review?.version === boardVersion && review?.id === boardId
    ? review?.scenes ?? [] : board?.approved_scenes ?? [];
  const reportBoard = workflow?.onBoard;
  useEffect(() => { reportBoard?.(board); }, [board, reportBoard]);
  const prompt = board ? flowPrompt(board) : "";

  useEffect(() => {
    const controller = new AbortController();
    request<Board[]>(path, token, { signal: controller.signal }).then((items) => {
      if (controller.signal.aborted) return;
      setBoards(items);
      setSelectedId(items[0]?.id ?? "");
    }).catch((error: Error) => {
      if (!controller.signal.aborted) setMessage(error.message);
    }).finally(() => {
      if (!controller.signal.aborted) setBusy(false);
    });
    setBusy(true);
    return () => controller.abort();
  }, [path, request, token]);

  useEffect(() => {
    setFlowUrl(localStorage.getItem(`flow-project:${scope}`) ?? "");
    if (!safariCaptureEnabled) return;
    setFlowRequest(crypto.randomUUID());
    function receive(event: Event) {
      let response: FlowResponse;
      try {
        response = JSON.parse((event as CustomEvent<string>).detail);
      } catch {
        return;
      }
      if (response?.ready) setFlowReady(true);
      const job = activeFlow.current;
      if (!job || response?.id !== job.id) return;
      if (response.error) {
        setMessage(response.error);
        setBusy(false);
        activeFlow.current = null;
      } else if (response.result) {
        const output = response.result;
        activeFlow.current = null;
        void perform(async () => {
          if (!flowImage.test(output.url) || !/^data:image\/(jpeg|png|webp);base64,/.test(output.data)) {
            throw new Error("ไม่ได้รับไฟล์ภาพนิ่งที่รองรับจาก Flow");
          }
          const blob = await (await fetch(output.data)).blob();
          const upload = new FormData();
          upload.set("image", blob, "storyboard-from-flow");
          const updated = await request<Board>(`${path}/${job.boardId}/image`, token, { method: "PUT", body: upload });
          setBoards((current) => current.map((item) => item.id === updated.id ? updated : item));
          setResultLink({ id: updated.id, url: output.url });
          setMessage("รับภาพนิ่งจาก Flow แล้ว พร้อมตรวจใน Studio");
        });
      } else if (response.status) {
        setMessage(response.status);
      }
    }
    window.addEventListener("studio:flow-response", receive);
    window.dispatchEvent(new CustomEvent("studio:flow-probe"));
    const probe = window.setTimeout(() => window.dispatchEvent(new CustomEvent("studio:flow-probe")), 700);
    return () => {
      window.clearTimeout(probe);
      window.removeEventListener("studio:flow-response", receive);
    };
  }, [path, request, scope, token]);

  useEffect(() => {
    if (!boardId || !boardVersion) return;
    const controller = new AbortController();
    let url = "";
    fetch(`/api/v1${path}/${boardId}/files/board?version=${boardVersion}`, {
      headers: { Authorization: `Bearer ${token}` }, signal: controller.signal,
    }).then((result) => {
      if (!result.ok) throw new Error("เปิดภาพ Storyboard ไม่สำเร็จ");
      return result.blob();
    }).then((blob) => {
      if (controller.signal.aborted) return;
      url = URL.createObjectURL(blob);
      setPreview({ id: boardId, version: boardVersion, url });
    }).catch((error: Error) => {
      if (!controller.signal.aborted) setMessage(error.message);
    });
    return () => {
      controller.abort();
      if (url) URL.revokeObjectURL(url);
    };
  }, [boardId, boardVersion, path, token]);

  async function perform(action: () => Promise<void>) {
    setMessage("");
    setBusy(true);
    try {
      await action();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "ดำเนินการไม่สำเร็จ");
    } finally {
      setBusy(false);
    }
  }

  function saveDraft(event: FormEvent<HTMLFormElement>, count: number) {
    event.preventDefault();
    if (!source) return;
    const fields = new FormData(event.currentTarget);
    const creativePrompt = String(fields.get("creative_prompt") ?? "").trim();
    if (workflow && !creativePrompt) {
      setMessage("ระบุพรอมป์สำหรับภาพนิ่งก่อนบันทึก");
      return;
    }
    const scenes = Array.from({ length: count }, (_, index) => ({
      seconds: Number(fields.get(`seconds-${index}`)),
      action: fields.get(`action-${index}`),
      dialogue: fields.get(`dialogue-${index}`),
    }));
    const payload = new FormData();
    payload.set("plan", JSON.stringify({
      source: source.kind, source_id: source.id, variant: fields.get("variant"),
      verified_details: fields.get("verified"), creative_prompt: creativePrompt,
      scenes, affiliate: workflow?.link,
    }));
    void perform(async () => {
      for (const asset of ["product", "presenter"] as const) {
        const uploaded = fields.get(asset);
        if (uploaded instanceof File && uploaded.size) {
          payload.set(asset, uploaded);
        } else if (revisionOf && (asset === "presenter" || String(fields.get("variant")).trim() === revisionOf.variant)) {
          const response = await fetch(`/api/v1${path}/${revisionOf.id}/files/${asset}`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          if (!response.ok) throw new Error("เปิดรูปอ้างอิงจากแผนเดิมไม่สำเร็จ");
          payload.set(asset, await response.blob(), revisionOf.files[asset]);
        } else {
          throw new Error("แนบภาพอ้างอิงที่ตรวจแล้วสำหรับตัวเลือกสินค้านี้");
        }
      }
      const item = await request<Board>(path, token, { method: "POST", body: payload });
      setBoards((current) => [item, ...current]);
      setSelectedId(item.id);
      setRevisionOf(undefined);
      if (workflow) setShowDraft(false);
      else onCloseDraft();
    });
  }

  function importImage(event: FormEvent<HTMLFormElement>, item: Board) {
    event.preventDefault();
    const fields = new FormData(event.currentTarget);
    void perform(async () => {
      const updated = await request<Board>(`${path}/${item.id}/image`, token, { method: "PUT", body: fields });
      setBoards((current) => current.map((entry) => entry.id === updated.id ? updated : entry));
      setResultLink((current) => current?.id === item.id ? null : current);
    });
  }

  function openFlow() {
    let destination: URL;
    try {
      destination = new URL(flowUrl.trim() || flowHome);
      const valid = destination.origin === "https://flow.google.com" ||
        (destination.origin === "https://labs.google" && destination.pathname.includes("/tools/flow"));
      if (!valid || destination.username || destination.password) throw new Error();
    } catch {
      setMessage("ใช้ URL ของ Google Flow");
      return;
    }
    const copy = navigator.clipboard?.writeText(prompt);
    window.open(destination.href, "_blank", "noopener,noreferrer");
    const fallback = "เปิด Flow แล้ว คัดลอกพรอมป์จากช่องด้านล่าง";
    if (!copy) setMessage(fallback);
    else void copy.then(() => setMessage("คัดลอกพรอมป์แล้ว วางใน Flow และแนบรูปอ้างอิงทั้งสองไฟล์"))
      .catch(() => setMessage(fallback));
  }

  async function generateInFlow(item: Board) {
    if (!flowReady || !flowRequest || busy || activeFlow.current) return;
    let destination: URL;
    try {
      destination = new URL(flowUrl.trim());
      if (destination.origin !== "https://flow.google.com" || !flowProject.test(destination.pathname) ||
          destination.search || destination.hash || destination.username || destination.password) throw new Error();
    } catch {
      setMessage("ระบุ URL หน้าโปรเจกต์หรือคอลเลกชัน Flow ก่อนเริ่มสร้างอัตโนมัติ");
      return;
    }
    const id = flowRequest;
    setFlowRequest(crypto.randomUUID());
    activeFlow.current = { id, boardId: item.id };
    setBusy(true);
    setMessage("กำลังอ่านแผนและรูปอ้างอิงจาก Studio");
    try {
      const refs = await Promise.all(["product", "presenter"].map(async (asset) => {
        const response = await fetch(`/api/v1${path}/${item.id}/files/${asset}`, {
          headers: { Authorization: `Bearer ${token}` },
          signal: AbortSignal.timeout(15000),
        });
        if (!response.ok) throw new Error("อ่านรูปอ้างอิงจาก Studio ไม่สำเร็จ");
        return { data: await imageData(await response.blob()) };
      }));
      localStorage.setItem(`flow-project:${scope}`, destination.href);
      const promptWithId = prompt.replace("Create a still-image storyboard only.",
        `Create a still-image storyboard only. Studio job ${id.slice(0, 8)} is internal metadata, never print it in the image.`);
      window.dispatchEvent(new CustomEvent("studio:flow-package", {
        detail: JSON.stringify({ id, url: destination.href, prompt: promptWithId, refs }),
      }));
      window.setTimeout(() => {
        if (activeFlow.current?.id === id) {
          activeFlow.current = null;
          setBusy(false);
          setMessage("หมดเวลารอผล ตรวจแท็บ Flow ก่อนเริ่มงานใหม่");
        }
      }, 330000);
    } catch (error) {
      activeFlow.current = null;
      setBusy(false);
      setMessage(error instanceof Error ? error.message : "ส่งแผนและรูปอ้างอิงไม่สำเร็จ");
    }
  }

  function download(item: Board, asset: Asset) {
    void perform(async () => {
      const response = await fetch(`/api/v1${path}/${item.id}/files/${asset}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error("ดาวน์โหลดรูปอ้างอิงไม่สำเร็จ");
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = url;
      link.download = item.files[asset] ?? asset;
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    });
  }

  const approve = (item: Board) => void perform(async () => {
    const updated = await request<Board>(`${path}/${item.id}/approval`, token, {
      method: "PUT",
      body: JSON.stringify({ version: item.review_version, scenes: reviewScenes }),
    });
    setBoards((current) => current.map((entry) => entry.id === updated.id ? updated : entry));
    setReview(undefined);
    setMessage("บันทึกผลตรวจภาพนิ่งแล้ว");
  });

  return <div className="trend-explorer" id={workflow ? undefined : "storyboards"}>
    {!workflow && <header className="workspace-header"><h1 tabIndex={-1}>งานผลิต</h1></header>}
    {message && <p className="notice" role="status">{message}</p>}
    {source && <section className="panel" hidden={!!workflow && workflow.step !== 1}>
      {workflow && <p className="muted">วิเคราะห์รูปต้นฉบับของตัวเลือกสินค้า เตรียมภาพนิ่งอ้างอิงแยกจาก Storyboard แล้วตรวจเทียบกับรูปจริงก่อนแนบ</p>}
      {(!workflow || (showDraft ?? !board)) ? <DraftForm
        key={revisionOf?.id ?? `${source.kind}-${source.id}`} source={source} initial={revisionOf} requirePrompt={!!workflow}
        busy={busy} onSave={saveDraft} onClose={workflow && board ? () => {
          setRevisionOf(undefined);
          setShowDraft(false);
        } : onCloseDraft} /> : board && <>
          <h2>แผนบันทึกแล้ว · {board.scenes.length} ฉาก</h2>
          {board.creative_prompt && <p className="studio-saved-prompt">{board.creative_prompt}</p>}
          {board.scenes.map((scene, index) => <article key={index} className="workflow-scene-summary">
            <strong>ฉาก {String(index + 1).padStart(2, "0")} · {scene.seconds} วิ</strong>
            <p>{scene.action}</p>
            {scene.dialogue && <p className="muted">{scene.dialogue}</p>}
          </article>)}
          <button type="button" className="secondary" onClick={() => {
            setRevisionOf(board);
            setShowDraft(true);
          }}>แก้พรอมป์หรือบทและบันทึกเป็นแผนใหม่</button>
        </>}
    </section>}
    <section className="panel" hidden={!!workflow && workflow.step !== 2}>
      <h2>{workflow ? "ตรวจและอนุมัติภาพนิ่ง" : "Storyboard ที่บันทึกไว้"}</h2>
      {matchingBoards.length ? <label>เลือกแผน<select disabled={busy} value={board?.id ?? ""}
        onChange={(event) => setSelectedId(event.target.value)}>
        {matchingBoards.map((item) => <option key={item.id} value={item.id}>
          {item.product_name} · {item.variant} · {item.id.slice(0, 8)}
        </option>)}
      </select></label> : <p>{workflow ? "บันทึกแผนและภาพอ้างอิงของสินค้านี้ก่อน" : "เลือกสินค้าจากหน้าสินค้าขายดีและค่าคอมหรือ Google Trends เพื่อเริ่มแผน"}</p>}
      {board && <>
        <p>{board.scenes.length} ฉาก · {board.scenes.reduce((sum, scene) => sum + scene.seconds, 0)} วินาทีตามแผน</p>
        <div className="storyboard-actions">
          <button type="button" className="secondary" disabled={busy} onClick={() => download(board, "product")}>
            ดาวน์โหลดรูปสินค้าจริง
          </button>
          <button type="button" className="secondary" disabled={busy} onClick={() => download(board, "presenter")}>
            ดาวน์โหลดรูปพิธีกร
          </button>
        </div>
        <label>ลิงก์โปรเจกต์หรือคอลเลกชัน Flow<input type="url" value={flowUrl} placeholder={flowHome}
          onChange={(event) => setFlowUrl(event.target.value)} /></label>
        <div className="storyboard-actions">
          {safariCaptureEnabled && <button type="button" className="primary" id="safari-flow-storyboard" data-request-id={flowRequest}
            disabled={busy || !flowReady || !flowRequest} onClick={() => void generateInFlow(board)}>
            สร้าง Storyboard ภาพนิ่งใน Flow
          </button>}
          <button type="button" className="secondary" onClick={openFlow}>คัดลอกพรอมป์และเปิด Flow</button>
        </div>
        {safariCaptureEnabled && !flowReady && <p className="muted">เปิด Studio ใน Safari พร้อมส่วนขยาย Affiliate Studio Capture 0.3.0 เพื่อสร้างและรับภาพอัตโนมัติ</p>}
        {resultLink?.id === board.id && <a href={resultLink.url} target="_blank" rel="noreferrer">เปิดภาพต้นฉบับใน Flow</a>}
        <label>พรอมป์สำหรับสร้างภาพนิ่ง<textarea readOnly rows={8} value={prompt} /></label>
        <form key={board.id} onSubmit={(event) => importImage(event, board)}>
          <label>ภาพ Storyboard จาก Flow<input name="image" type="file" accept={types} required /></label>
          <button className="secondary" disabled={busy}>{boardVersion ? "แทนที่ภาพสำหรับตรวจ" : "นำเข้าภาพเพื่อรอตรวจ"}</button>
        </form>
        {reviewImage && <>
          <p>ตรวจความสมจริง ใบหน้าพิธีกร รุ่น ฉลาก จำนวนสินค้า และการจับถือทีละฉาก</p>
          <a href={reviewImage.url} target="_blank" rel="noreferrer">
            <img className="storyboard-preview" src={reviewImage.url} alt={`Storyboard ${board.product_name}`} />
          </a>
          <fieldset className="workflow-shots" disabled={busy}>
            <legend>เลือกเฉพาะภาพนิ่งที่ตรวจแล้ว</legend>
            {board.scenes.map((scene, index) => <label key={index} className="checkbox">
              <input type="checkbox" checked={reviewScenes.includes(index + 1)} onChange={(event) => {
                const number = index + 1;
                const scenes = event.target.checked ? [...reviewScenes, number] : reviewScenes.filter((item) => item !== number);
                setReview({ id: board.id, version: reviewImage.version, scenes });
              }} />
              ฉาก {String(index + 1).padStart(2, "0")} · {scene.seconds} วิ · {scene.action}
            </label>)}
          </fieldset>
          <button type="button" className="primary" disabled={busy} onClick={() => approve(board)}>บันทึกฉากที่อนุมัติ</button>
          <p role="status">อนุมัติแล้ว {board.approved_scenes.length} / {board.scenes.length} ฉาก</p>
        </>}
      </>}
    </section>
  </div>;
}
