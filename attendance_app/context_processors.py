# attendance_app/context_processors.py
from .models import SchoolSettings, TeacherProfile

def school_and_profile(request):
    # Get or create school settings
    school_settings, _ = SchoolSettings.objects.get_or_create(id=1)
    
    profile = None
    if request.user.is_authenticated:
        # Only attempt to get TeacherProfile if user exists
        profile, _ = TeacherProfile.objects.get_or_create(user=request.user)
    
    return {
        'school_settings': school_settings,
        'profile': profile,
    }
