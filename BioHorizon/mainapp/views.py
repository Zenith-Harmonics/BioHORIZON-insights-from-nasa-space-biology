from django.shortcuts import render
from django.http import HttpResponse
from services import data_handler

# Create your views here.

def home(request):
    data = data_handler.Data()
    result_dict = data.get_latest_research(2)

    list_of_dicts = [{"title": k, "description": v} for k, v in result_dict.items()]
    return render(request, 'mainapp/index.html', {"result":list_of_dicts})
