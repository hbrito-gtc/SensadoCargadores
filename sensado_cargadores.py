# Los valores que esta leyendo del modulo LEchacal esta configurado para: Estimated Power in Watts. This is Irms*Vest.
# http://lechacal.com/wiki/index.php?title=Compute_Energy_used_using_a_RPICT+
#
#  PENDIENTE: Revisar las fases !!!. 
#
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

import paho.mqtt.client as mqtt
import serial
import json
import math
from datetime import datetime
import time

ser = serial.Serial('/dev/ttyAMA0', 38400)

client = mqtt.Client("P1")
client.username_pw_set(MQTT_USER, MQTT_PASS)
client.connect(MQTT_SERV)

last_time = time.time()

try:
    while 1:
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
        
 	    # Read one line from the serial buffer
        line = ser.readline()
	    # Remove the trailing carriage return line feed
        line = line[:-2]
	    # Create an array of the data
        Z = line.split(b' ')
	    # Print it for debug
        print(line)
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
        
        #print ("----------")
        #print ("Instant Power1: %s (W)" % Pest_C1)
        #print ("Accum Energy1: %.2f (Wh)" % E_C1)
        #print ("Instant Power2: %s (W)" % Pest_C2)
        #print ("Accum Energy2: %.2f (Wh)" % E_C2)
        #print ("Instant Power3: %s (W)" % Pest_C3)
        #print ("Accum Energy3: %.2f (Wh)" % E_C3)
	
        msg1 = {}
        if ((time.time()-last_time) > 30):
            print("Enviado mensaje de energia")
            msg1["E_C1"] = round(E_C1/1000.0, 2)
            msg1["E_C2"] = round(E_C2/1000.0, 2)
            msg1["E_C3"] = round(E_C3/1000.0, 2)
            msg1["P_C1"] = round(Pest_C1, 2)
            msg1["P_C2"] = round(Pest_C2, 2)
            msg1["P_C3"] = round(Pest_C3, 2)
            client.publish(MQTT_TOPIC, json.dumps(msg1)) 
            last_time = time.time()  # Reseteamos
        msg2 = {}
        for i in range(len(Z)):
            if (CHANNELS[i] != "NO_USADO"):
                msg2[CHANNELS[i]] = float(Z[i])
        client.publish(MQTT_TOPIC, json.dumps(msg2)) 

except KeyboardInterrupt:
	client.disconnect()
	ser.close()
