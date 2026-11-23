import shutil
import subprocess
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from app.renders import Render, _render, _write_normalized_image, render_video_path


def test_render_video_path_only_returns_artifacts_under_render_root(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("RENDER_ROOT", str(tmp_path))
    artifact = tmp_path / "render-1" / "preview.mp4"
    artifact.parent.mkdir()
    artifact.write_bytes(b"mp4")
    render = Render(
        id="render-1",
        workspace_id="workspace-1",
        product_id="product-1",
        status="completed",
        video_relpath="render-1/preview.mp4",
    )
    assert render_video_path(render) == artifact

    render.video_relpath = "../outside.mp4"
    with pytest.raises(FileNotFoundError):
        render_video_path(render)


def test_render_video_path_requires_artifact(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("RENDER_ROOT", str(tmp_path))
    render = Render(
        id="render-2",
        workspace_id="workspace-1",
        product_id="product-1",
        status="processing",
        video_relpath="render-2/preview.mp4",
    )
    with pytest.raises(FileNotFoundError):
        render_video_path(render)


@pytest.mark.skipif(
    not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
    reason="FFmpeg and ffprobe are required for the real render test",
)
@pytest.mark.parametrize("scenes", [None, ["กำลังมองหาอยู่ไหม?\nผ้าไมโครไฟเบอร์",
                                          "ผ้าเช็ดครัว Scotch-Brite",
                                          "ดูรายละเอียดสินค้าก่อนตัดสินใจ"]])
def test_mixed_images_render_to_valid_mp4(tmp_path: Path, scenes):
    inputs = []
    for index, (kind, mime, color) in enumerate(
        (
            ("JPEG", "image/jpeg", "seagreen"),
            ("PNG", "image/png", "olive"),
            ("WEBP", "image/webp", "navy"),
        )
    ):
        buffer = BytesIO()
        Image.new("RGB", (40, 70), color).save(buffer, format=kind)
        path = tmp_path / f"{index}.png"
        _write_normalized_image(buffer.getvalue(), mime, path)
        inputs.append(path)

    output = tmp_path / "preview.mp4"
    _render(inputs, output, scenes)

    assert output.is_file() and output.stat().st_size > 1024
    if scenes:
        for second in (2, 7, 12):
            frame = subprocess.run(
                ["ffmpeg", "-v", "error", "-ss", str(second), "-i", str(output),
                 "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"],
                check=True, capture_output=True,
            )
            with Image.open(BytesIO(frame.stdout)) as image:
                region = image.convert("L").crop((110, 1400, 970, 1650))
                assert sum(region.histogram()[220:]) > 250
