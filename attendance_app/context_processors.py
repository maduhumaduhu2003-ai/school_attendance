from .models import SchoolSettings

def school_settings_processor(request):
    school_settings, _ = SchoolSettings.objects.get_or_create(id=1)
    return {
        'school_settings': school_settings
    }
