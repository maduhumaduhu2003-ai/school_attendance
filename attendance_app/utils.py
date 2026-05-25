import africastalking
import logging
from django.conf import settings
from .models import AcademicYear
from django.utils import timezone

# Initialize logger
logger = logging.getLogger(__name__)

def send_sms(phone_number, message):
    """
    Send SMS using Africa's Talking
    Returns: (success, message)
    """
    if not phone_number:
        return False, "No phone number provided"
    
    try:
        # Initialize Africa's Talking
        africastalking.initialize(
            username=settings.AFRICASTALKING_USERNAME,
            api_key=settings.AFRICASTALKING_API_KEY
        )
        
        sms = africastalking.SMS
        
        # Send SMS
        response = sms.send(
            message,
            [phone_number],
            sender_id=settings.AFRICASTALKING_SENDER_ID
        )
        
        # Check response
        if response and response.get('SMSMessageData'):
            recipients = response['SMSMessageData']['Recipients']
            if recipients and len(recipients) > 0:
                status = recipients[0].get('status', '')
                if status == 'Success':
                    logger.info(f"SMS sent successfully to {phone_number}")
                    return True, "SMS sent successfully"
                else:
                    error_msg = recipients[0].get('status', 'Unknown error')
                    logger.error(f"SMS failed: {error_msg}")
                    return False, f"SMS failed: {error_msg}"
        
        return False, "No response from SMS gateway"
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"SMS sending error: {error_msg}")
        
        # Check for specific errors
        if 'insufficient' in error_msg.lower() or 'balance' in error_msg.lower():
            return False, " Salio la SMS halipo. Tafadhali wasiliana na Admin."
        elif 'network' in error_msg.lower():
            return False, " Tatizo la mtandao. Jaribu tena."
        else:
            return False, f" SMS failed: {error_msg[:100]}"


def auto_lock_expired_academic_year():
    """Auto-lock academic years that have ended"""
    current_year = timezone.now().year
    active_year = AcademicYear.objects.filter(is_active=True, is_locked=False).first()

    if active_year and current_year > active_year.year_end:
        active_year.is_active = False
        active_year.is_locked = True
        active_year.save()
        logger.info(f"Academic Year {active_year} has been auto-locked.")
        print(f"Academic Year {active_year} locked.")