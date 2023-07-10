# HTTP For Digi XBee
Archive of my HTTP requests implementation for the Digi XBee Cellular Modem to 
interface with Google Sheets. This was written for my senior capstone project, JAMES2.
 It took 
a lot of trial and error to figure a lot of this out, it was difficult finding any 
example code online. Hopefully by archiving this here, it can save someone else save
time later.

# Background
Utilizing the Digi XBee Cellular with HTTP requests was inspired by 
[this tutorial](https://www.digi.com/resources/documentation/Digidocs/90002253/Tasks/t_get_http.htm?tocpath=XBee%20connection%20examples%7C_____5) for a GET request
on the Digi documentation. I learned how to form my own HTTP requests using 
[this wonderful website](https://reqbin.com/req/nfilsyk5/get-request-example).
I've never utilized Google APIs before, so it took a good amount of digging to
find an auth type that worked for a fully autonomous modality. I finally landed on OAuth2 through a [service account authenticated via HTTP-REST.](https://developers.google.com/identity/protocols/oauth2/service-account#httprest) 
As described below, this requires a service account be created in Google Cloud Console
and for it to be added as a collaborator onto the Google Sheets spreadsheet that is
being accessed, in the same way you'd share a Google Sheets spreadsheet with anyone 
else. Once that service account is created, one downloads the credentials for it in
a .JSON format for **CellularSpreadsheet()** class to consume and you're off to the
races.

# Usage
To install the dependencies, in your virtual environment, run:

`pip install -r requirements.txt`

The various communications protocols have their own authentication requirements. Be sure
to check the appropriate section below for utilizing those.

# Classes
## HTTPCellular()
Adds HTTP features to *digi-xbee*'s CellularModem() class. On linux, 
requires user to be a part of the *dialout* group to access the USB 
ports. To do  so, use the following command (found from 
[here](https://meshtastic.discourse.group/t/question-on-permission-denied-dev-ttyusb0/590/7)):

`sudo usermod -a -G dialout <username>`

After performing this command, log out and back in.

## CellularSpreadsheet()
Utilizes **HTTPCellular()** to update a Google Spreadsheet via 
[REST requests](https://developers.google.com/sheets/api/reference/rest). 
*main()* shows an example of it in action. 
**Requires a `service_account.json` file** in the root of the directory. This must be generated from
the Google Cloud console. This service account **must be added with edit access to the spreadsheet being edited**, as well.
