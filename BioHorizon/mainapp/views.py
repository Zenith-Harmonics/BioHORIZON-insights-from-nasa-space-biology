from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.

def home(request):
    result_dict = {'expression data from drosophila melanogaster': 'Spaceflight alters Drosophila innate immune gene expression after infection.', 
                'response of human lymphoblastoid cells to hze (iron ions) or gamma-rays': 'Transcriptomic response of TK6 cells to HZE vs gamma irradiation.'}
    
    list_of_dicts = [{"title": k, "description": v} for k, v in result_dict.items()]
    return render(request, 'mainapp/index.html', {"result":list_of_dicts})
