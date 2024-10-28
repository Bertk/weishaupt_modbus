import asyncio

from pymodbus import ExceptionResponse, ModbusException, pymodbus_apply_logging_config
import pymodbus.client as ModbusClient
from pymodbus.client import AsyncModbusTcpClient as AsyncModbusTcpClient


async def main():
    pymodbus_apply_logging_config("DEBUG")
    host = "192.168.42.144"  # 10.10.1.225"
    port = 502
    client = ModbusClient.AsyncModbusTcpClient(
        host,
        port=port,
    )
    await client.connect()

    # binary_out = range(1, 9999)
    # binary_in = range(10001, 19999)
    binary_out = []
    binary_in = []
    input_register = range(30001, 39999)
    holding_register = range(40001, 49999)

    file = open("register.txt", "w")

    file.write("Binary out\n\n")

    for register in binary_out:
        try:
            rr = await client.read_coils(register, 1, slave=1)
            if len(rr.registers) > 0:
                val = rr.registers[0]
        except ModbusException as exc:
            val = exc
        if rr.isError():
            val = rr
        if isinstance(rr, ExceptionResponse):
            val = rr

        file.write(str(register) + ";" + str(val) + "\n")

    file.write("Binary in: \n\n")

    for register in binary_in:
        try:
            rr = await client.read_coils(register, 1, slave=1)
            if len(rr.registers) > 0:
                val = rr.registers[0]
        except ModbusException as exc:
            val = exc
        if rr.isError():
            val = rr
        if isinstance(rr, ExceptionResponse):
            val = rr

        file.write(str(register) + ";" + str(val) + "\n")

    file.write("Input Register: \n\n")

    for register in input_register:
        try:
            rr = await client.read_input_registers(register, slave=1)
            if len(rr.registers) > 0:
                val = rr.registers[0]
        except ModbusException as exc:
            val = exc
        if rr.isError():
            val = rr
        if isinstance(rr, ExceptionResponse):
            val = rr

        file.write(str(register) + ";" + str(val) + "\n")

    for register in holding_register:
        try:
            rr = await client.read_holding_registers(register, slave=1)
            if len(rr.registers) > 0:
                val = rr.registers[0]
        except ModbusException as exc:
            val = exc
        if rr.isError():
            val = rr
        if isinstance(rr, ExceptionResponse):
            val = rr

        file.write(str(register) + ";" + str(val) + "\n")

    client.close()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
