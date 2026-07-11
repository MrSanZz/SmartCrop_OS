import cv2
import numpy as np
from PIL import Image, ImageEnhance
import io, os, math
from typing import Optional, Tuple, List


def pil_to_cv2(img: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)

def cv2_to_pil(cv_img: np.ndarray) -> Image.Image:
    return Image.fromarray(cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB))

def pil_to_bytes(pil_img: Image.Image, fmt: str = "PNG") -> bytes:
    buf = io.BytesIO()
    if fmt.upper() in ("JPG", "JPEG"):
        pil_img.convert("RGB").save(buf, "JPEG", quality=95)
    else:
        pil_img.save(buf, "PNG")
    return buf.getvalue()

def order_points(pts: np.ndarray) -> np.ndarray:
    rect    = np.zeros((4, 2), dtype="float32")
    s       = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff    = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def _resample_contour(contour: np.ndarray, target_pts: int) -> np.ndarray:
    pts = contour.reshape(-1, 2).astype(np.float32)
    n   = len(pts)
    print(pts)
    print(n)
    if n < 2:
        return pts

    diffs = np.diff(pts, axis=0)
    dists = np.sqrt((diffs ** 2).sum(axis=1))
    cum   = np.concatenate([[0.0], np.cumsum(dists)])
    total = cum[-1]
    if total == 0:
        return pts

    sample_lengths = np.linspace(0, total, target_pts, endpoint=False)
    new_pts = np.zeros((target_pts, 2), dtype=np.float32)
    for i, sl in enumerate(sample_lengths):
        idx  = np.searchsorted(cum, sl) - 1
        idx  = int(np.clip(idx, 0, n - 2))
        seg  = cum[idx + 1] - cum[idx]
        t    = (sl - cum[idx]) / seg if seg > 0 else 0.0
        new_pts[i] = pts[idx] * (1 - t) + pts[idx + 1] * t
    print(new_pts)
    return new_pts


def _smooth_polygon(pts: np.ndarray, iterations: int = 3,
                    alpha: float = 0.4) -> np.ndarray:
    p = pts.copy()
    for _ in range(iterations):
        prev_pt  = np.roll(p, 1, axis=0)
        next_pt  = np.roll(p, -1, axis=0)
        p        = p * (1 - alpha) + (prev_pt + next_pt) * (alpha / 2)
    return p


def _edge_map(cv_img: np.ndarray) -> np.ndarray:
    gray  = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    blur3 = cv2.GaussianBlur(gray, (3, 3), 0)
    blur5 = cv2.GaussianBlur(gray, (5, 5), 0)

    c1 = cv2.Canny(blur3, 15, 60)
    c2 = cv2.Canny(blur5, 25, 90)

    sx  = cv2.Sobel(blur5, cv2.CV_64F, 1, 0, ksize=3)
    sy  = cv2.Sobel(blur5, cv2.CV_64F, 0, 1, ksize=3)
    mag = np.sqrt(sx ** 2 + sy ** 2)
    if mag.max() > 0:
        mag = np.uint8(mag / mag.max() * 255)
    _, sob = cv2.threshold(mag, 40, 255, cv2.THRESH_BINARY)

    log_ker = cv2.Laplacian(blur5, cv2.CV_64F)
    log_abs = np.abs(log_ker)
    if log_abs.max() > 0:
        log_u8 = np.uint8(log_abs / log_abs.max() * 255)
    else:
        log_u8 = np.zeros_like(gray)
    _, log_e = cv2.threshold(log_u8, 20, 255, cv2.THRESH_BINARY)

    edges = cv2.bitwise_or(c1, c2)
    edges = cv2.bitwise_or(edges, sob)
    edges = cv2.bitwise_or(edges, log_e)

    edges = cv2.dilate(edges, np.ones((2, 2), np.uint8), iterations=1)
    return edges


