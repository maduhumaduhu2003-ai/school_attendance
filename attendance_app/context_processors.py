from .models import SchoolSettings

def school_and_profile(request):
    school_settings = SchoolSettings.objects.first()

    if not school_settings:
        school_settings = SchoolSettings.objects.create(
            school_name="Mgunga Sec School"
        )

    return {
        'school_settings': school_settings,
    }