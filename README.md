# Gasoline Custom Component

Home Assistant Custom Component to Track Gasoline Prices

## Installation

Move the folder gasoline under `<ha-config-dir>/custom_components/gasoline`.

In the config create a section in `sensor`

```
sensor:

  - platform: gasoline
    interval: 1
    stations:
       - name: "Star E/St"
         id: 3562
       - name: "HEM E/St"
         id: 12892
       - name: "Markant Bo"
         id: 761
```

The id are the ids from clever-tanken.de, whereas you select one station. For example in the URL the ID here:
```
https://www.clever-tanken.de/tankstelle_details/11391
```
is 11391.
