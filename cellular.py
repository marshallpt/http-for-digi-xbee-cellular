from digi.xbee.devices import CellularDevice
from digi.xbee.models.protocol import IPProtocol
from digi.xbee.models.message import IPMessage
from digi.xbee.models.atcomm import ATCommand
from ipaddress import IPv4Address
from digi.xbee.exception import TimeoutException
from digi.xbee.exception import TransmitException
from json.decoder import JSONDecodeError
from serial.serialutil import SerialException
from datetime import datetime as dt
from datetime import timezone as tz

import json
import jwt
import time

class HTTPCellular():
    def __init__(self, timeout: int):
        """Figure out which COM port the XBee is on, initialize it, and return it."""
        max_port = 20
        num = 0
        port_prefix = "COM"
        found = False
        while True:
            try:
                # Windows path
                port = f"{port_prefix}{num}"
                self.device = CellularDevice(port, 9600)
                self.device.open()
            except SerialException:
                num += 1
            else:
                found = True
                break
            finally:
                if num >= max_port:
                    break
        
        num = 0
        while not found:
            try:
                print("Trying Linux paths...")
                port_prefix = "/dev/ttyUSB"
                port = f"{port_prefix}{num}"
                self.device = CellularDevice(port, 9600)
                self.device.open()
            except SerialException:
                num += 1
            else:
                break
            finally:
                if num >= max_port:
                    raise OSError(f"The XBee was not found in COM or devttyUSB ports 0-{max_port}.")
        
        self.device.set_sync_ops_timeout(timeout)
        print(f"--------------------------------------------\n"
            f"XBee CellularDevice found on {port_prefix}{num}.\n"
            f"IP Address of the XBee: {self.device.get_ip_addr()}\n"
            f"Timeout of the XBee: {self.device.get_sync_ops_timeout()}\n"
            f"--------------------------------------------")
    
    def __del__(self):
        self.device.close()

    def form_request(self,
                     method: str, 
                     url: str, 
                     data: dict=None,
                     params: dict=None, 
                     headers: dict=None,
                     debug: bool=False) -> str:
        """"Create HTTP request."""
        path = url[url.index('/'):]
        url = url[:url.index('/')]
        request =  f"{method} {path} HTTP/1.1\r\n"

        if headers is not None:
            body = ""
            for key, value in headers.items():
                body += f"{key}: {value}\r\n"
            request += body

        request += f"Host: {url}\r\n"

        content_type = "x-www-form-urlencoded"
        content_length = ""
        param_stuff = ""
        if params is not None:
            param_stuff = self.form_params(params)
            param_stuff += "\r\n\r\n"
            content_length = f"Content-Length: {len(param_stuff)}\r\n"

        data_stuff = ""
        if data is not None:
            data_stuff = "{\r\n"
            for key,value in data.items():
                data_stuff += f'  "{key}": {value},\r\n'
            data_stuff = data_stuff[:-3] + "\r\n}\r\n"
            content_type = "json"
            content_length = f"Content-Length: {len(param_stuff)+len(data_stuff)}\r\n"

        
        request += (f"Content-Type: application/{content_type}\r\n"
                    f"{content_length}\r\n"
                    f"{param_stuff}{data_stuff}")

        if debug:
            print(request)
        return f"{request}\r\n"

    def send_request(self,
                     method: str, 
                     url: str, 
                     data: dict=None,
                     params: dict=None, 
                     headers: dict=None,
                     max_attempts: int=5,
                     debug: bool=False) -> dict:
        """Send HTTP Request, return dict of response + amt of attempts it took."""

        url = url.replace("https://", "")
        url = url.replace("http://", "")
        request = self.form_request(method=method, 
                            url=url,
                            data=data,
                            params=params,
                            headers=headers)
        send_attempts = 1
        receive_attempts = 1
        response = ""
        while True:
            try:
                self.device.send_ip_data(ip_addr=self.get_ip(url=url), 
                                         dest_port=443, 
                                         protocol=IPProtocol.TCP_SSL, 
                                         data=request)
                while True:
                    ip_data = self.device.read_ip_data(timeout=20)
                    response += ip_data.data.decode('utf8')
                    try:
                        response = self.extract_response(response)
                        response = json.loads(response)
                    except (JSONDecodeError, ValueError):
                        """Wait for the next loop iteration."""
                        if debug:
                            print(f"One read was not enough...{response}")
                    else:
                        """Data read has completed!"""
                        break
                    finally:
                        receive_attempts += 1
                        if receive_attempts >= 20:
                            raise JSONDecodeError("Nothing received within 20 attempts.")
                
            except JSONDecodeError as e:
                print(f"WARNING: attempt {send_attempts} resulted in mal-formed JSON. {e}")
                if debug:
                    print(f"Here's what the response looked like: {response}")
                print("Retrying...")
                send_attempts += 1
            except ValueError as e:
                print(f"WARNING: attempt {send_attempts} did not result in any JSON. {e}")
                if debug:
                    print("Here's what the IPMessage object looked like:")
                    print(ip_data.data.decode("utf8"))
                print("Retrying...")
                send_attempts += 1
            except TimeoutException as e:
                print(f"WARNING: attempt {send_attempts} timed out. {e}")
                print("Retrying...")
                send_attempts += 1
            except TransmitException as e:
                print(f"WARNING: attempt {send_attempts} resulted in a transmit exception. {e}")
                print("Retrying...")
                send_attempts += 1
            else:
                break
            finally:
                if send_attempts == max_attempts+1:
                    print(f"FAILURE: max attempts {send_attempts-1} reached!")
                    break
                
        return response, send_attempts

    def get_ip(self, url: str) -> IPv4Address:
        """Perform DNS lookup."""
        domain = url[:url.index('/')]

        at_command = ATCommand(command="LA", parameter=domain)
        response = self.device._send_at_command(at_command, apply=True)
        self.device._check_at_cmd_response_is_valid(response=response)
        bytestring = response.response
        address = IPv4Address(f"{bytestring[0]}.{bytestring[1]}.{bytestring[2]}.{bytestring[3]}")
        return address

    def extract_response(self, ip_data: IPMessage)-> str:
        """IPMessage contains a lot of stuff we don't need - this
        returns the JSON content of the response."""
        # Converts from bytestring to str for parsing
        # decoded = ip_data.data.decode("utf8")
        decoded = ip_data
        
        # this assumes there is no opening bracket prior 
        # to the JSON content in the IPMessage object - I can't 
        # find info on how it's structured, but this seems to work
        response = decoded[decoded.index('{'):].strip()

        return response

    def form_params(self, params: dict)-> str:
        param_stuff = ""
        for key, value in params.items():
            param_stuff += f"{key}={value}&"
        param_stuff=param_stuff[:-1]
        return param_stuff
    
