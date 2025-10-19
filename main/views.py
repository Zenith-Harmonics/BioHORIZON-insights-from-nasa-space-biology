from django.shortcuts import render
from django.http import HttpResponse
# Assuming data_handler is correctly imported from main.services
from main.services.data_handler import data_handler

def home(request):
    # 1. Get search parameters from the request
    keyword = request.GET.get('q', '').strip()

    filters = {
        'organism_category': request.GET.get('organism', ''),
        'mission_category': request.GET.get('mission', ''),
        'experiment_type_category': request.GET.get('type', ''),
    }

    # 2. Use the defined function name, search_experiments
    experiments = data_handler.search_experiments(keyword=keyword, filters=filters)

    # 3. Get unique values for dropdown filters
    filter_options = data_handler.get_unique_filter_values()

    context = {
        'experiments': experiments,
        'filter_options': filter_options,
        'current_keyword': keyword,
        'current_filters': filters,
    }

    # FIX: Change the template path to 'home.html' based on your file structure.
    return render(request, 'home.html', context)

def paper(request, paper_osd):
    context = {}
    # Assuming the data handler is correctly implemented as defined previously.
    paper = data_handler.get_experiment_by_id(paper_osd)

    context = { "paper": paper}
    return render(request, "paper.html", context)

def about(request):
    return render(request, "about.html")
