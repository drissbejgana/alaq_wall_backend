"""
╔══════════════════════════════════════════════════════════════════════╗
║  OpenCV Floor Texture Renderer                                       ║
║                                                                      ║
║  Production-grade rendering pipeline using OpenCV's native C++       ║
║  routines for perspective warp, color transfer, and Poisson blend.   ║
║                                                                      ║
║  Pipeline:                                                           ║
║   1. Mask: cv2.fillPoly from YOLO polygon                           ║
║   2. Quad: cv2.approxPolyDP → convex hull → 4-corner extraction     ║
║   3. Tile: numpy tiling at requested scale                           ║
║   4. Warp: cv2.warpPerspective with Lanczos interpolation           ║
║   5. Color: LAB-space Reinhard transfer (match room lighting)        ║
║   6. Shadows: luminance ratio map from original floor                ║
║   7. Blend: cv2.seamlessClone (Poisson) + feathered alpha fallback  ║
║   8. AO: distance-transform-based darkening near edges              ║
╚══════════════════════════════════════════════════════════════════════╝
"""
import logging
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
#  Step 1: Build binary mask from polygon points
# ═══════════════════════════════════════════════════════════

def build_mask(
    polygons: list[list[dict]],
    img_h: int,
    img_w: int,
) -> np.ndarray:
    """
    Create a binary uint8 mask from one or more YOLO polygons.
    Each polygon is a list of {"x": float, "y": float} dicts.
    """
    mask = np.zeros((img_h, img_w), dtype=np.uint8)
    for poly in polygons:
        pts = np.array([[p["x"], p["y"]] for p in poly], dtype=np.int32)
        cv2.fillPoly(mask, [pts], 255)
    return mask


def feather_mask(mask: np.ndarray, radius: int = 5) -> np.ndarray:
    """Gaussian-blur the mask edges for soft blending."""
    if radius <= 0:
        return mask
    k = radius * 2 + 1
    return cv2.GaussianBlur(mask, (k, k), 0)


# ═══════════════════════════════════════════════════════════
#  Step 2: Extract perspective quad from polygon
# ═══════════════════════════════════════════════════════════

def extract_quad(polygons: list[list[dict]], img_h: int, img_w: int) -> np.ndarray:
    """
    Extract 4-corner perspective quad from floor polygon(s).

    Uses cv2.approxPolyDP (Ramer-Douglas-Peucker) to simplify,
    then finds the 4 convex hull vertices closest to the
    bounding box corners — these define the floor trapezoid.

    Returns shape (4, 2) float32: [TL, TR, BR, BL] in image coords.
    """
    # Combine all polygon points
    all_pts = []
    for poly in polygons:
        all_pts.extend([[p["x"], p["y"]] for p in poly])
    pts = np.array(all_pts, dtype=np.float32)

    # Simplify with RDP (OpenCV's built-in)
    hull = cv2.convexHull(pts.reshape(-1, 1, 2))
    hull = hull.reshape(-1, 2)

    # Bounding box corners
    x_min, y_min = hull.min(axis=0)
    x_max, y_max = hull.max(axis=0)

    target_corners = np.array([
        [x_min, y_min],  # TL
        [x_max, y_min],  # TR
        [x_max, y_max],  # BR
        [x_min, y_max],  # BL
    ], dtype=np.float32)

    # For each target corner, find the closest hull vertex
    quad = np.zeros((4, 2), dtype=np.float32)
    used = set()
    for i, target in enumerate(target_corners):
        dists = np.linalg.norm(hull - target, axis=1)
        sorted_indices = np.argsort(dists)
        for idx in sorted_indices:
            if idx not in used:
                quad[i] = hull[idx]
                used.add(idx)
                break

    return quad  # [TL, TR, BR, BL]


# ═══════════════════════════════════════════════════════════
#  Step 3: Tile texture to target size
# ═══════════════════════════════════════════════════════════