class CellularSpreadsheet():
    def __init__(self, spreadsheet_id: str):
        self.spreadsheet_id = spreadsheet_id
        self.http_device = HTTPCellular(timeout=20)
        self.scope = "https://www.googleapis.com/auth/spreadsheets"
        self.token = self._init_auth()
        self.auth_time = time.time()
        print("Auth token received!")
    
    def form_jwt(self, email:str, scope:str, private_key:str) -> str:
        """Return encoded JSON Web Token."""
        iat = dt.now(tz=tz.utc).timestamp()
        payload = {
            "iss": email,
            "scope": scope,
            "aud": "https://oauth2.googleapis.com/token",
            "exp": iat + 3600,
            "iat": iat
        }
        encoded_jwt = jwt.encode(payload, private_key, algorithm="RS256")
        # on linux, jwt.encode returns a bytearray, whereas on Windows
        # it returns a string
        if type(encoded_jwt) == bytearray:
            encoded_jwt = encoded_jwt.decode("UTF-8")
        return encoded_jwt

    def get_token(self,
                  email:str,
                  scope:str, 
                  private_key:str)-> str:
        """Return OAuth access token."""
        jwt = self.form_jwt(email=email, scope=scope, private_key=private_key)
        url = "https://oauth2.googleapis.com/token"
        params = {'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
                'assertion': jwt}
        # response = requests.post(url, data=params)
        response, attempts = self.http_device.send_request(method="POST", 
                                                    url=url,
                                                    params=params)
        return response['access_token']
    
    def _init_auth(self):
        with open("service_account.json") as f:
            service_account = json.load(f)
        
        token = self.get_token(email=service_account["client_email"],
                               scope=self.scope, 
                               private_key=service_account["private_key"])
        return token

    def get(self, range=None):
        self.check_auth()
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{self.spreadsheet_id}/"
        headers = {"Authorization": f"Bearer {self.token}"}
        if range == None:
            r, attempts = self.http_device.send_request(method="GET", 
                                                        url=url,
                                                        headers=headers)
        else:
            url += f"values/{range}"
            r, attempts = self.http_device.send_request(method="GET", 
                                                        url=url,
                                                        headers=headers)
        return r
    
    def append(self, values, range):
        self.check_auth()
        params = {
            "valueInputOption" : "USER_ENTERED",
            "insertDataOption" : "OVERWRITE"
        }
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{self.spreadsheet_id}/"
        url += f"values/{range}:append"
        url += f"?{self.http_device.form_params(params=params)}"
        headers = {"Authorization": f"Bearer {self.token}"}
        data = {
            "range": f'\"{range}\"',
            "majorDimension": '\"ROWS\"',
            "values": values
        }
        
        r, attempts = self.http_device.send_request(method="POST", 
                                                    data=data,
                                                    url=url,
                                                    headers=headers)
        return r

    def __del__(self):
        del self.http_device

    def check_auth(self):
        if time.time() - self.auth_time > 3600:
            # if more than an hour has passed, we need new token
            print("More than an hour has passed, re-authenticating...")
            self.token = self._init_auth()

def main():
    spreadsheet_id = "your-speadsheet-id-here"
    spreadsheet = CellularSpreadsheet(spreadsheet_id=spreadsheet_id)
    
    print("Updating spreadsheet...")
    # values NEEDS TO BE A 2D ARRAY.
    print(spreadsheet.append(values=[["james2", "rocks"]],range="A5:B5"))
    
    # We don't need this for JAMES2 - this was just for testing / completeness
    print("Getting the whole spreadsheet...")
    print(spreadsheet.get())

if __name__ == "__main__":
    main()
