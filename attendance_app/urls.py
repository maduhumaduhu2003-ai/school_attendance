from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.login_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('register-admin/', views.register_admin, name='register_admin'),
    path("forgot-password/", views.forgot_password, name="forgot_password"),
    path('verify-reset/', views.verify_reset, name='verify_reset'),
    # placeholders for dashboards
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('teacher-dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('mark_attendance/', views.mark_attendance, name='mark_attendance'),
    path('view_attendance/', views.view_attendance, name='view_attendance'),
    path('edit_attendance/<int:pk>/',views.edit_attendance, name='edit_attendance'),
    path('delete_attendance/<int:pk>/', views.delete_attendance, name='delete_attendance'),
    
    path('teacher_sms_logs/', views.teacher_sms_logs, name='teacher_sms_logs'),
    path('teacher/sms-logs/delete/<int:sms_id>/', views.delete_sms_log, name='delete_sms_log'),

    path('my_students/', views.my_students, name='my_students'),
    path("student-profile/<int:pk>/", views.student_profile_modal, name="student_profile_modal"),
    path("export-students-excel/", views.export_students_excel, name="export_students_excel"),
    path("export-students-pdf/", views.export_students_pdf, name="export_students_pdf"),
    path('profile/', views.teacher_profile_view, name='teacher_profile_view'),

    path('student-dashboard/', views.login_view, name='student_dashboard'),
    path('parent-dashboard/', views.login_view, name='parent_dashboard'),

    path('logout/', views.logout_view, name='logout'),
    path('register-teacher/', views.register_teacher, name='register_teacher'),
    path('edit_teacher/<int:id>/',views.edit_teacher, name='edit_teacher'),
    path('delete_teacher/<int:id>/',views.delete_teacher, name='delete_teacher'),
    path('delete-teacher/<int:teacher_id>/', views.delete_teacher, name='delete_teacher'),


    path('register_student/', views.register_student, name='register_student'),
    path('students/edit/<int:student_id>/', views.edit_student, name='edit_student'),
    path('students/delete/<int:student_id>/', views.delete_student, name='delete_student'),

    path('manage_classrooms/', views.manage_classrooms, name='manage_classrooms'),
    
    path('academic-years/', views.academic_years, name='academic_years'),
    path('academic-years/add/', views.add_academic_year, name='add_academic_year'),
    path('academic-years/edit/<int:id>/', views.edit_academic_year, name='edit_academic_year'),
    path('academic-years/delete/<int:id>/', views.delete_academic_year, name='delete_academic_year'),
    path('academic-years/generate/', views.generate_academic_year, name='generate_academic_year'),
    path('academic-year-summary/', views.academic_year_summary, name='academic_year_summary'),


   
    path('sms-logs/', views.sms_logs, name='sms_logs'),
   

    path('manage_classrooms/', views.manage_classrooms, name='manage_classrooms'),
    path('edit_classroom/<int:classroom_id>/', views.edit_classroom, name='edit_classroom'),
    path('delete_classroom/<int:classroom_id>/', views.delete_classroom, name='delete_classroom'),
    path('classroom/<int:class_id>/add_stream/', views.add_stream, name='add_stream'),
    path('get-streams/<int:classroom_id>/', views.get_streams, name='get_streams'),
    path('teacher_sms_logs/resend/<int:sms_id>/', views.resend_sms, name='resend_sms'),
    path('admin_profile/', views.admin_profile, name='admin_profile'),
    path('admin_settings/', views.school_settings, name='school_settings'),
    path('reset-password/', views.reset_password, name='reset_password'), 
    path('attendance/', views.attendance_report_cards, name='attendance_report'),
    path('attendance/<int:classroom_id>/', views.view_class_attendance, name='view_class_attendance'),
   

]   


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