def tile_texture(
    texture: np.ndarray,
    target_w: int,
    target_h: int,
    scale: float = 0.35,
    rotation: int = 0,
) -> np.ndarray:
    """
    Tile a texture image to fill target_w × target_h.
    Scale controls tile size. Rotation in degrees (0/90/180/270).
    """
    tex = texture.copy()

    # Rotate texture tile
    if rotation == 90:
        tex = cv2.rotate(tex, cv2.ROTATE_90_CLOCKWISE)
    elif rotation == 180:
        tex = cv2.rotate(tex, cv2.ROTATE_180)
    elif rotation == 270:
        tex = cv2.rotate(tex, cv2.ROTATE_90_COUNTERCLOCKWISE)

    # Scale tile size
    th, tw = tex.shape[:2]
    tile_w = max(1, int(tw * scale))
    tile_h = max(1, int(th * scale))
    tex = cv2.resize(tex, (tile_w, tile_h), interpolation=cv2.INTER_AREA)

    # Tile to fill target
    reps_x = (target_w // tile_w) + 2
    reps_y = (target_h // tile_h) + 2
    tiled = np.tile(tex, (reps_y, reps_x, 1))
    tiled = tiled[:target_h, :target_w]

    return tiled


# ═══════════════════════════════════════════════════════════
#  Step 4: Perspective warp
# ═══════════════════════════════════════════════════════════

def warp_texture_to_floor(
    tiled: np.ndarray,
    quad: np.ndarray,
    img_h: int,
    img_w: int,
) -> np.ndarray:
    """
    Warp the flat tiled texture into the floor's perspective shape.

    Uses cv2.getPerspectiveTransform to compute the 3×3 homography
    and cv2.warpPerspective with Lanczos interpolation.
    """
    th, tw = tiled.shape[:2]

    # Source: corners of the tiled texture rectangle
    src = np.array([
        [0, 0],       # TL
        [tw, 0],      # TR
        [tw, th],     # BR
        [0, th],      # BL
    ], dtype=np.float32)

    # Destination: floor quad corners
    dst = quad.astype(np.float32)

    M = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(
        tiled, M, (img_w, img_h),
        flags=cv2.INTER_LANCZOS4,
        borderMode=cv2.BORDER_REFLECT_101,
    )
    return warped


# ═══════════════════════════════════════════════════════════
#  Step 5: LAB color transfer (Reinhard method)
# ═══════════════════════════════════════════════════════════

def lab_color_transfer(
    source: np.ndarray,
    target: np.ndarray,
    mask: np.ndarray,
    strength: float = 0.7,
) -> np.ndarray:
    """
    Transfer the color statistics of the target (floor region of room)
    onto the source (warped texture), in LAB space.

    This makes the texture match the room's overall lighting and color cast.
    Strength 0-1 controls how much adaptation to apply.
    """
    source_lab = cv2.cvtColor(source, cv2.COLOR_BGR2LAB).astype(np.float64)
    target_lab = cv2.cvtColor(target, cv2.COLOR_BGR2LAB).astype(np.float64)

    mask_bool = mask > 127

    # Compute stats on masked regions
    src_pixels = source_lab[mask_bool]
    tgt_pixels = target_lab[mask_bool]

    if len(src_pixels) < 100 or len(tgt_pixels) < 100:
        return source

    src_mean = src_pixels.mean(axis=0)
    src_std = src_pixels.std(axis=0) + 1e-6
    tgt_mean = tgt_pixels.mean(axis=0)
    tgt_std = tgt_pixels.std(axis=0) + 1e-6

    # Transfer: shift and scale each channel
    result_lab = source_lab.copy()
    for c in range(3):
        channel = result_lab[:, :, c]
        transferred = (channel - src_mean[c]) * (tgt_std[c] / src_std[c]) + tgt_mean[c]
        # Blend with original based on strength
        result_lab[:, :, c] = channel * (1 - strength) + transferred * strength

    result_lab = np.clip(result_lab, 0, 255).astype(np.uint8)
    return cv2.cvtColor(result_lab, cv2.COLOR_LAB2BGR)


# ═══════════════════════════════════════════════════════════
#  Step 6: Shadow / lighting preservation
# ═══════════════════════════════════════════════════════════

def preserve_shadows(
    textured: np.ndarray,
    original: np.ndarray,
    mask: np.ndarray,
    strength: float = 0.85,
) -> np.ndarray:
    """
    Preserve the original floor's lighting patterns (shadows, reflections,
    light gradients) by transferring its luminance ratios onto the texture.

    1. Extract luminance of original floor
    2. Compute local average via heavy blur → ratio map
    3. Multiply texture luminance by ratio map
    """
    if strength <= 0:
        return textured

    # Convert to float
    orig_gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY).astype(np.float64)
    mask_f = (mask.astype(np.float64) / 255.0)

    # Heavy blur for "flat" floor lighting (what it would look like without shadows)
    flat_lum = cv2.GaussianBlur(orig_gray, (0, 0), sigmaX=40)
    flat_lum = np.maximum(flat_lum, 1.0)  # avoid division by zero

    # Ratio: how much each pixel deviates from the flat lighting
    # Values < 1 = shadows, > 1 = highlights
    ratio = orig_gray / flat_lum
    ratio = np.clip(ratio, 0.2, 2.5)

    # Apply with strength
    shadow_map = 1.0 + (ratio - 1.0) * strength

    # Apply to texture in LAB space (only L channel)
    tex_lab = cv2.cvtColor(textured, cv2.COLOR_BGR2LAB).astype(np.float64)
    tex_lab[:, :, 0] = np.clip(tex_lab[:, :, 0] * shadow_map, 0, 255)
    tex_lab = np.clip(tex_lab, 0, 255).astype(np.uint8)

    return cv2.cvtColor(tex_lab, cv2.COLOR_LAB2BGR)


# ═══════════════════════════════════════════════════════════
#  Step 7: Ambient occlusion near edges
# ═══════════════════════════════════════════════════════════

def apply_ambient_occlusion(
    image: np.ndarray,
    mask: np.ndarray,
    strength: float = 0.5,
    radius: int = 30,
) -> np.ndarray:
    """
    Darken pixels near floor-wall edges to simulate ambient occlusion.
    Uses distance transform for smooth falloff.
    """
    if strength <= 0:
        return image

    # Distance from each pixel to nearest mask edge
    dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5).astype(np.float64)
    dist = np.clip(dist / radius, 0, 1)

    # AO factor: 1 at center (no darkening), < 1 near edges
    ao = 1.0 - strength * 0.4 * (1.0 - dist * dist)
    ao = ao[:, :, np.newaxis]

    result = (image.astype(np.float64) * ao)
    return np.clip(result, 0, 255).astype(np.uint8)


