"""Quick, Draw! data: download, rasterize, prefix sampling."""
import json
import math
import os
import random
import urllib.request

import numpy as np
import torch
from torch.utils.data import Dataset

CLASSES = [
    "airplane", "apple", "banana", "bicycle", "book", "butterfly", "cat", "chair",
    "clock", "cloud", "cup", "eye", "fish", "flower", "guitar", "house", "key",
    "moon", "star", "tree",
]
N_PER_CLASS = 5000
N_TEST = 250
URL = "https://storage.googleapis.com/quickdraw_dataset/full/simplified/{}.ndjson"

CANVAS = 224          # working resolution before downsample
TARGET = 192          # longest side of the drawing after scaling
OUT = 28              # final image size
BLOCK = CANVAS // OUT  # 8


def download_all(out_dir="data", n=N_PER_CLASS):
    """Stream each class file, stop after n lines. Never downloads a whole file."""
    os.makedirs(out_dir, exist_ok=True)
    for word in CLASSES:
        path = os.path.join(out_dir, word + ".ndjson")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                have = sum(1 for _ in f)
            if have >= n:
                print(f"{word:10s} have {have}")
                continue
        print(f"{word:10s} downloading...", end=" ", flush=True)
        with urllib.request.urlopen(URL.format(word), timeout=120) as r:
            with open(path, "w", encoding="utf-8") as f:
                for i, line in enumerate(r):
                    if i >= n:
                        break
                    f.write(line.decode("utf-8"))
        print("done")


def load_split(data_dir="data"):
    """Per class: last N_TEST drawings by file order -> test, rest -> train."""
    train, test = [], []
    for label, word in enumerate(CLASSES):
        items = []
        with open(os.path.join(data_dir, word + ".ndjson"), encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= N_PER_CLASS:
                    break
                strokes = [(np.asarray(xs, dtype=np.int16), np.asarray(ys, dtype=np.int16))
                           for xs, ys in json.loads(line)["drawing"]]
                items.append((strokes, label))
        train.extend(items[:-N_TEST])
        test.extend(items[-N_TEST:])
    return train, test


def rasterize(strokes, line_width=3):
    """strokes -> 28x28 uint8 (0 blank, 255 ink).

    Ported by hand to JS in index.html -- keep the two identical.
    All rounding is floor(v + 0.5) (never round(), which is banker's rounding in
    Python but half-up in JS) and the downsample is integer (sum + 32) // 64, so
    the two implementations agree byte for byte.
    """
    xs_all, ys_all = [], []
    for s in strokes:
        xs_all.extend(s[0])
        ys_all.extend(s[1])
    if not xs_all:
        return np.zeros((OUT, OUT), dtype=np.uint8)

    minx, maxx = min(xs_all), max(xs_all)
    miny, maxy = min(ys_all), max(ys_all)
    w, h = maxx - minx, maxy - miny
    scale = 1.0 if (w < 1 and h < 1) else TARGET / max(w, h)
    ox = (CANVAS - w * scale) / 2.0 - minx * scale
    oy = (CANVAS - h * scale) / 2.0 - miny * scale

    img = np.zeros((CANVAS, CANVAS), dtype=np.uint8)
    half = line_width // 2
    for s in strokes:
        n = len(s[0])
        if n == 0:
            continue
        # same two rounded float64 ops as the JS port does per point
        xs = (np.asarray(s[0], dtype=np.float64) * scale + ox).tolist()
        ys = (np.asarray(s[1], dtype=np.float64) * scale + oy).tolist()
        if n == 1:
            px = np.array([math.floor(xs[0] + 0.5)], dtype=np.int64)
            py = np.array([math.floor(ys[0] + 0.5)], dtype=np.int64)
            _stamp(img, px, py, half, line_width)
            continue
        for i in range(n - 1):
            x0 = xs[i]
            y0 = ys[i]
            dx = xs[i + 1] - x0
            dy = ys[i + 1] - y0
            steps = int(math.ceil(max(abs(dx), abs(dy))))
            if steps < 1:
                steps = 1
            t = np.arange(steps + 1, dtype=np.float64) / steps
            px = np.floor(x0 + dx * t + 0.5).astype(np.int64)
            py = np.floor(y0 + dy * t + 0.5).astype(np.int64)
            _stamp(img, px, py, half, line_width)

    block = img.reshape(OUT, BLOCK, OUT, BLOCK).sum(axis=(1, 3), dtype=np.uint32)
    return ((block + 32) // 64).astype(np.uint8)


def _stamp(img, px, py, half, line_width):
    """Stamp a line_width square of 255 centred on each (px, py)."""
    for dy in range(line_width):
        yy = py - half + dy
        for dx in range(line_width):
            xx = px - half + dx
            m = (xx >= 0) & (xx < CANVAS) & (yy >= 0) & (yy < CANVAS)
            if m.any():
                img[yy[m], xx[m]] = 255


def take_prefix(strokes, f):
    """Keep the first ceil(f * total_points) points in stroke order."""
    total = 0
    for s in strokes:
        total += len(s[0])
    if total == 0:
        return []
    k = int(math.ceil(f * total))
    if k >= total:
        return strokes
    out = []
    for s in strokes:
        if k <= 0:
            break
        n = len(s[0])
        if n <= k:
            out.append(s)
            k -= n
        else:
            out.append([s[0][:k], s[1][:k]])
            k = 0
    return out


class QuickDrawDataset(Dataset):
    """Rasterizes on the fly. Train mode samples a stroke prefix per item."""

    def __init__(self, items, train=True, f=1.0, line_width=3):
        self.items = items
        self.train = train
        self.f = f
        self.line_width = line_width

    def __len__(self):
        return len(self.items)

    def __getitem__(self, i):
        strokes, label = self.items[i]
        if self.train:
            # random module, not numpy: torch reseeds random per DataLoader worker
            # but not numpy's global RNG, which would give all 4 workers the same
            # prefix stream.
            f = 1.0 if random.random() < 0.5 else random.uniform(0.15, 1.0)
        else:
            f = self.f
        img = rasterize(take_prefix(strokes, f), self.line_width)
        return torch.from_numpy(img).float().unsqueeze(0), label


if __name__ == "__main__":
    download_all()
