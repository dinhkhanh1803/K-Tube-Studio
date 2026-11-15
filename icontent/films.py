"""Phim trọn bộ miễn phí bản quyền từ Internet Archive (archive.org), qua API công khai của họ, không cần key.

Chỉ nhận phim mà iContent tin là dùng lại được (lồng tiếng, đăng lại, kiếm tiền):
  - Phạm vi công cộng (Public Domain Mark, CC0): phải ra đời trước 1980. Archive.org do người dùng tải lên và có người gắn nhãn
    "public domain" cho phim còn bản quyền (đo thật 2026-11-13: Boku no Hero Academia, Rockstar 2011, Virus 1980 đều mang nhãn
    đó). Phim Mỹ trước 1978 không gia hạn bản quyền thì đã hết, nên mốc năm loại được gần hết nhãn sai.
    Riêng bộ Prelinger (tư liệu do Rick Prelinger tuyển, đã hiến cho công chúng) không xét năm.
  - CC BY (ghi tên tác giả): mọi năm. Mỗi phim tải về có dòng ghi công trong meta.json.
  - Bỏ CC BY-SA (video làm ra cũng phải theo giấy phép đó), NC (cấm thương mại), ND (cấm sửa, mà lồng tiếng là sửa) như stock.py.
  - Chỉ tìm trong các bộ sưu tập có người tuyển (COLLECTIONS), không tìm cả archive.org: bộ "opensource_movies" là nơi ai cũng
    tải lên được, nhãn sai gần như toàn ở đó. Phim mở của Blender lấy theo danh sách dưới (BLENDER), chỉ phim có lời thoại.
Kiểm tra lại giấy phép lúc tải (fetch), nên dán link archive.org bất kỳ vào hàng đợi cũng qua cùng một cửa.
download.blender.org chặn máy bằng Cloudflare, nên phim Blender lấy bản trên archive.org.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from urllib.parse import unquote, urlparse

from .util import ROOT, check_cancel, ffmpeg, log, progress, safe_name, short_hash

UA = "iContent/0.6 (https://github.com/dienmoc86/icontent)"
API = "https://archive.org"
CACHE_DIR = ROOT / "assets" / ".films_cache"
SEARCH_TTL = 6 * 3600
META_TTL = 3600
PD_LAST_YEAR = 1979
PAGE_SIZE = 24

# id -> (tên hiện, bộ sưu tập archive.org)
COLLECTIONS = {
    "feature": ("Phim truyện", ["feature_films"]),
    "comedy": ("Hài", ["Comedy_Films"]),
    "horror": ("Kinh dị, viễn tưởng", ["SciFi_Horror"]),
    "noir": ("Hình sự", ["Film_Noir"]),
    "cartoon": ("Hoạt hình", ["classic_cartoons", "animationandcartoons"]),
    "tv": ("Phim truyền hình", ["classic_tv"]),
    "short": ("Phim ngắn", ["short_films"]),
    "docs": ("Tư liệu", ["prelinger"]),
}
TRUSTED_PD = {"prelinger"}                  # bộ không xét năm
# Phim mở của Blender Foundation (CC BY), bản trên archive.org. Chỉ phim có lời thoại: phim không lời thì không có gì để lồng tiếng.
BLENDER = ["ElephantsDream", "Tears-of-Steel", "Sintel", "CosmosLaundromatFirstCycle", "sprite-fright"]
CATEGORIES = [{"id": k, "name": v[0]} for k, v in COLLECTIONS.items()] + [{"id": "blender", "name": "Hoạt hình 3D mở (Blender)"}]
ALL_COLLECTIONS = sorted({c for _, cols in COLLECTIONS.values() for c in cols})
SORTS = {"popular": "downloads desc", "added": "addeddate desc", "old": "year asc", "new": "year desc"}

MP4_EXT = {".mp4", ".m4v"}
VIDEO_EXT = MP4_EXT | {".mkv", ".mov", ".avi", ".ogv", ".webm", ".mpeg", ".mpg", ".wmv", ".flv"}
SKIP_FORMATS = {"Thumbnail", "Animated GIF", "Item Tile", "JPEG", "PNG", "Metadata", "Archive BitTorrent", "Item Image"}


class FilmError(RuntimeError):
    pass


# ------------------------------------------------------------------ giấy phép
def license_of(url: str) -> dict | None:
    """licenseurl của archive.org -> {code, name}; None nếu không phải giấy phép iContent nhận."""
    u = (url or "").lower().strip()
    if "publicdomain/zero" in u:
        return {"code": "cc0", "name": "CC0, phạm vi công cộng"}
    if "publicdomain" in u:
        return {"code": "pd", "name": "Phạm vi công cộng"}
    m = re.search(r"/licenses/by/(\d(?:\.\d)?)", u)
    if m:
        return {"code": "by", "name": f"CC BY {m.group(1)}, ghi tên tác giả"}
    return None


def _year(md: dict) -> int | None:
    for k in ("year", "date"):
        v = md.get(k)
        if isinstance(v, list):
            v = v[0] if v else ""
        m = re.match(r"\s*(\d{4})", str(v or ""))
        if m:
            return int(m.group(1))
    return None


def _list(v) -> list[str]:
    return [str(x) for x in v] if isinstance(v, list) else ([str(v)] if v else [])


def check_allowed(ident: str, md: dict) -> dict:
    """Trả về giấy phép nếu phim dùng lại được, không thì FilmError nói rõ vì sao."""
    lic = license_of(_list(md.get("licenseurl"))[0] if md.get("licenseurl") else "")
    if not lic:
        raise FilmError("Phim này không ghi giấy phép miễn phí rõ ràng (phạm vi công cộng hoặc CC BY), "
                        "iContent không tải để tránh bị gậy bản quyền.")
    cols = set(_list(md.get("collection")))
    if ident not in BLENDER and not cols & set(ALL_COLLECTIONS):
        raise FilmError("Phim này nằm ngoài các bộ sưu tập đã kiểm trên archive.org (bộ do người dùng tự tải lên hay gắn nhãn "
                        "giấy phép sai). Hãy chọn phim trong Khám phá > Phim miễn phí.")
    if lic["code"] in ("pd", "cc0") and not cols & TRUSTED_PD:
        y = _year(md)
        if y is None or y > PD_LAST_YEAR:
            raise FilmError(f"Phim ghi \"phạm vi công cộng\" nhưng {'không rõ năm' if y is None else f'làm năm {y}'}: "
                            f"iContent chỉ tin nhãn này với phim trước {PD_LAST_YEAR + 1}, vì có người gắn nhãn sai cho phim còn bản quyền.")
    return lic


def _license_query() -> str:
    pd = f"(licenseurl:*publicdomain* AND (year:[1880 TO {PD_LAST_YEAR}] OR collection:({' OR '.join(TRUSTED_PD)})))"
    return f"({pd} OR licenseurl:*\\/licenses\\/by\\/*)"


# ------------------------------------------------------------------ gọi mạng
def _get_json(url: str, timeout: float = 30) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code >= 500 and attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            raise FilmError(f"Internet Archive báo lỗi {e.code}. Thử lại sau ít phút.") from None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            raise FilmError(f"Không kết nối được Internet Archive ({str(getattr(e, 'reason', e))[:100]}). Kiểm tra mạng.") from None
        except ValueError:
            raise FilmError("Internet Archive trả về dữ liệu không đọc được") from None
    raise FilmError("Không kết nối được Internet Archive")


_lock = threading.Lock()
_META: dict[str, tuple[float, dict]] = {}


def metadata(ident: str) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,120}", ident or ""):
        raise FilmError("Mã phim archive.org không hợp lệ")
    with _lock:
        hit = _META.get(ident)
        if hit and time.time() - hit[0] < META_TTL:
            return hit[1]
    data = _get_json(f"{API}/metadata/{ident}")
    if not data or not data.get("metadata"):
        raise FilmError("Không tìm thấy phim này trên archive.org (có thể đã bị gỡ)")
    with _lock:
        _META[ident] = (time.time(), data)
        if len(_META) > 300:
            for k in list(_META)[:100]:
                _META.pop(k, None)
    return data


def _cached(key: str, fn):
    f = CACHE_DIR / (hashlib.sha1(key.encode("utf-8")).hexdigest()[:20] + ".json")
    try:
        if time.time() - f.stat().st_mtime < SEARCH_TTL:
            return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    data = fn()
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    return data


# ------------------------------------------------------------------ tìm
def parse_duration(v) -> float:
    """'1:17:26' / '20:33' / '68 min' / '4483.21' -> giây."""
    if isinstance(v, list):
        v = v[0] if v else ""
    s = str(v or "").strip().lower()
    if not s:
        return 0.0
    if re.fullmatch(r"\d+(\.\d+)?", s):
        return float(s)
    if re.fullmatch(r"\d+(:\d{1,2}){1,2}(\.\d+)?", s):
        t = 0.0
        for p in s.split(":"):
            t = t * 60 + float(p)
        return t
    m = re.search(r"(\d+)\s*(?:h|hr|hour)", s)
    mins = re.search(r"(\d+)\s*(?:m|min)", s)
    secs = (int(m.group(1)) * 3600 if m else 0) + (int(mins.group(1)) * 60 if mins else 0)
    return float(secs)


def _clean_text(s, n: int = 400) -> str:
    if isinstance(s, list):
        s = " ".join(str(x) for x in s)
    s = re.sub(r"<[^>]+>", " ", str(s or ""))
    s = re.sub(r"&nbsp;|&#160;", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n]


def _card(d: dict) -> dict | None:
    lic = license_of(_list(d.get("licenseurl"))[0] if d.get("licenseurl") else "")
    if not lic:
        return None
    ident = d["identifier"]
    title = d.get("title")
    if isinstance(title, list):
        title = title[0] if title else ""
    return {
        "src": "archive", "id": ident, "title": str(title or ident), "year": _year(d),
        "duration": parse_duration(d.get("runtime")), "license": lic["name"], "lic": lic["code"],
        "creator": _clean_text(d.get("creator"), 80), "desc": _clean_text(d.get("description"), 300),
        "downloads": int(d.get("downloads") or 0), "cover": f"{API}/services/img/{ident}",
        "url": f"{API}/details/{ident}",
    }


def search(cat: str = "feature", query: str = "", sort: str = "popular", page: int = 1) -> dict:
    """-> {items, total, page, pages}. query rỗng: duyệt theo thể loại; có query: tìm trong mọi bộ (hoặc trong thể loại đang chọn)."""
    page = max(1, min(int(page or 1), 50))
    parts = ["mediatype:movies"]
    if cat == "blender":
        parts.append("identifier:(" + " OR ".join(BLENDER) + ")")
    else:
        cols = COLLECTIONS[cat][1] if cat in COLLECTIONS else ALL_COLLECTIONS
        parts += ["collection:(" + " OR ".join(cols) + ")", _license_query()]
    q = re.sub(r'[\\":()\[\]{}^~*?!+\-/]', " ", (query or "")).strip()[:100]
    if q:
        words = " ".join(q.split())
        parts.append(f'(title:({words}) OR subject:({words}) OR creator:({words}))')
    fl = ["identifier", "title", "year", "date", "runtime", "licenseurl", "creator", "description", "downloads"]
    params = [("q", " AND ".join(parts)), *[("fl[]", f) for f in fl], ("rows", PAGE_SIZE), ("page", page),
              ("output", "json"), ("sort[]", SORTS.get(sort, SORTS["popular"]))]
    url = f"{API}/advancedsearch.php?" + urllib.parse.urlencode(params)

    def run():
        r = _get_json(url).get("response") or {}
        items = [c for c in (_card(d) for d in r.get("docs") or []) if c]
        total = int(r.get("numFound") or 0)
        return {"items": items, "total": total, "page": page, "pages": max(1, -(-total // PAGE_SIZE))}
    return _cached(url, run)


def to_english(query: str, tcfg) -> str:
    """Từ khóa tiếng Việt -> tiếng Anh (archive.org chỉ có tên tiếng Anh). Chữ không dấu thì để nguyên; không dịch được thì ""."""
    from . import offline
    from .keys import translator_ready

    if all(ord(ch) < 128 for ch in query):
        return query
    model = tcfg.get("offline_model")
    if offline.ready(model) and offline.start():
        res = offline.translate_text(query, "en", model).strip().strip(".!\"“”")
        return res if res and all(ord(ch) < 128 for ch in res) else ""
    if tcfg.provider in ("claude", "openai") and translator_ready(tcfg):
        from .translate import make_translator

        schema = {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"], "additionalProperties": False}
        res = make_translator(tcfg).json_call("Translate the film search keyword into short English (a title, genre or topic). "
                                              "Return JSON {\"text\": ...}.", query, schema, max_tokens=200)
        return str(res.get("text") or "").strip()
    return ""


# ------------------------------------------------------------------ một phim: các video bên trong
def _height(f: dict) -> int:
    try:
        return int(float(f.get("height") or 0))
    except ValueError:
        return 0


def _aspect_vote(fs: list[dict]) -> float:
    """Tỉ lệ khung đúng của một phim, theo số đông các bản trong archive.org. Một bản riêng lẻ có thể sai: Duck and Cover bản
    MPEG4 thật ra 368x480 không ghi tỉ lệ điểm ảnh (xem ra méo dọc), trong khi các bản ogv 400x300, 512kb 320x240 đều 4:3.
    Chưa đủ hai bản đồng ý thì 0 (không sửa)."""
    votes: dict[float, list[float]] = {}
    for f in fs:
        try:
            w, h = int(float(f.get("width") or 0)), _height(f)
        except ValueError:
            continue
        if w > 0 and h > 0:
            votes.setdefault(round(w / h, 2), []).append(w / h)
    if not votes:
        return 0.0
    best = max(votes.values(), key=len)
    return sum(best) / len(best) if len(best) >= 2 else 0.0      # trung bình tỉ lệ thật: 4:3 ra 1,3333 (640 rộng), không phải 1,33


HEAVY_RATE = 12e6       # bit/giây: trên mức này là bản rip Blu-ray thô (Night of the Living Dead mkv 16 Mbps, 11,5 GB)
SAME_FILM_MIN = 2400    # giây: hai bản dài hơn 40 phút cùng độ dài (lệch ≤1 s) là cùng một phim


def _rank(f: dict, dur: float) -> tuple:
    """Thứ hạng một file khi chọn bản để tải. Nét trước, nhưng file nặng quá mức thì nhường bản ≥720p vừa phải:
    lồng tiếng xong vẫn xuất lại, tải 11 GB (8 tiếng ở tốc độ archive.org) để được cùng chất lượng 1080p là phí.
    Cùng độ nét: H.264 trước (format "MPEG4" của archive.org thường là MPEG-4 Part 2, trình duyệt không phát được), rồi mp4."""
    h, size = _height(f), int(f.get("size") or 0)
    heavy = dur > 0 and size * 8 / dur > HEAVY_RATE
    return (h >= 720 and not heavy, h, "h.264" in str(f.get("format") or "").lower(),
            Path(str(f.get("name"))).suffix.lower() in MP4_EXT, -size if heavy else size)


def videos(data: dict, max_height: int = 1080) -> list[dict]:
    """Các video khác nhau trong một mục (mục phim truyền hình, hoạt hình thường gom nhiều tập).
    Archive.org lưu bản gốc + các bản chuyển đổi (512Kb MPEG4, h.264...) trỏ về bản gốc: gom theo bản gốc, chọn file nét nhất
    không quá max_height, cùng độ nét thì ưu tiên mp4 (không phải chuyển). Bản chuyển đổi của archive.org thường chỉ 360p
    trong khi bản gốc 1080p (đo thật: Elephants Dream ed_hd.avi 1080p, ed_hd.mp4 360p), nên không ưu tiên mp4 trước độ nét.
    Một phim có khi được tải lên nhiều bản khác độ nét (ed_1024 576p + ed_hd 1080p): cùng độ dài, khác độ nét -> giữ bản nét nhất.
    Các tập phim truyền hình cùng độ nét nên không bị gộp nhầm."""
    groups: dict[str, list[dict]] = {}
    by_name = {str(f.get("name") or ""): f for f in data.get("files") or []}

    def root_of(f: dict) -> str:
        # bản chuyển đổi có khi chuyển từ bản chuyển đổi khác (Duck and Cover: .ia.mp4 <- .mp4 <- .mpeg gốc): lần tới tận bản gốc
        seen = set()
        while f.get("source") == "derivative" and f.get("original") in by_name and f["original"] not in seen:
            seen.add(f["original"])
            f = by_name[f["original"]]
        return str(f.get("original") or f.get("name")) if f.get("source") == "derivative" else str(f.get("name"))

    for f in data.get("files") or []:
        name = str(f.get("name") or "")
        if Path(name).suffix.lower() not in VIDEO_EXT or f.get("format") in SKIP_FORMATS:
            continue
        if re.search(r"(^|[._-])(sample|thumb|trailer)s?([._-]|$)", name, re.I) and len(data.get("files") or []) > 6:
            continue
        groups.setdefault(root_of(f), []).append(f)
    out = []
    for root, fs in groups.items():
        fit = [f for f in fs if _height(f) <= max_height] or [min(fs, key=_height)]
        dur = max((parse_duration(f.get("length")) for f in fs), default=0.0)
        best = max(fit, key=lambda f: _rank(f, dur))
        label = str(best.get("title") or "") or Path(root).stem.replace("_", " ")
        out.append({"key": root, "file": best["name"], "label": label, "duration": dur,
                    "size": int(best.get("size") or 0), "height": _height(best), "aspect": _aspect_vote(fs),
                    "top": max(_height(f) for f in fs), "rank": _rank(best, dur)})
    kept: list[dict] = []
    for v in sorted(out, key=lambda v: v["rank"], reverse=True):
        # cùng một phim tải lên nhiều bản: khác độ nét (ed_1024 + ed_hd), hoặc phim dài cùng độ nét (Night of the Living Dead:
        # bản mkv 11,5 GB + bản mp4 1,9 GB, cùng 5752,8 s). Tập phim truyền hình ngắn cùng độ nét thì không gộp.
        if v["duration"] > 60 and any(abs(k["duration"] - v["duration"]) <= 1.0 and (k["top"] != v["top"] or v["duration"] >= SAME_FILM_MIN)
                                      for k in kept):
            continue
        kept.append(v)
    out = [{k: x for k, x in v.items() if k not in ("top", "rank")} for v in kept]
    out.sort(key=lambda v: [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", v["key"])])
    return out


def detail(ident: str, max_height: int = 1080) -> dict:
    data = metadata(ident)
    md = data["metadata"]
    lic, reason = None, ""
    try:
        lic = check_allowed(ident, md)
    except FilmError as e:
        reason = str(e)
    title = md.get("title")
    if isinstance(title, list):
        title = title[0] if title else ""
    return {
        "id": ident, "title": str(title or ident), "year": _year(md), "creator": _clean_text(md.get("creator"), 120),
        "desc": _clean_text(md.get("description"), 1500), "license": lic["name"] if lic else "",
        "license_url": _list(md.get("licenseurl"))[0] if md.get("licenseurl") else "", "allowed": bool(lic), "reason": reason,
        "cover": f"{API}/services/img/{ident}", "url": f"{API}/details/{ident}", "videos": videos(data, max_height),
    }


# ------------------------------------------------------------------ link
def parse_url(url: str) -> tuple[str, str]:
    """archive.org/details/<id>[/<file>], /download/<id>/<file>, /embed/<id> -> (id, file hoặc "")."""
    u = urlparse(url)
    host = (u.hostname or "").lower()
    if not (host == "archive.org" or host.endswith(".archive.org")):
        raise FilmError("Không phải link archive.org")
    parts = [unquote(p) for p in u.path.split("/") if p]
    if len(parts) >= 2 and parts[0] in ("details", "download", "embed", "stream"):
        return parts[1], "/".join(parts[2:])
    raise FilmError("Link archive.org cần có dạng archive.org/details/<mã phim>")


def item_url(ident: str, file: str = "") -> str:
    return f"{API}/details/{ident}" + (f"/{urllib.parse.quote(file)}" if file else "")


_ISO = {"english": "en", "eng": "en", "en": "en", "french": "fr", "fre": "fr", "fra": "fr", "spanish": "es", "spa": "es",
        "german": "de", "ger": "de", "deu": "de", "italian": "it", "ita": "it", "russian": "ru", "rus": "ru",
        "japanese": "ja", "jpn": "ja", "chinese": "zh", "chi": "zh", "zho": "zh", "korean": "ko", "kor": "ko"}


def asr_language(md: dict) -> str:
    """Trường language của archive.org ("English", "eng", ["eng"]...) -> mã Whisper; không rõ thì "" (Whisper tự nhận)."""
    langs = _list(md.get("language"))
    codes = {_ISO.get(x.strip().lower(), "?") for x in langs if x.strip()}
    return codes.pop() if len(codes) == 1 and "?" not in codes else ""


def job_defaults(md: dict) -> dict:
    """Cấu hình riêng cho job phim (meta.json "defaults", xem pipeline.job_options)."""
    return {"asr": {"language": asr_language(md), "initial_prompt": ""}, "edit": {"blur_hardsub": False}}


def credit_line(title: str, year, creator: str, lic: dict, url: str) -> str:
    who = creator or "không rõ tác giả"
    return f"\"{title}\"{f' ({year})' if year else ''}, {who}. {lic['name']}. Nguồn: Internet Archive, {url}"


# ------------------------------------------------------------------ tải
# Archive.org cho mỗi kết nối khoảng 250 KB/giây (đo thật 2026-11-13: 147 MB mất 10 phút), phim truyện 600-800 MB phải chờ gần
# một giờ. File lớn tải 4 đoạn song song (như các trình quản lý tải), mỗi đoạn tự nối tiếp khi đứt mạng, chạy lại thì tải tiếp.
PARALLEL = 4
PARALLEL_MIN = 48 * 1024 * 1024


def _opener(proxy: str):
    handlers = [urllib.request.ProxyHandler({"http": proxy, "https": proxy})] if proxy else []
    return urllib.request.build_opener(*handlers)


def _remote_size(url: str, opener) -> int:
    """Cỡ file nếu máy chủ cho tải từng đoạn (Range), không thì 0."""
    try:
        with opener.open(urllib.request.Request(url, headers={"User-Agent": UA, "Range": "bytes=0-0"}), timeout=60) as r:
            m = re.search(r"/(\d+)$", r.headers.get("Content-Range") or "")
            return int(m.group(1)) if r.status == 206 and m else 0
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0


def _download(url: str, dst: Path, proxy: str = "") -> None:
    opener = _opener(proxy)
    size = _remote_size(url, opener)
    if size >= PARALLEL_MIN:
        _download_parallel(url, dst, size, opener)
    else:
        _download_single(url, dst, opener)


CHUNK = 16 * 1024 * 1024


def _download_parallel(url: str, dst: Path, size: int, opener) -> None:
    """File chia khúc 16 MB, 4 luồng lần lượt nhận khúc kế tiếp: mỗi kết nối archive.org nhanh chậm rất khác nhau (đo thật: 0,3 đến
    2 MB/giây), chia cứng 4 đoạn thì cả file chờ đoạn chậm nhất. Mỗi khúc một file .partN, chạy lại thì khúc nào đủ là bỏ qua."""
    n = max(PARALLEL, -(-size // CHUNK))
    step = -(-size // n)
    spans = [(i, i * step, min(size, (i + 1) * step) - 1) for i in range(n) if i * step < size]
    parts = [dst.with_name(f"{dst.name}.part{i}") for i, _, _ in spans]
    for old in dst.parent.glob(dst.name + ".part*"):       # khúc của lần chia khác (đổi CHUNK, bản cũ): bỏ
        if old not in parts:
            old.unlink(missing_ok=True)
    stop = threading.Event()
    errors: list[str] = []
    todo = list(spans)
    todo_lock = threading.Lock()

    def have(i: int) -> int:
        return parts[i].stat().st_size if parts[i].exists() else 0

    def worker() -> None:
        while not stop.is_set():
            with todo_lock:
                if not todo:
                    return
                span = todo.pop(0)
            fetch_span(*span)

    def fetch_span(i: int, a: int, b: int) -> None:
        need = b - a + 1
        fails = 0
        while not stop.is_set() and have(i) < need:
            got = have(i)
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Range": f"bytes={a + got}-{b}"})
            try:
                with opener.open(req, timeout=60) as r:
                    if r.status != 206:
                        raise OSError("máy chủ không cho tải từng đoạn")
                    with open(parts[i], "ab") as f:
                        while not stop.is_set():
                            chunk = r.read(256 << 10)       # nhỏ để bấm hủy là dừng ngay cả khi mạng chậm
                            if not chunk:
                                break
                            f.write(chunk)
                fails = 0
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                fails += 1
                if fails > 6:
                    errors.append(str(getattr(e, "reason", e))[:80])
                    stop.set()
                    return
                stop.wait(min(5 * fails, 30))
        if have(i) > need:          # đoạn hỏng (thừa byte): xóa để lần sau tải lại đúng
            parts[i].unlink(missing_ok=True)
            errors.append("đoạn tải bị lệch")
            stop.set()

    threads = [threading.Thread(target=worker, daemon=True) for _ in range(PARALLEL)]
    for t in threads:
        t.start()
    try:
        while any(t.is_alive() for t in threads):
            check_cancel()
            progress("download", sum(have(i) for i in range(len(parts))) / size)
            time.sleep(0.5)
    finally:
        stop.set()
        for t in threads:
            t.join(timeout=70)
    if errors:
        raise FilmError(f"Tải phim bị đứt nhiều lần ({errors[0]}). Bấm chạy lại để tải tiếp từ chỗ dở.")
    tmp = dst.with_name(dst.name + ".join")
    with open(tmp, "wb") as out:
        for p in parts:
            with open(p, "rb") as f:
                while chunk := f.read(8 << 20):
                    out.write(chunk)
    if tmp.stat().st_size != size:
        tmp.unlink(missing_ok=True)
        raise FilmError("File phim tải về không đủ dung lượng. Bấm chạy lại để tải lại.")
    tmp.replace(dst)
    for p in parts:
        p.unlink(missing_ok=True)


def _download_single(url: str, dst: Path, opener) -> None:
    """Tải về dst, đứt mạng thì nối tiếp từ chỗ dở (Range), tối đa 5 lần."""
    part = dst.with_name(dst.name + ".part")
    total = 0
    for attempt in range(6):
        have = part.stat().st_size if part.exists() else 0
        headers = {"User-Agent": UA}
        if have:
            headers["Range"] = f"bytes={have}-"
        try:
            with opener.open(urllib.request.Request(url, headers=headers), timeout=60) as r:
                if have and r.status != 206:          # máy chủ không nối tiếp được: tải lại từ đầu
                    have = 0
                    part.unlink(missing_ok=True)
                size = int(r.headers.get("Content-Length") or 0)
                total = have + size if size else total
                with open(part, "ab" if have else "wb") as f:
                    got = have
                    last = 0.0
                    while True:
                        check_cancel()
                        chunk = r.read(1 << 20)
                        if not chunk:
                            break
                        f.write(chunk)
                        got += len(chunk)
                        if total and time.time() - last > 0.5:
                            progress("download", got / total)
                            last = time.time()
            if total and part.stat().st_size < total:
                raise OSError("tải thiếu")
            part.replace(dst)
            return
        except urllib.error.HTTPError as e:
            if e.code == 416 and part.exists():         # đã đủ byte từ lần trước
                part.replace(dst)
                return
            if e.code < 500 or attempt == 5:
                raise FilmError(f"Internet Archive báo lỗi {e.code} khi tải phim") from None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if attempt == 5:
                raise FilmError(f"Tải phim bị đứt nhiều lần ({str(getattr(e, 'reason', e))[:80]}). Bấm chạy lại để tải tiếp.") from None
        wait = min(5 * (attempt + 1), 30)
        log("download", f"Mạng chập chờn, chờ {wait} giây rồi tải tiếp từ chỗ dở ...")
        for _ in range(wait * 2):
            check_cancel()
            time.sleep(0.5)


def _video_stream(path: Path) -> dict:
    from .util import find_ffmpeg

    _, exe = find_ffmpeg()
    r = subprocess.run([exe, "-v", "error", "-select_streams", "v:0", "-print_format", "json", "-show_streams", str(path)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        s = (json.loads(r.stdout or "{}").get("streams") or [{}])[0]
    except ValueError:
        s = {}
    sar = 1.0
    m = re.fullmatch(r"(\d+):(\d+)", str(s.get("sample_aspect_ratio") or ""))
    if m and int(m.group(1)) and int(m.group(2)):
        sar = int(m.group(1)) / int(m.group(2))
    a = subprocess.run([exe, "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {"codec": s.get("codec_name") or "", "pix_fmt": s.get("pix_fmt") or "", "w": int(s.get("width") or 0),
            "h": int(s.get("height") or 0), "sar": sar, "audio": bool((a.stdout or "").strip()),
            "dur": float(s.get("duration") or 0)}


def finalize_video(dl: Path, out: Path, aspect: float = 0.0, duration: float = 0.0) -> None:
    """File tải về -> source.mp4 mà cả quy trình và trình duyệt (Studio) dùng được: H.264 yuv420p, điểm ảnh vuông, đúng khung.
    File đã chuẩn thì chỉ đổi tên (không mất chất lượng, không tốn thời gian)."""
    s = _video_stream(dl)
    w, h = s["w"], s["h"]
    dar = (w * s["sar"] / h) if w and h else 0.0
    wrong_shape = bool(aspect and dar and abs(dar / aspect - 1) > 0.05)
    square = abs(s["sar"] - 1) < 0.01
    browser_ok = s["codec"] == "h264" and s["pix_fmt"] in ("yuv420p", "yuvj420p")
    if browser_ok and square and not wrong_shape:
        if dl.suffix.lower() in MP4_EXT:
            dl.replace(out)
        else:
            log("download", "Đóng gói lại phim sang MP4 ...")
            ffmpeg(["-i", dl.name, "-map", "0:v:0", "-map", "0:a:0?", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
                    "-movflags", "+faststart", out.name], cwd=dl.parent)
            dl.unlink(missing_ok=True)
        return
    if wrong_shape:
        hh = h - h % 2
        vf = f"scale={int(round(hh * aspect / 2)) * 2}:{hh},setsar=1"
        why = f"sửa khung hình méo ({w}x{h} -> tỉ lệ {aspect:.2f})"
    elif not square:
        vf = "scale=trunc(iw*sar/2)*2:trunc(ih/2)*2,setsar=1"
        why = "đưa điểm ảnh về hình vuông"
    else:
        vf = "scale=trunc(iw/2)*2:trunc(ih/2)*2"
        why = f"chuyển mã {s['codec'] or 'lạ'} sang H.264 để Studio phát được"
    log("download", f"Chuyển phim sang MP4: {why} ...")
    # tiếng ngắn hơn hình (Duck and Cover bản archive.org: hụt 0,45 giây) thì đệm im lặng cho bằng, kiểm định khỏi báo lệch
    # (-shortest cắt không chính xác: đo thật tiếng dài lố 0,9 giây; đệm đúng bằng độ dài hình rồi cắt theo hình)
    pad = ["-af", f"apad=whole_dur={s['dur']:.3f}", "-t", f"{s['dur']:.3f}"] if s["audio"] and s["dur"] else []
    ffmpeg(["-i", dl.name, "-map", "0:v:0", "-map", "0:a:0?", "-vf", vf, *pad, "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out.name], cwd=dl.parent,
           progress_stage="download", total=duration or None)
    dl.unlink(missing_ok=True)


def fetch(url: str, work: Path, cfg, force: bool = False) -> Path:
    """Tải một video của archive.org vào thư mục job (source.mp4 + meta.json, như download.fetch)."""
    from .download import _clear, _write_meta

    ident, want = parse_url(url)
    data = metadata(ident)
    md = data["metadata"]
    lic = check_allowed(ident, md)
    max_h = int(getattr(cfg.download, "max_height", 1080) or 1080)
    vids = videos(data, max_h)
    if not vids:
        raise FilmError("Mục này trên archive.org không có file video tải được")
    v = next((x for x in vids if want and want in (x["key"], x["file"])), None)
    if v is None:
        if want:
            raise FilmError("Không thấy video này trong mục archive.org (có thể đã đổi tên). Chọn lại trong Khám phá > Phim miễn phí.")
        v = vids[0]
        if len(vids) > 1:
            log("download", f"Mục có {len(vids)} video, tải video đầu: {v['label']}. Muốn tập khác, chọn trong Khám phá > Phim miễn phí.")
    title = str((md.get("title")[0] if isinstance(md.get("title"), list) else md.get("title")) or ident)
    if len(vids) > 1:
        title = f"{title} - {v['label']}"
    job = Path(work) / (f"archive_{safe_name(ident, 40)}" + (f"_{short_hash(v['key'])[:6]}" if len(vids) > 1 else ""))
    job.mkdir(parents=True, exist_ok=True)
    if force:
        _clear(job)
    src_url = item_url(ident, v["key"] if len(vids) > 1 else "")
    if not (job / "source.mp4").exists():
        ext = Path(v["file"]).suffix.lower()
        dl = job / f"dl{ext}"
        size = f"{v['size'] / 1e6:.0f} MB" if v["size"] else "?"
        log("download", f"[archive.org] {title[:70]} ({lic['name']}, {size}) ...")
        _download(f"{API}/download/{ident}/{urllib.parse.quote(v['file'])}", dl, getattr(cfg.download, "proxy", "") or "")
        finalize_video(dl, job / "source.mp4", float(v.get("aspect") or 0), float(v.get("duration") or 0))
    if force or not (job / "meta.json").exists():
        year = _year(md)
        creator = _clean_text(md.get("creator"), 120)
        _write_meta(job, {
            "source": src_url, "platform": "archive", "id": ident + (f"/{v['key']}" if len(vids) > 1 else ""),
            "title": title, "description": _clean_text(md.get("description"), 1000), "uploader": creator,
            "license": lic["name"], "license_url": _list(md.get("licenseurl"))[0],
            "credit": credit_line(title, year, creator, lic, item_url(ident)), "year": year,
            "defaults": job_defaults(md),
        })
    return job
