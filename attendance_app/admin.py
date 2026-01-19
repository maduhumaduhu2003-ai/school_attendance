from django.contrib import admin
from .models import User, Classroom, TeacherProfile, StudentProfile, ParentProfile, Attendance, AcademicYear, SMSLog

# Register your models here.

admin.site.register(User)
admin.site.register(Classroom)
admin.site.register(TeacherProfile)
admin.site.register(StudentProfile)
admin.site.register(ParentProfile)
admin.site.register(Attendance)
admin.site.register(AcademicYear)
admin.site.register(SMSLog)
