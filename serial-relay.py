import board
import busio
# import usb_cdc

uart = busio.UART(board.A2, board.A1, baudrate=9600)
# uart_send = busio.UART(board.A2, board.A2, baudrate=9600)
# cdc = usb_cdc.console

while True:
    # print(uart_receive.read(256))
    # cdc.write(b"Hello")
    # uart_read = uart.read(256)
    # if uart_read:
    #     uart.write(b"Hi")
        # cdc.write(uart_read)
    # cdc_read = cdc.read(256)
    # if cdc_read:
    #     uart.write(cdc_read)
    # uart.write(input("INPUT:").encode())
    uart.write(bytes(b"Hi"))