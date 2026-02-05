# attendance_app/context_processors.py
from .models import SchoolSettings, TeacherProfile

def school_and_profile(request):
    # Get or create school settings (ensure there is always one)
    school_settings, _ = SchoolSettings.objects.get_or_create(id=1)
    
    profile = None
    profile_picture_url = None

    if request.user.is_authenticated:
        try:
            # Try to get existing TeacherProfile, do NOT create automatically
            profile = TeacherProfile.objects.get(user=request.user)
            if profile.profile_picture:
                profile_picture_url = profile.profile_picture.url
        except TeacherProfile.DoesNotExist:
            profile = None
            profile_picture_url = None  # Will use default avatar in template

    return {
        'school_settings': school_settings,
        'profile': profile,
        'profile_picture_url': profile_picture_url,
    }