def _snap_dense_polygon(pts: np.ndarray, edges: np.ndarray,
                         snap_radius: int = 12) -> np.ndarray:
    H, W = edges.shape
    snapped = pts.copy()
    for i, (px, py) in enumerate(pts):
        px, py = float(px), float(py)
        x1 = max(0, int(px) - snap_radius)
        y1 = max(0, int(py) - snap_radius)
        x2 = min(W, int(px) + snap_radius + 1)
        y2 = min(H, int(py) + snap_radius + 1)
        roi   = edges[y1:y2, x1:x2]
        epts  = np.argwhere(roi > 0)  # (row, col)
        if len(epts):
            dists = np.sqrt((epts[:, 1] - (px - x1)) ** 2 +
                            (epts[:, 0] - (py - y1)) ** 2)
            best = epts[np.argmin(dists)]
            snapped[i] = [x1 + best[1], y1 + best[0]]
    return snapped


def _contour_to_dense_polygon(
    contour:     np.ndarray,
    cv_img:      np.ndarray,
    target_pts:  int = 80,
    snap_r:      int = 8,
    smooth_iter: int = 4,
    smooth_alpha:float = 0.35,
) -> np.ndarray:
    edges = _edge_map(cv_img)
    # 1. Resample merata / Resampling equally
    dense = _resample_contour(contour, target_pts)
    # 2. Pre-smoothing
    dense = _smooth_polygon(dense, iterations=smooth_iter, alpha=smooth_alpha)
    # 3. Edge snap
    dense = _snap_dense_polygon(dense, edges, snap_radius=snap_r)
    # 4. Post-smoothing ringan agar titik snap tidak terlihat kasar / Post smoothing so snapped dot wouldn't look rough
    dense = _smooth_polygon(dense, iterations=2, alpha=0.20)

    return dense.astype(np.float32)

def _quantize_colors(cv_img: np.ndarray,
                     n_clusters: int = 8) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    h, w    = cv_img.shape[:2]
    lab     = cv2.cvtColor(cv_img, cv2.COLOR_BGR2LAB).astype(np.float32)
    pixels  = lab.reshape(-1, 3)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.3)
    _, labels_flat, centers = cv2.kmeans(
        pixels, n_clusters, None, criteria,
        attempts=5, flags=cv2.KMEANS_PP_CENTERS
    )
    labels_2d = labels_flat.reshape(h, w).astype(np.int32)
    counts    = np.bincount(labels_flat.flatten(), minlength=n_clusters)
    return labels_2d, centers, counts


def _build_color_anomaly_mask(
    cv_img:        np.ndarray,
    n_clusters:    int   = 8,
    bg_freq_ratio: float = 0.18,
    min_obj_ratio: float = 0.02,
) -> Tuple[np.ndarray, dict]:
    h, w  = cv_img.shape[:2]
    total = h * w

    labels_2d, centers, counts = _quantize_colors(cv_img, n_clusters)
    freq_ratios  = counts / total
    bg_clusters  = set(np.where(freq_ratios > bg_freq_ratio)[0].tolist())
    obj_clusters = set(
        int(i) for i in np.where(
            (freq_ratios >= min_obj_ratio) & (freq_ratios <= bg_freq_ratio)
        )[0]
    )

    if len(obj_clusters) == 0:
        sorted_by_freq = np.argsort(freq_ratios)
        for idx in sorted_by_freq:
            if freq_ratios[idx] >= min_obj_ratio * 0.5:
                obj_clusters.add(int(idx))
                break

    anomaly_mask = np.zeros((h, w), dtype=np.uint8)
    for c in obj_clusters:
        anomaly_mask[labels_2d == c] = 255

    border_size   = max(8, int(min(h, w) * 0.04))
    border_region = np.zeros((h, w), dtype=bool)
    border_region[:border_size, :]  = True
    border_region[-border_size:, :] = True
    border_region[:, :border_size]  = True
    border_region[:, -border_size:] = True

    border_labels   = labels_2d[border_region]
    border_counts   = np.bincount(border_labels, minlength=n_clusters)
    border_dominant = set(np.where(border_counts > border_counts.sum() * 0.1)[0].tolist())

    confirmed_bg = bg_clusters | border_dominant
    for c in confirmed_bg:
        anomaly_mask[labels_2d == c] = 0
    obj_clusters -= confirmed_bg

    debug_info = {
        "n_clusters":   n_clusters,
        "freq_ratios":  freq_ratios.tolist(),
        "bg_clusters":  list(bg_clusters),
        "obj_clusters": list(obj_clusters),
        "border_bg":    list(border_dominant),
        "centers_lab":  centers.tolist(),
    }
    return anomaly_mask, debug_info


