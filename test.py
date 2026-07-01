from sensor import test_mic
import serial

ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=2)
test_mic(ser, duration_sec=40)
ser.close()