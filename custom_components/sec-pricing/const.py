"""Constants for the Leveranciers integration."""

DOMAIN = "leveranciers"

ENTSOE_API_KEY = ""
ENTSOE_REGION = "BE"
# vast €/kwh, vast voor vl, wal en brus Lager tarief volgens verbruik op jaarbasis: : 0-20.000 kWh: 1,4210 c€/kWh, 20.001-50.000 kWh: 1,2090 c€/kWh
BIJZ_ACCIJNS = 0.014210  #
# Bijdrage Energiefonds (€/maand)
ENERGIEFONDS_RES = 0
ENERGIEFONDS_NIET_RES = 9.57
# bijdrage op de energie vl 0.1926, wal 0.1926 bru 0.1926 c€/kwh
BIJDRAGE_ENERGIE = 0.001926  #
# aansluitingsvergoeding (vl 0, wal 0.075, bru 0.1926 c€/kwh
AANSLUITINGSVERGOEDING = 0.00075  #
# Groene certificaten (c€/kWh) vl 1.14 wal 2.86 bru 2.67
GSC = 0.0114  #
# WKK 0.4(c€/kWh)*
WKK = 0.004  #
