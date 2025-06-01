import os
import cv2
import requests
import pandas as pd
import numpy as np
from urllib.parse import urlparse

WATERMARK_TEXT      = '3D_Print'
WATERMARK_OPACITY   = 0.3       # 0.0 transparent, 1.0 opaque
WATERMARK_THICKNESS = 2
BORDER_COLOR        = (228, 100, 0)    # blue border (BGR)
BORDER_THICKNESS    = 10
WATERMARK_OPACITY   = 0.25            # 25% opacity
FONT                = cv2.FONT_HERSHEY_SIMPLEX


def ensure_dir(path: str):
    """Create directory if it doesn’t exist"""
    os.makedirs(path, exist_ok=True)


def load_code_image_urls(excel_path: str, sheet_name: str, code_col: str, image_col: str) -> list:
    """
    Read the Excel sheet and return a list of (code, image_url) tuples.
    """
    sheets = pd.read_excel(excel_path, sheet_name=None)
    df = sheets[sheet_name]
    # Drop rows where either code or image url is missing
    df = df[[code_col, image_col]].dropna(subset=[code_col, image_col])
    return list(df.itertuples(index=False, name=None))


def download_image(url: str, out_dir: str) -> str:
    """Download an image and return its saved filename (or '' on failure)"""
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except Exception as e:
        print(f"✗ Failed to download {url!r}: {e}")
        return ''
    fname = os.path.basename(urlparse(url).path) or 'image.jpg'
    save_path = os.path.join(out_dir, fname)
    with open(save_path, 'wb') as f:
        f.write(resp.content)
    print(f"Downloaded {fname} to {out_dir}")
    return fname


def add_border_and_watermark(in_path: str, out_path: str):
    """Load an image, add a border, overlay a semi-transparent diagonal watermark, and save it"""
    img = cv2.imread(in_path)
    if img is None:
        print(f"✗ Could not read {in_path}")
        return

    h, w = img.shape[:2]
    # 1) add colored border
    bordered = cv2.copyMakeBorder(
        img,
        top=BORDER_THICKNESS, bottom=BORDER_THICKNESS,
        left=BORDER_THICKNESS, right=BORDER_THICKNESS,
        borderType=cv2.BORDER_CONSTANT,
        value=BORDER_COLOR
    )
    bh, bw = bordered.shape[:2]  # border width/height

    # 2) create transparent overlay for watermark
    # overlay = cv2.cvtColor(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
    # overlay[:] = (0, 0, 0)  # make fully black/transparent overlay

    # create blank mask for text
    text_mask = np.zeros((bh, bw, 3), dtype=np.uint8)

    # compute text scale
    (text_w, text_h), baseline = cv2.getTextSize(WATERMARK_TEXT, FONT, 1.0, WATERMARK_THICKNESS)
    scale = (w / 2) / text_w

    # We want text centered inside the bordered area
    # let’s recompute size at final scale
    (scaled_w, scaled_h), _ = cv2.getTextSize(WATERMARK_TEXT, FONT, scale, WATERMARK_THICKNESS)

    # center of bordered image:
    cx, cy = bw // 2, bh // 2

    # top‐left corner so that text is centered:
    org_x = int(cx - (scaled_w / 2))
    # for y, popenCV putText uses the _baseline_ of text, so we add scaled_h
    org_y = int(cy + (scaled_h / 2))

    # position at roughly one-quarter down from top, one-quarter in from left
    org = (int((w + 2*BORDER_THICKNESS - text_w*scale) / 2),
           int((h + 2*BORDER_THICKNESS + text_h*scale) / 2))

    # put text onto text_mask
    cv2.putText(
        text_mask,
        WATERMARK_TEXT,
        (org_x, org_y),
        FONT,
        scale,
        (255, 255, 255),
        thickness=WATERMARK_THICKNESS,
        lineType=cv2.LINE_AA
    )

    # rotate text 45° for diagonal effect
    M = cv2.getRotationMatrix2D(
        (cx, cy),      # rotate around the center of the bordered image
        angle=-45,     # 45° diagonal
        scale=1.0
    )
    rotated_mask = cv2.warpAffine(text_mask, M, (bw, bh),
                                  flags=cv2.INTER_LINEAR,
                                  borderMode=cv2.BORDER_CONSTANT,
                                  borderValue=(0, 0, 0))

    output = bordered.copy()

    # Convert rotated mask to gray so we can threshold it
    gray_mask = cv2.cvtColor(rotated_mask, cv2.COLOR_BGR2GRAY)

    # werever gray_mask > 0, we know that pixel belongs to the text
    # we’ll normalize gray_mask to [0–1], then blend only those pixels
    alpha_mask = (gray_mask.astype(np.float32) / 255.0) * WATERMARK_OPACITY

    # blend
    for c in range(3):
        orig_chan = output[:, :, c].astype(np.float32)
        # wherever the mask is nonzero (i.e. text), blend white (255) with original
        blended_chan = alpha_mask * 255 + (1 - alpha_mask) * orig_chan
        # wherever mask == 0, alpha_mask is 0 → blended_chan == orig_chan → unchanged
        output[:, :, c] = blended_chan.clip(0, 255).astype(np.uint8)


    cv2.imwrite(out_path, output)
    print(f"Watermarked saved to {out_path}")
