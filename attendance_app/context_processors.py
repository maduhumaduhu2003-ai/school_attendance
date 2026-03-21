from .models import SchoolSettings

def school_and_profile(request):
    # Hakuna profiles za admin au teacher tena
    school_settings, _ = SchoolSettings.objects.get_or_create(id=1)

    return {
        'school_settings': school_settings,
    }