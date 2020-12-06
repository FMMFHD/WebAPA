from bs4 import BeautifulSoup
import pandas as pd
import requests
from requests.auth import HTTPBasicAuth
import tempfile
import re

from General_modules.module_access_external import request_Data_External_Source
from General_modules.module_GeoServer_access import checkWorkspace, verify_datastore, checkFeature, get_url_user_pwd_geoserver, headers_xml
from General_modules.module_logs import log_logs_file, log_error_file
import General_modules.global_settings as global_settings
from GeoExcel.module_excel import copy_excel_database


user = 'admin'
pwd = 'geoserver'
gs_rest_url = 'http://localhost:8080/geoserver/rest'

APA_website = "https://qualar.apambiente.pt"

db_user = global_settings.POSTGRESQL_USERNAME
db_password = global_settings.POSTGRESQL_PASSWORD
db_host = global_settings.POSTGRESQL_HOST
db_port = global_settings.POSTGRESQL_PORT
path = global_settings.EXTERNAL_PATH
Database = global_settings.DB_NAME_EMEP_APA


def init_formData(rede, estacao, ano):
    form_data = {}
    form_data['rede'] = rede
    form_data['estacao'] = estacao
    form_data['ano'] = ano
    form_data['day0'] = 1
    form_data['month0'] = 1
    form_data['day1'] = 31
    form_data['month1'] = 12
    return form_data


def convertDegreeToDecimal(number):
    """
        Converte graus,minutos,segundos para um valor decimal
    """
    if len(number.split("-")) == 1:
        positive = True
    else:
        positive = False

    split = number.split("\u00b0")
    d = float(split[0])    #Degree
    split = split[1].split("'")
    m = float(split[0])   #minute
    s = float(split[1].split('"')[0])  #second
    if positive:
        return d + (m/60) + (s/3600)
    else:
        return -1*(-1*d + (m/60) + (s/3600))


def get_csv_stations_APA(Path_save_csv):
    """
        Get the csv with stations information from the APA website
    """
    response = request_Data_External_Source('GET', APA_website + "/qualar/estacoes")

    link_csv = None

    if response is not None:
        soup = BeautifulSoup(response.text, "lxml")
        gdp_div_exports = soup.find("div", attrs={"class": "w2p_export_menu"})

        for option in gdp_div_exports.find_all("a"):
            if 'CSV' in option.contents[0] and len(option.contents[0]) > len('CSV'):
                link_csv = option['href']
                break

        if link_csv is not None:
            response = request_Data_External_Source('GET', APA_website + link_csv)

            if response is not None and response.status_code == 200:
                with open(Path_save_csv, "w") as f:
                    f.write(response.text)


def create_excel(Path_save_csv, Path_save_excel):
    """
        Create a new excel from the csv
    """
    dataframe_apa_csv = pd.read_csv(Path_save_csv)

    data_stations = {}

    data_stations['Id_estacao'] = list(dataframe_apa_csv['v_estacoes_metadados.estacao_id'])

    names = []

    Influencia = []

    estacao_nome_csv = list(dataframe_apa_csv['v_estacoes_metadados.estacao_nome'])

    influencia_nome_csv = list(dataframe_apa_csv['v_estacoes_metadados.influencia_nome'])

    for i in range(len(estacao_nome_csv)):
        
        names.append(estacao_nome_csv[i].encode('latin-1').decode('unicode_escape').encode('latin-1').decode('utf-8'))
        Influencia.append(influencia_nome_csv[i].encode('latin-1').decode('unicode_escape').encode('latin-1').decode('utf-8'))

    data_stations['name'] = names

    data_stations['Influencia'] = Influencia

    data_stations['Lat'] = list(dataframe_apa_csv['v_estacoes_metadados.latitude'])

    data_stations['Long'] = list(dataframe_apa_csv['v_estacoes_metadados.longitude'])

    add_deactivate_stations(data_stations)

    df = pd.DataFrame(data=data_stations)

    xlwriter = pd.ExcelWriter(Path_save_excel, engine='xlsxwriter')

    df.to_excel(xlwriter, index=False)
    
    worksheet = xlwriter.sheets['Sheet1']

    xlwriter.save()
    # xlwriter.close()