def _saliency_mask(cv_img: np.ndarray) -> np.ndarray:
    try:
        saliency = cv2.saliency.StaticSaliencySpectralResidual_create()
        success, saliency_map = saliency.computeSaliency(cv_img)
        if success:
            sal_u8 = np.uint8(saliency_map * 255)
            _, mask = cv2.threshold(sal_u8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return mask
    except Exception:
        pass
    return np.zeros(cv_img.shape[:2], dtype=np.uint8)


def _watershed_fg_mask(cv_img: np.ndarray) -> np.ndarray:
    gray  = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    blur  = cv2.GaussianBlur(gray, (5, 5), 0)
    _, th = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    ker_d    = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    sure_bg  = cv2.dilate(th, ker_d, iterations=3)
    dist_tf  = cv2.distanceTransform(th, cv2.DIST_L2, 5)
    if dist_tf.max() > 0:
        _, sure_fg = cv2.threshold(dist_tf, 0.4 * dist_tf.max(), 255, 0)
    else:
        sure_fg = th.copy()
    sure_fg = sure_fg.astype(np.uint8)

    unknown = cv2.subtract(sure_bg, sure_fg)

    _, markers = cv2.connectedComponents(sure_fg)
    markers    = markers + 1
    markers[unknown == 255] = 0
    markers    = cv2.watershed(cv_img, markers)

    fg_mask = np.where(markers > 1, 255, 0).astype(np.uint8)
    return fg_mask


def _grabcut_ai_mask(cv_img: np.ndarray,
                     hint_mask: Optional[np.ndarray] = None) -> np.ndarray:
    h, w = cv_img.shape[:2]

    if hint_mask is not None and hint_mask.sum() > 0:
        gc_mask = np.full((h, w), cv2.GC_BGD, dtype=np.uint8)
        gc_mask[hint_mask > 0] = cv2.GC_PR_FGD

        er_sz = max(5, int(min(h, w) * 0.03))
        ker   = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (er_sz, er_sz))
        sure_fg = cv2.erode(hint_mask, ker, iterations=2)
        gc_mask[sure_fg > 0] = cv2.GC_FGD

        border = max(8, int(min(h, w) * 0.03))
        gc_mask[:border, :]  = cv2.GC_BGD
        gc_mask[-border:, :] = cv2.GC_BGD
        gc_mask[:, :border]  = cv2.GC_BGD
        gc_mask[:, -border:] = cv2.GC_BGD

        init_mode = cv2.GC_INIT_WITH_MASK
        rect      = None
    else:
        margin   = int(min(h, w) * 0.05)
        rect     = (margin, margin, w - margin * 2, h - margin * 2)
        gc_mask  = np.zeros((h, w), dtype=np.uint8)
        init_mode = cv2.GC_INIT_WITH_RECT

    bgd_model = np.zeros((1, 65), np.float64)
    fgd_model = np.zeros((1, 65), np.float64)

    try:
        cv2.grabCut(cv_img, gc_mask, rect,
                    bgd_model, fgd_model,
                    8, init_mode)
        result = np.where(
            (gc_mask == cv2.GC_FGD) | (gc_mask == cv2.GC_PR_FGD),
            255, 0
        ).astype(np.uint8)
        return result
    except Exception:
        return hint_mask if hint_mask is not None else np.zeros((h, w), np.uint8)


