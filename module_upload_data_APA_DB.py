import pandas as pd
from bs4 import BeautifulSoup
import io
from xlwt import Workbook
import os

from General_modules.module_access_external import request_Data_External_Source
from General_modules.module_DB import sqlExecute
from General_modules.module_logs import log_logs_file
from General_modules import global_settings
from General_modules.module_DB import check_table
from GeoExcel.module_excel import copy_excel_database


PATH_EXCEL_TMP_FILE = global_settings.PATH_GLOBAL + "Excel_files/tmp.xls"
TABLENAME = global_settings.APA_TABLE_NAME
DB_NAME = global_settings.DB_NAME_EMEP_APA
db_user = global_settings.POSTGRESQL_USERNAME
db_password = global_settings.POSTGRESQL_PASSWORD
db_host = global_settings.POSTGRESQL_HOST
db_port = global_settings.POSTGRESQL_PORT


def init_formData_APA(rede, estacao, ano):
    form_data = {}
    form_data['rede'] = rede
    form_data['estacao'] = estacao
    form_data['ano'] = ano
    form_data['day0'] = 1
    form_data['month0'] = 1
    form_data['day1'] = 31
    form_data['month1'] = 12
    return form_data


def upload_data(year):
    """
        To upload the data to the database, it follows the following steps:
            - open excel estacao to retrieve feature of each station
            - get excel from APA site
            - copy the information to the database
    """
    msg = check_table_specific(year)
    if msg is None:
        msg = save_APA_Data(year)
        
        return msg
    return msg


def check_table_specific(year):
    """
        Verify if the table already exists on the database.\n
        Also it checks if the table already has information about the "year".
    """
    tableCharacteristics = """ "id_rede" INT, "id_estacao" INT, "id_gas" VARCHAR(255), "date" timestamp, "value" FLOAT"""
    check = check_table(DB_NAME, TABLENAME, tableCharacteristics, db_user, db_password, db_host, db_port, delete=False)

    if check == True:
        sql = """select count(id_estacao) from "%s" where EXTRACT(year from date) = %s """%(TABLENAME, year)
        resp = sqlExecute(DB_NAME, db_user, db_password, db_host, db_port, sql, True)
        if resp['success']:
            if resp['data'][0][0] == 0:
                return None
            else:
                msg = """The database already have the year {0}.\n
                Use this command: DELETE from "tablename" where EXTRACT(year from date) = {0}.""".format(year)
                log_logs_file(msg)
                return msg

    return "Check the Logs"


def extract_all_information():
    """
        Web scraping from the https://qualar1.apambiente.pt/qualar/index.php?page=6
    """
    inputs_information = []

    response = request_Data_External_Source('GET', "https://qualar1.apambiente.pt/qualar/index.php?page=6")
    if response is not None:
        soup = BeautifulSoup(response.text, "lxml")
        gdp_select_rede = soup.find("select", attrs={"name": "rede"})
        for option in gdp_select_rede.find_all("option"):
            id_rede = int(option['value'])
            if id_rede != -1:
                form_data = init_formData_APA(id_rede, -1, -1)
                response = request_Data_External_Source('POST', "https://qualar1.apambiente.pt/qualar/index.php?page=6&subpage=", data=form_data)
                if response is None:
                    continue
                
                soup = BeautifulSoup(response.text, "lxml")
                gdp_select_estacao = soup.find("select", attrs={"name": "estacao"})
                for _option in gdp_select_estacao.find_all("option"):
                    id_estacao = int(_option['value'])
                    if id_estacao != -1:
                        inputs_information.append([id_rede, id_estacao])

    return inputs_information


def extract_year_for_station(id_rede, id_estacao):
    """
        For a given station, get all the available years from the APA website
    """
    years = []
    form_data = init_formData_APA(id_rede, id_estacao, -1)
    response = request_Data_External_Source('POST', "https://qualar1.apambiente.pt/qualar/index.php?page=6&subpage=", data=form_data)
    if response is not None:
        soup = BeautifulSoup(response.text, "lxml")
        gdp_select_year = soup.find("select", attrs={"name": "ano"})
        for __option in gdp_select_year.find_all("option"):
            year = int(__option['value'])
            if year != -1:
                years.append(year)

    return years
                                

