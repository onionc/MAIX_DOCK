# coding=utf-8
# This file is part of MaixPY
# Copyright (c) sipeed.com
#
# Licensed under the MIT license:
#   http://www.opensource.org/licenses/mit-license.php
#


SSID = "XM-AE86"
PASW = "xxxxxx"

import time, network
from Maix import GPIO
from machine import UART
from fpioa_manager import fm
from board import board_info
from sys import exit
import socket
import sensor, image, lcd
import struct


class wifi():

    __is_m1w__ = True
    uart = None
    eb = None
    nic = None

    def init():
        if __class__.__is_m1w__:
            fm.register(0, fm.fpioa.GPIOHS1, force=True)
            M1wPower=GPIO(GPIO.GPIOHS1, GPIO.OUT)
            M1wPower.value(0) # b'\r\n ets Jan  8 2013,rst cause:1, boot mode:(7,6)\r\n\r\nwaiting for host\r\n'

        fm.register(board_info.WIFI_EN, fm.fpioa.GPIOHS0) # board_info.WIFI_EN == IO 8
        __class__.en = GPIO(GPIO.GPIOHS0,GPIO.OUT)

        fm.register(board_info.WIFI_RX,fm.fpioa.UART2_TX) # board_info.WIFI_RX == IO 7
        fm.register(board_info.WIFI_TX,fm.fpioa.UART2_RX) # board_info.WIFI_TX == IO 6
        __class__.uart = UART(UART.UART2, 115200, timeout=1000, read_buf_len=8192)

    def enable(en):
        __class__.en.value(en)

    def _at_cmd(cmd="AT\r\n", resp="OK\r\n", timeout=20):
        __class__.uart.write(cmd) # "AT+GMR\r\n"
        time.sleep_ms(timeout)
        tmp = __class__.uart.read()
        # print(tmp)
        if tmp and tmp.endswith(resp):
            return True
        return False

    def at_cmd(cmd="AT\r\n", timeout=20):
        __class__.uart.write(cmd) # "AT+GMR\r\n"
        time.sleep_ms(timeout)
        tmp = __class__.uart.read()
        return tmp

    def reset(force=False, reply=5):
        if force == False and __class__.isconnected():
            return True
        __class__.init()
        for i in range(reply):
            print('reset...')
            __class__.enable(False)
            time.sleep_ms(50)
            __class__.enable(True)
            time.sleep_ms(500) # at start > 500ms
            if __class__._at_cmd(timeout=500):
                break
        __class__._at_cmd()
        __class__._at_cmd('AT+UART_CUR=921600,8,1,0,0\r\n', "OK\r\n")
        __class__.uart = UART(UART.UART2, 921600, timeout=1000, read_buf_len=10240)
        # important! baudrate too low or read_buf_len too small will loose data
        #print(__class__._at_cmd())
        try:
            __class__.nic = network.ESP8285(__class__.uart)
            time.sleep_ms(500) # wait at ready to connect
        except Exception as e:
            print(e)
            return False
        return True

    def connect(ssid="wifi_name", pasw="pass_word"):
        if __class__.nic != None:
            return __class__.nic.connect(ssid, pasw)

    def ifconfig(): # should check ip != 0.0.0.0
        if __class__.nic != None:
            return __class__.nic.ifconfig()

    def isconnected():
        if __class__.nic != None:
            return __class__.nic.isconnected()
        return False

# 连接wifi
def enable_espat(reply=5):
    if wifi.isconnected() != True:
        for i in range(reply):
            try:
                wifi.reset()
                print('try AT connect wifi...', wifi._at_cmd())
                wifi.connect(SSID, PASW)
                if wifi.isconnected():
                    break
            except Exception as e:
                print(e)
    return wifi.isconnected()

def xor_checksum(data):
    """计算 XOR 校验"""
    checksum = 0
    for byte in data:
        checksum ^= byte
    return checksum

# 发送图片
ADDR = ("39.103.59.12", 9002)
def send_image(image_data):
    '''
    with open(image_path, "rb") as f:
        image_data = f.read()
    '''

    img_size = len(image_data)
    print("发送图片大小: {} 字节".format(img_size))

    client = socket.socket()
    client.connect(ADDR)

    client.settimeout(1)

    # 发送帧头
    client.send(b"\xAB\xCD")
    # 发送 4 字节的大小
    client.send(struct.pack("<I", img_size))
    # 发送图片数据
    client.send(image_data)
    # 校验
    cs = xor_checksum(image_data)
    print("checksum=", cs)
    client.send(struct.pack("<B", cs))

    # 等待服务器返回 LLM 结果
    response = client.recv(1024)
    llm_result = response.decode()
    print("LLM 结果:", llm_result)

    if llm_result.startswith("bingo!"):
        return llm_result[7:]
    return ""

# lcd init
def lcd_init():

    lcd.init(freq=15000000)
    sensor.reset()                      # Reset and initialize the sensor. It will
                                        # run automatically, call sensor.run(0) to stop
    sensor.set_pixformat(sensor.RGB565) # Set pixel format to RGB565 (or GRAYSCALE)
    sensor.set_framesize(sensor.QVGA)   # Set frame size to QVGA (320x240)
    sensor.skip_frames(time = 2000)     # Wait for settings take effect.

    # 导入字库
    image.font_load(image.UTF8, 16, 16, '/sd/0xA00000_font_uincode_16_16_tblr.Dzk')



if __name__ == "__main__":
    # 连接wifi
    if enable_espat(3) == False:
        print("ERROR: wifi连接失败·")
        exit()
    else:
        print("连接成功")
        print('network state:', wifi.isconnected(), wifi.ifconfig())

    print("连接成功2")

    # 视频和lcd初始化
    lcd_init()
    clock = time.clock()                # Create a clock object to track the FPS.

    tim = time.time()
    llm_desc = ""
    while(True):
        try:
            clock.tick()                    # Update the FPS clock.
            img = sensor.snapshot()         # Take a picture and return the image.

            # 每2秒取一次图片
            if time.time() -tim >2:
                tim = time.time()

                # 原图压缩jpeg，转字节
                img2 = img.compressed(quality=20)
                jpeg_bytes = img2.to_bytes()
                print("bytes length: %d bytes[0]: %x%x" %(len(jpeg_bytes), jpeg_bytes[0], jpeg_bytes[1]))

                # 发送图片获取描述信息
                llm_desc = send_image(jpeg_bytes)

            # 图片上加文字显示到lcd
            img.draw_string(20,100, llm_desc, x_spacing=2, mono_space=1, color=(255,0,0), scale=2)

            lcd.display(img)                # Display on LCD
            print(clock.fps())              # Note: MaixPy's Cam runs about half as fast when connected

        except Exception as e:
            print(e)


