# Home Assistant smartenergycontrol.be component

Custom component for Home Assistant to calculate hourly prices for all Belgian energy contract on the market



### Sensors
cunsuption and injections prices for all contracts in the datasource. Hourly today and hourly next day when available trought the entso-e intgration. Also a sensor that holds all distributor and government parameters for electricty price calculation.
  
------
## Installation


### Manual
Download this repository and place the contents of `custom_components` in your own `custom_components` map of your Home Assistant installation. Restart Home Assistant and add the integration through your settings. 

### HACS

Add ths repo https://github.com/smartenergycontrol-be/SEC-HA-Integrationto your custom repo's in HACS.
Search for "Smartenergycontrol" and add the HACS integrations. Restart Home Assistant and add the integration through your settings. 
The integration will ask for your postal code (all Belgian postcodes supported) and an API key (contat us if you want access).
The integration will get alle the up-to-date distribution tarifs for Belgiu (taxes, accijnzen, groene stoom WWK, capaciteits tarief etc) depending on where you live. You will be able to add all the existing Enegy contracts (fixed, flible and dynamic) that exist in the V-test from VREG (updated monthly). Select your current contract, add it as current, and select a nummber of other contracts from te list to compare.
See your real daily electricity cost with you existing contract and compare with other contracts or formulas out there.

------
## Configuration

You can choose your current contract en energy distributer trough postal code using the web UI. 

------

#### Updates

The integration is in an early state and receives a lot of updates. If you already setup this integration and encounter an error after updating, please try redoing the above installation steps. 

