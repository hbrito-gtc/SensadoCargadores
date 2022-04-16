# Los valores que esta leyendo del modulo LEchacal esta configurado para: Estimated Power in Watts. This is Irms*Vest.
# http://lechacal.com/wiki/index.php?title=Compute_Energy_used_using_a_RPICT+
#
#  PENDIENTE: Revisar las fases !!!. 
#
# Los niveles de logs 
# CRITICAL   50
# ERROR      40
# WARNING    30
# INFO       20
# DEBUG      10
# NOTSET     0

#---------------------------------- CONFIGURACION DE CONSTATES -------------------------------------
MQTT_SERV = "161.72.18.76"
MQTT_PATH = "RPICT7V1"
MQTT_USER = ""
MQTT_PASS = ""
MQTT_TOPIC = "/json/4jggokgpepnvsb2uv4s40d59ov/CarChargingStation/attrs/"

CHANNELS = ["NO_USADO", "Pest_C1_L1", "Pest_C1_L2", "Pest_C1_L3", "NO_USADO", "Pest_C2_L1", "Pest_C2_L2", "Pest_C2_L3",
            "NO_USADO", "Pest_C3_L1", "Pest_C3_L2", "Pest_C3_L3", "NO_USADO", "NO_USADO", "NO_USADO","NO_USADO", "NO_USADO"]

# Polling interval is 5 seconds
delta_T = 5./3600
 
# This will keep the sum of powers
P_sum_C1 = 0
P_sum_C2 = 0
P_sum_C3 = 0
 
# Memory for previous power reading
prev_P_C1 = 0
prev_P_C2 = 0
prev_P_C3 = 0
#---------------------------------------------------------------------------------------------------
import paho.mqtt.client as mqtt
import serial
import json
import math
from datetime import datetime
import time
import sys
import traceback
import socket
import logging
import logging.config
import yaml

def printExceptionInfo(e):
    # Get current system exception
    ex_type, ex_value, ex_traceback = sys.exc_info()
  
    # Extract unformatter stack traces as tuples
    trace_back = traceback.extract_tb(ex_traceback)

    # Format stacktrace
    stack_trace = list()

    for trace in trace_back:
        stack_trace.append("File : %s , Line : %d, Func.Name : %s, Message : %s" % (trace[0], trace[1], trace[2], trace[3]))
    logger.error("Exception type : %s " % ex_type.__name__)
    logger.error("Exception message : %s" %ex_value)
    logger.debug("Stack trace : %s" %stack_trace)

last_received_msg = ''

def on_message(client, userdata, message):
    global last_received_msg
    last_received_msg = str(message.payload.decode("utf-8"))


#with open('logging_config.yml', 'r') as f:   # Test
with open('/home/pi/SensadoCargadores/logging_config.yml', 'r') as f: # Production
    config = yaml.safe_load(f.read())
    logging.config.dictConfig(config)

logger = logging.getLogger(__name__)

logger.info("Arracado script sensado_cargadores.py")
last_time = time.time()
ser = ''
client = ''