def save_APA_Data(year=None):
    """
        To a specific year, save all the data from all stations to the Database named "APA_EMEP_DATA".\n
        The data is all saved on the same table, "<TABLENAME>".\n
        The data is retrieve from https://qualar1.apambiente.pt/qualar/excel_new.php?excel=1
    """
    if year is None:
        sql = "drop table {}".format(global_settings.APA_TABLE_NAME)
        sqlExecute(DB_NAME, db_user, db_password, db_host, db_port, sql, False)

    inputs_information = extract_all_information()
    gas_info = pd.read_excel(global_settings.PATH_EXCEL_GAS)
    gas_names = gas_info['Gas'].tolist()
    str_estacoes = ""
    tableCharacteristics = """ "id_rede" INT, "id_estacao" INT, "id_gas" VARCHAR(255), "date" timestamp, "value" FLOAT"""

    count_download_excels = 0

    information = {
        'gas_info': gas_info,
        'gas_names': gas_names, 
        'str_estacoes': "",
    }

    # for index, row in estacoes_info.iterrows():
    for input_info in inputs_information:
        if year is None:
            years = extract_year_for_station(input_info[0], input_info[1])
            for year in years:
                count_download_excels += 1
                extract_and_saved_excel(input_info[0], input_info[1], year, information, tableCharacteristics)
        else:
            count_download_excels += 1
            extract_and_saved_excel(input_info[0], input_info[1], year, information, tableCharacteristics)

    if year is None:
        year = "todos os anos possíveis"
    
    if len(str_estacoes.split(", ")) != count_download_excels:
        log_logs_file("Sucesso ano {}".format(year))
        return "Sucesso ano {}".format(year)
        
    log_logs_file("Não foi possível atualizar os dados do ano {}.".format(year))
    return "Não foi possível atualizar os dados do ano {}.".format(year)


def extract_and_saved_excel(id_rede, id_estacao, year, information, tableCharacteristics):
    """
        From the APA data store retrieve the excel, and saved the data in the database
    """
    information['Id_rede'] = id_rede
    information['Id_estacao'] = id_estacao

    form_data = init_formData_APA(id_rede, id_estacao, year)
    response = request_Data_External_Source('POST', "https://qualar1.apambiente.pt/qualar/excel_new.php?excel=1", data=form_data)

    if response.status_code == 200:
        with open(PATH_EXCEL_TMP_FILE, "w") as f:
            f.write(response.text)
        Recover_corrupt_file(PATH_EXCEL_TMP_FILE)

        copy_excel_database('', PATH_EXCEL_TMP_FILE, DB_NAME, TABLENAME, tableCharacteristics, save_to_database, db_user, db_password, db_host, db_port, delete=False, information=information)

        os.remove(PATH_EXCEL_TMP_FILE)

    else:
        information['str_estacoes'] += '{}'.format(information['Id_estacao']) + ', '


def Recover_corrupt_file(path):
    """
        Excel that we receive from APA, only have the content, missing the shield.\n
        So we assume the file is corrupted, and save its content to another file.\n
        Link: https://medium.com/@jerilkuriakose/recover-corrupt-excel-file-xls-or-xlsx-using-python-2eea6bb07aae
    """
    file1 = io.open(path, "r", encoding="utf-8")
    data = file1.readlines()
    file1.close()
    # Creating a workbook object
    xldoc = Workbook()
    # Adding a sheet to the workbook object
    sheet = xldoc.add_sheet("Sheet1", cell_overwrite_ok=True)
    # Iterating and saving the data to sheet
    for i, row in enumerate(data):
        # Two things are done here
        # Removeing the '\n' which comes while reading the file using io.open
        # Getting the values after splitting using '\t'
        for j, val in enumerate(row.replace('\n', '').split('\t')):
            sheet.write(i, j, val)
    
    # Saving the file as an excel file
    xldoc.save(path)


def is_number_tryexcept(s):
    """ Returns True if the string is a number. """
    try:
        s = s.replace(',','.')
        float(s)
        return True
    except ValueError:
        return False


def save_to_database(tableName, dataframe, fileName, information):
    """
        Save tha dataframe on the database
    """

    gas_info = information['gas_info']
    Id_rede = information['Id_rede']
    Id_estacao = information['Id_estacao']
    gas_names = information['gas_names']

    sql = ''

    if len(dataframe.columns) < 2:
        information['str_estacoes'] += '{}'.format(Id_estacao) + ', '
        return

    key_value = '''"id_rede", "id_estacao" , "id_gas", "date", "value"'''
    for column in dataframe.columns:
        if 'Data' != column:
            try:
                if column[-1] == ' ':
                    index = gas_names.index(column[:-1])
                else:
                    index = gas_names.index(column)
            except Exception as e:
                log_logs_file(str(e))
                continue
            for i in range(len(dataframe[column])):
                if pd.isnull(dataframe[column][i]) or pd.isnull(dataframe['Data'][i]):
                    continue
                if is_number_tryexcept(dataframe[column][i]):
                    value = "%s, %s, '%s','%s', %f"%(Id_rede, Id_estacao, gas_info['Id'][index], dataframe['Data'][i], float(dataframe[column][i].replace(',','.')))
                    sql += '''INSERT INTO "%s"(%s) VALUES (%s); '''%(tableName, key_value, value)

    if sql == "":
        information['str_estacoes'] += '{}'.format(Id_estacao) + ', '

    return sql
    
    
