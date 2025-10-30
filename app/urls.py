# app/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path("", views.weather_page, name="weather_page"),
    path("add/", views.add_city, name="add_city"),
    path("remove/<int:city_id>/", views.remove_city, name="remove_city"),
    # expose name 'trigger_now' so templates reversing that name succeed
    path("trigger/<int:city_id>/", views.trigger_city_now, name="trigger_now"),
]