def _fuse_masks(masks: List[np.ndarray],
                weights: Optional[List[float]] = None) -> np.ndarray:
    if not masks:
        return np.zeros_like(masks[0]) if masks else np.array([])

    if weights is None:
        weights = [1.0] * len(masks)

    h, w    = masks[0].shape
    accum   = np.zeros((h, w), dtype=np.float32)
    total_w = sum(weights)

    for mask, w_val in zip(masks, weights):
        if mask.shape == (h, w) and mask.sum() > 0:
            accum += (mask.astype(np.float32) / 255.0) * w_val

    consensus = (accum / total_w * 255).astype(np.uint8)
    _, final  = cv2.threshold(consensus, 127, 255, cv2.THRESH_BINARY)
    return final


def _clean_anomaly_mask(mask: np.ndarray, img_h: int, img_w: int) -> np.ndarray:
    k_open  = max(5,  int(min(img_h, img_w) * 0.008))
    k_close = max(15, int(min(img_h, img_w) * 0.035))

    ker_o = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k_open,  k_open))
    ker_c = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k_close, k_close))

    m = cv2.morphologyEx(mask, cv2.MORPH_OPEN,  ker_o, iterations=2)
    m = cv2.morphologyEx(m,    cv2.MORPH_CLOSE, ker_c, iterations=3)

    border = max(4, int(min(img_h, img_w) * 0.015))
    m[:border, :]  = 0
    m[-border:, :] = 0
    m[:, :border]  = 0
    m[:, -border:] = 0

    n_lab, labels, stats, _ = cv2.connectedComponentsWithStats(m)
    if n_lab <= 1:
        return m
    areas = stats[1:, cv2.CC_STAT_AREA]
    if len(areas) == 0:
        return m
    best   = 1 + int(np.argmax(areas))
    result = np.where(labels == best, 255, 0).astype(np.uint8)
    return result


def _refine_mask_with_edges(mask: np.ndarray, cv_img: np.ndarray) -> np.ndarray:
    edges = _edge_map(cv_img)

    ker   = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    dilated = cv2.dilate(mask, ker, iterations=2)

    boundary = dilated - cv2.erode(mask, ker, iterations=1)
    edge_on_boundary = cv2.bitwise_and(edges, boundary)

    expanded = mask.copy()
    expanded[edge_on_boundary > 0] = 255

    expanded = cv2.morphologyEx(expanded, cv2.MORPH_CLOSE,
                                 cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11)),
                                 iterations=2)
    return expanded


def _try_cfad_enhanced(cv_img: np.ndarray) -> Tuple[Optional[np.ndarray], str, dict]:
    h, w = cv_img.shape[:2]
    min_area_threshold = (h * w) * 0.02

    cfad_mask = None
    cfad_dbg  = {}
    configs   = [
        (8,  0.18, 0.02),
        (6,  0.20, 0.015),
        (10, 0.15, 0.02),
        (8,  0.25, 0.015),
        (6,  0.30, 0.01),
        (5,  0.35, 0.008),
        (4,  0.40, 0.005),
    ]
    for n_k, bg_r, min_r in configs:
        try:
            raw_mask, dbg = _build_color_anomaly_mask(cv_img, n_k, bg_r, min_r)
            clean_mask    = _clean_anomaly_mask(raw_mask, h, w)
            if clean_mask.sum() // 255 >= min_area_threshold:
                cfad_mask = clean_mask
                cfad_dbg  = dbg
                break
        except Exception:
            continue

    sal_mask = _saliency_mask(cv_img)
    if sal_mask.sum() > 0:
        sal_mask = _clean_anomaly_mask(sal_mask, h, w)

    wt_mask = _watershed_fg_mask(cv_img)
    if wt_mask.sum() > 0:
        wt_mask = _clean_anomaly_mask(wt_mask, h, w)

    valid_masks   = []
    valid_weights = []
    if cfad_mask is not None and cfad_mask.sum() > 0:
        valid_masks.append(cfad_mask);  valid_weights.append(2.5)
    if sal_mask.sum() > 0:
        valid_masks.append(sal_mask);   valid_weights.append(1.5)
    if wt_mask.sum() > 0:
        valid_masks.append(wt_mask);    valid_weights.append(1.0)

    if not valid_masks:
        return None, "failed", {}

    hint_mask = _fuse_masks(valid_masks, valid_weights)
    hint_mask = _clean_anomaly_mask(hint_mask, h, w)

    ai_mask = _grabcut_ai_mask(cv_img, hint_mask)
    if ai_mask.sum() > (h * w) * 0.01:
        ai_mask = _clean_anomaly_mask(ai_mask, h, w)
        final_mask = _fuse_masks([hint_mask, ai_mask], [1.0, 2.0])
    else:
        final_mask = hint_mask

    final_mask = _clean_anomaly_mask(final_mask, h, w)
    final_mask = _refine_mask_with_edges(final_mask, cv_img)
    final_mask = _clean_anomaly_mask(final_mask, h, w)

    if final_mask.sum() // 255 < min_area_threshold:
        return None, "failed", cfad_dbg

    method_str = "cfad-ai-fused"
    if cfad_mask is not None:
        method_str += f"-k{cfad_dbg.get('n_clusters', '?')}"
    return final_mask, method_str, cfad_dbg


