# Home Assistant smartenergycontrol.be component

Custom component for Home Assistant to calculate hourly prices for all Belgian energy contract on the market



### Sensors
cunsuption and injections prices for all contracts in the datasource. Hourly today and hourly next day when available trought the entso-e intgration. Also a sensor that holds all distributor and government parameters for electricty price calculation.
  
------
## Installation


### Manual
Download this repository and place the contents of `custom_components` in your own `custom_components` map of your Home Assistant installation. Restart Home Assistant and add the integration through your settings. 

### HACS

Search for "" when adding HACS integrations and add "Smartenergycontrol". Restart Home Assistant and add the integration through your settings. 

------
## Configuration

You can choose your current contract en energy distributer trough postal code using the web UI. 

------

#### Updates

The integration is in an early state and receives a lot of updates. If you already setup this integration and encounter an error after updating, please try redoing the above installation steps. 

