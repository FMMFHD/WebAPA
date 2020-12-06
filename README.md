# WebAPA

  Module that get the data from the APA database and saved it on the local database. It makes the connection between the stored APA data and the apps.

  Output of the data for APA graphics = 
  
  {

    "resolution": Temporal resolution,

    "apa_gas": id of the gas in the APA database,

    "<county> or <region>": County/Region Name,

    "station_name": Station Name
    
    "data": {

      "APA_GAS_NAME": Name of the gas according with the APA database,

      "x_line": Array of dates,

      "max_line": Array of max values,

      "min_line": Array of min values,

      "mean_line": Array of mean values,

      "std": Array of standard deviation values,

      "std_minus": Array of values (mean - std),

      "std_plus": Array of values (mean + std),

    }
  }
