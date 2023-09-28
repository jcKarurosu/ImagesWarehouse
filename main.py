# Programa para abrir un cerradura simple usando un servomotor para jalar la palanca
# Se dara acceso cuando se detecten 2 huellas validas a traves del sensor de huellas

# Hardware utilizado:
# Tarjeta de control: Raspberry Pico con Micropython
# Sensor de huellas: GROW R503
# Buzzer steren 
# Servomotor Steren MOT-100

#from asyncio.constants import LOG_THRESHOLD_FOR_CONNLOST_WRITES
from machine import UART, Pin, PWM
import time
import jcLibs.r503_sensor

_cServo_pwm_frequency = 50      # 50 Hz for control servomotor
_cServo_Open_position = 9000      # Duty Cycle to set servomotor in Open position
_cServo_Close_position = 1000    # Duti cycle to set servomotor in close position
_cBuzzer_pwm_frequency = 5000   # 5000 Hz for buzzer pwm signal

#Inicializacion ----------------------------------------------------------------------
led = Pin(25, Pin.OUT)	#Inicializa el pin que esta conectado al LED de la tarjeta
#Inicializa puerto serial para comunicarse con el sensor
sensor_uart = UART(0, baudrate=57600, tx=Pin(0), rx=Pin(1), timeout=7)
servo_pwm = PWM(Pin(2))  # PWM signal for Servomotor control
servo_pwm.freq(_cServo_pwm_frequency)
servo_pwm.duty_u16(_cServo_Close_position)
buzzer_pwm = PWM(Pin(4))	# PWM signal for buzzer control
buzzer_pwm.freq(_cBuzzer_pwm_frequency)
buzzer_pwm.duty_u16(0)  # Duty cycle de 0 para iniciar con el buzzer sin sonido
fps_finger_detected = Pin(28, Pin.IN)   # Pin WakeUp del sensor, activo en bajo
led.value(1)		#Enciende LED
time.sleep (0.5)    #El sensor al iniciar tarda 0.2 segundos para inicializarse
led.value(0)

#----------------------------------------------------------------------
#Se crea una instancia del sensor de huellas
try:
    sensor_huellas = jcLibs.r503_sensor.jc_Fingerprint(sensor_uart)
except RuntimeError:
    print("No se pudo inicializar el sensor... ")
    buzzer_pwm.duty_u16(32500)  # Emite pitido en buzzer
    time.sleep(1.5)
    buzzer_pwm.duty_u16(0)  # Apaga buzzer
    while True:
        led.toggle()
        time.sleep(0.5)

def get_FingerPrint():
    """Get a fingerprint image, template it and see if it matches"""
    print("Waiting for image...")
    while sensor_huellas.generate_image() != jcLibs.r503_sensor.Command_OK:
        pass
    print("Templating...")
    if sensor_huellas.gen_char_from_image(1) != jcLibs.r503_sensor.Command_OK:
        return False
    print("Searching...")
    if sensor_huellas.search_finger_lib() != jcLibs.r503_sensor.Command_OK:
        return False
    return True

def enroll_FingerPrint(location):
    """Take a 2 finger images and template it, then store them in location"""
    n_img = 5
    for fp_img in range(1,(n_img+1)):
        if fp_img == 1:
            print(f"Place finger on sensor, scanning finger 1 of {n_img} times", end="")
        else:
            print(f"Place same finger again, scanning finger {fp_img} of {n_img} times", end="")

        while True:
            i = sensor_huellas.generate_image()
            if i == jcLibs.r503_sensor.Command_OK:
                print("Image taken")
                break
            if i == jcLibs.r503_sensor.NoFingerOnSensor:
                print(".", end="")
            elif i == jcLibs.r503_sensor.ImageFail:
                print("Image error")
                return False
            else:
                print("Other error happen")
                return False
        
        print("Templating...", end="")
        i = sensor_huellas.gen_char_from_image(fp_img)  #Argument = Buffer num (1 - 6)
        if i == jcLibs.r503_sensor.Command_OK:
            print("Templated")
        else:
            if i == jcLibs.r503_sensor.FailGenerateCharFile:
                print("Over-disorderly fingerprint image")
            elif i == jcLibs.r503_sensor.FailGenerateCharFile2:
                print("Lackness of character point or over-smallness of fingerprint image")
            elif i == jcLibs.r503_sensor.FailGeneratingImg:
                print("Fail to generate image for the lackness of valid primary image")
            else:
                print("Other error")
            return False

        if fp_img < n_img:
            print("Remove finger")
            time.sleep(1)
            while i != jcLibs.r503_sensor.NoFingerOnSensor:
                i = sensor_huellas.generate_image()

    print("Creating model...", end="")
    i = sensor_huellas.generate_template()
    if i == jcLibs.r503_sensor.Command_OK:
        print("Created")
    else:
        if i == jcLibs.r503_sensor.FailCombineCharFiles:
            print("Prints did not match")
        else:
            print("Other error")
        return False

    print("Storing model #%d..." % location, end = "")
    i = sensor_huellas.store_template(location)
    if i == jcLibs.r503_sensor.Command_OK:
        print("Stored")
    else:
        if i == jcLibs.r503_sensor.PageIDBadLocation:
            print("Bad storage location")
        elif i == jcLibs.r503_sensor.ErrorWritingFlash:
            print("Flash storage error")
        else:
            print("Other error")
        return False

    return True

 # --------------------------------------------------------