def add_deactivate_stations(data_stations):
    """
        Get information about deactivate stations from the sit https://qualar1.apambiente.pt/qualar/index.php?page=4&subpage=2
    """
    names = []
    latitudes = []
    longitudes = []
    influencias = []
    ids = []

    count = 0

    init_url = "https://qualar1.apambiente.pt/qualar/"

    response = request_Data_External_Source('GET', init_url + "index.php?page=4&subpage=2") 

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "lxml")

        _input = soup.find_all('script', language='JavaScript')[0].prettify() 

        informations = re.findall(r"if \(artist == '(.*)'\) {[\n]*      if\(reloading\) {([^\{]*)}", _input)

        for info in informations:

            informations_station = re.findall(r"opt\('([\w]*)', '(.*)','(.*)'\)" ,info[1])

            for info_station in informations_station:
                _id_ = int(info_station[0])
                if _id_ not in data_stations['Id_estacao'] and _id_ not in ids:
                    name = ""
                    influencia = ""
                    latitude = 0.0
                    longitude = 0.0
                    _id = 0
                    get_longitude = False
                    
                    response1 = request_Data_External_Source('GET', init_url + info_station[1])
                    # print(init_url + info_station[1])

                    if response1 is not None and response1.status_code == 200:
                        soup1 = BeautifulSoup(response1.text, "lxml")
                        table = soup1.find_all('table')[5]
                        # table_body = table.find('tbody')
                        rows = table.find_all('tr')
                        for row in rows:
                            cols = row.find_all('td')
                            cols = [ele.text.strip() for ele in cols]
                            
                            if 'Tipo de Influência' in cols[0]:
                                influencia = cols[1].encode('latin-1').decode('unicode_escape').encode('latin-1').decode('utf-8')

                            if len(cols) == 3:
                                if 'WGS84' in cols[0]:
                                    if 'Latitude' in cols[1]:
                                        try:
                                            latitude = convertDegreeToDecimal(cols[2].encode('latin-1').decode('unicode_escape').encode('latin-1').decode('utf-8'))
                                        except:
                                            latitude = None

                                        get_longitude = True
                            
                            if get_longitude:
                                if 'Longitude' in cols[0]:
                                    get_longitude = False
                                    try:
                                        longitude = convertDegreeToDecimal(cols[1].encode('latin-1').decode('unicode_escape').encode('latin-1').decode('utf-8'))
                                    except:
                                        longitude = None

                            if 'Código' in cols[0]:
                                _id = int(cols[1])
                                
                        name = soup1.find_all('h3')[0].text.encode('latin-1').decode('unicode_escape').encode('latin-1').decode('utf-8')
                        
                        count += 1
                        # print(count, _id_, _id, _id_ == _id, latitude, longitude, name, influencia)
                        if _id_ == _id and longitude is not None and latitude is not None:
                            names.append(name)
                            latitudes.append(latitude)
                            longitudes.append(longitude)
                            influencias.append(influencia)
                            ids.append(_id)
                        else:
                            log_error_file("ERROR: station: {}".format(name))
                        
    data_stations['name'] += names
    
    data_stations['Influencia'] += influencias

    data_stations['Lat'] += latitudes

    data_stations['Long'] += longitudes

    data_stations['Id_estacao'] += ids


def check_estacoes(html, ids_estacao, ids_rede, id_rede):
    soup = BeautifulSoup(html, "lxml")
    gdp_select = soup.find("select", attrs={"name": "estacao"})
    for option in gdp_select.find_all("option"):
        if int(option['value']) != -1:
            try:
                index = ids_estacao.index(int(option['value']))
            except Exception as e:
                print(e)
                continue
            
            ids_rede[index] = id_rede


def update_estacoes(path_excel):
    """
        Add the id of network that each station belongs to excel
    """
    estacoes_info = pd.read_excel(path_excel)
    ids_rede = [0] * len(estacoes_info[list(estacoes_info.columns)[0]])
    # print(estacoes_info.columns)
    response = request_Data_External_Source('GET', "https://qualar1.apambiente.pt/qualar/index.php?page=6")
    if response is not None:
        soup = BeautifulSoup(response.text, "lxml")
        gdp_select = soup.find("select", attrs={"name": "rede"})
        for option in gdp_select.find_all("option"):
            if int(option['value']) != -1:
                form_data = init_formData(int(option['value']), -1, -1)
                response = request_Data_External_Source('POST', "https://qualar1.apambiente.pt/qualar/index.php?page=6&subpage=", data=form_data)
                if response is None:
                    continue
                check_estacoes(response.text, estacoes_info['Id_estacao'].tolist(), ids_rede, int(option['value']))
                
        estacoes_info['Id_rede'] = ids_rede
        estacoes_info.to_excel(path_excel, index=False)
    

def create_sql_stations_loc(tableName, dataframe, fileName, information, decimal=True):
    """
        Create the sql to save the data of the stations in the database
    """
    keys = '"Id_rede", "Id_estacao", "Location", "Name", "Tipo"'
    sql = ""
    for index, row in dataframe.iterrows():
        if not isinstance(row['Lat'], str) :
            lat = row['Lat']
            longitude = row['Long']
        else:
            lat = convertDegreeToDecimal(row['Lat'])
            longitude = convertDegreeToDecimal(row['Long'])
        coords = "ST_GeogFromText('SRID=4326;POINT(%f %f)')"%(longitude, lat)
        value = "%s, %s, %s, '%s', '%s'"%(row['Id_rede'], row['Id_estacao'], coords, row['name'], row['Influencia'])
        sql += '''INSERT INTO "%s"(%s) VALUES (%s); '''%(tableName, keys, value)
    
    return sql


