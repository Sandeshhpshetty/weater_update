'''# app/tasks.py
import os
import json
import requests
from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.utils import timezone
from requests.exceptions import RequestException

logger = get_task_logger(__name__)

WEATHER_API_URL = "https://api.openweathermap.org/data/2.5/weather"
WEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")  # set in env


def _fetch_weather_from_api(city_name: str):
    params = {"q": city_name, "appid": WEATHER_API_KEY, "units": "metric"}
    resp = requests.get(WEATHER_API_URL, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _maybe_send_email(to_email: str, subject: str, message: str):
    if not to_email:
        return
    from django.core.mail import send_mail
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [to_email], fail_silently=False)
    except Exception as e:
        # don't fail the whole task for email issues, just log
        logger.exception("Failed to send email to %s: %s", to_email, e)


@shared_task(bind=True, max_retries=6, acks_late=True)
def fetch_and_store_weather_for_city(self, city_id):
    """
    Task that fetches weather for a city id (City model), stores result on the City row,
    and optionally emails the user. Retries on network/HTTP errors with exponential backoff.
    """
    from .models import City  # local import to avoid app-loading issues
    try:
        city = City.objects.get(pk=city_id)
    except City.DoesNotExist:
        logger.warning("fetch_and_store_weather_for_city: city %s does not exist", city_id)
        return {"status": "missing", "city_id": city_id}

    city_name = city.name
    try:
        logger.info("Fetching weather for %s (city_id=%s)", city_name, city_id)
        data = _fetch_weather_from_api(city_name)
        temp = data.get("main", {}).get("temp")
        desc = data.get("weather", [{}])[0].get("description", "")

        # store in DB
        city.last_temp = temp
        city.last_desc = desc
        city.last_fetched_at = timezone.now()
        city.save(update_fields=["last_temp", "last_desc", "last_fetched_at", "updated_at"])

        # optionally notify by email
        if city.email:
            subject = f"Weather update for {city_name}"
            message = f"{city_name}: {temp}°C, {desc}"
            _maybe_send_email(city.email, subject, message)

        logger.info("Weather stored for %s: %s°C, %s", city_name, temp, desc)
        return {"status": "ok", "city": city_name, "temp": temp, "desc": desc}

    except RequestException as exc:
        # network/http errors -> exponential backoff retry
        retries = self.request.retries or 0
        countdown = min(2 ** retries, 600)  # cap at 10m
        logger.warning(
            "Network error fetching weather for %s (retries=%s) -> retry in %s sec: %s",
            city_name, retries, countdown, exc
        )
        raise self.retry(exc=exc, countdown=countdown)
    except Exception as exc:
        # unexpected errors: retry up to max_retries then fail
        retries = self.request.retries or 0
        if retries < self.max_retries:
            countdown = min(2 ** retries, 600)
            logger.exception("Unexpected error for %s - retrying (retries=%s)", city_name, retries)
            raise self.retry(exc=exc, countdown=countdown)
        logger.exception("Permanent failure fetching weather for %s", city_name)
        raise
'''

# app/tasks.py
import os
from celery import shared_task, group
from celery.utils.log import get_task_logger
from requests.exceptions import RequestException
from django.utils import timezone
from django.conf import settings

logger = get_task_logger(__name__)

WEATHER_API_URL = "https://api.openweathermap.org/data/2.5/weather"
WEATHER_API_KEY = settings.OPENWEATHER_API_KEY  # MUST be set in env


def _fetch_weather_from_api(city_name: str):
    import requests
    if not WEATHER_API_KEY:
        raise RuntimeError("OPENWEATHER_API_KEY environment variable is not set")
    params = {"q": city_name, "appid": WEATHER_API_KEY, "units": "metric"}
    resp = requests.get(WEATHER_API_URL, params=params, timeout=12)
    resp.raise_for_status()
    return resp.json()


def _maybe_send_email(to_email: str, subject: str, message: str):
    if not to_email:
        return
    from django.core.mail import send_mail
    try:
        send_mail(subject, message, os.environ.get("DEFAULT_FROM_EMAIL", "webmaster@localhost"), [to_email], fail_silently=False)
    except Exception:
        logger.exception("Failed to send email to %s", to_email)


@shared_task(bind=True, max_retries=6, acks_late=True)
def fetch_and_store_weather_for_city(self, city_id):
    """
    Fetch and store weather for City with id=city_id.
    Retries on network errors with exponential backoff.
    """
    from .models import City  # local import to avoid circular import at module load

    try:
        city = City.objects.get(pk=city_id)
    except City.DoesNotExist:
        logger.warning("fetch_and_store_weather_for_city: missing city id %s", city_id)
        return {"status": "missing", "city_id": city_id}

    try:
        logger.info("Fetching weather for %s (id=%s)", city.name, city_id)
        data = _fetch_weather_from_api(city.name)
        temp = data.get("main", {}).get("temp")
        desc = data.get("weather", [{}])[0].get("description", "")

        city.last_temp = temp
        city.last_desc = desc
        city.last_fetched_at = timezone.now()
        city.save(update_fields=["last_temp", "last_desc", "last_fetched_at", "updated_at"])

        if city.email:
            subject = f"Weather update for {city.name}"
            message = f"{city.name}: {temp}°C, {desc}"
            _maybe_send_email(city.email, subject, message)

        logger.info("Stored weather for %s: %s°C, %s", city.name, temp, desc)
        return {"status": "ok", "city": city.name, "temp": temp, "desc": desc}

    except RequestException as exc:
        retries = self.request.retries or 0
        countdown = min(2 ** retries, 600)
        logger.warning("Network error for %s (retries=%s) -> retry in %s sec: %s", city.name, retries, countdown, exc)
        raise self.retry(exc=exc, countdown=countdown)
    except Exception as exc:
        retries = self.request.retries or 0
        if retries < self.max_retries:
            countdown = min(2 ** retries, 600)
            logger.exception("Unexpected error for %s - retrying (retries=%s)", city.name, retries)
            raise self.retry(exc=exc, countdown=countdown)
        logger.exception("Permanent failure fetching weather for %s", city.name)
        raise


@shared_task
def update_all_cities():
    """
    Wrapper task: dispatch one fetch_and_store_weather_for_city per City in DB.
    Celery Beat will schedule this every 30 minutes.
    """
    from .models import City

    city_ids = list(City.objects.values_list("id", flat=True))
    if not city_ids:
        logger.info("update_all_cities: no cities to update")
        return {"status": "no_cities"}

    # fire off per-city tasks in parallel
    group_result = group(fetch_and_store_weather_for_city.s(cid) for cid in city_ids).apply_async()
    logger.info("update_all_cities: dispatched %d tasks", len(city_ids))
    return {"status": "dispatched", "count": len(city_ids), "group_id": group_result.id}

from django.core.mail import EmailMessage, get_connection
from django.core.mail import send_mail


def _maybe_send_email(to_email: str, subject: str, message: str, html_message: str = None):
    """
    Send email safely. Uses Django's EMAIL_ settings.
    - to_email: single recipient email address (string)
    - subject, message: text body
    - html_message: optional HTML body
    """
    if not to_email:
        return

    try:
        # Simple send_mail (uses EMAIL_BACKEND config)
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
            html_message=html_message,
        )
        logger.info("Email sent to %s (subject=%s)", to_email, subject)
    except Exception as e:
        # Log the error but do not raise — we don't want email error to crash the whole task
        logger.exception("Failed to send email to %s: %s", to_email, e)