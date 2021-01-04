# WebAPA

The objectives of the WebAPA component are to store observations data from the APA server in a georeferenced database. Besides storage, it offers an API for developing web applications with geospatial data.

WebAPA architecture is illustrated in figure below. The backend part is responsible to get and manage the data. The User Interface allows the user to download the data for all available years.

![WebAPA Diagram](https://github.com/FMMFHD/WebAPA/blob/main/img_readme/WebAPA_diagram.png)

There are some problems with the data downloaded from the APA server. The data is accessed by HTTP, because there are no web services to collect this data. To download the excel file it is necessary to select several inputs, because the downloaded data from APA is stored in excels files, one file per station/year. The only way to download the data is to replicate the interactions of the user through HTTP, using web scrapping, a technique used for extracting data from websites. To store the downloaded files, a method from the GeoExcel module is used to upload the excel files to the database. These files do not have information about the station location. So, it is necessary to get the locations of each station and then relate that information with pollutant concentrations from the air quality stations.

The data management is simple because the data is stored in the database. This data is only replaced by the system administrator that uses the user interface. To access the data, it is only necessary to create SQL statements to filter data that is stored in the database.

The data is divided by years at the APA server. Therefore, the objective of the user interface is to allow the admin user to select a year to download the data from the APA server. This process is time-consuming because it is necessary to download many files. The communication channel between the interface and the server is not indefinitely open. Thus, this interface has a limitation, because the user might never receive a success or error message, not knowing whether the execution was a success or not. To confirm that the data has been downloaded, the interface provides an input text and a button that allows this verification.

API is an interface that the programmer can use to obtain data. The available access points allow the programmer to obtain: a list of all the pollutants measured in a given station; a list of all the observations for a given station, pollutant, date, and temporal resolution.