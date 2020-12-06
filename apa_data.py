import json

from django.http import HttpResponse

from General_modules.module_DB import sqlExecute
from General_modules import global_settings


TABLENAME = global_settings.APA_TABLE_NAME
DB_NAME = global_settings.DB_NAME_EMEP_APA
db_user = global_settings.POSTGRESQL_USERNAME
db_password = global_settings.POSTGRESQL_PASSWORD
db_host = global_settings.POSTGRESQL_HOST
db_port = global_settings.POSTGRESQL_PORT

def get_ListGas(id_estacao):
    """
        Return all the gas that the station has information
    """
    table_gas_info = global_settings.GAS_INFORMATION_TABLE
    sql = '''SELECT DISTINCT id_gas, "Nome" FROM "{0}" inner join "{1}" on id_gas = "ID_APA" WHERE id_estacao = {2}'''.format(TABLENAME, table_gas_info, id_estacao)
    resp = sqlExecute(DB_NAME, db_user, db_password, db_host, db_port, sql, True)
    listGas = []
    if resp['success']:
        for id_gas in resp['data']:
            listGas.append({
                'Name': id_gas[1],
                'Id': id_gas[0]
            })
    return HttpResponse(content_type='text/json', content=json.dumps({
        "listGas": listGas,
    }))


def get_gasValues(id_estacao, id_gas, resolution, date):
    """
        Return a html table that contains all the values for a specific station with a specific gas at a specific temporal resolution, using date as reference
    """
    sql = sql_GasValues(id_estacao, id_gas, resolution, date)
    html = ""
    resp = sqlExecute(DB_NAME, db_user, db_password, db_host, db_port, sql, True)
    if resp['success']:
        html, data_array = makeHtmlTable(resp['data'])

    return HttpResponse(content_type='text/json', content=json.dumps({
        "htmlTable": html,
        "data_array": data_array,
    }))


def decompose_date(date):
    """
        Retrieve year, month, day, hour, minute, second from the date
    """
    split_date = date.split('-')
    year = split_date[0]
    month = split_date[1]
    split_date = split_date[2].split('T')
    day = split_date[0]
    split_date = split_date[1].split(':')
    hour = split_date[0]
    minute = split_date[1]
    second = split_date[2].split('.')[0]
    return [year, month, day, hour, minute, second]


def sql_GasValues(id_estacao, id_gas, resolution, date):
    """
        Create the sql sentence to get the values from the database.\n
        This values corresponds to a specific station with a specific gas at a specific temporal resolution, using date as reference
    """
    year, month, day, hour, minute, second = decompose_date(date)
    sql = """SELECT date, value from "{}" where id_estacao = {} and id_gas = '{}'""".format(TABLENAME, id_estacao, id_gas)

    _sql = " and EXTRACT(year from date) = {}".format(year)

    if resolution != 'year':
        _sql += " and EXTRACT(month from date) = {}".format(month)
        if resolution != 'month':
            _sql += " and EXTRACT(day from date) = {}".format(day)
            if resolution != 'day':
                _sql += " and EXTRACT(hour from date) = {}".format(hour)
    
    return sql + _sql


def makeHtmlTable(data):
    """
        To make the content more user friendly, transforms the data from the database to a html table
    """
    if len(data) > 0:
        data_array = []
        html = """<table class="tableApa"><tr><td>Date</td><td>Value</td></tr>"""
        for values in data:
            html += "<tr><td>{}</td><td>{}</td></tr>".format(values[0], values[1])
            data_array.append({
                'date': values[0],
                'value': values [1]
            })
        return [html + "</table>", data_array]
    else:
        return ["<h5>Empty Table</h5>", []]