# ═══════════════════════════════════════════════════════════
#  Step 8: Composite with seamlessClone or alpha blending
# ═══════════════════════════════════════════════════════════

def composite_seamless(
    room: np.ndarray,
    textured: np.ndarray,
    mask: np.ndarray,
) -> np.ndarray:
    """
    Use OpenCV's seamlessClone (Poisson blending) for edge-free compositing.
    Falls back to alpha blending if seamlessClone fails.
    """
    try:
        # seamlessClone needs a center point
        moments = cv2.moments(mask)
        if moments["m00"] > 0:
            cx = int(moments["m10"] / moments["m00"])
            cy = int(moments["m01"] / moments["m00"])
        else:
            h, w = mask.shape
            cx, cy = w // 2, h // 2

        # Ensure the textured region fully covers the mask
        # seamlessClone can fail if the source doesn't cover the mask region
        result = cv2.seamlessClone(
            textured, room, mask,
            (cx, cy),
            cv2.MIXED_CLONE,
        )
        return result
    except Exception as e:
        logger.warning(f"seamlessClone failed ({e}), falling back to alpha blending")
        return composite_alpha(room, textured, mask)


def composite_alpha(
    room: np.ndarray,
    textured: np.ndarray,
    mask: np.ndarray,
) -> np.ndarray:
    """Simple alpha blending with feathered mask."""
    alpha = feather_mask(mask, radius=8).astype(np.float64) / 255.0
    alpha = alpha[:, :, np.newaxis]
    result = room.astype(np.float64) * (1 - alpha) + textured.astype(np.float64) * alpha
    return np.clip(result, 0, 255).astype(np.uint8)


