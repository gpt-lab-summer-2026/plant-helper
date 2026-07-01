from machine import ADC, Pin
import json
import time

moisture_adc = ADC(Pin(34))
moisture_adc.atten(ADC.ATTN_11DB)

mic_adc = ADC(Pin(35))
mic_adc.atten(ADC.ATTN_11DB)

SAMPLE_US = 125           # 8 kHz — requires 921600 baud set in boot.py
BATCH_SIZE = 64

MOISTURE_INTERVAL = 2000  # ms
last_moisture_time = 0
last_moisture = 0

# 5-second window to press Ctrl+C in Thonny before the loop starts
print("Starting in 5s... press Ctrl+C to stop")
time.sleep(5)

try:
    while True:
        now = time.ticks_ms()

        # collect one audio batch at ~2 kHz and send over USB
        samples = []
        for _ in range(BATCH_SIZE):
            samples.append(mic_adc.read())
            time.sleep_us(SAMPLE_US)
        print(json.dumps({"a": samples}))

        # moisture every 2 seconds
        if time.ticks_diff(now, last_moisture_time) >= MOISTURE_INTERVAL:
            last_moisture = moisture_adc.read()
            last_moisture_time = now
            print(json.dumps({"m": last_moisture}))

except KeyboardInterrupt:
    print("Stopped.")