def _try_cfad(cv_img: np.ndarray) -> Tuple[Optional[np.ndarray], str, dict]:
    return _try_cfad_enhanced(cv_img)


def _border_color_fallback(cv_img: np.ndarray) -> np.ndarray:
    h, w = cv_img.shape[:2]
    lab  = cv2.cvtColor(cv_img, cv2.COLOR_BGR2LAB).astype(np.float32)
    bdr  = max(12, int(min(h, w) * 0.04))

    border_px = np.concatenate([
        lab[:bdr, :].reshape(-1, 3),
        lab[-bdr:, :].reshape(-1, 3),
        lab[:, :bdr].reshape(-1, 3),
        lab[:, -bdr:].reshape(-1, 3),
    ])
    bg_mean = np.median(border_px, axis=0)
    bg_std  = np.std(border_px, axis=0).clip(6, 35)

    dist = (np.abs(lab - bg_mean) / bg_std).sum(axis=2)
    fg   = (dist > 1.6).astype(np.uint8) * 255

    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    fg  = cv2.morphologyEx(fg, cv2.MORPH_OPEN,  ker, iterations=1)
    fg  = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, ker, iterations=3)

    n_lab, labels, stats, _ = cv2.connectedComponentsWithStats(fg)
    if n_lab > 1:
        best = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        fg   = np.where(labels == best, 255, 0).astype(np.uint8)
    return fg


def _mask_to_dense_polygon(mask: np.ndarray,
                            cv_img: np.ndarray,
                            target_pts: int = 80) -> Optional[np.ndarray]:
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cnts:
        return None
    contour = max(cnts, key=cv2.contourArea)
    pts     = _contour_to_dense_polygon(contour, cv_img, target_pts=target_pts)
    return pts


def _fit_quad_to_mask(mask: np.ndarray,
                       img_w: int, img_h: int) -> Optional[np.ndarray]:
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None
    contour = max(cnts, key=cv2.contourArea)
    peri    = cv2.arcLength(contour, True)
    border  = min(img_w, img_h) * 0.025

    for eps_frac in [0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10, 0.12]:
        approx = cv2.approxPolyDP(contour, eps_frac * peri, True)
        if len(approx) == 4:
            pts = approx.reshape(4, 2).astype("float32")
            if not any(
                x < border or x > img_w - border or
                y < border or y > img_h - border
                for (x, y) in pts
            ):
                return pts
    return None


