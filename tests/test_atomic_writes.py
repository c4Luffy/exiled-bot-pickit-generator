"""Concurrent writers must not collide over a shared temp file.

This app's own history: a shared ``<target>.tmp`` is safe for exactly one
writer. Two of them — a GUI generate racing the ``--regenerate`` task, or
simply two app instances launching at once — both open that one name. On
Windows the second fails outright with PermissionError, so the .ipd, the map
runner or the game-data cache silently is not written; on POSIX they interleave
and one renames a half-finished file over the real one. ``os.replace`` being
atomic never helped, because the clash happens before the swap.

Every writer therefore uses a UNIQUE temp name. These tests reproduce the
collision rather than trusting that.
"""
from __future__ import annotations

import os
import threading

import exilebot_pickit.generator as gen

ROUNDS = 24


def _hammer(fn, workers=8):
    """Run fn(i) on several threads at once; return any exception raised."""
    errors = []

    def run(i):
        try:
            fn(i)
        except Exception as e:                      # noqa: BLE001 - that's the point
            errors.append(e)

    threads = [threading.Thread(target=run, args=(i,)) for i in range(workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return errors


def test_concurrent_text_writes_do_not_collide(tmp_path):
    target = str(tmp_path / "poe1_pickit.ipd")
    for _ in range(ROUNDS // 8):
        errors = _hammer(lambda i: gen.write_text_atomic(target, f"payload {i}\n" * 200))
        assert not errors, f"concurrent write failed: {errors[0]!r}"
    # whoever won, the file must be one COMPLETE payload, never a mix
    lines = set(open(target, encoding="utf-8").read().splitlines())
    assert len(lines) == 1, f"interleaved content: {sorted(lines)[:3]}"


def test_concurrent_copies_do_not_collide(tmp_path):
    """The bot-folder copy: pickit and map runner both land this way."""
    srcs = []
    for i in range(8):
        s = tmp_path / f"src{i}.ipd"
        s.write_text(f"rules {i}\n" * 200, encoding="utf-8")
        srcs.append(str(s))
    dst = str(tmp_path / "bot" / "poe1_pickit.ipd")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, "w").close()

    for _ in range(ROUNDS // 8):
        errors = _hammer(lambda i: gen.copy_atomic(srcs[i], dst))
        assert not errors, f"concurrent copy failed: {errors[0]!r}"
    lines = set(open(dst, encoding="utf-8").read().splitlines())
    assert len(lines) == 1, f"interleaved content: {sorted(lines)[:3]}"


def test_concurrent_byte_writes_do_not_collide(tmp_path):
    """The bot's config.ini is rewritten this way."""
    target = str(tmp_path / "config.ini")
    for _ in range(ROUNDS // 8):
        errors = _hammer(
            lambda i: gen.write_bytes_atomic(target, (f"key={i}\n" * 200).encode("latin-1")))
        assert not errors, f"concurrent byte write failed: {errors[0]!r}"
    lines = set(open(target, encoding="latin-1").read().splitlines())
    assert len(lines) == 1


def test_no_temp_files_are_left_behind(tmp_path):
    target = str(tmp_path / "out.ipd")
    gen.write_text_atomic(target, "x\n")
    gen.write_bytes_atomic(str(tmp_path / "out.bin"), b"x")
    src = tmp_path / "s.ipd"
    src.write_text("y\n", encoding="utf-8")
    gen.copy_atomic(str(src), str(tmp_path / "copied.ipd"))
    leftovers = [f for f in os.listdir(tmp_path) if f.endswith(".tmp")]
    assert not leftovers, f"temp files left in the output folder: {leftovers}"


def test_a_failed_copy_leaves_the_original_intact(tmp_path):
    dst = tmp_path / "keep.ipd"
    dst.write_text("original\n", encoding="utf-8")
    try:
        gen.copy_atomic(str(tmp_path / "does-not-exist.ipd"), str(dst))
    except OSError:
        pass
    assert dst.read_text(encoding="utf-8") == "original\n"
    assert not [f for f in os.listdir(tmp_path) if f.endswith(".tmp")]
