from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable, Sequence
from zipfile import BadZipFile, ZipFile

REQUIRED_EXPORT_FILES = ("followers_1.json", "following.json")
OPTIONAL_EXPORT_FILES = ("recently_unfollowed_profiles.json",)

EXPORT_NAME_PATTERN = re.compile(
    r"instagram-(?P<account>.+)-(?P<date>\d{4}-\d{2}-\d{2})(?:-[A-Za-z0-9]+)?$"
)


@dataclass(frozen=True)
class ExportMetadata:
    source_name: str
    source_label: str
    source_kind: str
    detected_path: str
    account_name: str | None
    export_date: date | None
    sort_timestamp: datetime


@dataclass(frozen=True)
class InstagramExport:
    metadata: ExportMetadata
    followers: set[str]
    following: set[str]
    recently_unfollowed: set[str]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def parse_usernames(path: Path) -> set[str]:
    return parse_usernames_from_data(load_json(path))


def parse_usernames_from_bytes(raw_bytes: bytes) -> set[str]:
    return parse_usernames_from_data(json.loads(raw_bytes.decode("utf-8")))


def parse_usernames_from_data(data: Any) -> set[str]:
    usernames = _extract_usernames(data)
    return {username.casefold() for username in usernames if username}


def load_uploaded_exports(files: Sequence[tuple[str, bytes]]) -> list[InstagramExport]:
    exports: list[InstagramExport] = []
    for filename, raw_bytes in files:
        exports.append(load_export_from_zip_bytes(filename=filename, raw_bytes=raw_bytes))
    return sort_exports(exports)


def discover_local_exports(data_dir: Path) -> list[InstagramExport]:
    if not data_dir.exists():
        return []

    exports: list[InstagramExport] = []
    seen_directories: set[Path] = set()

    for followers_path in data_dir.rglob(REQUIRED_EXPORT_FILES[0]):
        export_dir = followers_path.parent
        following_path = export_dir / REQUIRED_EXPORT_FILES[1]
        if not following_path.exists() or export_dir in seen_directories:
            continue
        seen_directories.add(export_dir)
        exports.append(
            load_export_from_directory(
                data_dir=data_dir,
                export_dir=export_dir,
            )
        )

    for archive_path in data_dir.rglob("*.zip"):
        try:
            exports.append(load_export_from_zip_path(archive_path))
        except ValueError:
            continue

    return sort_exports(_deduplicate_exports(exports))


def load_export_from_zip_path(path: Path) -> InstagramExport:
    try:
        raw_bytes = path.read_bytes()
    except OSError as error:
        raise ValueError(f"Could not read archive: {path}") from error
    return load_export_from_zip_bytes(filename=path.name, raw_bytes=raw_bytes)


def load_export_from_zip_bytes(filename: str, raw_bytes: bytes) -> InstagramExport:
    try:
        with ZipFile(BytesIO(raw_bytes)) as archive:
            names = archive.namelist()
            candidate_paths = _discover_archive_candidate_paths(names)
            if not candidate_paths:
                raise ValueError("Archive does not contain Instagram follower exports.")

            detected_path = sorted(candidate_paths)[0]
            files = {
                name: _read_archive_json(
                    archive,
                    f"{detected_path}/{name}" if detected_path else name,
                )
                for name in REQUIRED_EXPORT_FILES
            }
            optional_files = {
                name: _read_archive_json(
                    archive,
                    f"{detected_path}/{name}" if detected_path else name,
                )
                for name in OPTIONAL_EXPORT_FILES
                if _archive_has_path(
                    names,
                    f"{detected_path}/{name}" if detected_path else name,
                )
            }
    except (BadZipFile, KeyError, json.JSONDecodeError) as error:
        raise ValueError("Invalid Instagram export ZIP file.") from error

    metadata = _build_metadata(
        source_name=filename,
        source_kind="zip",
        detected_path=detected_path or ".",
        sort_timestamp=_metadata_timestamp_from_name(filename),
    )
    return InstagramExport(
        metadata=metadata,
        followers=parse_usernames_from_data(files[REQUIRED_EXPORT_FILES[0]]),
        following=parse_usernames_from_data(files[REQUIRED_EXPORT_FILES[1]]),
        recently_unfollowed=parse_usernames_from_data(
            optional_files.get("recently_unfollowed_profiles.json", [])
        ),
    )


def load_export_from_directory(data_dir: Path, export_dir: Path) -> InstagramExport:
    root_dir = _determine_root_directory(data_dir=data_dir, export_dir=export_dir)
    sort_timestamp = _latest_directory_timestamp(export_dir)

    metadata = _build_metadata(
        source_name=root_dir.name,
        source_kind="directory",
        detected_path=str(export_dir),
        sort_timestamp=sort_timestamp,
    )
    followers = parse_usernames(export_dir / REQUIRED_EXPORT_FILES[0])
    following = parse_usernames(export_dir / REQUIRED_EXPORT_FILES[1])
    recently_unfollowed_path = export_dir / OPTIONAL_EXPORT_FILES[0]
    recently_unfollowed = (
        parse_usernames(recently_unfollowed_path)
        if recently_unfollowed_path.exists()
        else set()
    )

    return InstagramExport(
        metadata=metadata,
        followers=followers,
        following=following,
        recently_unfollowed=recently_unfollowed,
    )


