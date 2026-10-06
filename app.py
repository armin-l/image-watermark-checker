#!/usr/bin/env python3
"""Image Watermark / Content Credentials Checker - Prototype Backend."""

import os
import json
import hashlib
from pathlib import Path
from PIL import Image
import numpy as np


# ─── C2PA / Content Credentials Detection ──────────────────────────────

def extract_c2pa_metadata(image_path: str) -> dict:
    """Extract C2PA / Content Authenticity metadata from an image file."""
    result = {
        'has_c2pa': False,
        'c2pa_jsonld': [],
        'xmp_data': '',
        'metadata_warnings': []
    }

    try:
        img = Image.open(image_path)

        # Read raw bytes looking for embedded XMP/C2PA manifests
        with open(image_path, 'rb') as f:
            data = f.read()

        text_content = ''
        try:
            text_content = data.decode('utf-8', errors='replace')
        except Exception:
            pass

        # Check for XMP packet
        xmp_start = data.find(b'http://ns.adobe.com/xap/1.0/')
        c2pa_marker = data.find(b'C2PA ') or data.find(b'c2pa/')
        schema_org = data.find(b'schema.org')

        if xmp_start >= 0:
            snippet = data[xmp_start:xmp_start + 500].decode('utf-8', errors='replace')
            result['xmp_detected'] = True
            result['xmp_snippet_preview'] = snippet[:400] + ('...' if len(snippet) > 400 else '')

        if c2pa_marker is not None and c2pa_marker >= 0:
            snippet = data[c2pa_marker:c2pa_marker + 500].decode('utf-8', errors='replace')
            result['c2pa_manifest_found'] = True
            result['c2pa_snippet_preview'] = snippet[:400] + ('...' if len(snippet) > 400 else '')

        # EXIF via piexif if available
        try:
            import piexif
            exif_dict = piexif.load(str(image_path))
            tags_out = {}
            for key, vals in exif_dict.items():
                if key != 'thumbnail':
                    for k, v in vals.items():
                        tag_name = piexif.TAGS.get(key, {}).get(k, str(k))
                        val_str = repr(v)[:200] if not isinstance(v, str) else v
                        tags_out[str(tag_name)] = val_str
            result['exif_tags'] = tags_out
        except ImportError:
            pass
        except Exception as e:
            result['metadata_warnings'].append(f"piexif error: {e}")

    except FileNotFoundError:
        return {'error': f'File not found: {image_path}'}

    return result


# ─── Perceptual Hashing ──────────────────────────────

