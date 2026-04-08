from __future__ import annotations

import zipfile
from pathlib import Path

import fitz
from PIL import Image

from app.schemas.task import ConversionType
from app.utils.filename import build_unique_path

IMAGE_INPUT_FORMATS = {"jpg", "jpeg", "png", "webp"}
PDF_INPUT_FORMATS = {"pdf"}


def convert_uploaded_file(
    *,
    source_path: Path,
    task_dir: Path,
    conversion_type: ConversionType,
    output_format: str,
) -> tuple[Path, int]:
    if conversion_type == ConversionType.IMAGE:
        return _convert_image(source_path, task_dir, output_format), 1

    if conversion_type == ConversionType.PDF:
        return _convert_pdf(source_path, task_dir, output_format)

    raise ValueError(f"Unsupported conversion type: {conversion_type}")


def validate_source_file_for_conversion(
    *,
    source_path: Path,
    conversion_type: ConversionType,
) -> None:
    suffix = source_path.suffix.lower().removeprefix(".")

    if conversion_type == ConversionType.IMAGE and suffix not in IMAGE_INPUT_FORMATS:
        raise ValueError("Selected file is not a supported image format.")

    if conversion_type == ConversionType.PDF and suffix not in PDF_INPUT_FORMATS:
        raise ValueError("Selected file is not a supported PDF document.")


def _convert_image(source_path: Path, task_dir: Path, output_format: str) -> Path:
    normalized_output = _normalize_image_output_format(output_format)
    target_path = build_unique_path(task_dir / f"{source_path.stem}.{normalized_output}")

    with Image.open(source_path) as image:
        converted = image
        if normalized_output in {"jpg", "jpeg"} and image.mode not in {"RGB", "L"}:
            converted = image.convert("RGB")
        converted.save(target_path, format=_pillow_format_for_output(normalized_output))

    return target_path


def _convert_pdf(source_path: Path, task_dir: Path, output_format: str) -> tuple[Path, int]:
    normalized_output = _normalize_image_output_format(output_format)
    document = fitz.open(source_path)
    rendered_paths: list[Path] = []

    try:
        for page_index, page in enumerate(document, start=1):
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            page_path = task_dir / f"{source_path.stem}-page-{page_index:03d}.{normalized_output}"
            pixmap.save(page_path)

            if normalized_output in {"jpg", "jpeg"}:
                with Image.open(page_path) as image:
                    rgb_image = image.convert("RGB")
                    rgb_image.save(
                        page_path,
                        format=_pillow_format_for_output(normalized_output),
                    )

            rendered_paths.append(page_path)
    finally:
        document.close()

    if len(rendered_paths) == 1:
        return rendered_paths[0], 1

    archive_path = build_unique_path(task_dir / f"{source_path.stem}-{normalized_output}.zip")
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for rendered_path in rendered_paths:
            archive.write(rendered_path, arcname=rendered_path.name)
            rendered_path.unlink(missing_ok=True)

    return archive_path, len(rendered_paths)


def _normalize_image_output_format(output_format: str) -> str:
    return "jpg" if output_format == "jpeg" else output_format


def _pillow_format_for_output(output_format: str) -> str:
    if output_format in {"jpg", "jpeg"}:
        return "JPEG"
    return output_format.upper()
