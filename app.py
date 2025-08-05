import io
import cv2
import numpy as np
from fastapi import FastAPI, Response
from starlette.responses import StreamingResponse
from PIL import Image
from quantumblur.quantumblur import process_image  # core function from quantumblur.py

app = FastAPI()
cap = cv2.VideoCapture(0)  # your system webcam

def mjpeg_generator(shots=64, downscale=(128,128)):
    """
    Capture frames, apply quantum blur, and yield as MJPEG.
    - shots: number of quantum shots (lower → faster but noisier)
    - downscale: process at this resolution, then upsample
    """
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 1) Resize to reduce qubit count & speed up
        small = cv2.resize(frame, downscale, interpolation=cv2.INTER_AREA)
        # 2) Convert BGR→RGB and to PIL
        pil = Image.fromarray(cv2.cvtColor(small, cv2.COLOR_BGR2RGB))
        # 3) Quantum blur
        blurred_pil = process_image(
            pil,
            shots=shots,
            backend="qasm_simulator"       # use Aer’s qasm_simulator
        )
        # 4) Back to OpenCV BGR
        blurred = cv2.cvtColor(np.array(blurred_pil), cv2.COLOR_RGB2BGR)
        # 5) Upscale back to original size
        out_frame = cv2.resize(
            blurred,
            (frame.shape[1], frame.shape[0]),
            interpolation=cv2.INTER_LINEAR
        )
        # 6) JPEG-encode for MJPEG
        ret2, buf = cv2.imencode('.jpg', out_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if not ret2:
            continue
        jpg_bytes = buf.tobytes()

        # 7) Yield multipart frame
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + jpg_bytes + b"\r\n"
        )

@app.get("/stream")
def stream():
    return StreamingResponse(
        mjpeg_generator(shots=32, downscale=(128,128)),  # tune shots & size for latency
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/")
def home():
    # A minimal HTML page that Hydra can hook into
    return Response(
        """
        <html>
          <body style="margin:0; overflow:hidden; background:#000">
            <video id="qvideo"
              style="width:100vw; height:100vh; object-fit:cover"
              autoplay muted playsinline
              src="/stream">
            </video>
            <script src="https://unpkg.com/hydra-synth"></script>
            <script>
              // initialize Hydra on the <video> element
              s0.initVideo(document.getElementById('qvideo'));
              // feed it directly to output
              src(s0).out(o0);
            </script>
          </body>
        </html>
        """,
        media_type="text/html"
    )
