from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.login_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('register-admin/', views.register_admin, name='register_admin'),
    path("forgo-password/", views.forgot_password, name="forgot_password"),
    path('verify-reset/', views.verify_reset, name='verify_reset'),
    
    # ================= DASHBOARDS =================
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('teacher-dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    
    # ================= ATTENDANCE =================
    path('mark_attendance/', views.mark_attendance, name='mark_attendance'),
    path('view_attendance/', views.view_attendance, name='view_attendance'),
    path("attendance/export/pdf/", views.attendance_export_pdf, name="attendance_export_pdf"),
    path("attendance/export/excel/", views.attendance_export_excel, name="attendance_export_excel"),
    path('edit_attendance/<int:pk>/', views.edit_attendance, name='edit_attendance'),
    path('delete_attendance/<int:pk>/', views.delete_attendance, name='delete_attendance'),
    
    # ================= SMS LOGS =================
    path('teacher_sms_logs/', views.teacher_sms_logs, name='teacher_sms_logs'),
    path('sms-logs/', views.sms_logs, name='sms_logs'),
    
    # Teacher SMS URLs
    path('teacher/sms/delete/<int:sms_id>/', views.delete_sms_log, name='delete_sms_log'),
    path('teacher/sms/resend/<int:sms_id>/', views.resend_sms, name='resend_sms'),
    path('teacher/sms/bulk-delete/', views.bulk_delete_sms_logs_teacher, name='bulk_delete_sms_logs_teacher'),
    
    # Admin SMS URLs
    path('sms/delete/<int:sms_id>/', views.delete_sms_log_admin, name='delete_sms_log_admin'),
    path('sms/bulk-delete/', views.bulk_delete_sms_logs, name='bulk_delete_sms_logs'),
    
    # ================= STUDENTS =================
    path('my_students/', views.my_students, name='my_students'),
    path('edit-student-teacher/<int:student_id>/', views.edit_student_teacher, name='edit_student_teacher'),
    path("student-profile/<int:pk>/", views.student_profile_modal, name="student_profile_modal"),
    path("export-students-excel/", views.export_students_excel, name="export_students_excel"),
    path("export-students-pdf/", views.export_students_pdf, name="export_students_pdf"),
    path('register_student_admin/', views.register_student_admin, name='register_student_admin'),
    path('register_student_teacher/', views.register_student_teacher, name='register_student_teacher'),
    path('manage_student/', views.manage_student, name='manage_student'),
    path('students/edit/<int:student_id>/', views.edit_student_page, name='edit_student_page'),
    
    # ===== FIXED: DELETE STUDENT URLs (BOTH PATTERNS) =====
    # Pattern 1: Without prefix (used by template/JS)
    path('delete_student/<int:student_id>/', views.delete_student, name='delete_student'),
    # Pattern 2: With prefix (for compatibility)
    path('students/delete/<int:student_id>/', views.delete_student, name='delete_student_alt'),
    
    # Classroom students URL
    path('classroom/<int:classroom_id>/students/', views.classroom_students, name='classroom_students'),
    
    # ================= TEACHERS =================
    path('manage-teacher/', views.manage_teacher, name='manage_teacher'),
    path('register-teacher/', views.register_teacher, name='register_teacher'),
    path('edit_teacher/<int:id>/', views.edit_teacher, name='edit_teacher'),
    path('delete_teacher/<int:teacher_id>/', views.delete_teacher, name='delete_teacher'),
    
    # ================= CLASSROOMS =================
    path('manage_classrooms/', views.manage_classrooms, name='manage_classrooms'),
    path('edit_classroom/<int:classroom_id>/', views.edit_classroom, name='edit_classroom'),
    path('delete_classroom/<int:classroom_id>/', views.delete_classroom, name='delete_classroom'),
    path('classroom/<int:class_id>/add_stream/', views.add_stream, name='add_stream'),
    path('get-streams/<int:classroom_id>/', views.get_streams, name='get_streams'),
    
    # ================= ACADEMIC YEARS =================
    path('academic-years/', views.academic_years, name='academic_years'),
    path('academic-years/add/', views.add_academic_year, name='add_academic_year'),
    path('academic-years/edit/<int:id>/', views.edit_academic_year, name='edit_academic_year'),
    path('academic-years/delete/<int:id>/', views.delete_academic_year, name='delete_academic_year'),
    path('academic-years/generate/', views.generate_academic_year, name='generate_academic_year'),
    path('academic-year-summary/', views.academic_year_summary, name='academic_year_summary'),
    
    # ================= REPORTS =================
    path('attendance/', views.attendance_report_cards, name='attendance_report'),
    path('attendance/<int:classroom_id>/', views.view_class_attendance, name='view_class_attendance'),
    
    # ================= PROFILE & SETTINGS =================
    path('profile/', views.teacher_profile_view, name='teacher_profile_view'),
    path('admin_profile/', views.admin_profile, name='admin_profile'),
    path('admin_settings/', views.school_settings, name='school_settings'),
    
    # ================= AUTH & OTHER =================
    path('logout/', views.logout_view, name='logout'),
    path('reset-password/', views.reset_password, name='reset_password'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)