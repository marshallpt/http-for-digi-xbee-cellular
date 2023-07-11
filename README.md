# HTTP / Google Sheets For Digi XBee Cellular
Archive of my HTTP requests implementation for the 
[Digi XBee Cellular Modem](https://www.digi.com/products/models/xk3-c-a2-t-ub) to 
interface with Google Sheets. This was written for my senior capstone project, 
[JAMES2](https://drive.google.com/file/d/1XdHSq_d-kd0wOfchhkvFJ0ObRg7Xfi57/view):
an autonomous river drifter. It took a lot of trial and error to figure a lot of this out, as it was difficult finding example code online. Hopefully by archiving this publicly, it can assist others in the future.


# Background
Utilizing the Digi XBee Cellular with HTTP requests was inspired by 
[this tutorial](https://www.digi.com/resources/documentation/Digidocs/90002253/Tasks/t_get_http.htm?tocpath=XBee%20connection%20examples%7C_____5) for a GET request
on the Digi documentation. I learned how to form my own HTTP requests using 
[this wonderful website](https://reqbin.com/req/nfilsyk5/get-request-example).
I've never utilized Google APIs before, so it took a good amount of digging to
find an auth type that worked for a fully autonomous modality. 
I finally landed on OAuth2 through a 
[service account authenticated via HTTP-REST.](https://developers.google.com/identity/protocols/oauth2/service-account#httprest) 

For **HTTPCellular()**, I tended to to replicate the interface of the 
[Python Requests library](https://docs.python-requests.org/en/latest/) 
when possible, as this is the HTTP requests library I'm the most familiar with.
This can be seen in *send_request()* where `data`, `params`, and `headers` are parameters passed as dictionaries, similar to Python Requests. 

# Usage
## Dependencies
To install the dependencies, in your virtual environment, run:

`pip install -r requirements.txt`

## Classes
### HTTPCellular()
Adds HTTP features to *digi-xbee*'s 
[**CellularModem()**](https://xbplib.readthedocs.io/en/latest/api/digi.xbee.devices.html#digi.xbee.devices.CellularDevice)
class. On linux, requires user to be a part of the *dialout* group to access the USB 
ports. To do  so, use the following command (found 
[here](https://meshtastic.discourse.group/t/question-on-permission-denied-dev-ttyusb0/590/7)):

`sudo usermod -a -G dialout <username>`

After performing this command, log out and back in.

### CellularSpreadsheet()
Utilizes **HTTPCellular()** to update a Google Spreadsheet via 
[REST requests](https://developers.google.com/sheets/api/reference/rest). 
*main()* shows an example of it in action. 
**Requires `service_account.json`** to authenticate with Google. To get these credentials:

1. [Create a Google Cloud project](https://developers.google.com/workspace/guides/create-project).
2. [Create a Service Account](https://developers.google.com/identity/protocols/oauth2/service-account#creatinganaccount)
 within that project.
3. Create and download a service account key (instructions for which are in the link for #2).
4. Rename the .json file to `service_account.json`.
5. Place `service_account.json` in the same directory as `cellular.py`.

Once the service account is created and credentials are downloaded, it 
**must be added with edit access to the spreadsheet being edited**, as well.
 This is done in the same way as sharing a spreadsheet with any other user.

# Examples
## Performing a GET request
Doing the same GET request as described in the 
[Digi tutorial](https://www.digi.com/resources/documentation/Digidocs/90002253/Tasks/t_get_http.htm?tocpath=XBee%20connection%20examples%7C_____5) 
referenced previously.
```python
http_device = HTTPCellular(timeout=10)
url = "https://httpbin.org/ip"
r, num_attempts = http_device.send_request(method="GET", 
                                           url=url)
print(r)
```
## Performing a POST request
Performing a POST request, as can be seen in the *append()* method of the 
**CellularSpreadsheet()** class.
```python
http_device = HTTPCellular(timeout=10)
url = "https://example.website"
token = "your-token-here"
headers = {"Authorization": f"Bearer {token}"}
data = {
    "james2": "rocks"
}

r, num_attempts = http_device.send_request(method="POST", 
                                           data=data,
                                           url=url,
                                           headers=headers)
print(r)
```
## Appending a spreadsheet and printing its contents
As seen in *main()* of `cellular.py`.
```python
spreadsheet_id = "your-speadsheet-id-here"
spreadsheet = CellularSpreadsheet(spreadsheet_id=spreadsheet_id)

print("Updating spreadsheet...")
# values NEEDS TO BE A 2D ARRAY.
print(spreadsheet.append(values=[["james2", "rocks"]],range="A5:B5"))

# We don't need this for JAMES2 - this was just for testing / completeness
print("Getting the whole spreadsheet...")
print(spreadsheet.get())
```