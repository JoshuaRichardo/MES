import cv2
import time
import serial
from serial.serialutil import SerialException
from flask import Flask, Response, render_template_string
from ultralytics import YOLO

# =========================
# KONFIGURASI
# =========================

SERIAL_PORT = "COM7"
BAUD_RATE = 9600

CAMERA_INDEX = 1

# Cooldown dalam detik
COOLDOWN_SECONDS = 20

# Confidence minimum deteksi kucing
CONFIDENCE_THRESHOLD = 0.6

# Model YOLO
MODEL_PATH = "yolov8n.pt"

# Class ID kucing di COCO dataset adalah 15
CAT_CLASS_ID = 15

# =========================
# FLASK APP
# =========================

app = Flask(__name__)

# =========================
# GLOBAL STATE
# =========================

ser = None
last_trigger_time = 0

print("Memuat model YOLO...")
model = YOLO(MODEL_PATH)
print("Model YOLO siap.")

camera = cv2.VideoCapture(CAMERA_INDEX)

if not camera.isOpened():
    print("WARNING: Kamera tidak bisa dibuka. Cek CAMERA_INDEX.")


# =========================
# SERIAL FUNCTIONS
# =========================

def connect_serial():
    global ser

    try:
        if ser is not None and ser.is_open:
            return ser

        print(f"Mencoba koneksi ke {SERIAL_PORT}...")
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)

        # Arduino biasanya reset saat serial baru dibuka
        time.sleep(2)

        print(f"Berhasil terhubung ke {SERIAL_PORT}")
        return ser

    except SerialException as e:
        print(f"Gagal koneksi serial: {e}")
        ser = None
        return None

    except PermissionError as e:
        print(f"Permission error saat membuka serial: {e}")
        ser = None
        return None


def close_serial():
    global ser

    try:
        if ser is not None and ser.is_open:
            ser.close()
            print("Serial ditutup.")
    except Exception as e:
        print(f"Gagal menutup serial: {e}")

    ser = None


def send_servo_signal():
    global ser

    try:
        ser = connect_serial()

        if ser is None:
            print("Serial tidak tersedia. Sinyal servo tidak dikirim.")
            return False

        ser.write(b"F")
        ser.flush()

        print("Sinyal F berhasil dikirim ke Arduino.")
        return True

    except SerialException as e:
        print(f"Gagal kirim sinyal serial: {e}")
        print("Mencoba reconnect serial...")

        close_serial()
        time.sleep(1)

        try:
            ser = connect_serial()

            if ser is None:
                print("Reconnect gagal. Sinyal servo tidak dikirim.")
                return False

            ser.write(b"F")
            ser.flush()

            print("Sinyal F berhasil dikirim setelah reconnect.")
            return True

        except Exception as e2:
            print(f"Tetap gagal setelah reconnect: {e2}")
            close_serial()
            return False

    except PermissionError as e:
        print(f"Access denied saat write ke serial: {e}")
        print("Kemungkinan COM port sedang dipakai aplikasi lain.")
        close_serial()
        return False

    except Exception as e:
        print(f"Error tidak terduga saat kirim serial: {e}")
        close_serial()
        return False


# =========================
# DETECTION FUNCTION
# =========================

def detect_cat(frame):
    try:
        results = model(frame, verbose=False)

        cat_detected = False

        for result in results:
            boxes = result.boxes

            for box in boxes:
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])

                # Cek apakah ID adalah kucing (15)
                if class_id == CAT_CLASS_ID and confidence >= CONFIDENCE_THRESHOLD:
                    cat_detected = True

                    x1, y1, x2, y2 = box.xyxy[0]
                    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

                    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2) # Biru untuk kucing

                    label = f"Cat {confidence:.2f}"
                    cv2.putText(
                        frame,
                        label,
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (255, 0, 0),
                        2
                    )

        return cat_detected, frame

    except Exception as e:
        print(f"Error saat deteksi: {e}")
        return False, frame


# =========================
# VIDEO STREAM
# =========================

def generate_frames():
    global last_trigger_time

    while True:
        success, frame = camera.read()

        if not success:
            print("Gagal membaca frame dari kamera.")
            time.sleep(1)
            continue

        # Memanggil fungsi deteksi kucing
        cat_detected, frame = detect_cat(frame)

        current_time = time.time()
        elapsed = current_time - last_trigger_time
        cooldown_remaining = max(0, COOLDOWN_SECONDS - elapsed)

        if cat_detected:
            cv2.putText(
                frame,
                "CAT DETECTED",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 0, 0),
                2
            )

            if elapsed >= COOLDOWN_SECONDS:
                print("Kucing terdeteksi dan cooldown selesai. Mengirim sinyal servo...")
                success_send = send_servo_signal()

                if success_send:
                    last_trigger_time = current_time
                else:
                    print("Sinyal gagal dikirim. Cooldown tidak direset.")

            else:
                cv2.putText(
                    frame,
                    f"Cooldown: {cooldown_remaining:.1f}s",
                    (20, 80),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 255),
                    2
                )

        else:
            cv2.putText(
                frame,
                "No cat detected",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 255, 255),
                2
            )

        ret, buffer = cv2.imencode(".jpg", frame)

        if not ret:
            continue

        frame_bytes = buffer.tobytes()

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
        )


# =========================
# ROUTES
# =========================

@app.route("/")
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Cat Detector</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background: #111;
                color: white;
                text-align: center;
                margin: 0;
                padding: 30px;
            }

            h1 {
                margin-bottom: 20px;
                color: #3498db;
            }

            img {
                width: 80%;
                max-width: 900px;
                border: 4px solid #3498db;
                border-radius: 12px;
            }

            .info {
                margin-top: 20px;
                color: #ccc;
            }
        </style>
    </head>
    <body>
        <h1>Cat Detector Web</h1>
        <img src="/video_feed">
        <div class="info">
            Jika <b>Kucing</b> terdeteksi dan cooldown selesai, Python akan mengirim sinyal <b>F</b> ke Arduino.
        </div>
    </body>
    </html>
    """)


@app.route("/video_feed")
def video_feed():
    return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/test_servo")
def test_servo():
    success_send = send_servo_signal()

    if success_send:
        return "Sinyal F berhasil dikirim ke Arduino (Manual Test)."
    else:
        return "Gagal mengirim sinyal F ke Arduino. Cek terminal."


# =========================
# MAIN
# =========================

if __name__ == "__main__":
    try:
        connect_serial()
        # use_reloader=False sangat penting agar port tidak terkunci dua kali
        app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False, threaded=True)
    except KeyboardInterrupt:
        print("Program dihentikan.")
    finally:
        close_serial()
        camera.release()