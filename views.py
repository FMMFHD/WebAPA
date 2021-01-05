import json

from django.shortcuts import render, HttpResponse
from django.contrib.auth.decorators import login_required
from django.urls import reverse

from General_modules.module_logs import log_error_file, log_logs_file

from WebAPA.apa_data import get_ListGas, get_gasValues
from WebAPA.module_upload_data_APA_DB import upload_data, save_APA_Data


@login_required
def ui_interface(request, template='WebAPA/ui_interface.html'):
    """
        GET - View that creates the interface to the user to insert the yaer to retrieve the data from APA site 
        POST - For a given parameter it uploads the data from the APA site
    """

    if request.method == 'GET':
        return render(request, template, context={
            "path_update": reverse("APA_ui_interface"),
            "path_verification": reverse("Verify_data_year"),
        })
    
    if request.method == 'POST':
        try:
            year = request.POST['year']
        except:
            log_logs_file("Start the update APA DATA all years available")
            msg = save_APA_Data()
            log_logs_file("End the update APA DATA all years available")
            return HttpResponse(content_type="text/plain", content=msg)

        msg = upload_data(year)
        return HttpResponse(content_type="text/plain", content=msg)

    return HttpResponse(status=404)


def update_data_all_years(request):
    """
        From the parameters it will create an interval where it will upload the APA data from APA site
    """

    if request.method == 'GET':
        try:
            min_year = int(request.GET['min_year'])
            max_year = int(request.GET['max_year'])
        except Exception as e:
            log_error_file(str(e))
            log_logs_file("Start the update APA DATA all years available")
            save_APA_Data()
            log_logs_file("End the update APA DATA all years available")
            return HttpResponse(content_type="text/plain", content="Success")
        
        steps = max_year - min_year
        if steps >= 0:
            log_logs_file("Start the update APA DATA between {} and {}".format(min_year, max_year))
            if steps > 0:
                for i in range(steps+1):
                    upload_data(min_year+i)
            else:
                upload_data(min_year)

            log_logs_file("End the update APA DATA between {} and {}".format(min_year,max_year))
            return HttpResponse(content_type="text/plain", content="Success")

    return HttpResponse(status=404)


def Verify_data_year(request):
    """
        From the receive parameter, verifies if the data is already uploaded for the receiving year
    """

    if request.method == 'POST':
        try:
            year = request.POST['year']
        except:
            msg = """Error: Missing value."""
            return HttpResponse(content_type="text/plain", content=msg)

        msg = upload_data(year, verify=True)
        return HttpResponse(content_type="text/plain", content=msg)

    return HttpResponse(status=404)

    
def get_APA_listGas(request):
    """
        For given station returns all the gases
    """

    if request.method == 'GET':
        return get_ListGas(request.GET['Id_estacao'])
    return HttpResponse(status=404)


def get_APA_gasValues(request):
    """
        For a given pollutant definition it returns a html table with information
    """

    if request.method == 'GET':
        id_estacao = request.GET['Id_estacao']
        id_gas = request.GET['Id_gas']
        resolution = request.GET['resolution']
        date = request.GET['date']

        return get_gasValues(id_estacao, id_gas, resolution, date)
    return HttpResponse(status=404)