def perceptual_hash(image_path: str, hash_size: int = 8) -> dict:
    """Compute multiple perceptual hashes of an image."""
    img_gray = Image.open(image_path).convert('L').resize((hash_size * 4, hash_size), Image.LANCZOS)
    arr = np.array(img_gray.getdata(), dtype=np.float64).reshape(hash_size * 4, hash_size)

    avg = float(arr.mean())
    ahash_bits = (arr < avg).astype(int).flatten()
    ahex = hex(int("".join(map(str, ahash_bits)), 2))[2:].zfill(16)

    gray = np.array(Image.open(image_path).convert('L'))
    h, w = gray.shape

    col_means_left = gray[:, :w // 2].mean(axis=1)
    right_mean_vals = gray[:, w // 2:].mean(axis=1)
    dct_bits = (col_means_left > right_mean_vals.astype(float)).astype(int)
    dct_hex = format(int("".join(map(str, dct_bits)), 2), 'x').zfill(max(4, len(dct_bits)))

    sha256_raw = hashlib.sha256(open(image_path, 'rb').read()).hexdigest()

    color_img = Image.open(image_path).convert('RGB').resize((8, 8), Image.LANCZOS)
    pixels = list(color_img.getdata())
    r_vals = [p[0] for p in pixels]
    g_vals = [p[1] for p in pixels]
    b_vals = [p[2] for p in pixels]

    c_avg_r = sum(r_vals) / len(r_vals)
    c_avg_g = sum(g_vals) / len(g_vals)
    c_avg_b = sum(b_vals) / len(b_vals)

    color_sig_len = len([1 if rv >= c_avg_r else 0 for rv in r_vals]) + \
                    len([1 if gv >= c_avg_g else 0 for gv in g_vals]) + \
                    len([1 if bv >= c_avg_b else 0 for bv in b_vals])

    return {
        'aHash': f'0x{ahex}',
        'dct_hash': dct_hex[:8],
        'color_signature_length': color_sig_len,
        'sha256': sha256_raw,
        'file_size_bytes': os.path.getsize(image_path),
        'dimensions': {'width': img_gray.width, 'height': img_gray.height}
    }


# ─── Known Watermark Pattern Detection ──────────────────────────────

def detect_watermarks(image_path: str) -> dict:
    """Scan image bytes for known watermark signatures."""
    with open(image_path, 'rb') as f:
        data = f.read()

    text_content = ''
    try:
        text_content = data.decode('utf-8', errors='replace')
    except Exception:
        pass

    patterns = {
        'shutterstock': ['Shutterstock'],
        'gettyimages': ['Getty Images'],
        'adobe_stock': ['Adobe Stock'],
        'canva': ['Canva', 'Made with Canva'],
        'unsplash': ['Unsplash'],
        'istockphoto': ['iStock'],
        'dreamstime': ['Dreamstime'],
        'alamy': ['Alamy'],
        'depositphotos': ['DepositPhotos'],
    }

    found_patterns = {}
    lower_text = text_content.lower()
    for name, terms in patterns.items():
        matches = []
        for term in terms:
            pos = lower_text.find(term.lower())
            while pos is not None and pos >= 0:
                snippet_start = max(0, pos - 10)
                snippet_end = min(len(text_content), pos + len(term) + 40)
                snippet = repr(text_content[snippet_start:snippet_end])[:100]
                matches.append({'term': term, 'position': pos, 'context': snippet})
                next_pos = lower_text.find(term.lower(), pos + 1)
                pos = next_pos if next_pos > pos else None
        if matches:
            found_patterns[name] = matches

    return {'found_patterns': found_patterns}


# ─── Main API Handler ──────────────────────────────

class ImageChecker:
    def analyze(self, image_path: str) -> dict:
        result = {
            'file_info': {},
            'content_credentials': {},
            'perceptual_hashes': {},
            'watermark_detection': {},
            'external_services': get_external_service_links(image_path)
        }

        try:
            img = Image.open(str(image_path))
            fmt = img.format or ''
            mime_map = {'JPEG': 'image/jpeg', 'PNG': 'image/png',
                        'GIF': 'image/gif', 'WEBP': 'image/webp',
                        'BMP': 'image/bmp', 'TIFF': 'image/tiff'}
            result['file_info'] = {
                'path': str(image_path),
                'size_bytes': os.path.getsize(image_path),
                'format': fmt,
                'mode': img.mode,
                'width': img.width,
                'height': img.height,
                'mime_type': mime_map.get(fmt.upper(), 'application/octet-stream')
            }
        except Exception as e:
            result['error'] = f'Could not open image: {e}'
            return result

        result['content_credentials'] = extract_c2pa_metadata(str(image_path))
        result['perceptual_hashes'] = perceptual_hash(str(image_path))
        result['watermark_detection'] = detect_watermarks(str(image_path))

        return result


def _guess_mime(fmt):
    mapping = {'JPEG': 'image/jpeg', 'PNG': 'image/png',
               'GIF': 'image/gif', 'WEBP': 'image/webp',
               'BMP': 'image/bmp', 'TIFF': 'image/tiff'}
    return mapping.get((fmt or '').upper(), 'application/octet-stream')


EXTERNAL_SERVICES_DATA = [
    {
        'name': 'Google Lens Reverse Search',
        'url': 'https://lens.google.com/upload',
        'description': 'Finde ähnliche Bilder und Herkunft im Google Bildersuchindex.',
        'category': 'search',
        'free': True
    },
    {
        'name': 'TinEye (Reverse Image Search)',
        'url': 'https://tineye.com/',
        'description': 'Älteste Reverse-Image-Suche. Findet wo ein Bild online vorkommt.',
        'api_available': True,
        'pricing': 'API auf Anfrage / kostenpflichtig',
        'category': 'search',
        'free': False
    },
    {
        'name': 'Adobe Content Authenticity Explorer',
        'url': 'https://creator.adobe.com/platforms/content-authenticity/explorer.html',
        'description': 'Prüfe C2PA Content Credentials in Bildern (von Adobe).',
        'category': 'credentials',
        'free': True
    },
    {
        'name': 'Optanomy AI Image Identifier',
        'url': 'https://optonomy.ai/ai-image-id/',
        'description': 'Erkennt ob ein Bild von einer KI generiert wurde.',
        'category': 'ai_detection',
        'free_tier': True
    },
    {
        'name': 'Hive Moderation API',
        'url': 'https://www.hiveai.com/docs/api/image-moderation#deepfake-detection',
        'description': 'KI-generierte Inhalte erkennen via API ($0.001 pro Bild).',
        'api_key_required': True,
        'price_per_image': '$0.001',
        'endpoint': 'POST https://api.hivemodification.com/v1/deepfake/generate',
        'category': 'ai_detection'
    },
    {
        'name': 'SightEngine Image Analysis',
        'url': 'https://sightengine.com/products/image-analysis-api',
        'description': 'Bildanalyse: Deepfakes, Gewaltdarstellung, etc.',
        'trial_credits': 3000,
        'category': 'analysis'
    },
    {
        'name': 'Glaze / NightGuard (UChicago)',
        'url': 'https://glaze.cs.uchicago.edu/',
        'github': 'https://github.com/glaze-project/glaze',
        'nightguard_url': 'https://nightguard.cs.uchicago.edu/',
        'description': 'Open Source Tool — prüft ob Bilder für Training verwendet werden könnten ("perceptual fingerprinting").',
        'open_source': True,
        'category': 'protection_check'
    },
    {
        'name': 'Copyscape Images',
        'url': 'https://copyscape.com/images',
        'description': 'Findet kopierte Bilder online. Hat eine Developer-API.',
        'pricing': 'Ab $5/page',
        'api_available': True,
        'category': 'plagiarism'
    },
    {
        'name': 'Pimeyes Face Search',
        'url': 'https://pimeyes.com/',
        'description': 'Reverse Image Search speziell für Gesichter im Internet.',
        'paid_service': True,
        'starting_price': '~$27/search',
        'category': 'face_search'
    }
]


def get_external_service_links(image_path) -> list:
    sha = hashlib.sha256(open(str(image_path), 'rb').read()).hexdigest()[:8]
    return [dict(svc, image_sha_prefix=sha) for svc in EXTERNAL_SERVICES_DATA]


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Image Watermark & Content Credentials Checker')
    parser.add_argument('image_path', help='Path to the image file to analyze')
    args = parser.parse_args()

    checker = ImageChecker()
    result = checker.analyze(args.image_path)
    print(json.dumps(result, indent=2, default=str))
