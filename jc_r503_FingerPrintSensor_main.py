# Programa para abrir un cerradura simple usando un servomotor para jalar la palanca
# Se dara acceso cuando se detecten 2 huellas validas a traves del sensor de huellas

# Hardware utilizado:
# Tarjeta de control: Raspberry Pico con Micropython
# Sensor de huellas: GROW R503

# ESTA VERSION NO INCLUYE EL SERVOMOTOR NI EL BUZZER, ES LA VERSION BASE SOBRE LA 
# QUE SE CONSTRUYO EL PROGRAMA COMPLETO

#from asyncio.constants import LOG_THRESHOLD_FOR_CONNLOST_WRITES
from machine import UART, Pin
import time
import jcLibs.r503_sensor

#Inicializacion ----------------------------------------------------------------------
led = Pin(25, Pin.OUT)	#Inicializa el pin que esta conectado al LED de la tarjeta
#Inicializa puerto serial para comunicarse con el sensor
sensor_uart = UART(0, baudrate=57600, tx=Pin(0), rx=Pin(1), timeout=7)
led.value(1)		#Enciende LED
time.sleep (0.5)    #El sensor al iniciar tarda 0.2 segundos para inicializarse
led.value(0)

#----------------------------------------------------------------------
#Se crea una instancia del sensor de huellas
sensor_huellas = jcLibs.r503_sensor.jc_Fingerprint(sensor_uart)

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

while True:
    print(" ----------------- ")
    if sensor_huellas.read_templates() != jcLibs.r503_sensor.Command_OK:
        raise RuntimeError("Failed to read templates")
    print("Fingerprint templates: ", sensor_huellas.templates)
    print("0) set security level")
    print("1) enroll print")
    print("2) find print")
    print("3) delete print")
    print("4) Control aura (led)")
    print("5) Read Fingerprint template index table")
    print(" ----------------- ")

    c = int(input("> "))

    if c == 0:
        print("Current security level -> ", end="")
        print(sensor_huellas.security_level)
        x = int(input("Enter new security level (1 - 5): "))
        if sensor_huellas.set_SysParam(5, x) == jcLibs.r503_sensor.Command_OK:
            if sensor_huellas.read_SysParam() != jcLibs.r503_sensor.Command_OK:
                print("There is something wrong with sensor (ReadSysParam) . . .")
            #
            print("Security level -> ", end="")
            print(sensor_huellas.security_level)
            if sensor_huellas.security_level == x:
                print("New security level set correctly!")
            else:
                print("Looks like something happened while trying to set new security level :/")
        else:
            print("Something went wrong while setting security level :/")
    elif c == 1:
        sensor_huellas.led_ctrl(1, 128, 5, 1)   #Aura: yellow breathing
        sensor_huellas.led_ctrl(3, 1, 5, 1)
        enroll_FingerPrint(location_index)
        location_index += 1
        sensor_huellas.led_ctrl(6, 128, 5, 1)   #Aura: Gradually Off
    elif c == 2:
        if get_FingerPrint():
            sensor_huellas.led_ctrl(2, 128, 4, 2)   #Aura: Green, 2 times flashing
            print("Detected #", sensor_huellas.finger_ID, "with confidence ", sensor_huellas.confidence)
        else:
            sensor_huellas.led_ctrl(3, 1, 1, 1) #Aura: Red Always On
            print("Finger not found")
            time.sleep(1)
            sensor_huellas.led_ctrl(4, 1, 1, 1) #Aura: Always Off
    elif c == 3:
        if location_index > 1:
            location_index -= 1
            if sensor_huellas.delete_template(location_index) == jcLibs.r503_sensor.Command_OK:
                print("Deleted!")
            else:
                print("Failed to delete :(")
        else:
            print("There is no print to delete (index = 1)")
    elif c == 4:
        #Turn On LED
        print("Enter the 4 parameters for LED control...")
        led_ctrl = int(input("LED ctrl: 1-Breathing, 2-Flashing, 3-On, 4-Off, 5-GraduallyOn, 6-GraduallyOff: "))
        led_speed = int(input("LED Speed: 0 - 255: "))
        led_color = int(input("LED color: 1-Red, 2-Blue, 3-Purple, 4-Green, 5-Yellow, 6-Cyan, 7-White, 8-255-Off: "))
        led_times = int(input("LED times: 0-Infinte, 1-255, only works in breathing and flashing modes: "))
        #
        if sensor_huellas.led_ctrl(led_ctrl, led_speed, led_color, led_times) != jcLibs.r503_sensor.Command_OK:
            print("Error in aura control command... ")
        time.sleep(3)
    elif c == 5:
        #Read fingerprint template index table (0x1F)
        if sensor_huellas.read_templates() == jcLibs.r503_sensor.Command_OK:
            if not sensor_huellas.templates:
                print("Templates Library is empty")
                location_index = 1
            else:
                print("Valid templates are stored in next positions: ")
                print(sensor_huellas.templates)
                location_index = max(sensor_huellas.templates) + 1
            print(f"Location_index value updated to: {location_index}")
        else:
            print("Error while reading fingerprint templates index table")
    else:
        print("Invalid choice: Please try again")

print("----------- PROGRAMA TERMINADO -------------------")