# ═══════════════════════════════════════════════════════════
#  AUTO-DETECT PARAMETERS
#  Analyzes room image + floor mask to compute optimal settings
# ═══════════════════════════════════════════════════════════

def auto_detect_params(
    room_bgr: np.ndarray,
    mask: np.ndarray,
) -> dict:
    """
    Analyze the room image and floor mask to compute rendering parameters.

    Returns dict with: scale, edge_blend, shadow_strength,
    color_transfer_strength, ao_strength, brightness_shift
    """
    h, w = room_bgr.shape[:2]
    mask_bool = mask > 127

    # Floor area ratio
    floor_pixels = mask_bool.sum()
    total_pixels = h * w
    area_ratio = floor_pixels / total_pixels

    # Luminance stats of floor region
    gray = cv2.cvtColor(room_bgr, cv2.COLOR_BGR2GRAY)
    floor_lum = gray[mask_bool]
    if len(floor_lum) < 50:
        return _default_params()

    mean_lum = float(floor_lum.mean())
    std_lum = float(floor_lum.std())

    # Texture scale: larger floors → smaller tiles
    if area_ratio > 0.4:
        scale = 0.25
    elif area_ratio > 0.25:
        scale = 0.35
    elif area_ratio > 0.15:
        scale = 0.45
    else:
        scale = 0.55

    # Shadow preservation: high contrast → stronger
    shadow_strength = min(0.95, 0.5 + (std_lum / 60) * 0.4)

    # Edge blend: more pixels on mask boundary → more feathering needed
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    perimeter = sum(cv2.arcLength(c, True) for c in contours)
    # Jaggedness: perimeter relative to sqrt(area)
    jaggedness = perimeter / (np.sqrt(floor_pixels) + 1) if floor_pixels > 0 else 0
    edge_blend = int(np.clip(jaggedness * 0.8, 3, 15))

    # AO: always moderate-to-strong
    ao_strength = 0.5

    # Color transfer: moderate (too strong washes out the texture)
    color_strength = 0.65

    # Brightness adjustment
    if mean_lum < 80:
        brightness = -10
    elif mean_lum > 180:
        brightness = 10
    else:
        brightness = 0

    return {
        "scale": round(scale, 2),
        "edge_blend": edge_blend,
        "shadow_strength": round(shadow_strength, 2),
        "color_transfer_strength": round(color_strength, 2),
        "ao_strength": round(ao_strength, 2),
        "brightness_shift": brightness,
    }


def _default_params():
    return {
        "scale": 0.35,
        "edge_blend": 6,
        "shadow_strength": 0.75,
        "color_transfer_strength": 0.65,
        "ao_strength": 0.5,
        "brightness_shift": 0,
    }


# ═══════════════════════════════════════════════════════════
#  MAIN RENDER FUNCTION
# ═══════════════════════════════════════════════════════════

