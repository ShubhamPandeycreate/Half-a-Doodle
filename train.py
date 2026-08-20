"""Train the 20-class doodle CNN, print the two sanity numbers, export ONNX."""
import os
import sys
import time

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from data import CLASSES, QuickDrawDataset, load_split

EPOCHS = 25
BATCH = 256
WORKERS = 4


class Net(nn.Module):
    def __init__(self, n_classes=len(CLASSES)):
        super().__init__()
        self.features = nn.Sequential(
            # BatchNorm is not in the spec; added because the plain 10-epoch recipe
            # underfit (81.4% / 37.7% vs the 90% / 65% targets).
            nn.Conv2d(1, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(),
            nn.Conv2d(32, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(),
            nn.MaxPool2d(2),                                  # 32 x 14 x 14
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(),
            nn.Conv2d(64, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(),
            nn.MaxPool2d(2),                                  # 64 x 7 x 7
        )
        self.drop = nn.Dropout(0.3)
        self.fc = nn.Linear(64 * 7 * 7, n_classes)

    def forward(self, x):
        x = x / 255.0                 # raw 0-255 in, so the browser sends pixels as-is
        x = self.features(x)
        # spec used global average pool; flattening instead keeps the spatial layout,
        # which partial drawings need. Section 3 already bbox-normalises every input,
        # so GAP's translation invariance was redundant here.
        x = x.flatten(1)
        return self.fc(self.drop(x))


def evaluate(model, items, f, device):
    dl = DataLoader(QuickDrawDataset(items, train=False, f=f), batch_size=512,
                    num_workers=WORKERS, pin_memory=True)
    model.eval()
    correct = 0
    with torch.no_grad():
        for x, y in dl:
            pred = model(x.to(device, non_blocking=True)).argmax(1).cpu()
            correct += (pred == y).sum().item()
    return correct / len(items)


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    train_items, test_items = load_split()
    print(f"train {len(train_items)}  test {len(test_items)}  device {device}")

    dl = DataLoader(QuickDrawDataset(train_items, train=True), batch_size=BATCH,
                    shuffle=True, num_workers=WORKERS, pin_memory=True,
                    persistent_workers=True, drop_last=True)

    model = Net().to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3)
    lossf = nn.CrossEntropyLoss()

    for epoch in range(EPOCHS):
        model.train()
        t0 = time.time()
        loss_sum, correct, total = 0.0, 0, 0
        for x, y in dl:
            x = x.to(device, non_blocking=True)
            y = y.to(device, non_blocking=True)
            out = model(x)
            loss = lossf(out, y)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            loss_sum += loss.item() * y.size(0)
            correct += (out.argmax(1) == y).sum().item()
            total += y.size(0)
        torch.save(model.state_dict(), "model.pt")
        print(f"epoch {epoch + 1:2d}  loss {loss_sum / total:.4f}  "
              f"train_acc {correct / total:.4f}  {time.time() - t0:.0f}s")

    print("\nsanity check on the 5000 test drawings")
    print(f"  top-1 @ f=1.0 (complete) {evaluate(model, test_items, 1.0, device):.4f}")
    print(f"  top-1 @ f=0.3 (partial)  {evaluate(model, test_items, 0.3, device):.4f}")

    model.eval().cpu()
    # torch.onnx's progress messages contain emoji; the Windows console is cp1252
    sys.stdout.reconfigure(encoding="utf-8")
    # external_data=False keeps the weights inside model.onnx; the default splits
    # them into model.onnx.data, which would leave the browser with no weights.
    torch.onnx.export(model, torch.zeros(1, 1, 28, 28), "model.onnx",
                      opset_version=17, external_data=False)
    print(f"\nmodel.onnx  {os.path.getsize('model.onnx') / 1024:.0f} KB")


if __name__ == "__main__":
    main()
