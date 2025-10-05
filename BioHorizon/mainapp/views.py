from django.shortcuts import render
from django.http import HttpResponse
from services import data_handler

# Create your views here.

def home(request):
    q = request.GET.get('q', '').strip()
    data = data_handler.Data()
    result_dict_init = {'expression data from drosophila melanogaster': 'Spaceflight alters Drosophila innate immune gene expression after infection.', 'response of human lymphoblastoid cells to hze (iron ions) or gamma-rays': 'Transcriptomic response of TK6 cells to HZE vs gamma irradiation.'}

    if q:
        result_dict = data.search_articles(q)
    else:
        result_dict = result_dict_init

    items = [{"title": k, "description": v} for k, v in result_dict.items()]
    return render(request, 'mainapp/index.html', {"result": items, "q": q})

def details(request):
    article_id = request.GET.get('id', '').strip()
    data = data_handler.Data()
    article_details = data.get_article_details(article_id)

    if article_details:
        return render(request, 'mainapp/details.html', {"article": article_details})
    else:
        return HttpResponse("Article not found.", status=404)
    
def about(request):
    return render(request, 'mainapp/about.html')