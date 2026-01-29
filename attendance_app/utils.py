import africastalking
from django.conf import settings
from .models import AcademicYear
from django.utils import timezone

def send_sms(phone, message):
    try:
        africastalking.initialize(
            username=settings.AFRICASTALKING_USERNAME,
            api_key=settings.AFRICASTALKING_API_KEY
        )

        sms = africastalking.SMS
        response = sms.send(
            message=message,
            recipients=[phone],
            sender_id=getattr(settings, 'AFRICASTALKING_SENDER_ID', 'School_SMS')
        )
        print("SMS sent:", response)
        return True

    except Exception as e:
        print("SMS Error:", e)
        return False


def auto_lock_expired_academic_year():
    now = timezone.now().date()
    active_year = AcademicYear.objects.filter(is_active=True).first()

    if active_year and now > active_year.year_end:
        active_year.is_active = False
        active_year.is_locked = True
        active_year.save()
        print(f"Academic Year {active_year} locked.")
