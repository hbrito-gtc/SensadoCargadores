# Creara el puerto serie en el directorio local. Para probar que funciona cat ttyclient
#
#

from SerialEmulator import SerialEmulator
import time

emulator = SerialEmulator('./ttydevice','./ttyclient') 

for i in range (0,100):
    msg = '11 9.0 11.0 8.5 7.6 7.6 9.4 9.8 5.9 1.9 1.0 1.2 1.1 1.8 2.6 6.3 1.8\n'
    emulator.write(str.encode(msg))
    print("Enviando mensaje ", msg)
    time.sleep(2)

time.sleep(100000)     # Espera infinita, porque sino queda el puerto como no operativo.
emulator.read()



