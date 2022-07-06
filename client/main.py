import serial

ser = serial.Serial('/dev/serial0')

read_content = ""

while True:
    read_content+=ser.read().decode()
    for msg in read_content.split("\r\n")[:-1]:
        # print(msg)
        if msg.startswith("$GPGGA"):
            print(msg.split(","))
        else:
            print(msg)
    read_content = read_content.split("\r\n")[-1]
    