def _four_point_warp(cv_img: np.ndarray, pts: np.ndarray) -> np.ndarray:
    rect = order_points(pts)
    tl, tr, br, bl = rect
    maxW = max(int(np.linalg.norm(br - bl)), int(np.linalg.norm(tr - tl)))
    maxH = max(int(np.linalg.norm(tr - br)), int(np.linalg.norm(tl - bl)))
    dst  = np.array([[0, 0], [maxW - 1, 0], [maxW - 1, maxH - 1], [0, maxH - 1]],
                    dtype="float32")
    M    = cv2.getPerspectiveTransform(rect, dst)
    return cv2.warpPerspective(cv_img, M, (maxW, maxH))


def _tight_mask_crop(cv_img: np.ndarray, mask: np.ndarray) -> np.ndarray:
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return cv_img
    h, w    = cv_img.shape[:2]
    x, y, bw, bh = cv2.boundingRect(max(cnts, key=cv2.contourArea))
    x  = max(0, x - 2);  y  = max(0, y - 2)
    bw = min(w - x, bw + 4);  bh = min(h - y, bh + 4)
    return cv_img[y:y + bh, x:x + bw]


def auto_crop_document(pil_img: Image.Image) -> Tuple[Image.Image, str]:
    orig_w, orig_h = pil_img.size

    MAX_DETECT = 1500
    scale = min(1.0, MAX_DETECT / max(orig_w, orig_h))
    if scale < 1.0:
        small = pil_img.resize(
            (int(orig_w * scale), int(orig_h * scale)), Image.LANCZOS)
    else:
        small = pil_img

    cv_small = pil_to_cv2(small)
    sh, sw   = cv_small.shape[:2]

    mask_small, method_tag, debug = _try_cfad_enhanced(cv_small)

    if mask_small is None or mask_small.sum() == 0:
        mask_small  = _border_color_fallback(cv_small)
        method_tag  = "fallback-border"

    if scale < 1.0:
        mask_full = cv2.resize(mask_small, (orig_w, orig_h),
                               interpolation=cv2.INTER_NEAREST)
        ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask_full = cv2.morphologyEx(mask_full, cv2.MORPH_CLOSE, ker, iterations=2)
    else:
        mask_full = mask_small

    cv_full = pil_to_cv2(pil_img)
    quad    = _fit_quad_to_mask(mask_full, orig_w, orig_h)

    if quad is not None:
        warped = _four_point_warp(cv_full, quad)
        result = cv2_to_pil(warped)
        return result, "warp"

    cropped = _tight_mask_crop(cv_full, mask_full)
    if cropped.shape[0] > 20 and cropped.shape[1] > 20:
        return cv2_to_pil(cropped), "tight"

    bx = int(orig_w * 0.07);  by = int(orig_h * 0.07)
    return cv2_to_pil(cv_full[by:orig_h - by, bx:orig_w - bx]), "fallback"


