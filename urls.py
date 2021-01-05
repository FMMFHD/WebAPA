from django.conf.urls import url

from WebAPA.views import ui_interface, get_APA_listGas, get_APA_gasValues, update_data_all_years, Verify_data_year

urlpatterns = [
    url(r'^update$', ui_interface, name="APA_ui_interface"),
    url(r'^all_update$', update_data_all_years, name="APA_update_data_all_years"),
    url(r'^listGas$', get_APA_listGas, name='get_APA_listGas'),
    url(r'^GasValues$', get_APA_gasValues, name='get_APA_gasValues'),
    url(r'^verify_year$', Verify_data_year, name='Verify_data_year'),),
]