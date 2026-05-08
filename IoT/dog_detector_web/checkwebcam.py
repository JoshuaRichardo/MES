import cv2

# Coba buka webcam default
camera_index = 0 # ganti 1 atau 2 kalau ada lebih dari 1 kamera
camera = cv2.VideoCapture(camera_index)

if not camera.isOpened():
    print(f"Gagal membuka webcam dengan index {camera_index}")
else:
    print(f"Webcam dengan index {camera_index} berhasil dibuka")

    # Coba baca 1 frame
    ret, frame = camera.read()
    if ret:
        print("Frame berhasil dibaca dari webcam")
        cv2.imshow("Test Frame", frame)
        cv2.waitKey(3000)  # tampilkan 3 detik
        cv2.destroyAllWindows()
    else:
        print("Gagal membaca frame dari webcam")

camera.release()