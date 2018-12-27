#!/usr/bin/env python
import serial
import modbus_tk
import modbus_tk.defines as cst
from modbus_tk import modbus_rtu
from PyQt5 import QtCore, QtGui, Qt
import pyqtgraph as pg
import sys, time

class MainWidget(QtGui.QWidget):
    def __init__(self, data):
        super().__init__()
        plot = pg.PlotWidget()

        self.curve = pg.PlotCurveItem(list(range(len(data))), data, pen=pg.mkPen(color=(0x2E, 0x86, 0xAB), width=2))
        plot.addItem(self.curve)

        grid_alpha = 70
        x = plot.getAxis("bottom")
        y = plot.getAxis("left")
        x.setGrid(grid_alpha)
        y.setGrid(grid_alpha)
        x.setLabel("Sample")
        y.setLabel("Current (mA)")

        layout = QtGui.QVBoxLayout()
        layout.addWidget(plot)
        self.setLayout(layout)

class DM856V2:
    config_registers=[
        ["CURRENT_KP", 0x00],
        ["CURRENT_KI", 0x01],
        ["PEAK_CURRENT", 0x1F],
        ["MICROSTEP", 0x20],
        ["ANTIRES_AMP_1", 0x40],
        ["ANTIRES_PHASE_1", 0x41],
        ["ANTIRES_AMP_2", 0x44],
        ["ANTIRES_PHASE_2", 0x45],
        ["ANTIRES_AMP_3", 0x48],
        ["ANTIRES_PHASE_3", 0x49],
        ["IDLE_CURRENT", 0x4E],
        ["IDLE_TIME", 0x4F],
        ["FILTER_ENABLE", 0x50],
        ["ELECTRONIC_DAMPING", 0x99],
        ["PULSE_MODE", 0xFF]
        ]

    START_TEST=0x02 # or set nb step test
    TEST_CURRENT=0x04
    TEST_RESULT=0x05 # test multiple read (max 256)
    AUTOTEST=0x61 # write 1
    EEPROM_SAVE=0x0C # write 1

    BOTH_DIRECTION=0x1C
    POSITIVE_DIRECTION=0x1A
    NB_TESTS=0x19
    REV_PER_TEST=0x18 #unit 0.01 rev
    TIME_BETWEEN_TEST=0x1B #unit ms
    SPEED=0x16 #unit 0.01 rev per second
    RUN_TEST=0x09 #1 run, 0 stop

    def __init__(self, port, baudrate):
        self._dev_addr = 0x01
        try:
            self.ser = serial.Serial(port=port, baudrate=baudrate, bytesize=8, parity='N', stopbits=2, xonxoff=0)
        except serial.SerialException as e:
            print(e)
            sys.exit(0)

        try:
            self.master = modbus_rtu.RtuMaster(self.ser)
            self.master.set_timeout(5.0)
            self.master.set_verbose(True)
        except modbus_tk.modbus.ModbusError as e:
            print("%s- Code=%d", e, e.get_exception_code())
            sys.exit(0)

    def close(self):
        self.ser.close()

    def read_multiple_words(self, address, n):
        return self.master.execute(self._dev_addr, cst.READ_HOLDING_REGISTERS, address, n)

    def read_word(self, address):
        return self.read_multiple_words(address, 0x01)[0]

    def write_word(self, address, value):
        self.master.execute(self._dev_addr, cst.WRITE_SINGLE_REGISTER, address, output_value=value)

    def list_param(self):
        for i, reg in enumerate(self.config_registers):
            print('{:2d}'.format(i) + ". " + '{: <19}'.format(reg[0]) + ":", self.read_word(reg[1]))

    def set_param(self):
        print("Choose parameter index:")
        index = int(input())
        if(index < 0 or index >= len(self.config_registers)):
            print("This parameter does not exist.")
            return

        reg = self.config_registers[index]

        print("Choose a value for " + reg[0] + ":")
        val = int(input())
        self.write_word(reg[1], val)

    def store_on_eeprom(self):
        self.write_word(EEPROM_SAVE, 0x01)

    def current_loop_test(self):
        self.write_word(self.TEST_CURRENT, 3000)
        self.write_word(self.START_TEST, 1)
        data = list(self.read_multiple_words(self.TEST_RESULT, 200))
        self.write_word(self.START_TEST, 0)

        for i in range(len(data)):
            if(data[i] >= 1<<15):
                data[i] -= (1<<16)

        pg.setConfigOption('background', (0x35, 0x40, 0x45))
        pg.setConfigOption('foreground', (0xB0, 0xB0, 0xB0))
        pg.setConfigOption('antialias', True)
        app = QtGui.QApplication([])
        main_widget = MainWidget(data)
        main_widget.show()
        app.exec_()

    def resonance_test(self):
        self.write_word(self.BOTH_DIRECTION, 1)
        self.write_word(self.POSITIVE_DIRECTION, 1)
        self.write_word(self.NB_TESTS, 2)
        self.write_word(self.REV_PER_TEST, 500)
        self.write_word(self.SPEED, 500)
        self.write_word(self.TIME_BETWEEN_TEST, 50)
        self.write_word(self.RUN_TEST, 1)
        time.sleep(5)
        self.write_word(self.RUN_TEST, 0)

def show_menu():
    print("Command [l,s,x,c,r,q,?]? (type ? for help)")

def show_help():
    print("-----------------")
    print("l : list current parameters value")
    print("s : choose a parameter to set")
    print("x : write current parameters to EEPROM")
    print("c : run current loop test")
    print("r : run resonance test")
    print("q : quit")
    print("? : help")
    print("-----------------")

def main():
    driver = DM856V2('/dev/ttyUSB0', 38400)

    while(True):
        show_menu()

        cmd = input()
        if(cmd == 'l'):
            driver.list_param()
        elif(cmd == 's'):
            driver.set_param()
        elif(cmd == 'x'):
            driver.store_on_eeprom()
        elif(cmd == 'c'):
            driver.current_loop_test()
        elif(cmd == 'r'):
            driver.resonance_test()
        elif(cmd == 'q'):
            break
        elif(cmd == '?'):
            show_help()
        else:
            print("unknow option")

    driver.close()

if __name__ == "__main__":
    main()