while 1:
    try:
        # Incializamos conexion serie
        if not ser:
            logger.debug("Connecting to Serial")
            ser = serial.Serial('/dev/ttyAMA0', 38400)  # Produccion
            #ser = serial.Serial('ttyclient', 38400)     # Test

        # Reseteamos los contadores a las 00:00
        now = datetime.now()
        if (now.hour == 0 and now.minute == 0):
            # This will keep the sum of powers
            P_sum_C1 = 0
            P_sum_C2 = 0
            P_sum_C3 = 0
 
            # Memory for previous power reading
            prev_P_C1 = 0
            prev_P_C2 = 0
            prev_P_C3 = 0	
            
            logger.info("Reseteados los contadores diarios")
        
 	    # Read one line from the serial buffer
        line = ser.readline()
	    # Remove the trailing carriage return line feed
        line = line[:-2]
	    # Create an array of the data
        Z = line.split(b' ')
	    # Print it for debug
        logger.debug(line)
		# Publish to the MQTT broker
        Pest_C1_L1 = float(Z[1])
        Pest_C1_L2 = float(Z[2])
        Pest_C1_L3 = float(Z[3])
        # Importante: En caso de que se este cargando monofasico la formula cambia.
        Pest_C1 = Pest_C1_L1 + Pest_C1_L2 + Pest_C1_L3
     
        Pest_C2_L1 = float(Z[4])
        Pest_C2_L2 = float(Z[5])
        Pest_C2_L3 = float(Z[6])
        Pest_C2 = Pest_C2_L1 + Pest_C2_L2 + Pest_C2_L3
        
        Pest_C3_L1 = float(Z[13])
        Pest_C3_L2 = float(Z[14])
        Pest_C3_L3 = float(Z[15])
        Pest_C3 = Pest_C3_L1 + Pest_C3_L2 + Pest_C3_L3       
        	
        # Building the sum of powers
        P_sum_C1 += prev_P_C1 + Pest_C1
        P_sum_C2 += prev_P_C2 + Pest_C2
        P_sum_C3 += prev_P_C3 + Pest_C3

        # Saving the new Power reading as previous for next loop run
        prev_P_C1 = Pest_C1
        prev_P_C2 = Pest_C2
        prev_P_C3 = Pest_C3

        # Finally computing energy
        E_C1 = delta_T / 2 * P_sum_C1
        E_C2 = delta_T / 2 * P_sum_C2
        E_C3 = delta_T / 2 * P_sum_C3
        
        #logger.debug("----------")
        #logger.debug("Instant Power1: %s (W)" % Pest_C1)
        #logger.debug("Accum Energy1: %.2f (Wh)" % E_C1)
        #logger.debug("Instant Power2: %s (W)" % Pest_C2)
        #logger.debug("Accum Energy2: %.2f (Wh)" % E_C2)
        #logger.debug("Instant Power3: %s (W)" % Pest_C3)
        #logger.debug("Accum Energy3: %.2f (Wh)" % E_C3)
	
	    # Incializamos conexion MQTT, lo dejamos espaciado de la conexion serie para darle tiempo a que reciba la suscripcion
        # con la que comprobamos que el link esta funcionando.
        if client and not last_received_msg:
            logger.error('No se ha recivido msg de suscripcion. Fallo en la comunicacion MQTT')
            client.disconnect()
            client = ''  # Forzamos a reiniciar comunicacion
        else:
            last_received_msg = ''
            
        if not client:   # Si no hay mensaje, es que no funciona communicación, puesta estamos suscritos. 
            logger.debug("Connecting to MQTT server")
            client = mqtt.Client("P1")
            client.on_message=on_message  # Bind function to callback
            client.username_pw_set(MQTT_USER, MQTT_PASS)
            client.connect(MQTT_SERV)
            client.loop_start()        
            client.subscribe(MQTT_TOPIC)
            logger.info('Realizando suscripcion a '+MQTT_TOPIC)
	
        msg1 = {}
        if ((time.time()-last_time) > 30):
            msg1["E_C1"] = round(E_C1/1000.0, 2)
            msg1["E_C2"] = round(E_C2/1000.0, 2)
            msg1["E_C3"] = round(E_C3/1000.0, 2)
            msg1["P_C1"] = round(Pest_C1, 2)
            msg1["P_C2"] = round(Pest_C2, 2)
            msg1["P_C3"] = round(Pest_C3, 2)
            client.publish(MQTT_TOPIC, json.dumps(msg1))
            logger.debug("Enviado mensaje de energia: ")
            logger.debug(msg1)
            last_time = time.time()  # Reseteamos
        msg2 = {}
        for i in range(len(Z)):
            if (CHANNELS[i] != "NO_USADO"):
                msg2[CHANNELS[i]] = float(Z[i])
        client.publish(MQTT_TOPIC, json.dumps(msg2)) 
        time.sleep(0.5)  # IMP: Es importante este tiempo al menos porque si hubieran 2 mensaje seguidos 
        # uno de ellos no se publicaría en el broker, y fallaria la comprobacion mediante la suscripcion.

    except KeyboardInterrupt as e:
	    printExceptionInfo(e)
	    client.disconnect()
	    ser.close()
	    logger.warning('Keyboard exit')
	    sys.exit("Keyboard exit")    
	    
    except serial.SerialException as e:     # Captura una excepcion relacionada con el puerto serie 
        logger.error('Fallo en la comunicacion con puerto serie. Intentando reconectar...')
        printExceptionInfo(e)
        ser = ''                            # Así forzamos que en el siguiente ciclo vuelva a intentar la comunicación.
        time.sleep(5)
    
    except socket.timeout as e:             # Captura una excepcion relacionada con el puerto serie 
        logger.error("Fallo en la comunicacion con el servidor MQTT. Intentando reconectar...")
        printExceptionInfo(e)
        time.sleep(5)
        client = ''                         # Así forzamos que en el siguiente ciclo vuelva a intentar la comunicación.
    
    except Exception as e:                  # Captura cualquier excepcion no capturada y permitimos que el bucle continue. 
        printExceptionInfo(e)
        time.sleep(1)
        
        
        

