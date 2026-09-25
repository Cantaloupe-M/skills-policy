from __future__ import annotations

import csv
import io
import os
import shlex
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image


class TesseractNotFoundError(RuntimeError):
    pass


class _Output:
    STRING = 'string'
    BYTES = 'bytes'
    DICT = 'dict'


Output = _Output()


class _PytesseractState:
    tesseract_cmd = 'tesseract'


pytesseract = _PytesseractState()


def _prepare_image(image: Any):
    if isinstance(image, Image.Image):
        handle = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        handle.close()
        image.save(handle.name)
        return handle.name, True
    return os.fspath(image), False


def _run_tesseract(image: Any, *, config: str = '', lang: str | None = None, extra: list[str] | None = None) -> str:
    image_path, should_cleanup = _prepare_image(image)
    cmd = [pytesseract.tesseract_cmd, image_path, 'stdout']
    if lang:
        cmd.extend(['-l', lang])
    if config:
        cmd.extend(shlex.split(config))
    if extra:
        cmd.extend(extra)
    try:
        proc = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return proc.stdout
    except FileNotFoundError as exc:
        raise TesseractNotFoundError('tesseract executable not found') from exc
    finally:
        if should_cleanup:
            Path(image_path).unlink(missing_ok=True)


def image_to_string(image: Any, lang: str | None = None, config: str = '', **_: Any) -> str:
    return _run_tesseract(image, config=config, lang=lang)


def image_to_data(image: Any, lang: str | None = None, config: str = '', output_type: Any = None, **_: Any):
    raw = _run_tesseract(image, config=config, lang=lang, extra=['tsv'])
    if output_type == Output.DICT:
        reader = csv.DictReader(io.StringIO(raw), delimiter='\t')
        fieldnames = reader.fieldnames or []
        result = {name: [] for name in fieldnames}
        for row in reader:
            for key in fieldnames:
                value = row.get(key, '')
                if key in {'level', 'page_num', 'block_num', 'par_num', 'line_num', 'word_num', 'left', 'top', 'width', 'height'}:
                    try:
                        result[key].append(int(value))
                    except Exception:
                        result[key].append(-1)
                elif key == 'conf':
                    try:
                        result[key].append(float(value))
                    except Exception:
                        result[key].append(-1.0)
                else:
                    result[key].append(value)
        return result
    return raw


def get_tesseract_version() -> str:
    try:
        proc = subprocess.run([pytesseract.tesseract_cmd, '--version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return proc.stdout.splitlines()[0] if proc.stdout else ''
    except FileNotFoundError as exc:
        raise TesseractNotFoundError('tesseract executable not found') from exc
