import africastalking
import logging
from django.conf import settings
from .models import AcademicYear
from django.utils import timezone
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Initialize logger
logger = logging.getLogger(__name__)


def get_sms_session():
    """Create a session with timeout and retry strategy"""
    session = requests.Session()
    
    # Set default timeout
    session.timeout = 20
    
    # Retry strategy
    retry_strategy = Retry(
        total=2,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    
    return session


def send_sms(phone_number, message):
    """
    Send SMS using Africa's Talking with timeout
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
        
        # ========== METHOD 1: Set timeout via socket (GLOBAL) ==========
        import socket
        original_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(20)  # 20 seconds timeout
        
        try:
            # Send SMS
            response = sms.send(
                message,
                [phone_number],
                sender_id=settings.AFRICASTALKING_SENDER_ID
            )
        finally:
            # Restore original timeout
            socket.setdefaulttimeout(original_timeout)
        
        # ========== METHOD 2: If using custom HTTP session ==========
        # Alternative: If you want more control, you can override the SDK's session
        # Uncomment this if Method 1 doesn't work:
        """
        # Override the SDK's HTTP session with timeout
        if hasattr(sms, '_session'):
            sms._session = get_sms_session()
        
        response = sms.send(
            message,
            [phone_number],
            sender_id=settings.AFRICASTALKING_SENDER_ID
        )
        """
        
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
        
    except requests.exceptions.Timeout:
        logger.error(f"SMS timeout for {phone_number}")
        return False, "SMS service timeout - please try again"
        
    except socket.timeout:
        logger.error(f"Socket timeout for {phone_number}")
        return False, "SMS service timeout - please try again"
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"SMS sending error: {error_msg}")
        
        # Check for specific errors
        if 'insufficient' in error_msg.lower() or 'balance' in error_msg.lower():
            return False, "Insufficient SMS balance. Please contact Admin."
        elif 'timeout' in error_msg.lower():
            return False, "SMS service timeout. Please try again."
        elif 'network' in error_msg.lower():
            return False, " Network error. Please try again."
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