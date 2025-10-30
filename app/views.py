'''# app/views.py
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from django.urls import reverse
from .models import City

def _is_json_request(request):
    ct = request.META.get("CONTENT_TYPE", "")
    return ct.startswith("application/json")

@require_GET
def weather_page(request):
    """Render listing page with form (normal HTML)."""
    cities = City.objects.order_by("name")
    return render(request, "app/weather_page.html", {"cities": cities})

@require_http_methods(["POST"])
def add_city(request):
    """
    Accept both form POST and JSON POST.
    - form POST: redirect back to page
    - JSON POST: returns JSON
    """
    name = request.POST.get("name")
    email = request.POST.get("email")

    if not name and _is_json_request(request):
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "invalid json"}, status=400)
        name = payload.get("name")
        email = payload.get("email")

    if not name:
        if _is_json_request(request):
            return JsonResponse({"error": "missing 'name' in payload"}, status=400)
        return HttpResponseBadRequest("Missing 'name' field")

    name = name.strip()
    city, created = City.objects.get_or_create(name=name, defaults={"email": email or None})
    if not created and email:
        city.email = email or None
        city.save(update_fields=["email", "updated_at"])

    if _is_json_request(request):
        return JsonResponse({"status": "created" if created else "exists", "city": {"id": city.id, "name": city.name, "email": city.email}})
    return redirect(reverse("weather_page"))

@require_http_methods(["POST"])
def remove_city(request, city_id):
    city = get_object_or_404(City, pk=city_id)
    city.delete()
    if _is_json_request(request):
        return JsonResponse({"status": "deleted", "id": city_id})
    return redirect(reverse("weather_page"))

@require_http_methods(["POST"])
def trigger_now(request, city_id):
    """
    Trigger the per-city Celery task.
    Import the task locally to avoid circular-import issues.
    """
    # local import to avoid circular import issues at module import time
    try:
        from .tasks import update_city_weather
    except Exception as e:
        # If tasks failed to import, return a JSON error so you can see the underlying problem
        return JsonResponse({"error": "could not import task", "detail": str(e)}, status=500)

    city = get_object_or_404(City, pk=city_id)
    async_result = update_city_weather.delay(city.id)
    return JsonResponse({"status": "triggered", "task_id": async_result.id})
'''

# app/views.py
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from .models import City

def _is_json_request(request):
    ct = request.META.get("CONTENT_TYPE", "")
    return ct.startswith("application/json")

@require_GET
def weather_page(request):
    cities = City.objects.order_by("name")
    return render(request, "app/weather_page.html", {"cities": cities})

@require_http_methods(["POST"])
def add_city(request):
    # Support HTML form and JSON API
    name = request.POST.get("name")
    email = request.POST.get("email")
    if not name and _is_json_request(request):
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "invalid json"}, status=400)
        name = payload.get("name")
        email = payload.get("email")

    if not name:
        if _is_json_request(request):
            return JsonResponse({"error": "missing 'name' in payload"}, status=400)
        return HttpResponseBadRequest("Missing 'name' field")

    name = name.strip()
    city, created = City.objects.get_or_create(name=name, defaults={"email": email or None})
    if not created and email:
        city.email = email or None
        city.save(update_fields=["email", "updated_at"])

    if _is_json_request(request):
        return JsonResponse({"status": "created" if created else "exists", "city": {"id": city.id, "name": city.name, "email": city.email}})
    return redirect(reverse("weather_page"))

@require_POST
def remove_city(request, city_id):
    city = get_object_or_404(City, pk=city_id)
    city.delete()
    return JsonResponse({"status": "deleted", "id": city_id})

@require_POST
def trigger_city_now(request, city_id):
    # local import to avoid circular import errors at module import time
    try:
        from .tasks import fetch_and_store_weather_for_city
    except Exception as e:
        return JsonResponse({"error": "could not import task", "detail": str(e)}, status=500)

    city = get_object_or_404(City, pk=city_id)
    res = fetch_and_store_weather_for_city.delay(city.id)
    return JsonResponse({"status": "triggered", "task_id": res.id})