def stations_loc(path):
    """
        Upload to database and GeoServer the data about the locations of the stations
    """
    
    tableName = "stations_location"
    copy_excel_database('', path, Database, tableName, """ "Id_rede" INT, "Id_estacao" INT, "Name" VARCHAR(255), "Location" geography(POINT), "Tipo" VARCHAR(255)""", create_sql_stations_loc, db_user, db_password, db_host, db_port)

    xml = '<featureType><name>%s</name></featureType>'%(tableName)
    workspace = 'APA_EMEP_Data'
    datastore = 'Database'

    database_configuration = {
        "dataStore": {
            "name": "{}".format(datastore),
            "connectionParameters": {
                "entry": [
                    {"@key":"host","$":"{}".format(global_settings.POSTGRESQL_HOST)},
                    {"@key":"port","$":"{}".format(global_settings.POSTGRESQL_PORT)},
                    {"@key":"database","$":"{}".format(Database)},
                    {"@key":"user","$":"{}".format(global_settings.POSTGRESQL_USERNAME)},
                    {"@key":"passwd","$":"{}".format(global_settings.POSTGRESQL_PASSWORD)},
                    {"@key":"dbtype","$":"postgis"}
                ]
            }
        }
    }

    if checkWorkspace(workspace, gs_rest_url, user, pwd, False):
        if verify_datastore(workspace, datastore, gs_rest_url, user, pwd, database_configuration):
            if checkFeature(workspace, datastore, tableName, gs_rest_url, user, pwd):
                r = requests.post('{0}/workspaces/{1}/datastores/{2}/featuretypes'\
                    .format(gs_rest_url, workspace,datastore),
                                auth=HTTPBasicAuth(user, pwd),
                                data=xml,
                                headers=headers_xml
                                )
                log_logs_file("Upload Layer {}".format(r.status_code))

           

def get_and_upload_apa_website_info():
    """
        Method that gets information of the stations from APA website and upload to the internet
    """

    with tempfile.TemporaryDirectory(dir=global_settings.PATH_TMP_FILES) as directory: 
        Path_save_csv = directory + "/apa_website_csv.xls"

        Path_save_excel = directory + "/result.xls"

        get_csv_stations_APA(Path_save_csv)
        
        create_excel(Path_save_csv, Path_save_excel)

        update_estacoes(Path_save_excel)

        stations_loc(Path_save_excel)


def EMEP_APA_Excel(path):
    """ 
        Copy the excel that has EMEP and APA gas information to database
    """

    tableName = "EMEP_APA_INFO"
    tableCharacteristics = """ "Nome" VARCHAR(255), "Units" VARCHAR(255), "ID_APA" VARCHAR(255), "ID_EMEP" VARCHAR(255), "Formula" VARCHAR(255), "Formula_codificada" VARCHAR(255)"""
    copy_excel_database('', path, Database, tableName, tableCharacteristics, create_sql_EMEP_APA_Excel, db_user, db_password, db_host, db_port, "Processed")

def create_sql_EMEP_APA_Excel(tableName, dataframe, fileName, information):
    keys = '"Nome", "Units", "ID_APA", "ID_EMEP", "Formula", "Formula_codificada"'
    sql = ""
    for index, row in dataframe.iterrows():
        value = "'%s', '%s', '%s', '%s'"%(row['Nome'], row['Units'], row['ID_APA'], str(row['ID_EMEP']).replace(" ", ""))
        value += ", '%s', '%s'"%(row['Formula'], row['Formula_codificada'])
        sql += '''INSERT INTO "%s"(%s) VALUES (%s); '''%(tableName, keys, value)
    
    value = "'Classification of Total deposition of nitrogen', 'nan', 'nan', 'TDEP_N_critical_load', 'nan', 'nan' "
    sql += '''INSERT INTO "%s"(%s) VALUES (%s); '''%(tableName, keys, value)
    return sql

if __name__ == "__main__":
    choice = ''

    while choice.lower() != 'no' and  choice.lower() != 'yes':
        choice = input("Do you want to upload the information of stations : \n Yes \n No \n Choose: ")

    if choice.lower() == 'yes':

        choice = ''
    
        while choice.lower() != 'a' and  choice.lower() != 'b':
            choice = input("Do you want: \n A- Use local information \n B- Getting the information from the APA website directly \n Choose one: ")

        if choice.lower() == 'a':
            stations_loc(path + "my_geonode/Upload_GeoServer_Init/Excel_files/excel_estacao.xlsx")
        elif choice.lower() == 'b':
            get_and_upload_apa_website_info()

    choice = ''
    
    while choice.lower() != 'no' and  choice.lower() != 'yes':
        choice = input("Do you want to upload the information of gases : \n Yes \n No \n Choose: ")

    if choice.lower() == 'yes':
        EMEP_APA_Excel(path + "my_geonode/Upload_GeoServer_Init/Excel_files/tabela-poluentes-APA-EMEP-unidadades.xlsx")
    