def sort_exports(exports: Sequence[InstagramExport]) -> list[InstagramExport]:
    return sorted(
        exports,
        key=lambda export: (
            export.metadata.sort_timestamp,
            export.metadata.source_name.lower(),
        ),
    )


def _deduplicate_exports(exports: Iterable[InstagramExport]) -> list[InstagramExport]:
    deduplicated: dict[tuple[str | None, date | None, int, int], InstagramExport] = {}
    for export in exports:
        key = (
            export.metadata.account_name,
            export.metadata.export_date,
            len(export.followers),
            len(export.following),
        )
        deduplicated[key] = export
    return list(deduplicated.values())


def _discover_archive_candidate_paths(names: Sequence[str]) -> set[str]:
    followers_parents = {
        _archive_parent(name)
        for name in names
        if name.endswith(REQUIRED_EXPORT_FILES[0])
    }
    following_parents = {
        _archive_parent(name)
        for name in names
        if name.endswith(REQUIRED_EXPORT_FILES[1])
    }
    return followers_parents & following_parents


def _archive_parent(name: str) -> str:
    return name.rsplit("/", maxsplit=1)[0] if "/" in name else ""


def _archive_has_path(names: Sequence[str], target: str) -> bool:
    return target in names


def _read_archive_json(archive: ZipFile, path: str) -> Any:
    with archive.open(path) as file:
        return json.loads(file.read().decode("utf-8"))


def _determine_root_directory(data_dir: Path, export_dir: Path) -> Path:
    relative_parts = export_dir.relative_to(data_dir).parts
    if len(relative_parts) <= 1:
        return export_dir
    return data_dir / relative_parts[0]


def _latest_directory_timestamp(export_dir: Path) -> datetime:
    latest_mtime = max(
        path.stat().st_mtime
        for path in export_dir.iterdir()
        if path.is_file()
    )
    return datetime.fromtimestamp(latest_mtime)


def _build_metadata(
    source_name: str,
    source_kind: str,
    detected_path: str,
    sort_timestamp: datetime,
) -> ExportMetadata:
    stem = Path(source_name).stem
    account_name, export_date = _parse_export_name(stem)
    source_label = account_name or stem
    return ExportMetadata(
        source_name=source_name,
        source_label=source_label,
        source_kind=source_kind,
        detected_path=detected_path,
        account_name=account_name,
        export_date=export_date,
        sort_timestamp=(
            datetime.combine(export_date, datetime.min.time())
            if export_date is not None
            else sort_timestamp
        ),
    )


def _metadata_timestamp_from_name(source_name: str) -> datetime:
    _, export_date = _parse_export_name(Path(source_name).stem)
    if export_date is not None:
        return datetime.combine(export_date, datetime.min.time())
    return datetime.utcnow()


def _parse_export_name(name: str) -> tuple[str | None, date | None]:
    match = EXPORT_NAME_PATTERN.match(name)
    if not match:
        return None, None

    account_name = match.group("account")
    export_date = date.fromisoformat(match.group("date"))
    return account_name, export_date


def _extract_usernames(node: Any) -> set[str]:
    usernames: set[str] = set()

    if isinstance(node, dict):
        for key in ("username", "value", "title"):
            value = node.get(key)
            if isinstance(value, str):
                normalized = _normalize_username(value)
                if normalized:
                    usernames.add(normalized)

        href = node.get("href")
        if isinstance(href, str):
            normalized = _normalize_from_href(href)
            if normalized:
                usernames.add(normalized)

        label_values = node.get("label_values")
        if isinstance(label_values, list):
            for item in label_values:
                if (
                    isinstance(item, dict)
                    and item.get("label") == "Username"
                    and isinstance(item.get("value"), str)
                ):
                    normalized = _normalize_username(item["value"])
                    if normalized:
                        usernames.add(normalized)

        string_list_data = node.get("string_list_data")
        if isinstance(string_list_data, list):
            for item in string_list_data:
                usernames.update(_extract_usernames(item))

        for value in node.values():
            if isinstance(value, (dict, list)):
                usernames.update(_extract_usernames(value))

        return usernames

    if isinstance(node, list):
        for item in node:
            usernames.update(_extract_usernames(item))
        return usernames

    if isinstance(node, str):
        normalized = _normalize_username(node)
        if normalized:
            usernames.add(normalized)

    return usernames


def _normalize_from_href(href: str) -> str | None:
    cleaned = href.strip().rstrip("/")
    if not cleaned:
        return None

    if "instagram.com/" in cleaned:
        cleaned = cleaned.split("instagram.com/", maxsplit=1)[1]

    if cleaned.startswith("_u/"):
        cleaned = cleaned.split("_u/", maxsplit=1)[1]

    candidate = cleaned.split("/", maxsplit=1)[0]
    return _normalize_username(candidate)


def _normalize_username(value: str) -> str | None:
    candidate = value.strip().lstrip("@")
    if not candidate:
        return None

    if candidate.startswith("http://") or candidate.startswith("https://"):
        return _normalize_from_href(candidate)

    if "/" in candidate:
        return None

    if " " in candidate:
        return None

    return candidate
