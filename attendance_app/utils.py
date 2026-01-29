import africastalking
from django.conf import settings
from .models import AcademicYear
from django.utils import timezone


def send_sms(phone, message):
    try:
        africastalking.initialize(
            settings.AFRICASTALKING_USERNAME,
            settings.AFRICASTALKING_API_KEY
        )

        sms = africastalking.SMS
        sms.send(message, [phone])
        return True

    except Exception as e:
        print("SMS Error:", e)
        return False


def auto_lock_expired_academic_year():
    current_year = timezone.now().year
    active_year = AcademicYear.objects.filter(is_active=True).first()

    if active_year and current_year > active_year.year_end:
        active_year.is_active = False
        active_year.is_locked = True
        active_year.save()
