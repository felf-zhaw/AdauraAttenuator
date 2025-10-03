# -*- coding: utf-8 -*-
"""
Created on Tue Mar 12 21:57:23 2019

@author: Tristan Steele, tristan.steele@adfa.edu.au
@author: Flavio Felder, felf@zhaw.ch
"""

import serial.tools.list_ports
import serial
import time
from telnetlib import Telnet
import requests

__all__ = ["AdauraAttenuator"]
class AdauraAttenuator(object):
    """A class representing an Attenuator"""

    CONN_USB = "USB"
    CONN_TELNET = "TELNET"
    CONN_HTTP = "HTTP"

    ADAURA_TECH_VID = 0x04D8
    PID_CHANNEL_MAP = {
        0xEEF5: 4,
        0xECA8: 1,
    }

    @staticmethod
    def find_attenuators(vid=ADAURA_TECH_VID, pid=None):
        found_serial_numbers = []
        for pinfo in serial.tools.list_ports.comports():
            if pinfo.vid == vid and (pid == None or pinfo.pid == pid):
                found_serial_numbers.append((pinfo.serial_number, pinfo.device, pinfo.pid))
        return found_serial_numbers

    @staticmethod
    def find_attenuator(requested_serial):
        found_attenuators = AdauraAttenuator.find_attenuators()
        for _serial_number, device, pid in found_attenuators:
            if _serial_number == requested_serial.upper():
                return (_serial_number, device, pid)
        raise IOError('Could not find device with provided serial number.')

    def __init__(self, serial_number=None, baudrate=115200, 
                 connection=CONN_USB, ip_address=None, comport=None, num_channels=None):
        self.serial_number = serial_number
        self._connection_type = connection
        self.status = None

        self.num_channels = num_channels
        self.pid = None

        if self._connection_type == self.CONN_USB:
            if comport == None and serial_number != None:
                # Find a comport given the serial number
                result = AdauraAttenuator.find_attenuator(serial_number)
                self.comport = result[1]
                self.pid = result[2]
            elif comport != None:
                # If comport is given, try to find PID if possible
                ports = serial.tools.list_ports.comports()
                for pinfo in ports:
                    if pinfo.device == comport:
                        self.pid = pinfo.pid
                        break
                self.comport = comport
            else:
                raise Exception("USB Connection requested but no serial number or comport provided.")

            # Set num_channels if not specified
            if self.num_channels == None and self.pid != None:
                if self.pid in self.PID_CHANNEL_MAP:
                    self.num_channels = self.PID_CHANNEL_MAP[self.pid]
                else:
                    raise Exception(f"Unknown PID {self.pid}: cannot determine number of channels.")

            self.location = comport
            
            # Set up a serial port object
            try:
                self._serial = serial.Serial(self.comport, baudrate, timeout=5)
                self._serial.rts = False
            except Exception as ex:
                self.handle_serial_error(ex)

        #### SET UP IF WE ARE CONNECTED OVER ETHERNET            
        if self._connection_type == self.CONN_TELNET:
            assert ip_address != None
            
            # Connect to a remote IP address to control the attenuator.
            self._telnet = Telnet(host = ip_address, port = 23)
            
            # Authenticate
            self._telnet.read_until(b"Login: ")
            self._telnet.write('admin'.encode('ascii') + b"\n")
    
            self._telnet.read_until(b"Password: ")
            self._telnet.write('adaura'.encode('ascii') + b"\n")
            
            time.sleep(1)
            
            # Read the data in the buffer to flush it.
            self.device_flush_buffer()
            
            self.location = ip_address
            
        if self._connection_type == self.CONN_HTTP:
            # Use HTTP Requests to interact with the Attenuator
            assert ip_address != None
            
            self.location = 'http://{}'.format(ip_address)
            self._base_url = self.location
            
    
    def __del__(self):
        """Destructor"""
        try:
            self.close()
        except:
            pass # errors on shutdown
    
    def __str__(self):
        return "ADAURA Attenuator SRN: {}@:{}".format(self.serial_number, self.location)
    
    
    def _extract_from_info_string(self, query_string):
        """
        A helper function to extract a value from the info response.
        Returns None if the string is not found.
        """
        assert self._info_raw_response != None
        matches = [n.split(': ')[1].strip() for n in self._info_raw_response if query_string in n]
        return matches[0] if matches else ""


    def test(self, num):
        self.send_command('saa 90')

        # read 18 lines from the device
        responses = self.receive_response(num)
        for r in responses:
            print(r.strip())

       
    def get_info(self):
        """
        Get the current device information
        """
        
        self.send_command('info')

        # read 18 lines from the device
        responses = self.receive_response(18)

        # Store raw response against object
        self._info_raw_response = responses
        
        response_dict = {}
        
        response_dict['model'] = self._extract_from_info_string('Model: ')
        response_dict['sn'] = self._extract_from_info_string('SN: ')
        response_dict['fw_ver'] = self._extract_from_info_string('FW Ver: ')
        response_dict['fw_date'] = self._extract_from_info_string('FW Date: ')
        response_dict['bl_ver'] = self._extract_from_info_string('BL Ver: ')
        response_dict['mfg_date'] = self._extract_from_info_string('MFG Date: ')
        response_dict['default_attenuations'] = self._extract_from_info_string('Default Attenuations: ').split(" ")

        response_dict['mac_address'] = self._extract_from_info_string('MAC Address: ')
        response_dict['ip_address'] = self._extract_from_info_string('IP Address: ')
        response_dict['ip_subnet'] = self._extract_from_info_string('Subnet: ')
        response_dict['ip_gateway'] = self._extract_from_info_string('Gateway: ')
        response_dict['ip_dhcp'] = self._extract_from_info_string('DHCP: ')
            
        self.serial_number = response_dict['sn']
        
        self.info = response_dict
        
        return response_dict
        

    def get_status(self):
        """
        Get the current attenuation on all channels
        """
        self.send_command('status')
        
        response = self.receive_response(self.num_channels + 1)
        
        channel_values = []

        for ch in range(1,self.num_channels+1): # Loop from 1...num_channels
            this_channel = [n.split(': ')[1].strip() for n in response if 'Channel {}: '.format(ch) in n]
            
            if len(this_channel) > 0:
                channel_values.append(this_channel[0])
        
        self.status = [float(v) for v in channel_values]
        return channel_values
        
    
    def set_attenuator(self, channel, value):
        """
        Set the attenuation on a channel, checking that the response was correct.
        """
        
        tx_string = "set {0} {1}".format(channel, value)
        
        self.send_command(tx_string)
        
        # Get a line of response to determine if it was succesful
        response_one = self.receive_response(2)
        
        if value == 0 or (0.101 > value % 0.1 > 0.099):
            string_val = "{0:.1f}".format(value)
        else:
            # more than 1 decimal place
            string_val = "{0:.2f}".format(value)
        
        expected_response = "Channel {0} successfully set to {1}".format(channel,string_val)
        
        if not any([expected_response in l for l in response_one]):
            # Wasn't succesful, therefore error.
            raise IOError('Invalid attenuation specified.')
        else:    
            # Was succesful, flush the remainder of the response
            self.device_flush_buffer()
    
    
    def set_all_attenuators(self, *values):
        """
        Sets all attenuators to a designated attenuation level. Entering a single attenuation amount will set all 
        channels to that amount. Meanwhile, specifying attenuation levels for each channel in a multi-channel device will 
        set each channel to the specified amount.
        """
        tx_string = "saa {0}".format(" ".join([str(v) for v in values]))
        
        self.send_command(tx_string)

        # Get a line of response to determine if it was succesful
        response_one = self.receive_response(2)
        
        string_vals = []
        for value in values:
            if value == 0 or (0.101 > value % 0.1 > 0.099):
                string_val = "{0:.1f}".format(value)
            else:
                # more than 1 decimal place
                string_val = "{0:.2f}".format(value)
            string_vals.append(string_val)

        if len(string_vals) > 1:
            raise NotImplementedError('Multi-channel set not implemented yet - This is the perfect chance to contribute!')
        
        expected_response = "All channels set to {0}.".format(string_vals[0])

        if not any([expected_response in l for l in response_one]):
            # Wasn't succesful, therefore error.
            raise IOError('Invalid attenuation specified.')
        else:
            # Was succesful, flush the remainder of the response
            self.device_flush_buffer()


    def ramp_attenuators(self, *direction, low, high, step, step_time, mode='info'):
        """
        Fades the attenuation levels across each channel.\n
        direction: 'A' for Ascend, 'B' for Descend, 'E' for Exclude\n
        low: Low end of attenuation range in dB\n
        high: High end of attenuation range in dB\n
        step: Attenuation step in dB\n
        step_time: Time for each step in milliseconds
        """
        if low > high:
            raise ValueError("Low attenuation must be less than or equal to high attenuation.")

        tx_string = "RAMP {0} {1} {2} {3} {4}".format(" ".join(direction), low, high, step, step_time)

        self.send_command(tx_string)

        # Get a line of response to determine if it was succesful
        response_one = self.receive_response(2)

        expected_response = "# of steps: {0}".format(int((high - low) / step))

        if not any([expected_response in l for l in response_one]):
            # Wasn't succesful, therefore error.
            raise IOError(response_one)

        match mode:
            case 'blocking':
                response_one = self.receive_response(6)
                for r in response_one:
                    print(r.strip())
                # print received response every step
                for i in range(low, high, step):
                    time.sleep(step_time / 1000)
                    response_one = self.receive_response(1)
                    for r in response_one:
                        print(r.strip())
                # when the last step is reached
                response_one = self.receive_response(1)
                for r in response_one:
                    print(r.strip())
                
            case 'non-blocking':
                return (((high - low) / step + 0.5)* step_time / 1000 + 0.1)  # Return the time it took to ramp in seconds


    def locate(self):
        """
        Blinks the power LED on the device to locate it physically. 
        """
        self.send_command('locate')

        # Get a line of response to determine if it was succesful
        response_one = self.receive_response(2)
        expected_response = "Blinking the LED for 10 seconds..."

        if not any([expected_response in l for l in response_one]):
            # Wasn't succesful, therefore error.
            raise IOError('Invalid locate command.')
        else:
            # Was succesful, flush the remainder of the response
            self.device_flush_buffer()


    def send_command(self, command):
        """
        Send command to serial port
        """
        if self._connection_type == self.CONN_USB:
            
            if self._serial.is_open:
                try:
                    self._serial.flushInput()
                    # Unicode strings must be encoded
                    data = command.encode('utf-8')
                    self._serial.write(data)
                except Exception as ex:
                    self.handle_serial_error(ex)
            else:
                raise IOError('Try to send data when the connection is closed')
                
        elif self._connection_type == self.CONN_TELNET:
            
            send_command = command + '\n'
            
            self._telnet.write(send_command.encode('utf-8'))
            
        elif self._connection_type == self.CONN_HTTP:
            
            self._http_response = None
            
            cmd_resp = requests.get('{0}/execute.php?{1}'.format(self._base_url, command))
    
            self._http_response = cmd_resp.text

    def receive_response(self, num_lines = 2):
        """
        Read back data
        """
        if num_lines == 0:
            raise ValueError("Number of lines to read must be greater than 0.")

        receive_lines = []
        
        call_time = time.time()
        
        if self._connection_type == self.CONN_USB and self._serial.is_open or self._connection_type == self.CONN_TELNET:
            while True:
                try:
                    response = self.device_read_line()
                    receive_lines.append(response.decode())
                    
                    # Sleep if no data has been received
                    if response == "":
                        time.sleep(0.1)
                
                    if len(receive_lines) >= num_lines:
                        return receive_lines
                    
                    # Check how long this has been running for
                    run_time = time.time() - call_time
                    if run_time > 5:
                        return receive_lines
                    
                except:
                    # Ignore the error, just return it all
                    return receive_lines
                
        elif self._connection_type == self.CONN_HTTP:
            # the response is already stored
            return self._http_response.split('\r\n')

    def device_read_line(self):
        if self._connection_type == self.CONN_USB:
            return self._serial.readline()
        
        elif self._connection_type == self.CONN_TELNET:
            return self._telnet.read_until(b'\n', timeout = 5)
        
    def device_flush_buffer(self):
        if self._connection_type == self.CONN_USB:
            self._serial.flushInput()
        
        elif self._connection_type == self.CONN_TELNET:
            self._telnet.read_very_eager()

                
    def handle_serial_error(self, error=None):
        """
        Serial port error
        """
        # terminate connection
        try:
            self._serial.close()
        except:
            pass
        # forward exception
        if isinstance(error, Exception):
            raise error # pylint: disable-msg=E0702
    
    def close(self):
        """
        Close all resources
        """
        if self._connection_type == self.CONN_USB:
            self._serial.close()
        elif self._connection_type == self.CONN_TELNET:
            self._telnet.close()
