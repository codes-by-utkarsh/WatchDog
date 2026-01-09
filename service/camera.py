import cv2
import time

def capture():
    cam = cv2.VideoCapture(0)
    time.sleep(1)
    ret, frame = cam.read()
    cam.release()

    if ret:
        filename = f"intruder_{int(time.time())}.jpg"
        cv2.imwrite(filename, frame)
        return filename
    return None
