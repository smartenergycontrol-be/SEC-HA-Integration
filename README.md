# Home Assistant smartenergycontrol.be component

Custom component for Home Assistant to calculate hourly prices for all Belgian energy contract on the market



### Sensors
The integration adds the following sensors:
- Average Day-Ahead Electricity Price Today (This integration carries attributes with all prices)
- Highest Day-Ahead Electricity Price Today
- Lowest Day-Ahead Electricity Price Today
- Current Day-Ahead Electricity Price
- Current Percentage Relative To Highest Electricity Price Of The Day
- Next Hour Day-Ahead Electricity Price
- Time Of Highest Energy Price Today
- Time Of Lowest Energy Price Today
  
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

