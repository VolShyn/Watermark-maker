import os
import cv2
import requests
import pandas as pd
from urllib.parse import urlparse

WATERMARK_TEXT = '3D_Print'
WATERMARK_OPACITY = 0.3       # 0.0 transparent, 1.0 opaque
WATERMARK_THICKNESS = 2
BORDER_COLOR = (228, 100, 0)    # blue border (BGR)
BORDER_THICKNESS = 10


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

    # 2) create transparent overlay for watermark
    overlay = cv2.cvtColor(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
    overlay[:] = (0, 0, 0)  # make fully black/transparent overlay

    font = cv2.FONT_HERSHEY_SIMPLEX
    # estimate font scale so text width ≈half image width
    (text_w, text_h), _ = cv2.getTextSize(WATERMARK_TEXT, font, 1.0, WATERMARK_THICKNESS)
    scale = (w / 2) / text_w
    # position at roughly one-quarter down from top, one-quarter in from left
    org = (int((w + 2*BORDER_THICKNESS - text_w*scale) / 2),
           int((h + 2*BORDER_THICKNESS + text_h*scale) / 2))

    # put text onto overlay in white
    cv2.putText(
        overlay, WATERMARK_TEXT, org,
        fontFace=font,
        fontScale=scale,
        color=(255, 255, 255),
        thickness=WATERMARK_THICKNESS,
        lineType=cv2.LINE_AA
    )

    # rotate text 45° for diagonal effect
    M = cv2.getRotationMatrix2D(
        ( (org[0] + text_w*scale/2), (org[1] - text_h*scale/2) ),
        angle=-45,
        scale=1.0
    )
    overlay = cv2.warpAffine(overlay, M, (bordered.shape[1], bordered.shape[0]))

    # blend the overlay with the bordered image
    watermarked = cv2.addWeighted(overlay, WATERMARK_OPACITY, bordered, 1 - WATERMARK_OPACITY, 0)

    cv2.imwrite(out_path, watermarked)
    print(f"Watermarked saved to {out_path}")