led_ctrl = 3    # 0x1-Breathing, 0x2-Flashing, 0x3-AlwaysOn, 0x4-AlwaysOff, 0x5-GraduallyOn, 0x6-GraduallyOff
led_speed = 0   # Speed (1 byte): 0x00 - 0xFF, 256 gears, minimum 5s cycle
led_color = 1   # ColorIndex (1 byte): 1-Red, 2-Blue, 3-Purple, 4-Green, 5-Yellow, 6-Cyan, 7-White, 8-255-Off
led_times = 0   # Times (1 byte): 0-Infinte, 1-255, only in breathing and flashing modes

location_index = 1

#Se enciede 2 veces el aura en color azul y modo breathing para indicar que el sistema
#se ha encendido
sensor_huellas.led_ctrl(1, 128, 2, 2)
b_dummy = 0
servo_pwm.duty_u16(_cServo_Close_position)
buzzer_pwm.duty_u16(32500)  # Emite pitido en buzzer
time.sleep(0.25)
buzzer_pwm.duty_u16(0)  # Apaga buzzer
time.sleep(0.25)
buzzer_pwm.duty_u16(32500)  # Emite pitido en buzzer
time.sleep(0.25)
buzzer_pwm.duty_u16(0)  # Apaga buzzer

# ***********************************************************************
#while True:
#    if b_dummy == 0:
#        b_dummy = 1
#        led.value(1)
#        servo_pwm.duty_u16(_cServo_Open_position)
#        buzzer_pwm.duty_u16(32500)  # Emite pitido en buzzer
#        time.sleep(0.25)
#        buzzer_pwm.duty_u16(0)  # Apaga buzzer
#    else:
#        b_dummy = 0
#        led.value(0)
#        servo_pwm.duty_u16(_cServo_Close_position)
#    time.sleep(5)

# ***********************************************************************

#while True:
#    if fps_finger_detected.value():
#        led.value(1)
#    else:
#        led.value(0)

b_first_finger = False
i = 0
led.value(0)
f_ID_detected = 0
while True:
    # Ciclo principal en el que se espera a que el sensor detecte que se ha colocado algún dedo para escanear la huella
    # si la huella es reconocida se enciene el aura de color azul solicitando asi que se coloque una segunda huella
    # si la 2da huella es reconocida se activa el servomotor para abrir la puerta.
    # si una huella no se reconoce se activa el aura en color rojo
    if fps_finger_detected.value() == 0 and b_first_finger == False:
        led.value(1)
        if get_FingerPrint():
            sensor_huellas.led_ctrl(3, 128, 2, 2)   #Aura: Blue, Mode: Always ON
            b_first_finger = True
            f_ID_detected = sensor_huellas.finger_ID
            while fps_finger_detected.value() == 0:
                time.sleep(0.1)
                i += 1
                if i == 50:
                    sensor_huellas.led_ctrl(2, 60, 2, 0)   #Se pone a parpadear el aura en azul 10 veces para alertar al usuario de que cambie de huella
            if i >= 50:
                sensor_huellas.led_ctrl(3, 128, 2, 2)   #Se deja el aura en un azul fijo solo si se puso en modo parpadeo
        else:
            sensor_huellas.led_ctrl(3, 1, 1, 1) #Aura: Red Always On
            print("Finger not found")
            time.sleep(1)
            while not(fps_finger_detected.value()):
                pass
            sensor_huellas.led_ctrl(4, 1, 1, 1) #Aura: Always Off
    #
    if fps_finger_detected.value() == 0 and b_first_finger == True:
        b_first_finger = False
        if get_FingerPrint():
            if f_ID_detected != sensor_huellas.finger_ID:
                sensor_huellas.led_ctrl(2, 60, 4, 5) # El aura parpadea 5 veces en color verde
                servo_pwm.duty_u16(_cServo_Open_position)   # Abre cerradura
                buzzer_pwm.duty_u16(32500)  # Emite pitido en buzzer
                time.sleep(0.25)
                buzzer_pwm.duty_u16(0)  # Apaga buzzer
                time .sleep(2)
                servo_pwm.duty_u16(_cServo_Close_position)  # Deja de jalar la cerradura - cierra
                print("Detected #", sensor_huellas.finger_ID, "with confidence ", sensor_huellas.confidence)
                while not(fps_finger_detected.value()): # Aseguramos que se quite el dedo para iniciar de nuevo el proceso
                    pass
            else:
                sensor_huellas.led_ctrl(3, 1, 1, 1) #Aura: Red Always On
                print("Finger not found")
                time.sleep(1)
                i = 0
                while fps_finger_detected.value() == 0:
                    time.sleep(0.1)
                    i += 1
                    if i == 50:
                        sensor_huellas.led_ctrl(2, 60, 1, 0)   # Empieza a parpadear infinitamente en rojo
                sensor_huellas.led_ctrl(4, 1, 1, 1) #Aura: Always Off
        else:
            sensor_huellas.led_ctrl(3, 1, 1, 1) #Aura: Red Always On
            print("Finger not found")
            time.sleep(1)
            i = 0
            while fps_finger_detected.value() == 0:
                time.sleep(0.1)
                i += 1
                if i == 50:
                    sensor_huellas.led_ctrl(2, 60, 1, 0)   # Empieza a parpadear infinitamente en rojo
            sensor_huellas.led_ctrl(4, 1, 1, 1) #Aura: Always Off