def render_floor(
    room_image: np.ndarray,
    texture_image: np.ndarray,
    polygons: list[list[dict]],
    scale: Optional[float] = None,
    rotation: int = 0,
    blend_mode: str = "seamless",
    # These are auto-detected if not provided:
    shadow_strength: Optional[float] = None,
    color_transfer_strength: Optional[float] = None,
    ao_strength: Optional[float] = None,
    edge_blend: Optional[int] = None,
    brightness_shift: Optional[int] = None,
) -> np.ndarray:
    """
    Full rendering pipeline. Takes room image + texture + floor polygons,
    returns the composited result image.

    Parameters
    ----------
    room_image : BGR uint8 array (H, W, 3)
    texture_image : BGR uint8 array (any size, will be tiled)
    polygons : list of polygon point lists from YOLO
    scale : texture tile scale (None = auto-detect)
    rotation : 0, 90, 180, 270
    blend_mode : "seamless" (Poisson) or "alpha"
    """
    img_h, img_w = room_image.shape[:2]
    room = room_image.copy()

    logger.info(f"Rendering: {img_w}x{img_h}, {len(polygons)} polygon(s), "
                f"scale={scale}, rotation={rotation}")

    # ── 1. Build mask ──
    mask = build_mask(polygons, img_h, img_w)
    if mask.sum() == 0:
        logger.warning("Empty mask — returning original image")
        return room

    # ── Auto-detect params ──
    auto = auto_detect_params(room, mask)
    if scale is None:
        scale = auto["scale"]
    if shadow_strength is None:
        shadow_strength = auto["shadow_strength"]
    if color_transfer_strength is None:
        color_transfer_strength = auto["color_transfer_strength"]
    if ao_strength is None:
        ao_strength = auto["ao_strength"]
    if edge_blend is None:
        edge_blend = auto["edge_blend"]
    if brightness_shift is None:
        brightness_shift = auto["brightness_shift"]

    logger.info(f"Params: scale={scale}, shadow={shadow_strength}, "
                f"color={color_transfer_strength}, ao={ao_strength}, "
                f"edge_blend={edge_blend}, brightness={brightness_shift}")

    # ── 2. Extract perspective quad ──
    quad = extract_quad(polygons, img_h, img_w)

    # Compute bounding box of quad for tiled texture sizing
    quad_bb_w = int(np.max(quad[:, 0]) - np.min(quad[:, 0]))
    quad_bb_h = int(np.max(quad[:, 1]) - np.min(quad[:, 1]))
    # Over-size the tiled texture to prevent gaps after warp
    tile_w = max(quad_bb_w * 2, img_w)
    tile_h = max(quad_bb_h * 2, img_h)

    # ── 3. Tile texture ──
    tiled = tile_texture(texture_image, tile_w, tile_h, scale, rotation)

    # ── 4. Perspective warp ──
    warped = warp_texture_to_floor(tiled, quad, img_h, img_w)

    # ── 5. Brightness adjustment ──
    if brightness_shift != 0:
        warped_lab = cv2.cvtColor(warped, cv2.COLOR_BGR2LAB).astype(np.int16)
        warped_lab[:, :, 0] = np.clip(warped_lab[:, :, 0] + brightness_shift, 0, 255)
        warped = cv2.cvtColor(warped_lab.astype(np.uint8), cv2.COLOR_LAB2BGR)

    # ── 6. LAB color transfer ──
    warped = lab_color_transfer(warped, room, mask, color_transfer_strength)

    # ── 7. Shadow preservation ──
    warped = preserve_shadows(warped, room, mask, shadow_strength)

    # ── 8. Ambient occlusion ──
    warped = apply_ambient_occlusion(warped, mask, ao_strength)

    # ── 9. Composite ──
    if blend_mode == "seamless":
        result = composite_seamless(room, warped, mask)
    else:
        soft_mask = feather_mask(mask, radius=edge_blend)
        result = composite_alpha(room, warped, soft_mask)

    # ── 10. Final pass: also do alpha blend with feathered edges ──
    # seamlessClone handles interior well but sometimes the outer
    # boundary needs extra softening
    if blend_mode == "seamless" and edge_blend > 0:
        soft_mask = feather_mask(mask, radius=edge_blend)
        # Blend seamless result with original at edges only
        eroded = cv2.erode(mask, np.ones((edge_blend * 2, edge_blend * 2), np.uint8))
        edge_zone = soft_mask.astype(np.float64) / 255.0
        edge_only = (1.0 - eroded.astype(np.float64) / 255.0) * edge_zone
        edge_only = edge_only[:, :, np.newaxis]
        # Where edge_only > 0, blend result with alpha-blended version
        alpha_result = composite_alpha(room, warped, soft_mask)
        result = (result.astype(np.float64) * (1 - edge_only) +
                  alpha_result.astype(np.float64) * edge_only)
        result = np.clip(result, 0, 255).astype(np.uint8)

    return result