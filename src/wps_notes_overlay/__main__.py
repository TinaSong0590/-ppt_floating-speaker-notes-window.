"""CLI entry: python -m wps_notes_overlay [path.pptx]"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="WPS/PPT 演讲备注悬浮窗（支持飞书/腾讯会议防截屏隐身、置顶提词与按键翻页同步）"
    )
    parser.add_argument(
        "pptx",
        nargs="?",
        help="带演讲者备注的 .pptx 路径（可与 WPS / PowerPoint 正在放映的文件相同）",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="不启动 GUI，只验证备注解析与示例文稿",
    )
    parser.add_argument(
        "--dump-notes",
        metavar="OUT.json",
        help="把解析出的备注导出为 JSON（轻量 ZIP 解析，适合大文件）",
    )
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test(args.pptx)
    if args.dump_notes:
        return _dump_notes(args.pptx, args.dump_notes)

    from .app import run

    run(args.pptx)
    return 0


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _self_test(pptx: str | None) -> int:
    from .notes_loader import load_deck
    from . import privacy

    root = _repo_root()
    paths: list[Path] = []
    if pptx:
        paths.append(Path(pptx))
    else:
        paths.append(root / "samples" / "demo-notes.pptx")

    for path in paths:
        deck = load_deck(path)
        with_notes = sum(1 for s in deck.slides if s.notes.strip())
        print(
            f"OK loaded {deck.path.name}: {deck.count} slides, "
            f"{with_notes} with notes"
        )
        for s in deck.slides[:3]:
            preview = (s.notes[:60] + "…") if len(s.notes) > 60 else s.notes
            print(f"  [{s.index}] {s.title_hint!r} :: {preview!r}")
        if deck.count > 3:
            print(f"  … ({deck.count - 3} more slides)")

    print("--- privacy modes ---")
    for m in privacy.MODES:
        print(f"  {m.id}: is_safe={m.is_safe}")
    print("self-test passed")
    return 0


def _dump_notes(pptx: str | None, out: str) -> int:
    from .notes_loader import load_deck

    root = _repo_root()
    path = Path(pptx) if pptx else root / "samples" / "demo-notes.pptx"
    deck = load_deck(path)
    payload = {
        "path": str(deck.path),
        "slide_count": deck.count,
        "slides": [
            {
                "index": s.index,
                "title_hint": s.title_hint,
                "notes": s.notes,
                "has_notes": bool(s.notes.strip()),
            }
            for s in deck.slides
        ],
    }
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"wrote {out_path} ({deck.count} slides)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
