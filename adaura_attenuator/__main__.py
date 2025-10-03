from adaura_attenuator import AdauraAttenuator

#Some example code if running this directly.

found_attenuators = AdauraAttenuator.find_attenuators()

print(f"Found attenuators: {found_attenuators}")

if len(found_attenuators) == 0:
    exit(1)

found_attenuator = found_attenuators[0]
attenuator = AdauraAttenuator(serial_number=found_attenuator[0],comport=found_attenuator[1])
print(f"Attenuator Info: {attenuator.get_info()}")

#HTTP Connection
#attenuator = AdauraAttenuator(ip_address='111.111.111.111', 
#                              connection=AdauraAttenuator.CONN_HTTP,
#                                  )

# Telnet Connection
#attenuator = AdauraAttenuator(ip_address='111.111.111.111', 
#                              connection=AdauraAttenuator.CONN_TELNET,
#                                  )

info = attenuator.get_info()
status = attenuator.get_status()

attenuator.set_attenuator(1, 3)
attenuator.locate()