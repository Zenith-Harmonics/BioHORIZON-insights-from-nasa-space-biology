from django.shortcuts import render
from django.http import HttpResponse
from main.services import data_handler

def home(request):
    papers_list = data_handler.get_latest_papers()
    query = request.GET.get("q", "").strip()


    return render(request, "home.html", {
        "query": query,
        "papers": papers_list
    })

def paper(request, paper_osd):
    context = {}
    paper = data_handler.get_paper(paper_osd)

    context = { "paper": paper}
    return render(request, "paper.html", context)