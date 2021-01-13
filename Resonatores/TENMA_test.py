import serial
import pyvisa

rm = pyvisa.highlevel.ResourceManager()   # Opens the resource manager and sets it to variable rm
TENMA = rm.open_resource("ASRL8::INSTR", baud_rate = 9600, data_bits = 8)
TENMA.read_termination = '\n'
TENMA.write_termination = '\n'
TENMA.query_delay = 1
TENMA.send_end = True
TENMA.StopBits = 1

print(TENMA.query("*IDN?"))


