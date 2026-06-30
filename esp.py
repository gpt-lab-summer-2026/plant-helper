from machine import ADC, Pin, UART
import json
import time

# AO pin — GPIO34 (input-only, ideal for analog)
adc = ADC(Pin(34))
adc.atten(ADC.ATTN_11DB)    # full 0-3.3V range
adc.width(ADC.WIDTH_12BIT)  # 0-4095

# UART2 for Pi communication
uart = UART(2, baudrate=9600, tx=Pin(17), rx=Pin(16))

while True:
    moisture = adc.read()
    voltage = moisture / 4095 * 3.3

    payload = json.dumps({"moisture": moisture})
    uart.write(payload + "\n")

    print(f"raw: {moisture}  voltage: {voltage:.2f}V")  # debug

    time.sleep(2)
