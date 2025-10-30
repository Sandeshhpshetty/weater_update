from django.http import HttpResponse

def index(request):
    return HttpResponse("Django + Celery setup is running successfully ✅")