def get_cfad_debug_overlay(pil_img: Image.Image) -> Image.Image:
    orig_w, orig_h = pil_img.size
    MAX_DETECT     = 10000
    scale = min(1.0, MAX_DETECT / max(orig_w, orig_h))
    small = (pil_img.resize((int(orig_w * scale), int(orig_h * scale)), Image.LANCZOS)
             if scale < 1.0 else pil_img)
    cv_s  = pil_to_cv2(small)

    mask, _, _ = _try_cfad_enhanced(cv_s)
    if mask is None:
        mask = _border_color_fallback(cv_s)

    if scale < 1.0:
        mask = cv2.resize(mask, (orig_w, orig_h),
                          interpolation=cv2.INTER_NEAREST)

    cv_full = pil_to_cv2(pil_img)
    dense_pts = _mask_to_dense_polygon(mask, cv_full, target_pts=80)

    cnts, _  = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    overlay  = cv_full.copy()
    cv2.drawContours(overlay, cnts, -1, (0, 255, 0), 3)

    tint       = overlay.copy()
    tint[mask > 0] = (tint[mask > 0] * 0.6 +
                      np.array([0, 0, 180]) * 0.4).astype(np.uint8)
    result     = cv2.addWeighted(overlay, 0.7, tint, 0.3, 0)

    if dense_pts is not None and len(dense_pts) > 2:
        pts_i32 = dense_pts.astype(np.int32)
        cv2.polylines(result, [pts_i32], True, (0, 255, 255), 2)
        for pt in pts_i32[::max(1, len(pts_i32) // 40)]:
            cv2.circle(result, tuple(pt), 4, (0, 200, 255), -1)

    quad = _fit_quad_to_mask(mask, orig_w, orig_h)
    if quad is not None:
        pts = quad.astype(np.int32)
        cv2.polylines(result, [pts], True, (0, 165, 255), 3)
        for pt in pts:
            cv2.circle(result, tuple(pt), 10, (0, 120, 255), -1)

    return cv2_to_pil(result)

def snap_points_to_edges(pil_img: Image.Image,
                          pts: np.ndarray,
                          radius: int = 28) -> np.ndarray:
    cv_img = pil_to_cv2(pil_img)
    edges  = _edge_map(cv_img)
    H, W   = edges.shape
    snapped = pts.copy()
    for i, (px, py) in enumerate(pts):
        x1 = max(0, int(px) - radius);  y1 = max(0, int(py) - radius)
        x2 = min(W, int(px) + radius);  y2 = min(H, int(py) + radius)
        roi  = edges[y1:y2, x1:x2]
        epts = np.argwhere(roi > 0)
        if len(epts):
            dists = np.sqrt((epts[:, 1] - (px - x1)) ** 2 +
                            (epts[:, 0] - (py - y1)) ** 2)
            best  = epts[np.argmin(dists)]
            snapped[i] = [x1 + best[1], y1 + best[0]]
    return snapped


def _expand_polygon_to_dense(
    user_pts:    np.ndarray,
    cv_img:      np.ndarray,
    target_pts:  int  = 80,
    snap_r:      int  = 10,
) -> np.ndarray:
    h, w  = cv_img.shape[:2]
    pts_i = user_pts.astype(np.int32)

    rough_mask = np.zeros((h, w), dtype=np.uint8)
    cv2.fillPoly(rough_mask, [pts_i], 255)

    gc_mask = _grabcut_ai_mask(cv_img, rough_mask)
    if gc_mask.sum() > (h * w) * 0.005:
        refined = _fuse_masks([rough_mask, gc_mask], [1.5, 1.0])
        refined = _clean_anomaly_mask(refined, h, w)
        refined = _refine_mask_with_edges(refined, cv_img)
        refined = _clean_anomaly_mask(refined, h, w)
    else:
        refined = rough_mask

    cnts, _ = cv2.findContours(refined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cnts:
        dense = _resample_contour(pts_i, target_pts)
        dense = _smooth_polygon(dense, iterations=3)
        return dense.astype(np.float32)

    contour = max(cnts, key=cv2.contourArea)
    dense   = _contour_to_dense_polygon(
        contour, cv_img,
        target_pts   = target_pts,
        snap_r       = snap_r,
        smooth_iter  = 4,
        smooth_alpha = 0.35,
    )
    return dense


def manual_polygon_crop(
    pil_img:        Image.Image,
    polygon_points: list,
    apply_enhance:  bool = True,
    enhance_params: dict = None,
    use_grabcut:    bool = True,
) -> Image.Image:
    if len(polygon_points) < 3:
        raise ValueError("The minimum is 3 pts.")

    pts    = np.array(polygon_points, dtype=np.float32)
    cv_img = pil_to_cv2(pil_img)
    h, w   = cv_img.shape[:2]
    pts[:, 0] = np.clip(pts[:, 0], 0, w - 1)
    pts[:, 1] = np.clip(pts[:, 1], 0, h - 1)

    if len(pts) == 4:
        warped = _four_point_warp(cv_img, pts)
        result = cv2_to_pil(warped)
        if apply_enhance and enhance_params:
            result = enhance_image(result, **enhance_params)
        return result

    perimeter_est = cv2.arcLength(pts.astype(np.int32), True)
    target_pts    = max(60, min(120, int(perimeter_est / max(w, h) * 150)))

    dense_pts = _expand_polygon_to_dense(
        pts, cv_img,
        target_pts = target_pts,
        snap_r     = max(6, int(min(h, w) * 0.008)),
    )

    dp_i32  = dense_pts.astype(np.int32)
    mask_d  = np.zeros((h, w), dtype=np.uint8)
    cv2.fillPoly(mask_d, [dp_i32], 255)

    if use_grabcut and mask_d.sum() > 0:
        gc_final = _grabcut_ai_mask(cv_img, mask_d)
        if gc_final.sum() > (h * w) * 0.005:
            mask_d = _fuse_masks([mask_d, gc_final], [1.0, 1.5])
            mask_d = _clean_anomaly_mask(mask_d, h, w)

    mask_d = _refine_mask_with_edges(mask_d, cv_img)
    mask_d = _clean_anomaly_mask(mask_d, h, w)

    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask_d)
    if n > 1:
        best   = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        mask_d = np.where(labels == best, 255, 0).astype(np.uint8)

    out = cv_img.copy()
    out[mask_d == 0] = 255

    cnts, _ = cv2.findContours(mask_d, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if cnts:
        x, y, bw, bh = cv2.boundingRect(max(cnts, key=cv2.contourArea))
        x  = max(0, x);  y  = max(0, y)
        bw = min(w - x, bw);  bh = min(h - y, bh)
        out = out[y:y + bh, x:x + bw]

    result = cv2_to_pil(out)
    if apply_enhance and enhance_params:
        result = enhance_image(result, **enhance_params)
    return result


def enhance_image(
    pil_img:    Image.Image,
    brightness: float = 1.05,
    contrast:   float = 1.3,
    sharpness:  float = 1.8,
    saturation: float = 1.1,
    denoise:    bool  = True,
    clahe:      bool  = True,
) -> Image.Image:
    cv_img = pil_to_cv2(pil_img.convert("RGB"))

    if denoise:
        cv_img = cv2.fastNlMeansDenoisingColored(cv_img, None, 6, 6, 7, 21)

    if clahe:
        lab     = cv2.cvtColor(cv_img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l       = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8)).apply(l)
        cv_img  = cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)

    r = cv2_to_pil(cv_img)
    r = ImageEnhance.Brightness(r).enhance(brightness)
    r = ImageEnhance.Contrast(r).enhance(contrast)
    r = ImageEnhance.Sharpness(r).enhance(sharpness)
    r = ImageEnhance.Color(r).enhance(saturation)
    return r


def remove_background(pil_img: Image.Image, model: str = "u2net") -> Image.Image:
    try:
        from rembg import remove, new_session
        return remove(pil_img, session=new_session(model))
    except ImportError:
        return _grabcut_rembg(pil_img)


def _grabcut_rembg(pil_img: Image.Image) -> Image.Image:
    cv_img = pil_to_cv2(pil_img)
    h, w   = cv_img.shape[:2]
    mask   = np.zeros((h, w), np.uint8)
    mx, my = int(w * .05), int(h * .05)
    cv2.grabCut(cv_img, mask, (mx, my, w - mx * 2, h - my * 2),
                np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64),
                10, cv2.GC_INIT_WITH_RECT)
    m2   = np.where((mask == 2) | (mask == 0), 0, 255).astype("uint8")
    m2   = cv2.GaussianBlur(m2, (5, 5), 0)
    rgba = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGBA)
    rgba[:, :, 3] = m2
    return Image.fromarray(rgba, "RGBA")


def upscale_image(pil_img: Image.Image, scale: float = 2.0) -> Image.Image:
    return pil_img.resize(
        (int(pil_img.width * scale), int(pil_img.height * scale)),
        Image.LANCZOS)


def save_image(pil_img: Image.Image, path: str, dpi: int = 300):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".jpg", ".jpeg"):
        pil_img.convert("RGB").save(path, "JPEG", quality=95, dpi=(dpi, dpi))
    else:
        pil_img.save(path, dpi=(dpi, dpi))
