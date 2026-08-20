# Half a Doodle

Draw something in the browser and a small neural network guesses what it is, updating live as you draw. It runs entirely client side. There is no server doing the thinking, just a static HTML page and a tiny ONNX model.

![demo of drawing a doodle and getting live guesses](assets/demo.gif)

Try it: open `index.html` after starting a local server (see below). It will not work if you just double click the file, because the browser blocks the model file from loading over `file://`.

## Why this is harder than it sounds

Most weekend versions of this project score well on a test set and then guess "hurricane" at everything the moment you actually draw something live. That happens for three reasons, and this project is built around avoiding all three:

1. **The model has to see unfinished drawings during training.** If you only ever train on complete sketches, a half finished doodle looks like nothing the model has seen before.
2. **The rasterizer (the thing that turns your pen strokes into a 28x28 image the model can read) has to behave identically in Python, where the model is trained, and in JavaScript, where the browser runs it.** Any difference in how thick the lines are, how they get scaled, or how the pixels get rounded creates a mismatch between training and real use.
3. **A partial drawing gets normalized to its own bounding box, not the box of a finished drawing.** In the browser you can only ever measure the box of what has been drawn so far, so training has to work the same way.

## What is in here

- `data.py` downloads the training data and turns raw pen strokes into 28x28 images.
- `train.py` builds and trains the model, checks how accurate it is, and exports it to ONNX so a browser can run it.
- `index.html` is the whole demo: the drawing canvas, a hand written JavaScript port of the same rasterizer used in Python, and the code that talks to the model.
- `model.onnx` is the trained model, a few hundred kilobytes.
- `parity.json` holds a few drawings, run through the Python rasterizer ahead of time, that the page checks itself against on load. If the JavaScript version does not produce the exact same pixels, you will see it fail in the browser console.

## Running the demo

You need Python installed, nothing else.

```bash
git clone https://github.com/ShubhamPandeycreate/Half-a-Doodle.git
cd Half-a-Doodle
python -m http.server 8000
```

If `python` is not found, try `python3` instead. The important part is running this command from inside the project folder, since it serves whatever directory you are standing in when you run it.

Then open `http://localhost:8000/index.html` in a browser. The page will load the model, run a quick self check comparing its rasterizer against the reference in `parity.json`, and then let you draw. Open the browser console if you want to see the self check result.

## Retraining it yourself

You will need PyTorch, plus `onnx` and `onnxscript` for the export step.

```bash
python data.py
python train.py
```

`data.py` downloads 5,000 drawings each for 20 categories (things like cat, house, star, tree) directly from Google's Quick, Draw! dataset, and saves them locally. `train.py` trains for a while, prints how accurate the model is both on finished drawings and on partial ones, and writes out `model.onnx` at the end.

## What it can draw

airplane, apple, banana, bicycle, book, butterfly, cat, chair, clock, cloud, cup, eye, fish, flower, guitar, house, key, moon, star, tree

That is the whole vocabulary. Draw anything else and it will confidently guess one of these twenty things anyway, because that is all it knows.

## How good is it

On a held out test set of drawings it has never seen: about 93% accurate on finished drawings, and about 54% accurate on a drawing that is only 30% complete (measuring just the single best guess). If you count it as correct whenever the right answer shows up anywhere in the top three guesses, those numbers rise to about 98% and 80%.

## License

MIT. See `LICENSE`.
